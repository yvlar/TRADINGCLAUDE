"""Tests CI standard pour ApiKeyService et endpoints /admin/keys — Sprint 62.

Aucun appel Claude réel. asyncpg est mocké via AsyncMock.
CI standard : pytest -m "not e2e and not evals"
"""
from __future__ import annotations

import hashlib
import uuid
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock

import pytest
import pytest_asyncio
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from app.api.endpoints.admin import router as admin_router
from app.services.api_key_service import ApiKeyRecord, ApiKeyService

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_NOW = datetime(2026, 5, 14, 12, 0, 0, tzinfo=timezone.utc)
_KEY_ID = uuid.UUID("11111111-1111-1111-1111-111111111111")
_TOKEN = "test-bearer-token-xyz"
_HASH = hashlib.sha256(_TOKEN.encode()).hexdigest()


def _make_row(
    *,
    key_id: uuid.UUID = _KEY_ID,
    name: str = "Yves",
    role: str = "admin",
    active: bool = True,
    last_used_at: datetime | None = None,
    expires_at: datetime | None = None,
) -> dict:
    return {
        "id": key_id,
        "name": name,
        "role": role,
        "active": active,
        "created_at": _NOW,
        "last_used_at": last_used_at,
        "expires_at": expires_at,
    }


def _make_pool(
    *,
    fetchrow_return=None,
    fetch_return=None,
    execute_return: str = "UPDATE 1",
) -> AsyncMock:
    pool = AsyncMock()
    pool.fetchrow = AsyncMock(return_value=fetchrow_return)
    pool.fetch = AsyncMock(return_value=fetch_return or [])
    pool.execute = AsyncMock(return_value=execute_return)
    return pool


def _make_admin_app(svc: AsyncMock) -> FastAPI:
    """App minimale avec admin_router — sans middleware d'auth (tests isolation)."""
    app = FastAPI()
    app.state.api_key_service = svc

    @app.middleware("http")
    async def inject_api_key_record(request, call_next):
        # Simule l'env admin (clé env) → record = None
        request.state.api_key_record = None
        return await call_next(request)

    app.include_router(admin_router)
    return app


# ---------------------------------------------------------------------------
# Groupe 1 : ApiKeyRecord schema
# ---------------------------------------------------------------------------


class TestApiKeyRecordSchema:

    def test_schema_valide_champs_requis(self):
        record = ApiKeyRecord(
            id=_KEY_ID,
            name="Marie",
            role="reader",
            active=True,
            created_at=_NOW,
            last_used_at=None,
            expires_at=None,
        )
        assert record.name == "Marie"
        assert record.role == "reader"
        assert record.active is True
        assert record.last_used_at is None

    def test_schema_expires_at_none_valide(self):
        record = ApiKeyRecord(
            id=_KEY_ID,
            name="Admin",
            role="admin",
            active=True,
            created_at=_NOW,
            last_used_at=_NOW,
            expires_at=None,
        )
        assert record.expires_at is None
        assert record.last_used_at == _NOW


# ---------------------------------------------------------------------------
# Groupe 2 : validate_key()
# ---------------------------------------------------------------------------


class TestValidateKey:

    @pytest.mark.asyncio
    async def test_validate_key_retourne_none_si_token_inconnu(self):
        pool = _make_pool(fetchrow_return=None)
        svc = ApiKeyService(db_pool=pool)
        result = await svc.validate_key("token-inconnu")
        assert result is None

    @pytest.mark.asyncio
    async def test_validate_key_retourne_none_si_cle_inactive(self):
        row = _make_row(active=False)
        pool = _make_pool(fetchrow_return=row)
        svc = ApiKeyService(db_pool=pool)
        result = await svc.validate_key(_TOKEN)
        assert result is None

    @pytest.mark.asyncio
    async def test_validate_key_retourne_none_si_cle_expiree(self):
        expiry = _NOW - timedelta(hours=1)
        row = _make_row(expires_at=expiry)
        pool = _make_pool(fetchrow_return=row)
        svc = ApiKeyService(db_pool=pool)
        result = await svc.validate_key(_TOKEN)
        assert result is None

    @pytest.mark.asyncio
    async def test_validate_key_retourne_record_si_valide(self):
        row = _make_row(expires_at=_NOW + timedelta(days=30))
        pool = _make_pool(fetchrow_return=row)
        svc = ApiKeyService(db_pool=pool)
        result = await svc.validate_key(_TOKEN)
        assert result is not None
        assert result.name == "Yves"
        assert result.role == "admin"
        assert result.active is True


