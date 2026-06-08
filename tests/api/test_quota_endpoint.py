"""Tests d'intégration — endpoint GET /quota (auth-scoped, lecture seule du quota mensuel E5-S6)."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest
import pytest_asyncio

from app.api.main import app
from app.services.quota_service import QuotaStatus


def _sample_status(*, used: int = 12, limit: int | None = 50) -> QuotaStatus:
    remaining = None if limit is None else max(0, limit - used)
    return QuotaStatus(
        plan="free",
        used=used,
        limit=limit,
        remaining=remaining,
        reset_at=datetime(2026, 7, 1, 0, 0, tzinfo=timezone.utc),
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
async def quota_client(client, _mock_auth_token_service):
    """Client avec auth_token_service mocké et un quota_service dont read_status est mocké."""
    prev_auth = getattr(app.state, "auth_token_service", None)
    prev_quota = getattr(app.state, "quota_service", None)
    app.state.auth_token_service = _mock_auth_token_service
    mock_service = AsyncMock()
    mock_service.read_status = AsyncMock(return_value=_sample_status())
    app.state.quota_service = mock_service
    try:
        yield client
    finally:
        app.state.auth_token_service = prev_auth
        app.state.quota_service = prev_quota


_COOKIE = {"access_token": "fake-jwt-access-token"}


@pytest.mark.asyncio
async def test_quota_sans_session_renvoie_401(quota_client):
    response = await quota_client.get("/quota")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_quota_authentifie_renvoie_plan_used_remaining(quota_client):
    response = await quota_client.get("/quota", cookies=_COOKIE)
    assert response.status_code == 200
    body = response.json()
    assert body["plan"] == "free"
    assert body["used"] == 12
    assert body["limit"] == 50
    assert body["remaining"] == 38
    assert body["reset_at"].startswith("2026-07-01")


@pytest.mark.asyncio
async def test_quota_lecture_seule_n_incremente_pas(quota_client):
    """L'endpoint appelle read_status (lecture) et jamais check/increment (mutation)."""
    await quota_client.get("/quota", cookies=_COOKIE)
    app.state.quota_service.read_status.assert_awaited_once()
    app.state.quota_service.increment.assert_not_awaited()
    app.state.quota_service.check.assert_not_awaited()


@pytest.mark.asyncio
async def test_quota_plan_non_resolu_renvoie_reponse_neutre(quota_client):
    """Fail-open : plan non résolu côté service → limit/remaining None, pas de 500."""
    app.state.quota_service.read_status = AsyncMock(
        return_value=QuotaStatus(
            plan="unknown",
            used=0,
            limit=None,
            remaining=None,
            reset_at=datetime(2026, 7, 1, 0, 0, tzinfo=timezone.utc),
        )
    )
    response = await quota_client.get("/quota", cookies=_COOKIE)
    assert response.status_code == 200
    body = response.json()
    assert body["plan"] == "unknown"
    assert body["limit"] is None
    assert body["remaining"] is None


@pytest.mark.asyncio
async def test_quota_ne_lit_pas_tenant_id_en_query(quota_client):
    """L'isolation vient du contexte tenant serveur — un tenant_id en query est ignoré."""
    await quota_client.get(
        "/quota", params={"tenant_id": str(uuid.uuid4())}, cookies=_COOKIE
    )
    # read_status est appelé sans argument tenant (résolu par le ContextVar serveur).
    args, kwargs = app.state.quota_service.read_status.call_args
    assert args == ()
    assert kwargs == {}
