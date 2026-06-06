"""Endpoint SSE POST /analyze-stream — résultats skill par skill en temps réel."""
from __future__ import annotations

import json
import logging
from collections.abc import AsyncGenerator

from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse

from app.orchestrator.core import AnalyzeRequest, Orchestrator
from app.services.quota_service import QuotaExceededError, QuotaService
from app.utils.error_sanitization import log_internal_error
from app.utils.quota_http import quota_exceeded_http

logger = logging.getLogger(__name__)

router = APIRouter()


async def _sse_generator(
    body: AnalyzeRequest,
    orchestrator: Orchestrator,
    cache,
    observability,
    composite_history_service=None,
    esg_history_service=None,
    quota_service: QuotaService | None = None,
) -> AsyncGenerator[str, None]:
    """Convertit les events de stream_company_analysis au format SSE texte."""
    consumed = False
    try:
        async for event in orchestrator.stream_company_analysis(
            body, cache=cache, observability=observability,
            composite_history_service=composite_history_service,
            esg_history_service=esg_history_service,
        ):
            event_type = event["event"]
            # Le quota n'est consommé que par une analyse fraîche (event `complete`, cost_usd>0).
            # Un `cached` ne consomme rien (cohérent avec /analyze et le metering Sprint 166).
            if event_type == "complete" and event["data"].get("cost_usd", 0) > 0:
                consumed = True
            data = json.dumps(event["data"], ensure_ascii=False, default=str)
            yield f"event: {event_type}\ndata: {data}\n\n"
        if quota_service is not None and consumed:
            await quota_service.increment()
    except Exception as exc:
        # body générique : str(exc) ne sort jamais dans le flux SSE (fuite potentielle)
        correlation_id = log_internal_error(exc, logger, f"Erreur SSE pour {body.ticker}")
        error_data = json.dumps(
            {"message": "Erreur interne", "correlation_id": correlation_id}, ensure_ascii=False
        )
        yield f"event: error\ndata: {error_data}\n\n"


@router.post(
    "/analyze-stream",
    summary="Analyse SSE — résultats skill par skill",
    description=(
        "Même payload que POST /analyze. "
        "Retourne un flux text/event-stream : un event `skill_start` + `skill_result` "
        "par skill exécuté, puis un event `complete` avec l'AnalyzeResponse complète. "
        "Si l'analyse est en cache : un unique event `cached` avec la réponse complète."
    ),
)
async def analyze_stream(request: Request, body: AnalyzeRequest) -> StreamingResponse:
    orchestrator: Orchestrator = request.app.state.orchestrator
    cache = getattr(request.app.state, "analysis_cache", None)
    observability = getattr(request.app.state, "observability", None)
    composite_history_service = getattr(request.app.state, "composite_history_service", None)
    esg_history_service = getattr(request.app.state, "esg_history_service", None)
    quota_service: QuotaService | None = getattr(request.app.state, "quota_service", None)

    # Borne dure vérifiée AVANT d'ouvrir le flux : un dépassement renvoie un vrai 429 HTTP
    # (impossible une fois le StreamingResponse 200 commencé).
    if quota_service is not None:
        try:
            await quota_service.check()
        except QuotaExceededError as err:
            raise quota_exceeded_http(err) from err
    return StreamingResponse(
        _sse_generator(
            body, orchestrator, cache, observability,
            composite_history_service, esg_history_service,
            quota_service=quota_service,
        ),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
        },
    )