# ---------------------------------------------------------------------------
# Groupe 3 : create_key()
# ---------------------------------------------------------------------------


class TestCreateKey:

    @pytest.mark.asyncio
    async def test_create_key_retourne_tuple_token_et_record(self):
        new_id = uuid.uuid4()
        row = _make_row(key_id=new_id, name="Marie", role="reader")
        pool = _make_pool(fetchrow_return=row)
        svc = ApiKeyService(db_pool=pool)
        token, record = await svc.create_key(name="Marie", role="reader")
        assert isinstance(token, str)
        assert len(token) > 10
        assert record.name == "Marie"
        assert record.role == "reader"
        assert record.id == new_id
        # Le token clair n'est pas le hash stocké
        assert token != hashlib.sha256(token.encode()).hexdigest()


# ---------------------------------------------------------------------------
# Groupe 4 : record_usage()
# ---------------------------------------------------------------------------


class TestRecordUsage:

    @pytest.mark.asyncio
    async def test_record_usage_appelle_execute(self):
        pool = _make_pool()
        svc = ApiKeyService(db_pool=pool)
        await svc.record_usage(_KEY_ID)
        pool.execute.assert_awaited_once()
        call_args = pool.execute.call_args
        assert str(_KEY_ID) in str(call_args)


# ---------------------------------------------------------------------------
# Groupe 5 : endpoints /admin/keys
# ---------------------------------------------------------------------------


class TestAdminEndpoints:

    @pytest_asyncio.fixture
    async def admin_client(self):
        new_id = uuid.uuid4()
        mock_row = _make_row(key_id=new_id, name="Test", role="reader")
        mock_record = ApiKeyRecord(
            id=new_id,
            name="Test",
            role="reader",
            active=True,
            created_at=_NOW,
            last_used_at=None,
            expires_at=None,
        )
        mock_svc = AsyncMock(spec=ApiKeyService)
        mock_svc.create_key = AsyncMock(return_value=("token-clair-xyz", mock_record))
        mock_svc.list_keys = AsyncMock(return_value=[mock_record])
        mock_svc.revoke_key = AsyncMock(return_value=True)
        app = _make_admin_app(mock_svc)
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            yield c

    @pytest.mark.asyncio
    async def test_post_admin_keys_retourne_201_avec_token(self, admin_client):
        resp = await admin_client.post("/admin/keys", json={"name": "Test", "role": "reader"})
        assert resp.status_code == 201
        body = resp.json()
        assert "token" in body
        assert body["token"] == "token-clair-xyz"
        assert body["key"]["name"] == "Test"

    @pytest.mark.asyncio
    async def test_get_admin_keys_retourne_200(self, admin_client):
        resp = await admin_client.get("/admin/keys")
        assert resp.status_code == 200
        body = resp.json()
        assert isinstance(body, list)
        assert len(body) == 1
        assert body[0]["name"] == "Test"

    @pytest.mark.asyncio
    async def test_delete_admin_keys_retourne_200(self, admin_client):
        key_id = str(uuid.uuid4())
        resp = await admin_client.delete(f"/admin/keys/{key_id}")
        assert resp.status_code == 200
        body = resp.json()
        assert body["revoked"] is True


# ---------------------------------------------------------------------------
# Groupe 6 : Rétrocompatibilité
# ---------------------------------------------------------------------------


class TestRetrocompatibilite:

    @pytest.mark.asyncio
    async def test_retrocompatibilite_api_key_env_sans_service(self):
        """Si ApiKeyService absent, API_KEY env suffit — comportement original."""
        from app.middleware.auth import BearerTokenMiddleware

        test_key = "my-env-api-key"
        mini_app = FastAPI()
        mini_app.add_middleware(BearerTokenMiddleware, api_key=test_key)

        @mini_app.get("/protected")
        async def protected():
            return {"ok": True}

        async with AsyncClient(
            transport=ASGITransport(app=mini_app), base_url="http://test"
        ) as c:
            # Sans token → 401
            r_no_token = await c.get("/protected")
            assert r_no_token.status_code == 401

            # Token env correct → 200
            r_valid = await c.get("/protected", headers={"Authorization": f"Bearer {test_key}"})
            assert r_valid.status_code == 200

            # Mauvais token → 401
            r_bad = await c.get("/protected", headers={"Authorization": "Bearer mauvais"})
            assert r_bad.status_code == 401
