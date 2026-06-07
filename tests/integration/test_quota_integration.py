"""Quotas E4-S2 contre un PostgreSQL migré — résolution plan→bornes + application de la borne.

Skippé par défaut : nécessite `RLS_TEST_DATABASE_URL` pointant un PostgreSQL **migré**
(`alembic upgrade head`, donc 0007_plan_limits appliquée). Prouve que `QuotaService` résout
les bornes du plan d'un tenant réel et applique la borne dure (429 au dépassement) ainsi que
la borne screener par plan. Redis est remplacé par FakeRedis (le compteur n'est qu'un
dispositif d'application dans la fenêtre — la borne se prouve sur le seuil, pas l'infra).
"""
from __future__ import annotations

import os
from datetime import datetime, timezone
from uuid import UUID

import asyncpg
import fakeredis
import pytest

from app.models.tenant import LEGACY_TENANT_ID
from app.services.quota_service import QuotaExceededError, QuotaService, _month_key

_RLS_DB_URL = os.environ.get("RLS_TEST_DATABASE_URL")

pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(
        not _RLS_DB_URL,
        reason="RLS_TEST_DATABASE_URL non défini (PG migré avec 0007_plan_limits requis)",
    ),
]


@pytest.fixture
async def pool():
    p = await asyncpg.create_pool(_RLS_DB_URL, min_size=1, max_size=2)
    try:
        yield p
    finally:
        await p.close()


@pytest.mark.asyncio
async def test_plan_limits_seede_free_et_pro(pool):
    rows = await pool.fetch("SELECT plan FROM plan_limits ORDER BY plan")
    plans = {r["plan"] for r in rows}
    assert {"free", "pro"} <= plans


@pytest.mark.asyncio
async def test_resolve_bornes_du_tenant_legacy(pool):
    """Le tenant legacy démarre au plan free (DEFAULT) → bornes free résolues."""
    service = QuotaService(db_pool=pool, redis_client=fakeredis.FakeAsyncRedis(decode_responses=True))
    limits = await service._resolve_limits(LEGACY_TENANT_ID)
    assert limits is not None
    assert limits.plan == "free"
    assert limits.max_analyses_per_month == 50
    assert limits.max_screener_tickers == 5


@pytest.mark.asyncio
async def test_429_au_dela_du_quota_et_autorisation_sous_quota(pool):
    redis = fakeredis.FakeAsyncRedis(decode_responses=True)
    service = QuotaService(db_pool=pool, redis_client=redis)
    key = _month_key(LEGACY_TENANT_ID, datetime.now(timezone.utc))

    # Sous la borne (49/50) → autorisé.
    await redis.set(key, 49)
    await service.check(LEGACY_TENANT_ID)

    # À la borne (50/50) → 429.
    await redis.set(key, 50)
    with pytest.raises(QuotaExceededError) as exc:
        await service.check(LEGACY_TENANT_ID)
    assert exc.value.limit == 50


@pytest.mark.asyncio
async def test_borne_screener_par_plan(pool):
    service = QuotaService(db_pool=pool, redis_client=fakeredis.FakeAsyncRedis(decode_responses=True))
    await service.check_screener_size(5, LEGACY_TENANT_ID)  # = borne free → OK
    with pytest.raises(QuotaExceededError):
        await service.check_screener_size(6, LEGACY_TENANT_ID)  # > borne free → 429


@pytest.mark.asyncio
async def test_increment_pose_le_compteur_mensuel(pool):
    redis = fakeredis.FakeAsyncRedis(decode_responses=True)
    service = QuotaService(db_pool=pool, redis_client=redis)
    tenant = UUID(str(LEGACY_TENANT_ID))
    await service.increment(tenant)
    key = _month_key(tenant, datetime.now(timezone.utc))
    assert int(await redis.get(key)) == 1
    assert await redis.ttl(key) > 0  # TTL posé au premier incrément
