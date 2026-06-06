from __future__ import annotations

import json
import logging
from uuid import UUID

import asyncpg

from app.db.tenant_context import resolve_tenant
from app.models.watchlist import WatchlistCreate, WatchlistEntry
from app.services.audit_log_service import AuditLogService, record_audit_safe
from app.skills.tier2.graham_analysis.schemas import GrahamRatios

logger = logging.getLogger(__name__)

_SELECT_COLS = """
    id, ticker, workflow, ratios, score_alerte_min,
    created_at, last_analyzed_at, last_score, last_verdict,
    last_intrinsic_value, last_price_checked, price_alert_threshold_pct,
    last_composite_score, composite_alert_threshold,
    esg_alert_threshold, last_esg_score
"""


class DuplicateWatchlistError(Exception):
    """Ticker déjà présent dans la watchlist pour ce workflow (parité E2E ↔ prod)."""


class WatchlistService:
    """CRUD sur la table watchlist PostgreSQL."""

    def __init__(
        self, db_pool: asyncpg.Pool, audit_log: AuditLogService | None = None
    ) -> None:
        self._db = db_pool
        self._audit = audit_log

    async def add_entry(
        self, create: WatchlistCreate, tenant_id: UUID | None = None
    ) -> WatchlistEntry:
        ticker = create.ticker.upper()
        # Garde anti-doublon (ticker + workflow) — alignée sur le service en mémoire
        # des E2E ; sans elle, la prod acceptait des doublons silencieux (BUG-005).
        # Le SELECT est un court-circuit best-effort ; la garantie réelle vient de
        # l'index unique idx_watchlist_ticker_workflow (résistant aux courses TOCTOU).
        existing = await self._db.fetchval(
            "SELECT 1 FROM watchlist WHERE ticker = $1 AND workflow = $2",
            ticker,
            create.workflow,
        )
        if existing:
            raise DuplicateWatchlistError(
                f"Ticker {ticker} déjà présent dans la watchlist pour ce workflow"
            )
        ratios_json = create.ratios.model_dump_json() if create.ratios else None
        tenant = resolve_tenant(tenant_id)
        try:
            row = await self._db.fetchrow(
                f"""
                INSERT INTO watchlist (ticker, workflow, ratios, score_alerte_min, tenant_id)
                VALUES ($1, $2, $3::jsonb, $4, $5)
                RETURNING {_SELECT_COLS}
                """,
                ticker,
                create.workflow,
                ratios_json,
                create.score_alerte_min,
                tenant,
            )
        except asyncpg.UniqueViolationError:
            # Course gagnée par une requête concurrente entre le SELECT et l'INSERT.
            raise DuplicateWatchlistError(
                f"Ticker {ticker} déjà présent dans la watchlist pour ce workflow"
            )
        entry = _row_to_entry(row)
        await record_audit_safe(
            self._audit,
            "watchlist.create",
            "watchlist",
            entry.id,
            metadata={"ticker": entry.ticker, "workflow": entry.workflow},
        )
        return entry

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
        deleted = result.split()[-1] != "0"
        if deleted:
            await record_audit_safe(
                self._audit, "watchlist.delete", "watchlist", entry_id
            )
        return deleted

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

    async def update_esg_score(self, entry_id: str, esg_score: float | None) -> None:
        """Met à jour le dernier esg_score pour un ticker."""
        await self._db.execute(
            "UPDATE watchlist SET last_esg_score = $2 WHERE id = $1::uuid",
            entry_id,
            esg_score,
        )

    async def update_esg_threshold(self, entry_id: str, threshold: float) -> None:
        """Met à jour le seuil d'alerte ESG pour une entrée watchlist."""
        await self._db.execute(
            "UPDATE watchlist SET esg_alert_threshold = $2 WHERE id = $1::uuid",
            entry_id,
            threshold,
        )

    async def update_price_threshold(self, entry_id: str, threshold: float) -> None:
        """Met à jour le seuil d'alerte de prix (décimal, ex: 0.10 = 10%) pour une entrée watchlist."""
        await self._db.execute(
            "UPDATE watchlist SET price_alert_threshold_pct = $2 WHERE id = $1::uuid",
            entry_id,
            threshold,
        )

    async def update_composite_score(self, entry_id: str, composite_score: float) -> None:
        """Met a jour le score composite de reference (baseline pour les alertes)."""
        await self._db.execute(
            "UPDATE watchlist SET last_composite_score = $2 WHERE id = $1::uuid",
            entry_id,
            composite_score,
        )

    @staticmethod
    def check_esg_degradation(
        entry: WatchlistEntry, previous_score: float | None
    ) -> bool:
        """Retourne True si la dégradation ESG dépasse le seuil esg_alert_threshold."""
        if entry.last_esg_score is None or previous_score is None:
            return False
        return (previous_score - entry.last_esg_score) > entry.esg_alert_threshold

    async def get_all_with_composite(self) -> list[dict]:
        """Retourne toutes les entrées watchlist enrichies du dernier composite_score et de la dernière annotation."""
        rows = await self._db.fetch(
            """
            SELECT
                w.id::text AS id,
                w.ticker,
                w.created_at,
                w.composite_alert_threshold,
                COALESCE(csh.score, w.last_composite_score) AS composite_score_latest,
                csh.label AS composite_label_latest,
                w.last_esg_score,
                w.esg_alert_threshold,
                COALESCE(ann.note, '') AS derniere_annotation
            FROM watchlist w
            LEFT JOIN LATERAL (
                SELECT score, label
                FROM composite_score_history
                WHERE ticker = w.ticker
                ORDER BY recorded_at DESC
                LIMIT 1
            ) csh ON true
            LEFT JOIN LATERAL (
                SELECT a.note
                FROM annotations a
                JOIN analysis_history h USING (analysis_id)
                WHERE h.ticker = w.ticker
                ORDER BY a.created_at DESC
                LIMIT 1
            ) ann ON true
            ORDER BY w.created_at DESC
            """
        )
        return [dict(row) for row in rows]


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

    raw_composite = row.get("last_composite_score")
    raw_comp_threshold = row.get("composite_alert_threshold")
    raw_esg_threshold = row.get("esg_alert_threshold")
    raw_last_esg = row.get("last_esg_score")

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
        last_composite_score=float(raw_composite) if raw_composite is not None else None,
        composite_alert_threshold=float(raw_comp_threshold) if raw_comp_threshold is not None else 15.0,
        esg_alert_threshold=float(raw_esg_threshold) if raw_esg_threshold is not None else 5.0,
        last_esg_score=float(raw_last_esg) if raw_last_esg is not None else None,
    )
