"""Bascule de plan Stripe → quotas (E5, Sprint 201) contre un PostgreSQL migré.

Skippé par défaut : nécessite `RLS_TEST_DATABASE_URL` pointant un PostgreSQL **migré**
(`alembic upgrade head`) et un rôle **NOSUPERUSER** — câblé dans le job CI
« Migrations — Alembic + RLS » (liste explicite de fichiers).

`test_stripe_billing_webhook.py` (E4-S7) prouve webhook signé → `tenants.plan`. Ces tests
prouvent la **promesse produit complète** : un `QuotaService` construit AVANT le webhook,
dans le même process, voit la **nouvelle** borne immédiatement après la bascule — sans
recréation de service ni redémarrage. Si un futur refactor introduisait un cache de plan
en mémoire (`_resolve_limits` mémoïsé…), la bascule resterait invisible jusqu'au reboot :
régression de facturation silencieuse que ces tests détectent.

Redis (compteur mensuel) est mocké `get→None` : le sprint prouve la résolution de PLAN,
pas le compteur — déjà couvert en unitaire par `test_quota_service.py`, fail-open compris.
"""
from __future__ import annotations

import hashlib
import hmac
import json
import os
import time
import uuid
from unittest.mock import AsyncMock

import asyncpg
import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from app.api.endpoints.billing import router as billing_router
from app.services.quota_service import QuotaService
from app.services.stripe_service import StripeService

_RLS_DB_URL = os.environ.get("RLS_TEST_DATABASE_URL")

pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(
        not _RLS_DB_URL,
        reason="RLS_TEST_DATABASE_URL non défini (PG migré + rôle NOSUPERUSER requis)",
    ),
]

_WEBHOOK_SECRET = "whsec_test_secret"
_PRICES = {"free": "price_free_test", "pro": "price_pro_test"}


def _sign(payload: bytes, secret: str) -> str:
    """Construit un en-tête `Stripe-Signature` valide (schéma t=…,v1=HMAC-SHA256)."""
    ts = int(time.time())
    signed = f"{ts}.".encode() + payload
    digest = hmac.new(secret.encode(), signed, hashlib.sha256).hexdigest()
    return f"t={ts},v1={digest}"


def _subscription_event(tenant_id: str, event_type: str) -> bytes:
    """Événement d'abonnement Stripe minimal (price pro) — `event_type` paramétré.

    Pour `customer.subscription.deleted`, le price est ignoré par `_sync_subscription`
    (repli forcé au plan par défaut) — le même objet sert aux deux sens de bascule."""
    event = {
        "id": "evt_" + uuid.uuid4().hex,
        "object": "event",
        "type": event_type,
        "data": {
            "object": {
                "id": "sub_" + uuid.uuid4().hex,
                "customer": "cus_" + uuid.uuid4().hex,
                "status": "active",
                "metadata": {"tenant_id": tenant_id},
                "items": {"data": [{"price": {"id": _PRICES["pro"]}}]},
            }
        },
    }
    return json.dumps(event).encode()


def _build_client(pool: asyncpg.Pool) -> AsyncClient:
    """App minimale : router billing + StripeService réel sur le pool fourni."""
    app = FastAPI()
    app.state.stripe_service = StripeService(
        pool,
        secret_key="sk_test_unused",
        webhook_secret=_WEBHOOK_SECRET,
        price_by_plan=_PRICES,
    )
    app.include_router(billing_router)
    return AsyncClient(transport=ASGITransport(app=app), base_url="http://test")


def _quota_service(pool: asyncpg.Pool) -> QuotaService:
    """QuotaService réel sur le même pool ; Redis mocké get→None (compteur hors périmètre)."""
    redis = AsyncMock()
    redis.get = AsyncMock(return_value=None)
    return QuotaService(db_pool=pool, redis_client=redis)


async def _seed_tenant(tenant_id: str, plan: str) -> None:
    """Pose (ou remet) le tenant de test au plan voulu — état de départ contrôlé."""
    probe = await asyncpg.connect(_RLS_DB_URL)
    try:
        if await probe.fetchval("SELECT current_setting('is_superuser')") == "on":
            pytest.skip("Fournir un rôle NOSUPERUSER (la preuve serait vacuous)")
        # Slug calculé côté Python : mêler `$1::uuid` et `right($1, …)` (texte) sur un même
        # paramètre rendrait l'inférence de type PostgreSQL ambiguë.
        await probe.execute(
            "INSERT INTO tenants (id, name, slug, plan) "
            "VALUES ($1::uuid, 'E5S201', $3, $2) "
            "ON CONFLICT (id) DO UPDATE SET plan = $2",
            tenant_id,
            plan,
            f"s201-{tenant_id[-4:]}",
        )
    finally:
        await probe.close()


