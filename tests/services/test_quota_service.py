"""Tests unitaires du QuotaService (E4-S2) — bornes de plan par tenant, sans DB ni Redis réels."""
from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import AsyncMock
from uuid import UUID

import pytest

from app.services.quota_service import (
    QuotaExceededError,
    QuotaService,
    _month_key,
    _seconds_until_month_end,
)

_TENANT = UUID("00000000-0000-0000-0000-0000000000aa")
_FREE_ROW = {
    "plan": "free",
    "max_analyses_per_month": 50,
    "max_screener_tickers": 5,
    "retention_days": 30,
}


def _service(*, plan_row: dict | None = _FREE_ROW, count: str | None = None) -> tuple[QuotaService, AsyncMock, AsyncMock]:
    """Fabrique un QuotaService avec db.fetchrow et redis mockés ; retourne (service, db, redis)."""
    db = AsyncMock()
    db.fetchrow = AsyncMock(return_value=plan_row)
    redis = AsyncMock()
    redis.get = AsyncMock(return_value=count)
    redis.incr = AsyncMock(return_value=1)
    redis.expire = AsyncMock(return_value=True)
    return QuotaService(db_pool=db, redis_client=redis), db, redis


@pytest.mark.asyncio
async def test_resolve_plan_vers_bornes():
    service, db, _ = _service()
    limits = await service._resolve_limits(_TENANT)
    assert limits is not None
    assert limits.plan == "free"
    assert limits.max_analyses_per_month == 50
    assert limits.max_screener_tickers == 5
    # La résolution joint tenants → plan_limits en une requête.
    assert db.fetchrow.await_count == 1


@pytest.mark.asyncio
async def test_sous_la_borne_autorise():
    service, _, _ = _service(count="49")
    await service.check(_TENANT)  # 49 < 50 → ne lève pas


@pytest.mark.asyncio
async def test_a_la_borne_leve():
    service, _, _ = _service(count="50")
    with pytest.raises(QuotaExceededError) as exc:
        await service.check(_TENANT)
    assert exc.value.plan == "free"
    assert exc.value.used == 50
    assert exc.value.limit == 50
    assert exc.value.retry_after_s and exc.value.retry_after_s > 0


@pytest.mark.asyncio
async def test_increment_pose_expire_au_premier_incr():
    service, _, redis = _service()
    redis.incr = AsyncMock(return_value=1)
    await service.increment(_TENANT)
    redis.incr.assert_awaited_once()
    redis.expire.assert_awaited_once()


@pytest.mark.asyncio
async def test_increment_ne_repose_pas_expire_apres_le_premier():
    service, _, redis = _service()
    redis.incr = AsyncMock(return_value=7)  # clé déjà existante ce mois
    await service.increment(_TENANT)
    redis.expire.assert_not_awaited()


@pytest.mark.asyncio
async def test_check_and_increment_incremente():
    service, _, redis = _service(count="10")
    await service.check_and_increment(_TENANT)
    redis.incr.assert_awaited_once()


@pytest.mark.asyncio
async def test_screener_au_dela_de_la_borne_leve():
    service, _, _ = _service()
    with pytest.raises(QuotaExceededError) as exc:
        await service.check_screener_size(6, _TENANT)  # plan free max 5
    assert exc.value.limit == 5
    assert exc.value.retry_after_s is None  # borne de taille, pas temporelle


@pytest.mark.asyncio
async def test_screener_sous_la_borne_autorise():
    service, _, _ = _service()
    await service.check_screener_size(5, _TENANT)  # exactement la borne → autorisé


@pytest.mark.asyncio
async def test_plan_introuvable_fail_open():
    """Tenant/plan non résolu → aucune borne appliquée (ni check ni screener ne lèvent)."""
    service, _, _ = _service(plan_row=None)
    await service.check(_TENANT)
    await service.check_screener_size(999, _TENANT)


@pytest.mark.asyncio
async def test_redis_en_panne_fail_open_a_la_lecture():
    """Panne Redis à la lecture → compteur 0 → requête autorisée (fail-open documenté)."""
    service, _, redis = _service()
    redis.get = AsyncMock(side_effect=ConnectionError("redis down"))
    await service.check(_TENANT)  # ne lève pas malgré la panne


