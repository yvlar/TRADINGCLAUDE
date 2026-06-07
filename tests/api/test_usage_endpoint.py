"""Tests d'intégration — endpoint GET /usage (auth-scoped, agrégation usage_events E4-S5)."""
from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest
import pytest_asyncio

from app.api.main import app
from app.models.usage import UsageBySkill, UsageResponse


def _sample_response(days: int = 30) -> UsageResponse:
    return UsageResponse(
        period_days=days,
        total_cost_usd=0.03,
        total_tokens_input=3000,
        total_tokens_output=1500,
        by_skill=[
            UsageBySkill(
                skill="graham_analysis",
                cost_usd=0.02,
                tokens_input=2000,
                tokens_output=1000,
                events=2,
            ),
        ],
        daily_cost={"2026-06-06": 0.03},
    )


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
async def usage_client(client, _mock_auth_token_service):
    """Client avec auth_token_service mocké et un UsageEventService mocké."""
    prev_auth = getattr(app.state, "auth_token_service", None)
    prev_usage = getattr(app.state, "usage_event_service", None)
    app.state.auth_token_service = _mock_auth_token_service
    mock_service = AsyncMock()
    mock_service.aggregate = AsyncMock(return_value=_sample_response())
    app.state.usage_event_service = mock_service
    try:
        yield client
    finally:
        # Restaure l'état partagé de `app` — évite la fuite des mocks aux tests suivants.
        app.state.auth_token_service = prev_auth
        app.state.usage_event_service = prev_usage


_COOKIE = {"access_token": "fake-jwt-access-token"}


@pytest.mark.asyncio
async def test_usage_sans_session_renvoie_401(usage_client):
    response = await usage_client.get("/usage")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_usage_authentifie_renvoie_forme_agregee(usage_client):
    response = await usage_client.get("/usage", cookies=_COOKIE)
    assert response.status_code == 200
    body = response.json()
    assert body["period_days"] == 30
    assert body["total_cost_usd"] == 0.03
    assert body["total_tokens_input"] == 3000
    assert body["total_tokens_output"] == 1500
    assert body["by_skill"][0]["skill"] == "graham_analysis"
    assert body["by_skill"][0]["events"] == 2
    assert body["daily_cost"] == {"2026-06-06": 0.03}


@pytest.mark.asyncio
async def test_usage_transmet_days_au_service(usage_client):
    await usage_client.get("/usage", params={"days": 7}, cookies=_COOKIE)
    app.state.usage_event_service.aggregate.assert_awaited_once_with(days=7)


@pytest.mark.asyncio
@pytest.mark.parametrize("days", [0, 366, -1])
async def test_usage_days_hors_bornes_renvoie_422(usage_client, days):
    response = await usage_client.get("/usage", params={"days": days}, cookies=_COOKIE)
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_usage_ne_lit_pas_tenant_id_en_query(usage_client):
    """L'isolation vient de la RLS serveur — un tenant_id en query est ignoré (pas de filtre applicatif)."""
    await usage_client.get(
        "/usage", params={"tenant_id": str(uuid.uuid4())}, cookies=_COOKIE
    )
    # `days` reste au défaut ; aucun tenant_id n'est propagé au service.
    _, kwargs = app.state.usage_event_service.aggregate.call_args
    assert kwargs == {"days": 30}
