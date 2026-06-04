from __future__ import annotations

import json
import logging
import uuid
from datetime import datetime, timezone

import asyncpg
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import Response

from app.services.composite_history_service import CompositeHistoryService
from app.services.pdf_report_service import PdfReportService
from app.services.ratios_recon import (
    extract_earnings_ratios,
    extract_graham_ratios,
    extract_valuation_ratios,
    reconstruct_ratios_traces,
)
from app.utils.error_sanitization import sanitized_http_500
from app.utils.ticker_sanitizer import sanitize_ticker

logger = logging.getLogger(__name__)

router = APIRouter(tags=["ticker-report"])

_ROW_COLUMNS = (
    "id, ticker, workflow_name, skills_used, input_data, result, cost_usd, created_at"
)


@router.get(
    "/ticker-report/{ticker}",
    summary="Rapport PDF multi-pages par ticker",
    response_class=Response,
)
async def get_ticker_report(
    request: Request,
    ticker: str,
    days: int = 90,
    analysis_id: str | None = None,
) -> Response:
    """
    Génère un rapport PDF incluant l'historique composite_score et les résultats skills.

    Sans `analysis_id` : dernière analyse + historique 90 j (404 si aucune donnée composite).
    Avec `analysis_id` : cible une analyse précise (404 si absente ou ticker différent) et
    enrichit le PDF (verdicts skill par skill, ratios clés, annotation, score ESG).
    Paramètre `days` : fenêtre historique (défaut 90, max 365).
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

    db_pool: asyncpg.Pool | None = getattr(request.app.state, "db_pool", None)

    last_analysis = None
    ratios = None
    earnings_ratios = None
    valuation_ratios = None
    row = None

    if analysis_id is not None:
        # Ciblage d'une analyse précise — l'analyse fait foi, l'historique composite est optionnel.
        if db_pool is None:
            raise HTTPException(status_code=503, detail="db_pool non disponible")
        row = await _fetch_analysis_by_id(db_pool, analysis_id, sanitized)
        if row is None:
            raise HTTPException(
                status_code=404,
                detail=f"Analyse introuvable pour id={analysis_id} et ticker={sanitized}",
            )
        history = await composite_history_service.get_history(sanitized, limit=days)
    else:
        history = await composite_history_service.get_history(sanitized, limit=days)
        if not history:
            raise HTTPException(
                status_code=404,
                detail=f"Aucune donnée disponible pour le ticker : {sanitized}",
            )
        if db_pool is not None:
            try:
                row = await db_pool.fetchrow(
                    f"""
                    SELECT {_ROW_COLUMNS}
                    FROM analysis_history
                    WHERE ticker = $1
                    ORDER BY created_at DESC
                    LIMIT 1
                    """,
                    sanitized,
                )
            except Exception:
                logger.exception(
                    "Impossible de récupérer la dernière analyse pour %s — PDF sans skills",
                    sanitized,
                )

    if row is not None:
        last_analysis = _reconstruct_analyze_response(row)
        ratios = _extract_ratios(row)
        earnings_ratios = _extract_earnings_ratios(row)
        valuation_ratios = _extract_valuation_ratios(row)

    annotation_note: str | None = None
    esg_score: float | None = None
    if last_analysis is not None:
        annotation_note = await _fetch_annotation(request, last_analysis.analysis_id)
        esg_score = await _resolve_esg_score(request, last_analysis, sanitized)

    try:
        pdf_bytes = await pdf_service.generate_ticker_report(
            ticker=sanitized,
            history=history,
            last_analysis=last_analysis,
            ratios=ratios,
            earnings_ratios=earnings_ratios,
            valuation_ratios=valuation_ratios,
            annotation=annotation_note,
            esg_score=esg_score,
        )
    except Exception as exc:
        raise sanitized_http_500(
            exc, logger, f"Erreur lors de la génération du rapport PDF pour {sanitized}"
        ) from exc

    date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    filename = f"{sanitized}-report-{date_str}.pdf"

    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


async def _fetch_analysis_by_id(
    db_pool: asyncpg.Pool, analysis_id: str, ticker: str
) -> asyncpg.Record | None:
    """Charge la ligne analysis_history ciblée ; None si id mal formé, absent ou ticker différent."""
    try:
        uuid.UUID(analysis_id)
    except (ValueError, TypeError):
        return None
    return await db_pool.fetchrow(
        f"""
        SELECT {_ROW_COLUMNS}
        FROM analysis_history
        WHERE id = $1::uuid AND ticker = $2
        """,
        analysis_id,
        ticker,
    )


async def _fetch_annotation(request: Request, analysis_id: str) -> str | None:
    """Retourne la note d'annotation de l'analyse, ou None si absente/indisponible."""
    service = getattr(request.app.state, "annotation_service", None)
    if service is None:
        return None
    try:
        annotation = await service.get(analysis_id)
    except Exception:
        logger.warning("Échec récupération annotation pour %s", analysis_id, exc_info=True)
        return None
    return annotation.note if annotation is not None else None


async def _resolve_esg_score(
    request: Request, last_analysis: "AnalyzeResponse", ticker: str
) -> float | None:
    """Score ESG depuis le result de l'analyse, sinon dernier score persisté (esg_score_history)."""
    if last_analysis.esg is not None:
        return float(last_analysis.esg.esg_score)
    service = getattr(request.app.state, "esg_history_service", None)
    if service is None:
        return None
    try:
        points = await service.get_history(ticker, limit=1)
    except Exception:
        logger.warning("Échec récupération esg_score_history pour %s", ticker, exc_info=True)
        return None
    return points[0].score if points else None


