"""Endpoint Sprint 89 — GET /esg-history/{ticker}.

Retourne {ticker, points: [...]} avec les N derniers scores ESG persistes
dans esg_score_history. 404 si aucun point enregistre pour ce ticker.
"""
from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException, Query, Request
from pydantic import BaseModel

from app.services.esg_history_service import EsgHistoryPoint, EsgHistoryService
from app.utils.ticker_sanitizer import sanitize_ticker

logger = logging.getLogger(__name__)

router = APIRouter()


class EsgHistoryResponse(BaseModel):
    """Reponse de GET /esg-history/{ticker}."""

    ticker: str
    points: list[EsgHistoryPoint]


@router.get(
    "/esg-history/{ticker}",
    response_model=EsgHistoryResponse,
    summary="Historique des scores ESG pour un ticker",
    description=(
        "Retourne l'evolution temporelle du score ESG d'un ticker, "
        "triee par date decroissante. Limite configurable (1-365, defaut 100). "
        "404 si aucun point enregistre."
    ),
)
async def get_esg_history(
    ticker: str,
    request: Request,
    limit: int = Query(default=100, ge=1, le=365),
) -> EsgHistoryResponse:
    validated = sanitize_ticker(ticker)
    service: EsgHistoryService = request.app.state.esg_history_service
    points = await service.get_history(ticker=validated, limit=limit)
    if not points:
        raise HTTPException(
            status_code=404,
            detail=f"Aucun historique ESG pour {validated}",
        )
    return EsgHistoryResponse(ticker=validated, points=points)
