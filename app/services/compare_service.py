from __future__ import annotations

import logging
from typing import Any

import asyncpg
from pydantic import BaseModel

from app.utils.ticker_sanitizer import sanitize_ticker

logger = logging.getLogger(__name__)


class TickerComparison(BaseModel):
    ticker: str
    analysis_id: str | None = None
    graham_verdict: str | None = None
    graham_score: int | None = None
    buffett_verdict: str | None = None
    dorsey_moat_type: str | None = None
    composite_score: float | None = None
    composite_label: str | None = None
    created_at: str | None = None


class CompareResponse(BaseModel):
    tickers: list[str]
    comparisons: list[TickerComparison]


class CompareService:
    """Récupère et compare les dernières analyses depuis analysis_history pour plusieurs tickers."""

    def __init__(self, db_pool: asyncpg.Pool) -> None:
        self._db = db_pool

    async def compare(self, tickers: list[str]) -> CompareResponse:
        """Retourne la dernière analyse disponible pour chaque ticker — aucun appel Claude."""
        validated = [sanitize_ticker(t) for t in tickers]

        rows = await self._db.fetch(
            """
            SELECT DISTINCT ON (ah.ticker)
                ah.id::text         AS analysis_id,
                ah.ticker,
                ah.result,
                ah.created_at,
                csh.score           AS composite_score,
                csh.label           AS composite_label
            FROM analysis_history ah
            LEFT JOIN LATERAL (
                SELECT score, label
                FROM composite_score_history
                WHERE ticker = ah.ticker
                ORDER BY recorded_at DESC
                LIMIT 1
            ) csh ON true
            WHERE ah.ticker = ANY($1::text[])
            ORDER BY ah.ticker, ah.created_at DESC
            """,
            validated,
        )

        rows_by_ticker: dict[str, Any] = {row["ticker"]: row for row in rows}

        comparisons: list[TickerComparison] = []
        for ticker in validated:
            row = rows_by_ticker.get(ticker)
            if row is None:
                comparisons.append(TickerComparison(ticker=ticker))
                continue

            result: dict = row["result"] or {}
            graham = result.get("graham") or {}
            buffett = result.get("buffett_quality") or {}
            dorsey = result.get("dorsey_moat") or {}

            graham_score_raw = graham.get("defensive_score")
            comparisons.append(
                TickerComparison(
                    ticker=ticker,
                    analysis_id=row["analysis_id"],
                    graham_verdict=graham.get("verdict"),
                    graham_score=int(graham_score_raw) if graham_score_raw is not None else None,
                    buffett_verdict=buffett.get("verdict"),
                    dorsey_moat_type=dorsey.get("moat_type"),
                    composite_score=float(row["composite_score"]) if row["composite_score"] is not None else None,
                    composite_label=row["composite_label"],
                    created_at=row["created_at"].isoformat() if row["created_at"] else None,
                )
            )

        return CompareResponse(tickers=validated, comparisons=comparisons)
