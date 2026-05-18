from __future__ import annotations

import logging
from datetime import datetime

import asyncpg
from pydantic import BaseModel

from app.utils.ticker_sanitizer import sanitize_ticker

logger = logging.getLogger(__name__)


class CompositeHistoryPoint(BaseModel):
    id: str
    ticker: str
    score: float
    label: str
    workflow: str
    recorded_at: datetime


class CompositeHistoryService:
    """CRUD sur la table composite_score_history."""

    def __init__(self, db_pool: asyncpg.Pool) -> None:
        self._db = db_pool

    async def record(
        self, ticker: str, score: float, label: str, workflow: str
    ) -> None:
        """Insère un nouveau point d'historique du composite_score."""
        validated = sanitize_ticker(ticker)
        await self._db.execute(
            """
            INSERT INTO composite_score_history (ticker, score, label, workflow)
            VALUES ($1, $2, $3, $4)
            """,
            validated,
            score,
            label,
            workflow,
        )
        logger.debug("composite_score enregistré : %s score=%.1f label=%s", validated, score, label)

    async def get_recent(
        self, ticker: str, max_age_hours: int = 24
    ) -> CompositeHistoryPoint | None:
        """Retourne le dernier composite_score si récent (< max_age_hours), sinon None."""
        validated = sanitize_ticker(ticker)
        row = await self._db.fetchrow(
            """
            SELECT id, ticker, score, label, workflow, recorded_at
            FROM composite_score_history
            WHERE ticker = $1 AND recorded_at > NOW() - ($2 || ' hours')::interval
            ORDER BY recorded_at DESC
            LIMIT 1
            """,
            validated,
            str(max_age_hours),
        )
        if row is None:
            return None
        return CompositeHistoryPoint(
            id=str(row["id"]),
            ticker=row["ticker"],
            score=float(row["score"]),
            label=row["label"],
            workflow=row["workflow"],
            recorded_at=row["recorded_at"],
        )

    async def get_history(
        self, ticker: str, limit: int = 90
    ) -> list[CompositeHistoryPoint]:
        """Retourne les N derniers points triés par recorded_at ASC."""
        validated = sanitize_ticker(ticker)
        rows = await self._db.fetch(
            """
            SELECT id, ticker, score, label, workflow, recorded_at
            FROM composite_score_history
            WHERE ticker = $1
            ORDER BY recorded_at ASC
            LIMIT $2
            """,
            validated,
            limit,
        )
        return [
            CompositeHistoryPoint(
                id=str(row["id"]),
                ticker=row["ticker"],
                score=float(row["score"]),
                label=row["label"],
                workflow=row["workflow"],
                recorded_at=row["recorded_at"],
            )
            for row in rows
        ]
