"""Endpoint GET /performance/{ticker} — rendement rétrospectif depuis le cours enregistré."""
from __future__ import annotations

import json
import logging

from fastapi import APIRouter, Request
from pydantic import BaseModel

from app.utils.ticker_sanitizer import sanitize_ticker

logger = logging.getLogger(__name__)
router = APIRouter()


class PerformanceEntry(BaseModel):
    analysis_id: str
    created_at: str
    price_at_analysis: float | None
    price_current: float | None
    rendement_pct: float | None
    composite_score: float | None
    workflow: str


class PerformanceResponse(BaseModel):
    ticker: str
    entries: list[PerformanceEntry]


def _compute_rendement(price_at: float | None, price_current: float | None) -> float | None:
    """Calcule le rendement en % depuis price_at vers price_current. None si l'un des cours est absent."""
    if price_at is None or price_current is None or price_at == 0.0:
        return None
    return round((price_current - price_at) / price_at * 100, 2)


def _extract_composite_score(result_json: str) -> float | None:
    """Extrait composite_score.score depuis le JSONB result, ou None si absent."""
    try:
        data = json.loads(result_json)
        cs = data.get("composite_score")
        if isinstance(cs, dict):
            val = cs.get("score")
            return float(val) if val is not None else None
    except Exception:
        pass
    return None


@router.get(
    "/performance/{ticker}",
    response_model=PerformanceResponse,
    summary="Rendement rétrospectif des analyses pour un ticker",
)
async def get_performance(ticker: str, request: Request) -> PerformanceResponse:
    """
    Retourne le rendement rétrospectif entre le cours enregistré à l'analyse
    et le cours actuel (Yahoo Finance) pour chaque analyse historique du ticker.
    rendement_pct = None si price_at_analysis ou price_current est absent.
    """
    ticker = sanitize_ticker(ticker)

    db_pool = request.app.state.db_pool
    yahoo_extractor = request.app.state.yahoo_extractor

    rows = await db_pool.fetch(
        """
        SELECT id, created_at, price_at_analysis, result, workflow_name
        FROM analysis_history
        WHERE ticker = $1
        ORDER BY created_at DESC
        """,
        ticker,
    )

    price_current = await yahoo_extractor.get_price(ticker)

    entries: list[PerformanceEntry] = []
    for row in rows:
        price_at = row["price_at_analysis"]
        entries.append(
            PerformanceEntry(
                analysis_id=str(row["id"]),
                created_at=row["created_at"].isoformat(),
                price_at_analysis=price_at,
                price_current=price_current,
                rendement_pct=_compute_rendement(price_at, price_current),
                composite_score=_extract_composite_score(row["result"]),
                workflow=row["workflow_name"],
            )
        )

    return PerformanceResponse(ticker=ticker, entries=entries)
