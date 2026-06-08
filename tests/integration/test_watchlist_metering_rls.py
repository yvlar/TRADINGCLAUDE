"""Metering RLS bout-en-bout des analyses watchlist planifiées (E5-S1).

Skippé par défaut : nécessite `RLS_TEST_DATABASE_URL` pointant un PostgreSQL **migré**
(`alembic upgrade head`) et un rôle **NOSUPERUSER** (un superuser contourne la RLS).

Prouve, via le chemin réel du worker (`SELECT FROM tenants` → `tenant_scope(tenant)` →
`apply_tenant_context` → GUC → RLS) : une entrée watchlist du tenant B re-analysée par
`_execute_watchlist_analysis` émet son `usage_event` **sous B** (visible sous B, masqué sous le
tenant legacy). L'orchestrateur réel (appels Claude) est remplacé par un faux qui écrit un vrai
`usage_event` via le `UsageEventService` réel — c'est l'attribution tenant du metering qu'on teste,
pas le LLM.
"""
from __future__ import annotations

import os
import uuid
from unittest.mock import AsyncMock, MagicMock, patch

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

_TENANT_LEGACY = "00000000-0000-0000-0000-000000000001"
_TENANT_B = "00000000-0000-0000-0000-0000000000bb"


@pytest.mark.asyncio
async def test_metering_watchlist_impute_au_tenant_proprietaire():
    from app.db.tenant_context import apply_tenant_context
    from app.services.usage_event_service import UsageEventService
    from app.workers import tasks
    from tests.conftest import as_tenant

    probe = await asyncpg.connect(_RLS_DB_URL)
    try:
        if await probe.fetchval("SELECT current_setting('is_superuser')") == "on":
            pytest.skip("RLS contournée par un superuser — fournir un rôle NOSUPERUSER")
        await probe.execute(
            "INSERT INTO tenants (id, name, slug, plan) "
            "VALUES ($1::uuid, 'WL-B', 'wl-metering-b', 'free') ON CONFLICT (id) DO NOTHING",
            _TENANT_B,
        )
    finally:
        await probe.close()

    # Deux pools distincts : `worker_pool` est rendu au worker via `_build_orchestrator` patché et
    # FERMÉ par `_execute_watchlist_analysis` (son `finally`) → ne pas le réutiliser après l'appel.
    # `pool` (séparé) sert au setup, aux assertions et au nettoyage, donc reste ouvert.
    worker_pool = await asyncpg.create_pool(
        _RLS_DB_URL, min_size=1, max_size=2, setup=apply_tenant_context
    )
    pool = await asyncpg.create_pool(
        _RLS_DB_URL, min_size=1, max_size=2, setup=apply_tenant_context
    )
    suffixe = uuid.uuid4().hex[:8].upper()
    # Ticker borné à 6 caractères [A-Z0-9] (contrainte `sanitize_ticker`, donc `AnalyzeRequest`) ;
    # l'unicité de l'événement repose sur `skill_marker`, pas sur le ticker.
    ticker_b = f"W{suffixe[:5]}"
    skill_marker = f"wl-metering-{suffixe}"  # marqueur unique pour retrouver l'événement
    # Le metering écrit via le pool du worker (sous le `tenant_scope` que le worker pose).
    usage_service = UsageEventService(worker_pool)

    # Faux orchestrateur : écrit un vrai usage_event sous le contexte tenant courant (celui que le
    # worker a posé via `tenant_scope`). Ne métre QUE notre ticker → une entrée legacy éventuelle ne
    # pollue pas l'assertion d'isolation.
    fake_orch = MagicMock()

    async def _run(request):
        if request.ticker == ticker_b:
            await usage_service.record(
                skill=skill_marker,
                workflow=request.workflow,
                cost_usd=0.01,
                tokens_input=1,
                tokens_output=1,
            )
        resp = MagicMock()
        resp.graham = None
        return resp

    fake_orch.run_company_analysis = AsyncMock(side_effect=_run)

    try:
        with as_tenant(_TENANT_B):
            await pool.execute(
                """
                INSERT INTO watchlist (ticker, workflow, tenant_id)
                VALUES ($1, 'value_graham',
                        NULLIF(current_setting('app.tenant_id', true), '')::uuid)
                """,
                ticker_b,
            )

        with patch.object(
            tasks, "_build_orchestrator", AsyncMock(return_value=(fake_orch, worker_pool))
        ):
            await tasks._execute_watchlist_analysis()  # ferme worker_pool dans son finally

        with as_tenant(_TENANT_B):
            visible_b = await pool.fetchval(
                "SELECT COUNT(*) FROM usage_events WHERE skill = $1", skill_marker
            )
        with as_tenant(_TENANT_LEGACY):
            visible_legacy = await pool.fetchval(
                "SELECT COUNT(*) FROM usage_events WHERE skill = $1", skill_marker
            )

        assert visible_b == 1  # conso imputée à B
        assert visible_legacy == 0  # jamais sous legacy (RLS masque)
    finally:
        with as_tenant(_TENANT_B):
            await pool.execute("DELETE FROM usage_events WHERE skill = $1", skill_marker)
            await pool.execute("DELETE FROM watchlist WHERE ticker = $1", ticker_b)
        await pool.close()
        await worker_pool.close()  # idempotent si déjà fermé par le worker (échec avant l'appel)
