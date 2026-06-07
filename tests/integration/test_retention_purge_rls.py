"""Isolation RLS + borne de la purge de rétention par plan (E4-S6).

Skippé par défaut : nécessite `RLS_TEST_DATABASE_URL` pointant un PostgreSQL **migré**
(`alembic upgrade head`) et un rôle **NOSUPERUSER** (un superuser contourne la RLS).

Prouve, via le chemin réel (`set_current_tenant` → `apply_tenant_context` → GUC → RLS) :
- **borne** : pour free=30, une ligne à J-31 est purgée, une ligne à J-29 conservée ;
- **isolation** : la purge exécutée sous le tenant A ne supprime QUE les lignes périmées de A —
  les lignes de B (même périmées) restent intactes (la RLS scope le DELETE).
"""
from __future__ import annotations

import os
import uuid

import asyncpg
import pytest

_RLS_DB_URL = os.environ.get("RLS_TEST_DATABASE_URL")

pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(
        not _RLS_DB_URL,
        reason="RLS_TEST_DATABASE_URL non défini (PG migré + rôle NOSUPERUSER requis)",
    ),
]

_TENANT_A = "00000000-0000-0000-0000-000000000001"  # tenant legacy (plan free=30 après migration)
_TENANT_B = "00000000-0000-0000-0000-0000000000bb"


async def _insert_aged_analysis(pool: asyncpg.Pool, ticker: str, days_ago: int) -> None:
    """Insère une ligne analysis_history datée NOW()-days_ago sous le contexte tenant courant."""
    await pool.execute(
        """
        INSERT INTO analysis_history (ticker, input_data, result, tenant_id, created_at)
        VALUES ($1, '{}'::jsonb, '{}'::jsonb,
                NULLIF(current_setting('app.tenant_id', true), '')::uuid,
                NOW() - ($2 || ' days')::interval)
        """,
        ticker,
        str(days_ago),
    )


async def _count(pool: asyncpg.Pool, ticker_like: str) -> set[str]:
    rows = await pool.fetch(
        "SELECT ticker FROM analysis_history WHERE ticker LIKE $1", ticker_like
    )
    return {r["ticker"] for r in rows}


@pytest.mark.asyncio
async def test_purge_respecte_la_borne_et_isole_le_tenant():
    from app.db.tenant_context import apply_tenant_context
    from app.services.retention_service import RetentionService
    from tests.conftest import as_tenant

    probe = await asyncpg.connect(_RLS_DB_URL)
    try:
        if await probe.fetchval("SELECT current_setting('is_superuser')") == "on":
            pytest.skip("RLS contournée par un superuser — fournir un rôle NOSUPERUSER")
        # Tenant B au plan free (retention_days=30), comme A (legacy).
        await probe.execute(
            "INSERT INTO tenants (id, name, slug, plan) "
            "VALUES ($1::uuid, 'RLS-B', 'rls-test-b', 'free') ON CONFLICT (id) DO NOTHING",
            _TENANT_B,
        )
    finally:
        await probe.close()

    pool = await asyncpg.create_pool(
        _RLS_DB_URL, min_size=1, max_size=2, setup=apply_tenant_context
    )
    suffixe = uuid.uuid4().hex[:8].upper()
    a_old = f"AOLD{suffixe}"   # J-31 → purgé (free=30)
    a_edge = f"AEDGE{suffixe}"  # J-29 → conservé
    b_old = f"BOLD{suffixe}"   # J-40, tenant B → intact (purge sous A seulement)
    like = f"%{suffixe}"
    service = RetentionService(db_pool=pool)
    try:
        with as_tenant(_TENANT_A):
            await _insert_aged_analysis(pool, a_old, 31)
            await _insert_aged_analysis(pool, a_edge, 29)
        with as_tenant(_TENANT_B):
            await _insert_aged_analysis(pool, b_old, 40)

        # Purge sous le contexte du tenant A uniquement.
        with as_tenant(_TENANT_A):
            result = await service.purge_tenant(_TENANT_A)

        assert result is not None
        assert result.retention_days == 30
        assert result.deleted_by_table["analysis_history"] == 1  # seulement a_old

        # Borne : A voit a_edge (J-29) mais plus a_old (J-31).
        with as_tenant(_TENANT_A):
            visible_a = await _count(pool, like)
        assert a_edge in visible_a
        assert a_old not in visible_a

        # Isolation : la ligne périmée de B (J-40) survit — la purge sous A ne l'a pas touchée.
        with as_tenant(_TENANT_B):
            visible_b = await _count(pool, like)
        assert b_old in visible_b
    finally:
        for tenant, tickers in ((_TENANT_A, (a_old, a_edge)), (_TENANT_B, (b_old,))):
            with as_tenant(tenant):
                for ticker in tickers:
                    await pool.execute(
                        "DELETE FROM analysis_history WHERE ticker = $1", ticker
                    )
        await pool.close()
