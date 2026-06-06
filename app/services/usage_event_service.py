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

logger = logging.getLogger(__name__)


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
