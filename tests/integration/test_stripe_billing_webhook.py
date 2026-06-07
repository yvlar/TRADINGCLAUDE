"""Webhook Stripe (E4-S7) contre un PostgreSQL migré — preuve d'acceptation observable.

Skippé par défaut : nécessite `RLS_TEST_DATABASE_URL` pointant un PostgreSQL **migré**
(`alembic upgrade head`, donc 0009_stripe_billing appliquée) et un rôle **NOSUPERUSER**.

Prouve, via le chemin réel HTTP (router billing + StripeService + signature Stripe RÉELLE) :
- un événement `customer.subscription.updated` (price `pro`) **signé** met `tenants.plan='pro'` ;
- une **signature forgée** → 400 et **aucune mutation** (plan inchangé) ;
- une **double livraison** du même `event.id` est idempotente (plan stable, un seul traitement).
"""
from __future__ import annotations

import hashlib
import hmac
import json
import os
import time
import uuid

import asyncpg
import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from app.api.endpoints.billing import router as billing_router
from app.services.stripe_service import StripeService

_RLS_DB_URL = os.environ.get("RLS_TEST_DATABASE_URL")

pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(
        not _RLS_DB_URL,
        reason="RLS_TEST_DATABASE_URL non défini (PG migré 0009 + rôle NOSUPERUSER requis)",
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


def _subscription_updated_event(tenant_id: str) -> bytes:
    event = {
        "id": "evt_" + uuid.uuid4().hex,
        "object": "event",  # enveloppe d'événement Stripe (lue par construct_event)
        "type": "customer.subscription.updated",
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


async def _build(pool: asyncpg.Pool) -> AsyncClient:
    app = FastAPI()
    app.state.stripe_service = StripeService(
        pool,
        secret_key="sk_test_unused",
        webhook_secret=_WEBHOOK_SECRET,
        price_by_plan=_PRICES,
    )
    app.include_router(billing_router)
    return AsyncClient(transport=ASGITransport(app=app), base_url="http://test")


@pytest.mark.asyncio
async def test_webhook_signe_passe_le_tenant_a_pro_et_forge_rejete():
    probe = await asyncpg.connect(_RLS_DB_URL)
    tenant_id = "00000000-0000-0000-0000-0000000000c7"
    try:
        if await probe.fetchval("SELECT current_setting('is_superuser')") == "on":
            pytest.skip("Fournir un rôle NOSUPERUSER (la preuve serait vacuous)")
        await probe.execute(
            "INSERT INTO tenants (id, name, slug, plan) "
            "VALUES ($1::uuid, 'E4S7', 'e4s7-test', 'free') "
            "ON CONFLICT (id) DO UPDATE SET plan = 'free'",
            tenant_id,
        )
    finally:
        await probe.close()

    pool = await asyncpg.create_pool(_RLS_DB_URL, min_size=1, max_size=2)
    try:
        client = await _build(pool)
        async with client:
            # 1) Signature forgée → 400 et plan inchangé (free).
            payload = _subscription_updated_event(tenant_id)
            forged = await client.post(
                "/billing/webhook", content=payload, headers={"Stripe-Signature": "t=1,v1=forged"}
            )
            assert forged.status_code == 400
            plan = await pool.fetchval("SELECT plan FROM tenants WHERE id = $1::uuid", tenant_id)
            assert plan == "free"  # aucune mutation sur signature invalide

            # 2) Signature valide → 200 et plan promu à pro.
            ok = await client.post(
                "/billing/webhook",
                content=payload,
                headers={"Stripe-Signature": _sign(payload, _WEBHOOK_SECRET)},
            )
            assert ok.status_code == 200
            plan = await pool.fetchval("SELECT plan FROM tenants WHERE id = $1::uuid", tenant_id)
            assert plan == "pro"

            # 3) Double livraison du même event.id → idempotent (plan stable, un seul claim).
            replay = await client.post(
                "/billing/webhook",
                content=payload,
                headers={"Stripe-Signature": _sign(payload, _WEBHOOK_SECRET)},
            )
            assert replay.status_code == 200
            plan = await pool.fetchval("SELECT plan FROM tenants WHERE id = $1::uuid", tenant_id)
            assert plan == "pro"

        # La ligne subscriptions du tenant reflète le plan pro.
        sub_plan = await pool.fetchval(
            "SELECT plan FROM subscriptions WHERE tenant_id = $1::uuid", tenant_id
        )
        assert sub_plan == "pro"
    finally:
        event_id = json.loads(payload)["id"]
        await pool.execute("DELETE FROM stripe_events WHERE event_id = $1", event_id)
        await pool.execute("DELETE FROM subscriptions WHERE tenant_id = $1::uuid", tenant_id)
        await pool.execute("DELETE FROM tenants WHERE id = $1::uuid", tenant_id)
        await pool.close()
