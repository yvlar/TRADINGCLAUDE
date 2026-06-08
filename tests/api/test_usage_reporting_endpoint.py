"""Tests d'intégration — endpoint GET /usage/reporting (auth-scoped, curseur de report Stripe E5-S2)."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest
import pytest_asyncio

from app.api.main import app

# Curseur fictif : dernière fenêtre rapportée à Stripe pour le tenant courant.
_REPORTED_THROUGH = datetime(2026, 6, 1, 12, 0, tzinfo=timezone.utc)


@pytest.fixture
def _mock_auth_token_service():
    mock = AsyncMock()
    mock.decode_access_token = MagicMock(
        return_value={
            "sub": str(uuid.uuid4()),
            "email": "test@test.com",
            "role": "reader",
            "jti": str(uuid.uuid4()),
            "exp": 9_999_999_999,
        }
    )
    mock.is_jti_blacklisted.return_value = False
    return mock


@pytest_asyncio.fixture
async def reporting_client(client, _mock_auth_token_service):
    """Client avec auth mocké + StripeService (curseur) et UsageEventService (COUNT) mockés."""
    prev_auth = getattr(app.state, "auth_token_service", None)
    prev_usage = getattr(app.state, "usage_event_service", None)
    prev_stripe = getattr(app.state, "stripe_service", None)
    app.state.auth_token_service = _mock_auth_token_service
    # Par défaut : curseur posé + 7 événements en attente (le COUNT est mocké, pas la DB).
    mock_stripe = AsyncMock()
    mock_stripe.get_usage_reported_through = AsyncMock(return_value=_REPORTED_THROUGH)
    mock_usage = AsyncMock()
    mock_usage.count_events_in_window = AsyncMock(return_value=7)
    app.state.stripe_service = mock_stripe
    app.state.usage_event_service = mock_usage
    try:
        yield client
    finally:
        # Restaure l'état partagé de `app` — évite la fuite des mocks aux tests suivants.
        app.state.auth_token_service = prev_auth
        app.state.usage_event_service = prev_usage
        app.state.stripe_service = prev_stripe


_COOKIE = {"access_token": "fake-jwt-access-token"}


@pytest.mark.asyncio
async def test_reporting_sans_session_renvoie_401(reporting_client):
    response = await reporting_client.get("/usage/reporting")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_reporting_avec_curseur_renvoie_pending(reporting_client):
    """Curseur posé → reported_through ISO + pending_events = COUNT sur la fenêtre non rapportée."""
    response = await reporting_client.get("/usage/reporting", cookies=_COOKIE)
    assert response.status_code == 200
    body = response.json()
    assert body["pending_events"] == 7
    assert body["reported_through"].startswith("2026-06-01T12:00:00")


@pytest.mark.asyncio
async def test_reporting_compte_la_fenetre_depuis_le_curseur(reporting_client):
    """Le COUNT est borné à la fenêtre `(reported_through, now]` — borne basse = le curseur lu."""
    await reporting_client.get("/usage/reporting", cookies=_COOKIE)
    args, _ = app.state.usage_event_service.count_events_in_window.call_args
    since, until = args
    assert since == _REPORTED_THROUGH
    assert until > since  # `now()` strictement après le curseur


@pytest.mark.asyncio
async def test_reporting_sans_abonnement_renvoie_none_et_total(reporting_client):
    """Pas d'abonnement → reported_through None ; le COUNT couvre tout l'historique (since=None)."""
    app.state.stripe_service.get_usage_reported_through = AsyncMock(return_value=None)
    app.state.usage_event_service.count_events_in_window = AsyncMock(return_value=42)
    response = await reporting_client.get("/usage/reporting", cookies=_COOKIE)
    assert response.status_code == 200
    body = response.json()
    assert body["reported_through"] is None
    assert body["pending_events"] == 42
    since, _ = app.state.usage_event_service.count_events_in_window.call_args[0]
    assert since is None
