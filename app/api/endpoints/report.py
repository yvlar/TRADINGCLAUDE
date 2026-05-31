from __future__ import annotations

import json
import logging
import os
from datetime import datetime, timezone

import asyncpg
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import Response

from app.orchestrator.core import (
    AnalyzeRequest,
    AnalyzeResponse,
    Orchestrator,
    _graham_ratios_trace,
)
from app.services.report import ReportService
from app.utils.error_sanitization import sanitized_http_500

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/report", tags=["report"])

_REPORT_OUTPUT_DIR = os.getenv("REPORT_OUTPUT_DIR", "reports")


def _get_report_service() -> ReportService:
    return ReportService(output_dir=_REPORT_OUTPUT_DIR)


def _pdf_response(pdf_bytes: bytes, ticker: str) -> Response:
    date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    filename = f"{ticker}-{date_str}.pdf"
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.post(
    "",
    summary="Déclenche une analyse et retourne le rapport PDF",
    response_class=Response,
)
async def post_report(request: Request, body: AnalyzeRequest) -> Response:
    """
    Exécute le même workflow que POST /analyze, puis génère un PDF structuré.
    Retourne le PDF en streaming (application/pdf).
    """
    orchestrator: Orchestrator = request.app.state.orchestrator
    cache = getattr(request.app.state, "analysis_cache", None)
    observability = getattr(request.app.state, "observability", None)

    try:
        analysis = await orchestrator.run_company_analysis(
            body, cache=cache, observability=observability
        )
    except Exception as exc:
        raise sanitized_http_500(
            exc, logger, f"Erreur lors de l'analyse pour le rapport PDF — ticker {body.ticker}"
        ) from exc

    try:
        report_service = _get_report_service()
        pdf_bytes = report_service.generate_pdf(analysis)
    except Exception as exc:
        raise sanitized_http_500(
            exc, logger, f"Erreur lors de la génération du PDF pour {body.ticker}"
        ) from exc

    return _pdf_response(pdf_bytes, body.ticker)


@router.get(
    "/{analysis_id}",
    summary="Régénère le rapport PDF depuis l'historique",
    response_class=Response,
)
async def get_report(request: Request, analysis_id: str) -> Response:
    """
    Récupère une analyse depuis analysis_history par son UUID et génère le PDF correspondant.
    Retourne 404 si l'analysis_id est inconnu.
    """
    db_pool: asyncpg.Pool = request.app.state.db_pool

    try:
        row = await db_pool.fetchrow(
            """
            SELECT id, ticker, workflow_name, skills_used, input_data, result, cost_usd, created_at
            FROM analysis_history
            WHERE id = $1::uuid
            """,
            analysis_id,
        )
    except Exception as exc:
        raise sanitized_http_500(
            exc, logger, f"Erreur DB lors de la récupération de l'analyse {analysis_id}"
        ) from exc

    if row is None:
        raise HTTPException(status_code=404, detail=f"Analyse introuvable : {analysis_id}")

    try:
        analysis = _reconstruct_response(row)
    except Exception as exc:
        raise sanitized_http_500(
            exc, logger, f"Erreur lors de la reconstruction de l'analyse {analysis_id}"
        ) from exc

    try:
        report_service = _get_report_service()
        pdf_bytes = report_service.generate_pdf(analysis)
    except Exception as exc:
        raise sanitized_http_500(
            exc, logger, f"Erreur lors de la génération du PDF pour {analysis_id}"
        ) from exc

    return _pdf_response(pdf_bytes, row["ticker"])


def _reconstruct_ratios_trace(row) -> tuple[str | None, str | None]:
    """Reconstruit la traçabilité (date ISO, source) des ratios Graham depuis input_data persisté."""
    from app.skills.tier2.graham_analysis.schemas import GrahamRatios

    try:
        raw = row["input_data"]
    except (KeyError, IndexError):
        return None, None
    if raw is None:
        return None, None
    try:
        data: dict = json.loads(raw) if isinstance(raw, str) else dict(raw)
    except (ValueError, TypeError):
        return None, None
    if not data:
        return None, None
    try:
        ratios = GrahamRatios.model_validate(data)
    except Exception:
        return None, None
    return _graham_ratios_trace(ratios)


def _reconstruct_response(row) -> AnalyzeResponse:
    """
    Reconstruit une AnalyzeResponse minimale depuis une ligne analysis_history.
    Seul le champ graham est obligatoire — les autres skills sont optionnels.
    """
    result_str = row["result"]
    result: dict = json.loads(result_str) if isinstance(result_str, str) else dict(result_str)
    skills_used: list[str] = json.loads(row["skills_used"]) if isinstance(row["skills_used"], str) else list(row["skills_used"])

    created_at = row["created_at"]
    created_at_str = created_at.isoformat() if isinstance(created_at, datetime) else str(created_at)

    # Import ici pour éviter les imports circulaires au niveau module
    from app.skills.tier2.buffett_quality.schemas import BuffettQualityOutput
    from app.skills.tier2.canadian_tax.schemas import CanadianTaxOutput
    from app.skills.tier2.damodaran_narrative.schemas import DamodararOutput
    from app.skills.tier2.dorsey_moat.schemas import DorseyMoatOutput
    from app.skills.tier2.earnings_quality.schemas import EarningsQualityOutput
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

    def _try_parse(model_cls, key: str):
        data = result.get(key)
        if data is None:
            return None
        try:
            return model_cls.model_validate(data)
        except Exception:
            logger.warning("Impossible de parser %s depuis result[%s]", model_cls.__name__, key)
            return None

    graham_data = result.get("graham")
    if graham_data is None:
        raise ValueError("Clé 'graham' absente dans result — analyse corrompue")
    graham = GrahamAnalysisOutput.model_validate(graham_data)

    ratios_fetched_at, ratios_source = _reconstruct_ratios_trace(row)

    return AnalyzeResponse(
        analysis_id=str(row["id"]),
        ticker=row["ticker"],
        workflow=row["workflow_name"],
        skills_applied=skills_used,
        graham=graham,
        ratios_fetched_at=ratios_fetched_at,
        ratios_source=ratios_source,
        earnings_quality=_try_parse(EarningsQualityOutput, "earnings_quality"),
        dorsey=_try_parse(DorseyMoatOutput, "dorsey_moat"),
        buffett=_try_parse(BuffettQualityOutput, "buffett_quality"),
        valuation=_try_parse(StockValuationOutput, "stock_valuation"),
        thesis=_try_parse(ThesisBuilderOutput, "investment_thesis_builder"),
        munger=_try_parse(MungerOutput, "munger_mental_models"),
        canadian_tax=_try_parse(CanadianTaxOutput, "canadian_tax_considerations"),
        lynch=_try_parse(LynchOutput, "lynch_categories"),
        fisher=_try_parse(FisherOutput, "fisher_scuttlebutt"),
        klarman=_try_parse(KlarmanOutput, "klarman_margin"),
        greenblatt=_try_parse(GreenblattOutput, "greenblatt_magic_formula"),
        damodaran=_try_parse(DamodararOutput, "damodaran_narrative"),
        marks=_try_parse(MarksOutput, "marks_cycles_risk"),
        pabrai=_try_parse(PabraiOutput, "pabrai_dhandho"),
        cost_usd=float(row["cost_usd"]),
        created_at=created_at_str,
    )
