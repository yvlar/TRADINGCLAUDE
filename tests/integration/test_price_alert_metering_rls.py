"""Metering RLS bout-en-bout de l'analyse déclenchée par alerte prix (E5-S7).

Skippé par défaut : nécessite `RLS_TEST_DATABASE_URL` pointant un PostgreSQL **migré**
(`alembic upgrade head`) et un rôle **NOSUPERUSER** (un superuser contourne la RLS).

Prouve, via le chemin réel du worker (`run_full_analysis` → `_execute_analysis(tenant_id)` →
`tenant_scope(tenant)` → `apply_tenant_context` → GUC → RLS) : l'analyse d'un ticker déclenchée
par une alerte prix d'un tenant B émet son `usage_event` **sous B** (visible sous B, masqué sous
le tenant legacy). C'est l'attribution tenant à travers la frontière Celery (l'argument `tenant_id`
restaure le contexte que le ContextVar ne traverse pas) que l'on teste : l'orchestrateur réel
(appels Claude) est remplacé par un faux qui écrit un vrai `usage_event` via le `UsageEventService` réel.
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


async def _seed_tenant_b(probe: asyncpg.Connection) -> None:
    if await probe.fetchval("SELECT current_setting('is_superuser')") == "on":
        pytest.skip("RLS contournée par un superuser — fournir un rôle NOSUPERUSER")
    await probe.execute(
        "INSERT INTO tenants (id, name, slug, plan) "
        "VALUES ($1::uuid, 'PRICE-B', 'price-metering-b', 'free') ON CONFLICT (id) DO NOTHING",
        _TENANT_B,
    )


@pytest.mark.asyncio
async def test_analyse_alerte_prix_imputee_au_tenant_proprietaire():
    from app.db.tenant_context import apply_tenant_context
    from app.services.usage_event_service import UsageEventService
    from app.workers import tasks
    from tests.conftest import as_tenant

    probe = await asyncpg.connect(_RLS_DB_URL)
    try:
        await _seed_tenant_b(probe)
    finally:
        await probe.close()

    # `worker_pool` est rendu au worker via `_build_orchestrator` patché et FERMÉ par
    # `_execute_analysis` (son `finally`) → ne pas le réutiliser après l'appel. `pool` sert aux assertions.
    worker_pool = await asyncpg.create_pool(
        _RLS_DB_URL, min_size=1, max_size=2, setup=apply_tenant_context
    )
    pool = await asyncpg.create_pool(
        _RLS_DB_URL, min_size=1, max_size=2, setup=apply_tenant_context
    )
    suffixe = uuid.uuid4().hex[:8].upper()
    ticker_b = f"P{suffixe[:5]}"
    skill_marker = f"price-metering-{suffixe}"
    usage_service = UsageEventService(worker_pool)

    # Faux orchestrateur : métré sous le contexte tenant courant (posé par `_execute_analysis`).
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
        resp.model_dump.return_value = {"ticker": request.ticker}
        return resp

    fake_orch.run_company_analysis = AsyncMock(side_effect=_run)

    try:
        with patch.object(
            tasks, "_build_orchestrator", AsyncMock(return_value=(fake_orch, worker_pool))
        ):
            # `tenant_id=B` restaure le contexte propriétaire que le broker Celery ne propage pas.
            await tasks._execute_analysis(
                {"ticker": ticker_b, "workflow": "value_graham"}, _TENANT_B
            )

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
        await pool.close()
        await worker_pool.close()  # idempotent si déjà fermé par le worker
