"""Isolation RLS de l'agrégation `usage_events` via `UsageEventService.aggregate` (E4-S5).

Skippé par défaut : nécessite `RLS_TEST_DATABASE_URL` pointant un PostgreSQL **migré**
(`alembic upgrade head`) et un rôle **NOSUPERUSER** (un superuser contourne la RLS).

Prouve que l'agrégation tourne **sous le contexte tenant** (ContextVar → setup du pool →
GUC → RLS) : chaque tenant ne voit que SA consommation dans le total, la ventilation par
skill et la série quotidienne — pas un `WHERE tenant_id=` applicatif, l'isolation native.
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

_TENANT_A = "00000000-0000-0000-0000-000000000001"  # tenant legacy (présent après migration)
_TENANT_B = "00000000-0000-0000-0000-0000000000bb"


@pytest.mark.asyncio
async def test_aggregate_isole_la_consommation_par_tenant():
    """Tenant A n'agrège que ses propres `usage_events` ; B les siens (RLS via pool setup)."""
    from app.db.tenant_context import apply_tenant_context
    from app.services.usage_event_service import UsageEventService
    from tests.conftest import as_tenant

    # Garde : un superuser contourne la RLS — le test serait faussement vert.
    probe = await asyncpg.connect(_RLS_DB_URL)
    try:
        if await probe.fetchval("SELECT current_setting('is_superuser')") == "on":
            pytest.skip("RLS contournée par un superuser — fournir un rôle NOSUPERUSER")
        await probe.execute(
            "INSERT INTO tenants (id, name, slug) VALUES ($1::uuid, 'RLS-B', 'rls-test-b') "
            "ON CONFLICT (id) DO NOTHING",
            _TENANT_B,
        )
    finally:
        await probe.close()

    pool = await asyncpg.create_pool(
        _RLS_DB_URL, min_size=1, max_size=2, setup=apply_tenant_context
    )
    svc = UsageEventService(db_pool=pool)
    skill_a = f"SKILLA{uuid.uuid4().hex[:6]}"
    skill_b = f"SKILLB{uuid.uuid4().hex[:6]}"
    try:
        # A : 2 événements (coût total 0.03). B : 1 événement (coût 1.0) — montants distincts
        # pour qu'une fuite cross-tenant change visiblement les totaux.
        with as_tenant(_TENANT_A):
            await svc.record(skill=skill_a, workflow="value_graham",
                             cost_usd=0.02, tokens_input=2000, tokens_output=1000)
            await svc.record(skill=skill_a, workflow="value_graham",
                             cost_usd=0.01, tokens_input=1000, tokens_output=500)
        with as_tenant(_TENANT_B):
            await svc.record(skill=skill_b, workflow="compounder_buffett",
                             cost_usd=1.0, tokens_input=9, tokens_output=9)

        with as_tenant(_TENANT_A):
            agg_a = await svc.aggregate(days=1)
        with as_tenant(_TENANT_B):
            agg_b = await svc.aggregate(days=1)

        # A ne voit que sa consommation (skill_a, total 0.03), jamais celle de B.
        skills_a = {s.skill for s in agg_a.by_skill}
        assert skill_a in skills_a
        assert skill_b not in skills_a
        a_cost = next(s for s in agg_a.by_skill if s.skill == skill_a)
        assert a_cost.events == 2
        assert a_cost.cost_usd == pytest.approx(0.03)

        # B ne voit que la sienne (skill_b, coût 1.0), jamais celle de A.
        skills_b = {s.skill for s in agg_b.by_skill}
        assert skill_b in skills_b
        assert skill_a not in skills_b
        assert agg_b.total_cost_usd == pytest.approx(1.0)
    finally:
        # NOSUPERUSER soumis à la RLS → supprimer chaque ligne sous son propre tenant.
        with as_tenant(_TENANT_A):
            await pool.execute("DELETE FROM usage_events WHERE skill = $1", skill_a)
        with as_tenant(_TENANT_B):
            await pool.execute("DELETE FROM usage_events WHERE skill = $1", skill_b)
        await pool.close()
