"""Tests d'intégration — endpoints GET/PUT /preferences/screener (auth-scoped)."""
from __future__ import annotations

import json
import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest
import pytest_asyncio

from app.api.main import app


class _FakePrefsPool:
    """Pool asyncpg minimal stateful — round-trip réel sur le SQL du service."""

    def __init__(self) -> None:
        self._store: dict[tuple[str, str], str] = {}

    async def fetchrow(self, query: str, *args):
        if "INSERT" in query:
            user_id, key, value_json = args
            self._store[(user_id, key)] = value_json
            return {"value": value_json}
        # SELECT value FROM user_preferences WHERE user_id = $1 AND key = $2
        user_id, key = args
        stored = self._store.get((user_id, key))
        return {"value": stored} if stored is not None else None


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
async def prefs_client(client, _mock_auth_token_service):
    """Client avec auth_token_service mocké et un pool de préférences stateful."""
    app.state.auth_token_service = _mock_auth_token_service
    app.state.db_pool = _FakePrefsPool()
    yield client


_COOKIE = {"access_token": "fake-jwt-access-token"}


@pytest.mark.asyncio
async def test_get_screener_sans_session_renvoie_401(prefs_client):
    response = await prefs_client.get("/preferences/screener")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_put_screener_sans_session_renvoie_401(prefs_client):
    response = await prefs_client.put(
        "/preferences/screener", json={"sort": {"key": "ticker", "asc": True}, "filter": []}
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_get_screener_vide_renvoie_null(prefs_client):
    response = await prefs_client.get("/preferences/screener", cookies=_COOKIE)
    assert response.status_code == 200
    assert response.json() == {"sort": None, "filter": None}


@pytest.mark.asyncio
async def test_put_puis_get_round_trip(prefs_client):
    body = {"sort": {"key": "composite", "asc": False}, "filter": ["FORT", "MODÉRÉ"]}
    put = await prefs_client.put("/preferences/screener", json=body, cookies=_COOKIE)
    assert put.status_code == 200
    assert put.json() == body

    get = await prefs_client.get("/preferences/screener", cookies=_COOKIE)
    assert get.status_code == 200
    assert get.json() == body


@pytest.mark.asyncio
async def test_put_idempotent_remplace_la_valeur(prefs_client):
    first = {"sort": {"key": "ticker", "asc": True}, "filter": ["FORT"]}
    second = {"sort": {"key": "score", "asc": False}, "filter": []}

    await prefs_client.put("/preferences/screener", json=first, cookies=_COOKIE)
    await prefs_client.put("/preferences/screener", json=second, cookies=_COOKIE)

    get = await prefs_client.get("/preferences/screener", cookies=_COOKIE)
    assert get.json() == second


@pytest.mark.asyncio
async def test_put_clef_de_tri_invalide_renvoie_422(prefs_client):
    response = await prefs_client.put(
        "/preferences/screener",
        json={"sort": {"key": "inconnu", "asc": True}, "filter": []},
        cookies=_COOKIE,
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_get_decode_jsonb_str(prefs_client):
    # asyncpg renvoie le JSONB comme str : le service doit le désérialiser
    pool: _FakePrefsPool = app.state.db_pool
    sub = app.state.auth_token_service.decode_access_token.return_value["sub"]
    pool._store[(sub, "screener")] = json.dumps(
        {"sort": {"key": "freshness", "asc": True}, "filter": None}
    )

    response = await prefs_client.get("/preferences/screener", cookies=_COOKIE)
    assert response.status_code == 200
    assert response.json() == {"sort": {"key": "freshness", "asc": True}, "filter": None}


@pytest.mark.asyncio
async def test_get_valeur_corrompue_traitee_comme_absente(prefs_client):
    # Préférence héritée/illisible : 200 avec champs null, pas un 500
    pool: _FakePrefsPool = app.state.db_pool
    sub = app.state.auth_token_service.decode_access_token.return_value["sub"]
    pool._store[(sub, "screener")] = json.dumps({"sort": {"key": "INVALIDE", "asc": 3}})

    response = await prefs_client.get("/preferences/screener", cookies=_COOKIE)
    assert response.status_code == 200
    assert response.json() == {"sort": None, "filter": None}
