"""Tests des endpoints d'authentification — Sprint login."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest
import pytest_asyncio

from app.api.main import app
from app.services.user_service import EmailAlreadyExistsError


def _make_user(email: str = "test@test.com", role: str = "reader") -> dict:
    """Fabrique un dict utilisateur pour les mocks."""
    return {
        "id": uuid.uuid4(),
        "email": email,
        "role": role,
        "is_active": True,
        "created_at": datetime(2026, 1, 1, tzinfo=timezone.utc),
        "hashed_password": "$argon2id$v=19$m=65536,t=2,p=2$hash$hash",
    }


@pytest.fixture
def _mock_user_service():
    mock = AsyncMock()
    user = _make_user()
    mock.create_user.return_value = user
    mock.authenticate.return_value = user
    mock.get_by_id.return_value = user
    mock.update_last_login.return_value = None
    mock.update_password.return_value = None
    mock._pool = AsyncMock()
    mock._pool.fetchrow.return_value = {"id": user["id"]}
    return mock


@pytest.fixture
def _mock_auth_token_service():
    mock = AsyncMock()
    mock.create_access_token.return_value = "fake-jwt-access-token"
    mock.create_refresh_token.return_value = "fake-refresh-uuid"
    mock.decode_access_token.return_value = {
        "sub": str(uuid.uuid4()),
        "email": "test@test.com",
        "role": "reader",
        "jti": str(uuid.uuid4()),
        "exp": 9_999_999_999,
    }
    mock.is_jti_blacklisted.return_value = False
    mock.blacklist_jti.return_value = None
    mock.invalidate_refresh_token.return_value = None
    mock.rotate_refresh_token.return_value = ("new-refresh-token", uuid.uuid4())
    return mock


@pytest.fixture
def _mock_password_reset_service():
    mock = MagicMock()
    mock.create_reset_token.return_value = "fake-reset-token"
    mock.verify_reset_token.return_value = uuid.uuid4()
    mock.send_reset_email = AsyncMock(return_value=None)
    return mock


@pytest_asyncio.fixture
async def auth_client(client, _mock_user_service, _mock_auth_token_service, _mock_password_reset_service):
    """Client HTTP avec services auth mockés dans app.state."""
    app.state.user_service = _mock_user_service
    app.state.auth_token_service = _mock_auth_token_service
    app.state.password_reset_service = _mock_password_reset_service
    yield client


# ---- POST /auth/register ----

@pytest.mark.asyncio
async def test_register_success(auth_client):
    response = await auth_client.post(
        "/auth/register",
        json={"email": "new@test.com", "password": "MonMotDePasse123!"},
    )
    assert response.status_code == 201
    data = response.json()
    assert "user" in data
    assert "email" in data["user"]


@pytest.mark.asyncio
async def test_register_duplicate_email(auth_client, _mock_user_service):
    _mock_user_service.create_user.side_effect = EmailAlreadyExistsError("email existe")
    response = await auth_client.post(
        "/auth/register",
        json={"email": "dup@test.com", "password": "MonMotDePasse123!"},
    )
    assert response.status_code == 409


@pytest.mark.asyncio
async def test_register_weak_password(auth_client):
    response = await auth_client.post(
        "/auth/register",
        json={"email": "test@test.com", "password": "court"},
    )
    assert response.status_code == 422


# ---- POST /auth/login ----

@pytest.mark.asyncio
async def test_login_success(auth_client):
    response = await auth_client.post(
        "/auth/login",
        json={"email": "test@test.com", "password": "MonMotDePasse123!"},
    )
    assert response.status_code == 200
    data = response.json()
    assert "user" in data


@pytest.mark.asyncio
async def test_login_wrong_password(auth_client, _mock_user_service):
    _mock_user_service.authenticate.return_value = None
    response = await auth_client.post(
        "/auth/login",
        json={"email": "test@test.com", "password": "mauvais-mdp"},
    )
    assert response.status_code == 401
    assert response.json()["detail"] == "Email ou mot de passe incorrect"


@pytest.mark.asyncio
async def test_login_rate_limit(auth_client):
    app.state.redis_pool.incr = AsyncMock(return_value=6)
    response = await auth_client.post(
        "/auth/login",
        json={"email": "test@test.com", "password": "MonMotDePasse123!"},
    )
    assert response.status_code == 429
    app.state.redis_pool.incr = AsyncMock(return_value=1)


# ---- POST /auth/logout ----

@pytest.mark.asyncio
async def test_logout_success(auth_client):
    response = await auth_client.post("/auth/logout")
    assert response.status_code == 204


# ---- GET /auth/me ----

@pytest.mark.asyncio
async def test_me_without_cookie(auth_client):
    response = await auth_client.get("/auth/me")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_me_with_valid_cookie(auth_client, _mock_user_service):
    user = _make_user()
    _mock_user_service.get_by_id.return_value = user
    response = await auth_client.get(
        "/auth/me",
        cookies={"access_token": "fake-jwt-access-token"},
    )
    assert response.status_code == 200
    data = response.json()
    assert "email" in data


# ---- POST /auth/forgot-password ----

@pytest.mark.asyncio
async def test_forgot_password_known_email(auth_client):
    response = await auth_client.post(
        "/auth/forgot-password",
        json={"email": "test@test.com"},
    )
    assert response.status_code == 204


@pytest.mark.asyncio
async def test_forgot_password_unknown_email(auth_client, _mock_user_service):
    _mock_user_service._pool.fetchrow.return_value = None
    response = await auth_client.post(
        "/auth/forgot-password",
        json={"email": "unknown@test.com"},
    )
    assert response.status_code == 204


# ---- POST /auth/reset-password ----

@pytest.mark.asyncio
async def test_reset_password_valid_token(auth_client, _mock_user_service):
    response = await auth_client.post(
        "/auth/reset-password",
        json={"token": "fake-reset-token", "new_password": "NouveauMdP123!"},
    )
    assert response.status_code == 204
    _mock_user_service.update_password.assert_called_once()


@pytest.mark.asyncio
async def test_reset_password_invalid_token(auth_client, _mock_password_reset_service):
    _mock_password_reset_service.verify_reset_token.return_value = None
    response = await auth_client.post(
        "/auth/reset-password",
        json={"token": "bad-token", "new_password": "NouveauMdP123!"},
    )
    assert response.status_code == 400
