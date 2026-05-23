"""Service Sprint 99 — historique des alertes Celery dans alert_history.

Pattern identique a EsgHistoryService (Sprint 89). Les alertes sont enregistrees
en best-effort par les workers Celery (ESG degradation, screener FORT, prix seuil).
"""
from __future__ import annotations

import logging

import asyncpg

logger = logging.getLogger(__name__)


class AlertHistoryService:
    """CRUD sur la table alert_history."""

    def __init__(self, db_pool: asyncpg.Pool) -> None:
        self._db = db_pool

    async def record(
        self,
        ticker: str,
        type: str,
        valeur: float | None,
        seuil: float | None,
        message: str | None,
    ) -> int:
        """Insere une alerte dans alert_history et retourne son id."""
        row = await self._db.fetchrow(
            """
            INSERT INTO alert_history (ticker, type, valeur, seuil, message)
            VALUES ($1, $2, $3, $4, $5)
            RETURNING id
            """,
            ticker,
            type,
            valeur,
            seuil,
            message,
        )
        alert_id = int(row["id"])
        logger.debug("Alerte enregistrée : %s %s id=%d", type, ticker, alert_id)
        return alert_id

    async def get_recent(self, limit: int = 50) -> list[dict]:
        """Retourne les N dernières alertes triées par created_at DESC."""
        rows = await self._db.fetch(
            """
            SELECT id, ticker, type, valeur, seuil, message, created_at
            FROM alert_history
            ORDER BY created_at DESC
            LIMIT $1
            """,
            limit,
        )
        return [
            {
                "id": row["id"],
                "ticker": row["ticker"],
                "type": row["type"],
                "valeur": row["valeur"],
                "seuil": row["seuil"],
                "message": row["message"],
                "created_at": row["created_at"].isoformat(),
            }
            for row in rows
        ]
