from __future__ import annotations

import json
import logging
from datetime import datetime, timezone

import asyncpg
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import Response

from app.services.composite_history_service import CompositeHistoryService
from app.services.pdf_report_service import PdfReportService
from app.utils.ticker_sanitizer import sanitize_ticker

logger = logging.getLogger(__name__)

router = APIRouter(tags=["ticker-report"])


@router.get(
    "/ticker-report/{ticker}",
    summary="Rapport PDF multi-pages par ticker",
    response_class=Response,
)
async def get_ticker_report(
    request: Request,
    ticker: str,
    days: int = 90,
) -> Response:
    """
    Génère un rapport PDF incluant l'historique composite_score et les résultats skills.
    Retourne 404 si aucune donnée composite disponible pour le ticker.
    Paramètre optionnel : days (fenêtre historique, défaut 90, max 365).
    """
    if days < 1 or days > 365:
        raise HTTPException(status_code=422, detail="days doit être entre 1 et 365")

    try:
        sanitized = sanitize_ticker(ticker)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    composite_history_service: CompositeHistoryService | None = getattr(
        request.app.state, "composite_history_service", None
    )
    if composite_history_service is None:
        raise HTTPException(status_code=503, detail="CompositeHistoryService non disponible")

    pdf_service: PdfReportService | None = getattr(
        request.app.state, "pdf_report_service", None
    )
    if pdf_service is None:
        raise HTTPException(status_code=503, detail="PdfReportService non disponible")

    history = await composite_history_service.get_history(sanitized, limit=days)
    if not history:
        raise HTTPException(
            status_code=404,
            detail=f"Aucune donnée disponible pour le ticker : {sanitized}",
        )

    # Dernière analyse depuis analysis_history (optionnel — PDF reste valide sans elle)
    last_analysis = None
    db_pool: asyncpg.Pool | None = getattr(request.app.state, "db_pool", None)
    if db_pool is not None:
        try:
            row = await db_pool.fetchrow(
                """
                SELECT id, ticker, workflow_name, skills_used, result, cost_usd, created_at
                FROM analysis_history
                WHERE ticker = $1
                ORDER BY created_at DESC
                LIMIT 1
                """,
                sanitized,
            )
            if row is not None:
                last_analysis = _reconstruct_analyze_response(row)
        except Exception:
            logger.exception(
                "Impossible de récupérer la dernière analyse pour %s — PDF sans skills",
                sanitized,
            )

    try:
        pdf_bytes = await pdf_service.generate_ticker_report(
            ticker=sanitized,
            history=history,
            last_analysis=last_analysis,
        )
    except Exception as exc:
        logger.exception("Erreur lors de la génération du rapport PDF pour %s", sanitized)
        raise HTTPException(
            status_code=500, detail=f"Erreur génération PDF : {exc}"
        ) from exc

    date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    filename = f"{sanitized}-report-{date_str}.pdf"

    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


def _reconstruct_analyze_response(row) -> "AnalyzeResponse | None":
    """Reconstruit une AnalyzeResponse minimale (Graham + Buffett + Dorsey) depuis analysis_history."""
    from app.orchestrator.core import AnalyzeResponse
    from app.skills.tier2.buffett_quality.schemas import BuffettQualityOutput
    from app.skills.tier2.dorsey_moat.schemas import DorseyMoatOutput
    from app.skills.tier2.graham_analysis.schemas import GrahamAnalysisOutput

    result_str = row["result"]
    result: dict = (
        json.loads(result_str) if isinstance(result_str, str) else dict(result_str)
    )
    skills_used: list[str] = (
        json.loads(row["skills_used"])
        if isinstance(row["skills_used"], str)
        else list(row["skills_used"])
    )

    graham_data = result.get("graham")
    if graham_data is None:
        return None

    try:
        graham = GrahamAnalysisOutput.model_validate(graham_data)
    except Exception:
        logger.warning("Impossible de parser GrahamAnalysisOutput depuis analysis_history")
        return None

    def _try_parse(model_cls, key: str):
        data = result.get(key)
        if data is None:
            return None
        try:
            return model_cls.model_validate(data)
        except Exception:
            return None

    created_at = row["created_at"]
    created_at_str = (
        created_at.isoformat() if isinstance(created_at, datetime) else str(created_at)
    )

    return AnalyzeResponse(
        analysis_id=str(row["id"]),
        ticker=row["ticker"],
        workflow=row["workflow_name"],
        skills_applied=skills_used,
        graham=graham,
        buffett=_try_parse(BuffettQualityOutput, "buffett_quality"),
        dorsey=_try_parse(DorseyMoatOutput, "dorsey_moat"),
        cost_usd=float(row["cost_usd"]),
        created_at=created_at_str,
    )