async def _cleanup(pool: asyncpg.Pool, tenant_id: str, payload: bytes) -> None:
    """Retire les lignes de test (event journalisé, abonnement, tenant)."""
    event_id = json.loads(payload)["id"]
    await pool.execute("DELETE FROM stripe_events WHERE event_id = $1", event_id)
    await pool.execute("DELETE FROM subscriptions WHERE tenant_id = $1::uuid", tenant_id)
    await pool.execute("DELETE FROM tenants WHERE id = $1::uuid", tenant_id)


async def _expected_limits(pool: asyncpg.Pool) -> tuple[int, int]:
    """Bornes mensuelles free/pro lues dans `plan_limits` — jamais codées en dur.

    Garde de non-vacuité : si les deux plans partageaient la même borne, la bascule
    serait indétectable côté quota et le test prouverait du vide."""
    free = await pool.fetchval(
        "SELECT max_analyses_per_month FROM plan_limits WHERE plan = 'free'"
    )
    pro = await pool.fetchval(
        "SELECT max_analyses_per_month FROM plan_limits WHERE plan = 'pro'"
    )
    assert free is not None and pro is not None, "plan_limits non seedée (migration)"
    assert free != pro, "Bornes free/pro identiques — bascule indétectable (vacuité)"
    return free, pro


@pytest.mark.asyncio
async def test_upgrade_webhook_rend_la_borne_pro_visible_sans_redemarrage() -> None:
    """free→pro : le QuotaService construit AVANT le webhook voit la borne pro après."""
    tenant_id = "00000000-0000-0000-0000-0000000000c8"
    await _seed_tenant(tenant_id, "free")

    payload = _subscription_event(tenant_id, "customer.subscription.updated")
    pool = await asyncpg.create_pool(_RLS_DB_URL, min_size=1, max_size=2)
    try:
        limit_free, limit_pro = await _expected_limits(pool)
        quota = _quota_service(pool)

        # Pré-condition non vacue : le même service voit d'abord la borne free.
        before = await quota.read_status(uuid.UUID(tenant_id))
        assert before.plan == "free"
        assert before.limit == limit_free

        client = _build_client(pool)
        async with client:
            ok = await client.post(
                "/billing/webhook",
                content=payload,
                headers={"Stripe-Signature": _sign(payload, _WEBHOOK_SECRET)},
            )
            assert ok.status_code == 200

        plan = await pool.fetchval("SELECT plan FROM tenants WHERE id = $1::uuid", tenant_id)
        assert plan == "pro"  # parité E4-S7 (chemin webhook intact)

        # Cœur du sprint : le MÊME QuotaService (aucune recréation) reflète la bascule.
        after = await quota.read_status(uuid.UUID(tenant_id))
        assert after.plan == "pro"
        assert after.limit == limit_pro
        assert after.remaining == limit_pro  # compteur mocké à zéro → tout le quota pro
    finally:
        # `finally` imbriqué : un échec du nettoyage DB ne doit ni masquer l'échec
        # d'origine du test ni laisser le pool ouvert.
        try:
            await _cleanup(pool, tenant_id, payload)
        finally:
            await pool.close()


@pytest.mark.asyncio
async def test_downgrade_webhook_replie_la_borne_free_sans_redemarrage() -> None:
    """pro→free : `customer.subscription.deleted` replie plan ET borne vus par le quota."""
    tenant_id = "00000000-0000-0000-0000-0000000000c9"
    await _seed_tenant(tenant_id, "pro")

    payload = _subscription_event(tenant_id, "customer.subscription.deleted")
    pool = await asyncpg.create_pool(_RLS_DB_URL, min_size=1, max_size=2)
    try:
        limit_free, limit_pro = await _expected_limits(pool)
        quota = _quota_service(pool)

        before = await quota.read_status(uuid.UUID(tenant_id))
        assert before.plan == "pro"
        assert before.limit == limit_pro

        client = _build_client(pool)
        async with client:
            ok = await client.post(
                "/billing/webhook",
                content=payload,
                headers={"Stripe-Signature": _sign(payload, _WEBHOOK_SECRET)},
            )
            assert ok.status_code == 200

        plan = await pool.fetchval("SELECT plan FROM tenants WHERE id = $1::uuid", tenant_id)
        assert plan == "free"

        after = await quota.read_status(uuid.UUID(tenant_id))
        assert after.plan == "free"
        assert after.limit == limit_free
        assert after.remaining == limit_free  # symétrie upgrade : compteur mocké à zéro
    finally:
        # `finally` imbriqué : un échec du nettoyage DB ne doit ni masquer l'échec
        # d'origine du test ni laisser le pool ouvert.
        try:
            await _cleanup(pool, tenant_id, payload)
        finally:
            await pool.close()
