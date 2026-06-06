"""Service Sprint 89 — historique des scores ESG.

Pattern identique a CompositeHistoryService (Sprint 57). La logique du verdict
est centralisee dans app.utils.esg_utils.esg_verdict() (Sprint 88) pour eviter
toute duplication entre endpoints, services et workers.
"""
from __future__ import annotations

import logging
from datetime import datetime
from uuid import UUID

import asyncpg
from pydantic import BaseModel

from app.db.tenant_context import resolve_tenant
from app.utils.esg_utils import esg_verdict
from app.utils.ticker_sanitizer import sanitize_ticker

logger = logging.getLogger(__name__)


class EsgHistoryPoint(BaseModel):
    """Un point de l'historique ESG persiste dans esg_score_history."""

    id: str
    ticker: str
    score: float
    verdict: str
    recorded_at: datetime


class EsgHistoryService:
    """CRUD sur la table esg_score_history."""

    def __init__(self, db_pool: asyncpg.Pool) -> None:
        self._db = db_pool

    async def record(
        self, ticker: str, score: float, tenant_id: UUID | None = None
    ) -> None:
        """Insère un nouveau point d'historique ESG.

        Calcule le verdict via esg_verdict() puis INSERT. Le ticker est valide
        via sanitize_ticker — leve HTTPException 422 si invalide.
        """
        validated = sanitize_ticker(ticker)
        verdict = esg_verdict(score)
        tenant = resolve_tenant(tenant_id)
        await self._db.execute(
            """
            INSERT INTO esg_score_history (ticker, score, verdict, tenant_id)
            VALUES ($1, $2, $3, $4)
            """,
            validated,
            float(score),
            verdict,
            tenant,
        )
        logger.debug(
            "esg_score enregistre : %s score=%.1f verdict=%s",
            validated, score, verdict,
        )

    async def get_latest_previous(self, ticker: str) -> float | None:
        """Retourne le score ESG avant le dernier enregistrement (2e le plus récent).

        Retourne None si moins de 2 entrées pour ce ticker.
        """
        validated = sanitize_ticker(ticker)
        row = await self._db.fetchrow(
            """
            SELECT score
            FROM esg_score_history
            WHERE ticker = $1
            ORDER BY recorded_at DESC
            LIMIT 1
            OFFSET 1
            """,
            validated,
        )
        return float(row["score"]) if row else None

    async def get_history(
        self, ticker: str, limit: int = 100
    ) -> list[EsgHistoryPoint]:
        """Retourne les N derniers points ESG tries par recorded_at DESC."""
        validated = sanitize_ticker(ticker)
        rows = await self._db.fetch(
            """
            SELECT id, ticker, score, verdict, recorded_at
            FROM esg_score_history
            WHERE ticker = $1
            ORDER BY recorded_at DESC
            LIMIT $2
            """,
            validated,
            limit,
        )
        return [
            EsgHistoryPoint(
                id=str(row["id"]),
                ticker=row["ticker"],
                score=float(row["score"]),
                verdict=row["verdict"],
                recorded_at=row["recorded_at"],
            )
            for row in rows
        ]