# Extraction des ratios depuis input_data : source partagée avec /report (ratios_recon).
# Aliases privés conservés pour les imports de tests existants.
_extract_ratios = extract_graham_ratios
_extract_earnings_ratios = extract_earnings_ratios
_extract_valuation_ratios = extract_valuation_ratios


# Mapping clé du JSONB result → (champ AnalyzeResponse, classe Pydantic du skill)
def _result_skill_map() -> list[tuple[str, str, type]]:
    from app.skills.tier2.buffett_quality.schemas import BuffettQualityOutput
    from app.skills.tier2.canadian_tax.schemas import CanadianTaxOutput
    from app.skills.tier2.damodaran_narrative.schemas import DamodararOutput
    from app.skills.tier2.dorsey_moat.schemas import DorseyMoatOutput
    from app.skills.tier2.earnings_quality.schemas import EarningsQualityOutput
    from app.skills.tier2.esg_simplified.schemas import EsgOutput
    from app.skills.tier2.fisher_scuttlebutt.schemas import FisherOutput
    from app.skills.tier2.graham_analysis.schemas import GrahamAnalysisOutput
    from app.skills.tier2.greenblatt.schemas import GreenblattOutput
    from app.skills.tier2.klarman_margin.schemas import KlarmanOutput
    from app.skills.tier2.lynch_categories.schemas import LynchOutput
    from app.skills.tier2.marks_cycles.schemas import MarksOutput
    from app.skills.tier2.munger_mental.schemas import MungerOutput
    from app.skills.tier2.pabrai_dhandho.schemas import PabraiOutput
    from app.skills.tier2.stock_valuation.schemas import StockValuationOutput
    from app.skills.tier2.thesis_builder.schemas import ThesisBuilderOutput

    return [
        ("graham", "graham", GrahamAnalysisOutput),
        ("earnings_quality", "earnings_quality", EarningsQualityOutput),
        ("dorsey_moat", "dorsey", DorseyMoatOutput),
        ("buffett_quality", "buffett", BuffettQualityOutput),
        ("stock_valuation", "valuation", StockValuationOutput),
        ("investment_thesis_builder", "thesis", ThesisBuilderOutput),
        ("munger_mental_models", "munger", MungerOutput),
        ("canadian_tax_considerations", "canadian_tax", CanadianTaxOutput),
        ("lynch_categories", "lynch", LynchOutput),
        ("fisher_scuttlebutt", "fisher", FisherOutput),
        ("klarman_margin", "klarman", KlarmanOutput),
        ("greenblatt_magic_formula", "greenblatt", GreenblattOutput),
        ("damodaran_narrative", "damodaran", DamodararOutput),
        ("marks_cycles_risk", "marks", MarksOutput),
        ("pabrai_dhandho", "pabrai", PabraiOutput),
        ("esg_simplified", "esg", EsgOutput),
    ]


def _reconstruct_analyze_response(row) -> "AnalyzeResponse | None":
    """Reconstruit une AnalyzeResponse depuis analysis_history en parsant tous les skills présents.

    Un skill dont le JSON ne valide pas est ignoré (pas d'échec global). Retourne None
    uniquement si le result est illisible.
    """
    from app.orchestrator.core import AnalyzeResponse

    result_str = row["result"]
    try:
        result: dict = (
            json.loads(result_str) if isinstance(result_str, str) else dict(result_str)
        )
    except (ValueError, TypeError):
        logger.warning("result illisible dans analysis_history — PDF sans skills")
        return None

    skills_used_raw = row["skills_used"]
    skills_used: list[str] = (
        json.loads(skills_used_raw)
        if isinstance(skills_used_raw, str)
        else list(skills_used_raw)
    )

    parsed_fields: dict = {}
    for result_key, field_name, model_cls in _result_skill_map():
        data = result.get(result_key)
        if data is None:
            continue
        try:
            parsed_fields[field_name] = model_cls.model_validate(data)
        except Exception:
            logger.warning(
                "Skill %s ignoré (validation échouée) lors de la reconstruction PDF", result_key
            )

    created_at = row["created_at"]
    created_at_str = (
        created_at.isoformat() if isinstance(created_at, datetime) else str(created_at)
    )

    return AnalyzeResponse(
        analysis_id=str(row["id"]),
        ticker=row["ticker"],
        workflow=row["workflow_name"],
        skills_applied=skills_used,
        cost_usd=float(row["cost_usd"]),
        created_at=created_at_str,
        **reconstruct_ratios_traces(row),
        **parsed_fields,
    )
