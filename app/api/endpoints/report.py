from __future__ import annotations

import logging
import os
from datetime import datetime, timezone

import asyncpg
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import Response

from app.api.endpoints.auth import _get_current_user
from app.db.tenant_context import tenant_scope
from app.orchestrator.core import (
    AnalyzeRequest,
    AnalyzeResponse,
    Orchestrator,
)
from app.services.analysis_reconstruction import reconstruct
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
    Retourne le PDF en streaming (application/pdf). 401 si non authentifié.
    """
    user = await _get_current_user(request)
    orchestrator: Orchestrator = request.app.state.orchestrator
    cache = getattr(request.app.state, "analysis_cache", None)
    observability = getattr(request.app.state, "observability", None)

    try:
        # Analyse exécutée sous le tenant du demandeur : metering + écritures (RLS)
        # ciblent son tenant, jamais le tenant legacy (E4-S11). Explicite à dessein —
        # source unique du tenant hors `TenantContextMiddleware` (test harness bare-app
        # sans middleware) ; ne pas retirer même si la requête le pose déjà en prod.
        with tenant_scope(user.get("tenant_id")):
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
    Retourne 401 si non authentifié, 404 si l'analysis_id est inconnu ou appartient à un autre tenant.
    """
    user = await _get_current_user(request)
    db_pool: asyncpg.Pool = request.app.state.db_pool

    try:
        # Lecture sous le tenant du demandeur : la RLS masque les analyses des autres
        # tenants → un rapport ne reflète jamais les données d'un tiers (E4-S11).
        # Explicite à dessein (cf. post_report) : ne pas retirer comme « redondant ».
        with tenant_scope(user.get("tenant_id")):
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


def _reconstruct_response(row) -> AnalyzeResponse:
    """
    Reconstruit une AnalyzeResponse depuis une ligne analysis_history.
    Seul le champ graham est obligatoire (ValueError sinon) — les autres skills sont optionnels.
    """
    response = reconstruct(row, require_graham=True)
    # require_graham=True ne retourne jamais None (result illisible propage) — invariant.
    assert response is not None
    return response
