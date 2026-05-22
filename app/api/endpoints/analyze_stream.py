"""Endpoint SSE POST /analyze-stream — résultats skill par skill en temps réel."""
from __future__ import annotations

import json
import logging
from collections.abc import AsyncGenerator

from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse

from app.orchestrator.core import AnalyzeRequest, Orchestrator

logger = logging.getLogger(__name__)

router = APIRouter()


async def _sse_generator(
    body: AnalyzeRequest,
    orchestrator: Orchestrator,
    cache,
    observability,
    composite_history_service=None,
    esg_history_service=None,
) -> AsyncGenerator[str, None]:
    """Convertit les events de stream_company_analysis au format SSE texte."""
    try:
        async for event in orchestrator.stream_company_analysis(
            body, cache=cache, observability=observability,
            composite_history_service=composite_history_service,
            esg_history_service=esg_history_service,
        ):
            event_type = event["event"]
            data = json.dumps(event["data"], ensure_ascii=False, default=str)
            yield f"event: {event_type}\ndata: {data}\n\n"
    except Exception as exc:
        logger.exception("Erreur SSE pour %s", body.ticker)
        error_data = json.dumps({"message": str(exc)}, ensure_ascii=False)
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
    return StreamingResponse(
        _sse_generator(
            body, orchestrator, cache, observability,
            composite_history_service, esg_history_service,
        ),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
        },
    )
