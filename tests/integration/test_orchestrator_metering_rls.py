"""Isolation RLS de l'émission `usage_events` par l'orchestrateur (E5, Sprint 203).

Skippé par défaut : nécessite `RLS_TEST_DATABASE_URL` pointant un PostgreSQL **migré**
(`alembic upgrade head`) et un rôle **NOSUPERUSER** — câblé dans le job CI
« Migrations — Alembic + RLS » (liste explicite de fichiers).

Les tests S163-S166 prouvent la policy table par table ; S177/S181/S185 couvrent les chemins
workers planifiés. Chaînon restant : l'émission depuis l'ORCHESTRATEUR (`_emit_usage_events`)
sous un `tenant_scope` donné — `usage_events` est la source unique de facturation, une fuite
cross-tenant ici serait une anomalie de facturation silencieuse. Deux barrières prouvées :
(1) l'événement émis sous A est invisible sous B (USING) et le coût nul n'émet rien ;
(2) un INSERT forgé `tenant_id=B` depuis le scope A est rejeté par la DB (WITH CHECK) —
même un bug applicatif passant le mauvais tenant serait bloqué par PostgreSQL, pas par l'app.

Aucun appel Claude réel : les `UsageDetail` sont construits à la main et les skills de
l'orchestrateur sont des mocks inertes — c'est l'attribution tenant du metering qu'on teste.
"""
from __future__ import annotations

import os
import uuid
from unittest.mock import MagicMock

import asyncpg
import pytest

from app.db.tenant_context import apply_tenant_context
from app.orchestrator.core import Orchestrator
from app.services.usage_event_service import UsageEventService
from app.skills.base import UsageDetail
from tests.conftest import as_tenant

_RLS_DB_URL = os.environ.get("RLS_TEST_DATABASE_URL")

pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(
        not _RLS_DB_URL,
        reason="RLS_TEST_DATABASE_URL non défini (PG migré + rôle NOSUPERUSER requis)",
    ),
]

_TENANT_A = "00000000-0000-0000-0000-0000000000a3"
_TENANT_B = "00000000-0000-0000-0000-0000000000b3"


async def _seed_tenants_and_probe() -> None:
    """Pose les deux tenants de test ; skip si superuser (la RLS serait contournée — preuve vacue)."""
    probe = await asyncpg.connect(_RLS_DB_URL)
    try:
        if await probe.fetchval("SELECT current_setting('is_superuser')") == "on":
            pytest.skip("RLS contournée par un superuser — fournir un rôle NOSUPERUSER")
        for tenant_id, slug in ((_TENANT_A, "orch-met-a"), (_TENANT_B, "orch-met-b")):
            await probe.execute(
                "INSERT INTO tenants (id, name, slug, plan) "
                "VALUES ($1::uuid, 'S203', $2, 'free') ON CONFLICT (id) DO NOTHING",
                tenant_id,
                slug,
            )
    finally:
        await probe.close()


def _usage(cost_usd: float) -> UsageDetail:
    """UsageDetail factice — seuls coût et tokens comptent pour le metering."""
    return UsageDetail(
        tokens_input=10,
        tokens_output=5,
        tokens_cache_read=0,
        tokens_cache_creation=0,
        cost_usd=cost_usd,
        model="claude-test",
    )


@pytest.mark.asyncio
async def test_emission_orchestrateur_scopee_au_tenant_courant() -> None:
    """`_emit_usage_events` sous scope A : visible par A, invisible par B, coût nul filtré."""
    await _seed_tenants_and_probe()
    pool = await asyncpg.create_pool(
        _RLS_DB_URL, min_size=1, max_size=2, setup=apply_tenant_context
    )
    marker = f"orch-metering-{uuid.uuid4().hex[:8]}"
    # Orchestrateur réel minimal : seuls db_pool + 2 skills sont requis (mocks inertes, jamais
    # appelés) ; le service de metering est le VRAI, branché sur le pool RLS — c'est le chemin
    # réel `_emit_usage_events` → `record_usage_safe` → INSERT qu'on exerce.
    orch = Orchestrator(
        pool, MagicMock(), MagicMock(), usage_event_service=UsageEventService(pool)
    )

    try:
        with as_tenant(_TENANT_A):
            await orch._emit_usage_events(
                skills_applied=[marker, f"{marker}-cache"],
                # le 2ᵉ usage (cache hit, coût nul) ne doit RIEN émettre (filtre cost_usd > 0)
                all_usages=[_usage(0.01), _usage(0.0)],
                workflow="value_graham",
            )

        with as_tenant(_TENANT_A):
            vus_a = await pool.fetch(
                "SELECT skill FROM usage_events WHERE skill LIKE $1 || '%'", marker
            )
        with as_tenant(_TENANT_B):
            vus_b = await pool.fetchval(
                "SELECT COUNT(*) FROM usage_events WHERE skill LIKE $1 || '%'", marker
            )

        assert [r["skill"] for r in vus_a] == [marker]  # émis sous A, coût nul absent
        assert vus_b == 0  # la RLS (USING) masque l'événement de A sous le scope B
    finally:
        with as_tenant(_TENANT_A):
            await pool.execute(
                "DELETE FROM usage_events WHERE skill LIKE $1 || '%'", marker
            )
        await pool.close()


@pytest.mark.asyncio
async def test_insert_forge_cross_tenant_rejete_par_with_check() -> None:
    """Un INSERT forgé `tenant_id=B` depuis le scope A est rejeté par la policy WITH CHECK."""
    await _seed_tenants_and_probe()
    pool = await asyncpg.create_pool(
        _RLS_DB_URL, min_size=1, max_size=2, setup=apply_tenant_context
    )
    marker = f"orch-forge-{uuid.uuid4().hex[:8]}"

    try:
        with as_tenant(_TENANT_A):
            # `match` sur le message de policy : discrimine d'un échec d'INSERT non lié (FK, NOT NULL).
            with pytest.raises(asyncpg.PostgresError, match="row-level security"):
                await pool.execute(
                    "INSERT INTO usage_events (tenant_id, skill, workflow) "
                    "VALUES ($1::uuid, $2, 'value_graham')",
                    _TENANT_B,
                    marker,
                )

        # Ceinture : rien n'a été écrit — ni visible de A, ni de B.
        for tenant in (_TENANT_A, _TENANT_B):
            with as_tenant(tenant):
                restant = await pool.fetchval(
                    "SELECT COUNT(*) FROM usage_events WHERE skill = $1", marker
                )
                assert restant == 0
    finally:
        await pool.close()
