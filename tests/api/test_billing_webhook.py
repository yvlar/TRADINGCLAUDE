"""Tests d'intégration — endpoints /billing (webhook Stripe + checkout, E4-S7).

StripeService mocké : on valide le contrat HTTP (signature → 400, idempotence acquittée,
503 si non configuré, checkout authentifié). La preuve bout-en-bout avec signature réelle +
PG migré est dans `tests/integration/test_stripe_billing_webhook.py`.
"""
from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest
import pytest_asyncio

from app.api.main import app
from app.services.stripe_service import InvalidWebhookSignatureError, NoStripeCustomerError


@pytest_asyncio.fixture
async def billing_client(client):
    """Client avec un StripeService mocké (configuré, signature/handle stubés)."""
    prev = getattr(app.state, "stripe_service", None)
    service = MagicMock()
    service.is_configured = True
    service.verify_event = MagicMock(return_value={"id": "evt_1", "type": "x"})
    service.handle_event = AsyncMock(return_value=True)
    service.create_checkout_session = AsyncMock(return_value="https://stripe/checkout")
    service.create_billing_portal_session = AsyncMock(return_value="https://stripe/portal")
    app.state.stripe_service = service
    try:
        yield client, service
    finally:
        app.state.stripe_service = prev


@pytest.mark.asyncio
async def test_webhook_signature_invalide_renvoie_400_sans_traitement(billing_client):
    c, service = billing_client
    service.verify_event = MagicMock(side_effect=InvalidWebhookSignatureError("forgée"))
    resp = await c.post("/billing/webhook", content=b"{}", headers={"Stripe-Signature": "forged"})
    assert resp.status_code == 400
    service.handle_event.assert_not_awaited()  # aucune mutation sur signature invalide


@pytest.mark.asyncio
async def test_webhook_signature_valide_traite_et_200(billing_client):
    c, service = billing_client
    resp = await c.post("/billing/webhook", content=b"{}", headers={"Stripe-Signature": "t=1,v1=ok"})
    assert resp.status_code == 200
    assert resp.json() == {"received": True}
    service.handle_event.assert_awaited_once()


@pytest.mark.asyncio
async def test_webhook_event_duplique_reste_200(billing_client):
    """Une double livraison (handle_event → False) est acquittée 200 (idempotence côté service)."""
    c, service = billing_client
    service.handle_event = AsyncMock(return_value=False)
    resp = await c.post("/billing/webhook", content=b"{}", headers={"Stripe-Signature": "t=1,v1=ok"})
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_webhook_503_si_non_configure(billing_client):
    c, service = billing_client
    service.is_configured = False
    resp = await c.post("/billing/webhook", content=b"{}", headers={"Stripe-Signature": "x"})
    assert resp.status_code == 503


@pytest.mark.asyncio
async def test_checkout_sans_session_renvoie_401(billing_client):
    c, _ = billing_client
    resp = await c.post("/billing/checkout", json={"plan": "pro"})
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_checkout_authentifie_retourne_url(billing_client):
    c, service = billing_client
    auth = AsyncMock()
    auth.decode_access_token = MagicMock(
        return_value={
            "sub": str(uuid.uuid4()),
            "email": "t@t.com",
            "role": "reader",
            "jti": str(uuid.uuid4()),
            "exp": 9_999_999_999,
        }
    )
    auth.is_jti_blacklisted = AsyncMock(return_value=False)
    prev_auth = getattr(app.state, "auth_token_service", None)
    app.state.auth_token_service = auth
    try:
        resp = await c.post(
            "/billing/checkout", json={"plan": "pro"}, cookies={"access_token": "fake"}
        )
    finally:
        app.state.auth_token_service = prev_auth
    assert resp.status_code == 200
    assert resp.json() == {"checkout_url": "https://stripe/checkout"}
    service.create_checkout_session.assert_awaited_once()


def _authed_token_service():
    auth = AsyncMock()
    auth.decode_access_token = MagicMock(
        return_value={
            "sub": str(uuid.uuid4()),
            "email": "t@t.com",
            "role": "reader",
            "jti": str(uuid.uuid4()),
            "exp": 9_999_999_999,
        }
    )
    auth.is_jti_blacklisted = AsyncMock(return_value=False)
    return auth


@pytest.mark.asyncio
async def test_portal_sans_session_renvoie_401(billing_client):
    c, _ = billing_client
    resp = await c.post("/billing/portal")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_portal_authentifie_retourne_url(billing_client):
    c, service = billing_client
    prev_auth = getattr(app.state, "auth_token_service", None)
    app.state.auth_token_service = _authed_token_service()
    try:
        resp = await c.post("/billing/portal", cookies={"access_token": "fake"})
    finally:
        app.state.auth_token_service = prev_auth
    assert resp.status_code == 200
    assert resp.json() == {"portal_url": "https://stripe/portal"}
    service.create_billing_portal_session.assert_awaited_once()


@pytest.mark.asyncio
async def test_portal_sans_customer_renvoie_409(billing_client):
    c, service = billing_client
    service.create_billing_portal_session = AsyncMock(side_effect=NoStripeCustomerError("aucun"))
    prev_auth = getattr(app.state, "auth_token_service", None)
    app.state.auth_token_service = _authed_token_service()
    try:
        resp = await c.post("/billing/portal", cookies={"access_token": "fake"})
    finally:
        app.state.auth_token_service = prev_auth
    assert resp.status_code == 409


@pytest.mark.asyncio
async def test_portal_503_si_non_configure(billing_client):
    c, service = billing_client
    service.is_configured = False
    prev_auth = getattr(app.state, "auth_token_service", None)
    app.state.auth_token_service = _authed_token_service()
    try:
        resp = await c.post("/billing/portal", cookies={"access_token": "fake"})
    finally:
        app.state.auth_token_service = prev_auth
    assert resp.status_code == 503