@pytest.mark.asyncio
async def test_redis_en_panne_fail_open_a_l_increment():
    service, _, redis = _service()
    redis.incr = AsyncMock(side_effect=ConnectionError("redis down"))
    await service.increment(_TENANT)  # avalé, pas de propagation


def test_month_key_format():
    now = datetime(2026, 6, 6, 12, 0, tzinfo=timezone.utc)
    assert _month_key(_TENANT, now) == f"quota:{_TENANT}:2026-06"


def test_seconds_until_month_end_juin():
    now = datetime(2026, 6, 6, 0, 0, tzinfo=timezone.utc)
    # Du 6 juin 00:00 au 1er juillet 00:00 = 25 jours.
    assert _seconds_until_month_end(now) == 25 * 24 * 3600


def test_seconds_until_month_end_decembre_bascule_annee():
    now = datetime(2026, 12, 31, 0, 0, tzinfo=timezone.utc)
    assert _seconds_until_month_end(now) == 24 * 3600  # → 1er janvier 2027


# ---- read_status (E5-S6) : lecture seule du quota ----


@pytest.mark.asyncio
async def test_read_status_plan_free_avec_consommation():
    """K analyses consommées → used=K, remaining=limit−K, plan résolu depuis plan_limits."""
    service, db, _ = _service(count="12")
    status = await service.read_status(_TENANT)
    assert status.plan == "free"
    assert status.used == 12
    assert status.limit == 50
    assert status.remaining == 38
    # La résolution du plan passe par la jointure tenants → plan_limits (réutilisée, pas dupliquée).
    assert db.fetchrow.await_count == 1


@pytest.mark.asyncio
async def test_read_status_reset_at_est_le_premier_du_mois_suivant():
    service, _, _ = _service(count="0")
    status = await service.read_status(_TENANT)
    # Bascule au 1er du mois suivant à 00:00 UTC (jour 1, heure 0).
    assert status.reset_at.day == 1
    assert status.reset_at.hour == 0
    assert status.reset_at.tzinfo is not None


@pytest.mark.asyncio
async def test_read_status_compteur_a_zero_remaining_egal_limite():
    service, _, _ = _service(count=None)  # aucune clé Redis ce mois
    status = await service.read_status(_TENANT)
    assert status.used == 0
    assert status.remaining == 50


@pytest.mark.asyncio
async def test_read_status_n_incremente_jamais_le_compteur():
    """Lecture seule : aucun incr/expire Redis déclenché par read_status."""
    service, _, redis = _service(count="5")
    await service.read_status(_TENANT)
    redis.get.assert_awaited_once()
    redis.incr.assert_not_awaited()
    redis.expire.assert_not_awaited()


@pytest.mark.asyncio
async def test_read_status_plan_introuvable_fail_open_neutre():
    """Plan non résolu → réponse neutre (limit/remaining None), jamais d'erreur."""
    service, _, redis = _service(plan_row=None)
    status = await service.read_status(_TENANT)
    assert status.plan == "unknown"
    assert status.limit is None
    assert status.remaining is None
    assert status.used == 0
    # Plan absent → on n'a même pas tenté de lire le compteur Redis.
    redis.get.assert_not_awaited()


@pytest.mark.asyncio
async def test_read_status_redis_en_panne_fail_open():
    """Panne Redis à la lecture → used=0 / remaining=limite (pas d'exception)."""
    service, _, redis = _service()
    redis.get = AsyncMock(side_effect=ConnectionError("redis down"))
    status = await service.read_status(_TENANT)
    assert status.used == 0
    assert status.remaining == 50


@pytest.mark.asyncio
async def test_read_status_db_en_panne_fail_open_neutre():
    """Panne DB à la résolution du plan → réponse neutre, jamais d'exception (pas de 500)."""
    service, db, _ = _service()
    db.fetchrow = AsyncMock(side_effect=ConnectionError("postgres down"))
    status = await service.read_status(_TENANT)
    assert status.plan == "unknown"
    assert status.limit is None
    assert status.remaining is None
    assert status.used == 0
