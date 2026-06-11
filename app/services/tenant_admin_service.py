"""Service de listing des tenants pour l'admin — Sprint 204 (onboarding/support B2B)."""
from __future__ import annotations

import asyncpg

from app.models.tenant import TenantAdminEntry


class TenantAdminService:
    """Lecture seule des tenants — `tenants`/`subscriptions` sont HORS RLS (pool standard)."""

    def __init__(self, db_pool: asyncpg.Pool) -> None:
        self._db = db_pool

    async def list_tenants(self, limit: int = 100) -> list[TenantAdminEntry]:
        """Retourne les tenants, plus récents d'abord, avec leur customer Stripe éventuel."""
        rows = await self._db.fetch(
            """
            SELECT t.id, t.name, t.slug, t.plan, t.created_at, s.stripe_customer_id
            FROM tenants t
            LEFT JOIN subscriptions s ON s.tenant_id = t.id
            ORDER BY t.created_at DESC
            LIMIT $1
            """,
            limit,
        )
        return [
            TenantAdminEntry(
                id=row["id"],
                name=row["name"],
                slug=row["slug"],
                plan=row["plan"],
                stripe_customer_id=row["stripe_customer_id"],
                created_at=row["created_at"],
            )
            for row in rows
        ]
