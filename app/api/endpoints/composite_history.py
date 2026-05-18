from __future__ import annotations

import logging

from fastapi import APIRouter, Query, Request

from app.services.composite_history_service import CompositeHistoryPoint, CompositeHistoryService
from app.utils.ticker_sanitizer import sanitize_ticker

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get(
    "/composite-history/{ticker}",
    response_model=list[CompositeHistoryPoint],
    summary="Historique du composite_score pour un ticker",
    description=(
        "Retourne l'évolution temporelle du composite_score d'un ticker, "
        "triée par date croissante. Limite configurable (1-365, défaut 90)."
    ),
)
async def get_composite_history(
    ticker: str,
    request: Request,
    limit: int = Query(default=90, ge=1, le=365),
) -> list[CompositeHistoryPoint]:
    validated = sanitize_ticker(ticker)
    service: CompositeHistoryService = request.app.state.composite_history_service
    return await service.get_history(ticker=validated, limit=limit)
