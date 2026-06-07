"""Service de metering append-only — E4-S1 (socle de facturation).

Chaque skill exécuté avec succès produit une ligne `usage_events` (INSERT pur, jamais
UPDATE/DELETE) attribuée au tenant courant : source de vérité unique de la consommation
facturable (agrégation E4-S2 quotas, E4-S5 export). Calqué sur `AuditLogService`.
"""
from __future__ import annotations

import logging
from datetime import datetime
from decimal import Decimal
from uuid import UUID

import asyncpg
from pydantic import BaseModel

from app.db.tenant_context import resolve_tenant
from app.models.usage import UsageBySkill, UsageResponse

logger = logging.getLogger(__name__)

# Fenêtre d'agrégation par défaut de `GET /usage` (cohérent avec `GET /metrics`).
_DEFAULT_USAGE_DAYS = 30


class UsageEvent(BaseModel):
    id: UUID
    tenant_id: UUID
    skill: str
    workflow: str
    cost_usd: float
    tokens_input: int
    tokens_output: int
    created_at: datetime


class UsageEventService:
    """Metering append-only — INSERT pur, aucun UPDATE ni DELETE applicatif."""

    def __init__(self, db_pool: asyncpg.Pool) -> None:
        self._db = db_pool

    async def record(
        self,
        skill: str,
        workflow: str,
        cost_usd: float,
        tokens_input: int,
        tokens_output: int,
        tenant_id: UUID | None = None,
    ) -> UsageEvent:
        """Insère un événement de consommation et le retourne (append-only).

        `tenant_id` défaut `resolve_tenant(...)` : la colonne écrite dérive de la même
        source que le GUC RLS (égalité exigée par le `WITH CHECK` de la policy).
        """
        tenant = resolve_tenant(tenant_id)
        # cost_usd → Decimal : asyncpg exige un Decimal pour une colonne NUMERIC (un float
        # lèverait DataError), et la précision monétaire ne doit pas transiter par un float.
        row = await self._db.fetchrow(
            """
            INSERT INTO usage_events (tenant_id, skill, workflow, cost_usd, tokens_input, tokens_output)
            VALUES ($1::uuid, $2, $3, $4, $5, $6)
            RETURNING id, tenant_id, skill, workflow, cost_usd, tokens_input, tokens_output, created_at
            """,
            str(tenant),
            skill,
            workflow,
            Decimal(str(cost_usd)),
            tokens_input,
            tokens_output,
        )
        return _row_to_event(row)

    async def aggregate(self, days: int = _DEFAULT_USAGE_DAYS) -> UsageResponse:
        """Agrège la consommation du tenant courant sur `days` jours (lecture seule).

        Aucun filtre `WHERE tenant_id` : l'isolation vient de la RLS (GUC `app.tenant_id`
        posé par connexion via `apply_tenant_context`) — chaque requête ne voit que les
        lignes du tenant courant. `cost_usd` (NUMERIC) est arrondi à 6 décimales en `float`
        côté API, comme `MetricsResponse`.
        """
        # Lié en str ($1) dans `($1 || ' days')::interval`, comme `get_metrics`.
        window = str(days)

        totals_row = await self._db.fetchrow(
            """
            SELECT
                COALESCE(SUM(cost_usd), 0)      AS total_cost,
                COALESCE(SUM(tokens_input), 0)  AS total_in,
                COALESCE(SUM(tokens_output), 0) AS total_out
            FROM usage_events
            WHERE created_at >= NOW() - ($1 || ' days')::interval
            """,
            window,
        )

        skill_rows = await self._db.fetch(
            """
            SELECT skill,
                   COALESCE(SUM(cost_usd), 0)      AS cost,
                   COALESCE(SUM(tokens_input), 0)  AS tok_in,
                   COALESCE(SUM(tokens_output), 0) AS tok_out,
                   COUNT(*)                        AS nb
            FROM usage_events
            WHERE created_at >= NOW() - ($1 || ' days')::interval
            GROUP BY skill
            ORDER BY cost DESC
            """,
            window,
        )

        daily_rows = await self._db.fetch(
            """
            SELECT to_char(date_trunc('day', created_at), 'YYYY-MM-DD') AS day,
                   COALESCE(SUM(cost_usd), 0)                            AS cost
            FROM usage_events
            WHERE created_at >= NOW() - ($1 || ' days')::interval
            GROUP BY day
            ORDER BY day
            """,
            window,
        )

        return UsageResponse(
            period_days=days,
            total_cost_usd=round(float(totals_row["total_cost"]), 6),
            total_tokens_input=int(totals_row["total_in"]),
            total_tokens_output=int(totals_row["total_out"]),
            by_skill=[
                UsageBySkill(
                    skill=row["skill"],
                    cost_usd=round(float(row["cost"]), 6),
                    tokens_input=int(row["tok_in"]),
                    tokens_output=int(row["tok_out"]),
                    events=int(row["nb"]),
                )
                for row in skill_rows
            ],
            daily_cost={row["day"]: round(float(row["cost"]), 6) for row in daily_rows},
        )

    async def count_window(self, start: datetime, end: datetime) -> int:
        """Compte les événements de consommation du tenant courant dans `[start, end)` (lecture seule).

        Unité facturable de la facturation à l'usage (E4-S9) : chaque ligne `usage_events` = une
        exécution de skill métrée. Aucun filtre `WHERE tenant_id` — l'isolation vient de la RLS (GUC
        `app.tenant_id` posé par connexion) : le compte ne porte que sur le tenant courant. Borne
        haute exclusive pour ne jamais compter deux fois un événement à la frontière de deux fenêtres.
        """
        row = await self._db.fetchrow(
            """
            SELECT COUNT(*) AS nb
            FROM usage_events
            WHERE created_at >= $1 AND created_at < $2
            """,
            start,
            end,
        )
        return int(row["nb"])


def _row_to_event(row: asyncpg.Record) -> UsageEvent:
    return UsageEvent(
        id=row["id"],
        tenant_id=row["tenant_id"],
        skill=row["skill"],
        workflow=row["workflow"],
        cost_usd=float(row["cost_usd"]),
        tokens_input=row["tokens_input"],
        tokens_output=row["tokens_output"],
        created_at=row["created_at"],
    )


async def record_usage_safe(
    service: UsageEventService | None,
    skill: str,
    workflow: str,
    cost_usd: float,
    tokens_input: int,
    tokens_output: int,
    tenant_id: UUID | None = None,
) -> None:
    """Metering best-effort — un échec n'avorte JAMAIS l'analyse (log + continue)."""
    if service is None:
        return
    try:
        await service.record(
            skill=skill,
            workflow=workflow,
            cost_usd=cost_usd,
            tokens_input=tokens_input,
            tokens_output=tokens_output,
            tenant_id=tenant_id,
        )
    except Exception:
        logger.exception("Échec d'écriture du metering usage_events : %s/%s", skill, workflow)
