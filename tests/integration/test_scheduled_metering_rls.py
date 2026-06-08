"""Metering RLS bout-en-bout du screener planifié et des alertes composites (E5-S4).

Skippé par défaut : nécessite `RLS_TEST_DATABASE_URL` pointant un PostgreSQL **migré**
(`alembic upgrade head`) et un rôle **NOSUPERUSER** (un superuser contourne la RLS).

Prouve, via le chemin réel des workers (`SELECT FROM tenants` → `tenant_scope(tenant)` →
`apply_tenant_context` → GUC → RLS) : la conso d'un screener planifié / d'une vérif d'alerte
composite du tenant B émet son `usage_event` **sous B** (visible sous B, masqué sous le tenant
legacy). L'orchestrateur réel (appels Claude) est remplacé par un faux qui écrit un vrai
`usage_event` via le `UsageEventService` réel — c'est l'attribution tenant du metering qu'on teste.
"""
from __future__ import annotations

import os
import uuid
from datetime import datetime, timezone
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
        "VALUES ($1::uuid, 'SCHED-B', 'sched-metering-b', 'free') ON CONFLICT (id) DO NOTHING",
        _TENANT_B,
    )


@pytest.mark.asyncio
async def test_screener_planifie_impute_au_tenant_proprietaire():
    from app.db.tenant_context import apply_tenant_context
    from app.services.usage_event_service import UsageEventService
    from app.skills.tier2.graham_analysis.schemas import GrahamRatios
    from app.workers import tasks
    from tests.conftest import as_tenant

    probe = await asyncpg.connect(_RLS_DB_URL)
    try:
        await _seed_tenant_b(probe)
    finally:
        await probe.close()

    # `worker_pool` est rendu au worker via `_build_orchestrator` patché et FERMÉ par
    # `_execute_scheduled_screener` (son `finally`) → ne pas le réutiliser après l'appel.
    # `pool` (séparé) sert au setup, aux assertions et au nettoyage.
    worker_pool = await asyncpg.create_pool(
        _RLS_DB_URL, min_size=1, max_size=2, setup=apply_tenant_context
    )
    pool = await asyncpg.create_pool(
        _RLS_DB_URL, min_size=1, max_size=2, setup=apply_tenant_context
    )
    suffixe = uuid.uuid4().hex[:8].upper()
    ticker_b = f"S{suffixe[:5]}"
    skill_marker = f"sched-metering-{suffixe}"
    usage_service = UsageEventService(worker_pool)

    # Faux orchestrateur : métré sous le contexte tenant courant (posé par le worker). Réponse
    # NON-FORT (composite_score None, graham None) → aucune écriture alert_history à nettoyer.
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
        resp.composite_score = None
        resp.cost_usd = 0.0
        resp.created_at = datetime.now(timezone.utc)
        return resp

    fake_orch.run_company_analysis = AsyncMock(side_effect=_run)

    fake_extractor = MagicMock()
    fake_extractor.extract = AsyncMock(return_value=GrahamRatios(eps_growth_total=0.0, price=10.0))

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

        # Les chemins worker créent leur propre db_pool depuis DATABASE_URL (lecture watchlist/tenants) :
        # le pointer sur la DB de test (rôle NOSUPERUSER) → la lecture watchlist passe bien par la RLS.
        with (
            patch.dict(os.environ, {"DATABASE_URL": _RLS_DB_URL}),
            patch.object(
                tasks, "_build_orchestrator", AsyncMock(return_value=(fake_orch, worker_pool))
            ),
            patch.object(tasks, "YahooFinanceExtractor", return_value=fake_extractor),
            patch.object(tasks, "WebhookService", return_value=AsyncMock()),
            patch.object(tasks, "SlackService", return_value=AsyncMock()),
        ):
            await tasks._execute_scheduled_screener()  # ferme worker_pool dans son finally

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
        await worker_pool.close()  # idempotent si déjà fermé par le worker


@pytest.mark.asyncio
async def test_alerte_composite_impute_au_tenant_proprietaire():
    from app.db.tenant_context import apply_tenant_context
    from app.services.usage_event_service import UsageEventService
    from app.workers import tasks
    from tests.conftest import as_tenant

    probe = await asyncpg.connect(_RLS_DB_URL)
    try:
        await _seed_tenant_b(probe)
    finally:
        await probe.close()

    worker_pool = await asyncpg.create_pool(
        _RLS_DB_URL, min_size=1, max_size=2, setup=apply_tenant_context
    )
    pool = await asyncpg.create_pool(
        _RLS_DB_URL, min_size=1, max_size=2, setup=apply_tenant_context
    )
    suffixe = uuid.uuid4().hex[:8].upper()
    ticker_b = f"C{suffixe[:5]}"
    skill_marker = f"composite-metering-{suffixe}"
    usage_service = UsageEventService(worker_pool)

    # Réponse avec composite_score sous la baseline → alerte ; le metering écrit un usage_event sous B.
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
        resp.composite_score = MagicMock(score=50.0)
        return resp

    fake_orch.run_company_analysis = AsyncMock(side_effect=_run)

    try:
        # Baseline élevée (80) → chute > seuil (15) → alerte déclenchée pour B.
        with as_tenant(_TENANT_B):
            await pool.execute(
                """
                INSERT INTO watchlist (ticker, workflow, last_composite_score, tenant_id)
                VALUES ($1, 'value_graham', 80.0,
                        NULLIF(current_setting('app.tenant_id', true), '')::uuid)
                """,
                ticker_b,
            )

        # db_pool interne créé depuis DATABASE_URL → pointer sur la DB de test (rôle NOSUPERUSER).
        # EmailService patché : l'alerte déclenchée ne doit pas tenter d'envoi SMTP réel selon l'env CI.
        with (
            patch.dict(os.environ, {"DATABASE_URL": _RLS_DB_URL}),
            patch.object(
                tasks, "_build_orchestrator", AsyncMock(return_value=(fake_orch, worker_pool))
            ),
            patch.object(tasks, "WebhookService", return_value=AsyncMock()),
            patch.object(tasks, "EmailService", return_value=AsyncMock()),
        ):
            await tasks._execute_composite_alert_check()  # ferme worker_pool dans son finally

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
        await worker_pool.close()
