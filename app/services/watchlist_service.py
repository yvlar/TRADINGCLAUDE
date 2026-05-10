from __future__ import annotations

import json
import logging

import asyncpg

from app.models.watchlist import WatchlistCreate, WatchlistEntry
from app.skills.tier2.graham_analysis.schemas import GrahamRatios

logger = logging.getLogger(__name__)

_SELECT_COLS = """
    id, ticker, workflow, ratios, score_alerte_min,
    created_at, last_analyzed_at, last_score, last_verdict,
    last_intrinsic_value, last_price_checked, price_alert_threshold_pct
"""


class WatchlistService:
    """CRUD sur la table watchlist PostgreSQL."""

    def __init__(self, db_pool: asyncpg.Pool) -> None:
        self._db = db_pool

    async def add_entry(self, create: WatchlistCreate) -> WatchlistEntry:
        ratios_json = create.ratios.model_dump_json() if create.ratios else None
        row = await self._db.fetchrow(
            f"""
            INSERT INTO watchlist (ticker, workflow, ratios, score_alerte_min)
            VALUES ($1, $2, $3::jsonb, $4)
            RETURNING {_SELECT_COLS}
            """,
            create.ticker.upper(),
            create.workflow,
            ratios_json,
            create.score_alerte_min,
        )
        return _row_to_entry(row)

    async def list_entries(self) -> list[WatchlistEntry]:
        rows = await self._db.fetch(
            f"""
            SELECT {_SELECT_COLS}
            FROM watchlist
            ORDER BY created_at DESC
            """
        )
        return [_row_to_entry(row) for row in rows]

    async def get_entry(self, entry_id: str) -> WatchlistEntry | None:
        try:
            row = await self._db.fetchrow(
                f"""
                SELECT {_SELECT_COLS}
                FROM watchlist WHERE id = $1::uuid
                """,
                entry_id,
            )
        except Exception:
            return None
        return _row_to_entry(row) if row else None

    async def delete_entry(self, entry_id: str) -> bool:
        try:
            result = await self._db.execute(
                "DELETE FROM watchlist WHERE id = $1::uuid", entry_id
            )
        except Exception:
            return False
        # asyncpg retourne "DELETE N" — N est le nombre de lignes supprimées
        return result.split()[-1] != "0"

    async def update_last_analyzed(
        self,
        entry_id: str,
        score: int | None,
        verdict: str | None,
        intrinsic_value: float | None = None,
    ) -> None:
        await self._db.execute(
            """
            UPDATE watchlist
            SET last_analyzed_at = NOW(), last_score = $2, last_verdict = $3,
                last_intrinsic_value = $4
            WHERE id = $1::uuid
            """,
            entry_id,
            score,
            verdict,
            intrinsic_value,
        )

    async def update_price_checked(self, entry_id: str, price: float) -> None:
        await self._db.execute(
            "UPDATE watchlist SET last_price_checked = $2 WHERE id = $1::uuid",
            entry_id,
            price,
        )


def _row_to_entry(row) -> WatchlistEntry:
    ratios_raw = row["ratios"]
    ratios: GrahamRatios | None = None
    if ratios_raw:
        ratios = GrahamRatios.model_validate(
            json.loads(ratios_raw) if isinstance(ratios_raw, str) else ratios_raw
        )

    raw_intrinsic = row["last_intrinsic_value"]
    raw_price_checked = row["last_price_checked"]
    raw_threshold = row["price_alert_threshold_pct"]

    return WatchlistEntry(
        id=str(row["id"]),
        ticker=row["ticker"],
        workflow=row["workflow"],
        ratios=ratios,
        score_alerte_min=row["score_alerte_min"],
        created_at=row["created_at"],
        last_analyzed_at=row["last_analyzed_at"],
        last_score=row["last_score"],
        last_verdict=row["last_verdict"],
        last_intrinsic_value=float(raw_intrinsic) if raw_intrinsic is not None else None,
        last_price_checked=float(raw_price_checked) if raw_price_checked is not None else None,
        price_alert_threshold_pct=float(raw_threshold) if raw_threshold is not None else 0.10,
    )
