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
from app.models.tenant import LEGACY_TENANT_ID
from app.services.api_key_service import ApiKeyRecord, ApiKeyService

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_NOW = datetime(2026, 5, 14, 12, 0, 0, tzinfo=timezone.utc)
_KEY_ID = uuid.UUID("11111111-1111-1111-1111-111111111111")
_TENANT_ID = uuid.UUID("22222222-2222-2222-2222-222222222222")
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
    tenant_id: uuid.UUID = _TENANT_ID,
) -> dict:
    return {
        "id": key_id,
        "name": name,
        "role": role,
        "active": active,
        "created_at": _NOW,
        "last_used_at": last_used_at,
        "expires_at": expires_at,
        "tenant_id": tenant_id,
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
            tenant_id=_TENANT_ID,
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
            tenant_id=_TENANT_ID,
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

    @pytest.mark.asyncio
    async def test_validate_key_expose_le_tenant_de_la_cle(self):
        """E4-S3 : le tenant propriétaire est lu depuis la table et exposé sur le record."""
        row = _make_row(tenant_id=_TENANT_ID)
        pool = _make_pool(fetchrow_return=row)
        svc = ApiKeyService(db_pool=pool)
        result = await svc.validate_key(_TOKEN)
        assert result is not None
        assert result.tenant_id == _TENANT_ID
        # Le SELECT de validation doit demander la colonne tenant_id.
        assert "tenant_id" in str(pool.fetchrow.call_args)


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

    @pytest.mark.asyncio
    async def test_create_key_rattache_au_tenant_explicite(self):
        """E4-S3 : un tenant explicite est inséré tel quel (colonne tenant_id du INSERT)."""
        row = _make_row(tenant_id=_TENANT_ID)
        pool = _make_pool(fetchrow_return=row)
        svc = ApiKeyService(db_pool=pool)
        _, record = await svc.create_key(name="Marie", tenant_id=_TENANT_ID)
        assert record.tenant_id == _TENANT_ID
        call_args = pool.fetchrow.call_args
        assert "tenant_id" in str(call_args)
        # Position épinglée (5e param du INSERT) : attrape un futur réordonnancement de colonnes
        # que le simple `in` raterait. Lié en str (cast ::uuid), symétrique à UsageEventService.
        assert call_args.args[-1] == str(_TENANT_ID)

    @pytest.mark.asyncio
    async def test_create_key_defaut_legacy_hors_contexte(self):
        """Sans tenant explicite ni contexte posé → resolve_tenant retombe sur legacy."""
        row = _make_row(tenant_id=LEGACY_TENANT_ID)
        pool = _make_pool(fetchrow_return=row)
        svc = ApiKeyService(db_pool=pool)
        _, record = await svc.create_key(name="Marie")
        assert record.tenant_id == LEGACY_TENANT_ID
        assert str(LEGACY_TENANT_ID) in pool.fetchrow.call_args.args

    @pytest.mark.asyncio
    async def test_create_key_rattache_au_tenant_courant_du_contextvar(self):
        """Sans tenant explicite mais contexte posé → la clé hérite du tenant courant."""
        from app.db.tenant_context import reset_current_tenant, set_current_tenant

        row = _make_row(tenant_id=_TENANT_ID)
        pool = _make_pool(fetchrow_return=row)
        svc = ApiKeyService(db_pool=pool)
        token = set_current_tenant(_TENANT_ID)
        try:
            await svc.create_key(name="Marie")
        finally:
            reset_current_tenant(token)
        assert str(_TENANT_ID) in pool.fetchrow.call_args.args


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
            tenant_id=_TENANT_ID,
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


class TestMiddlewareThreadingTenant:
    """E4-S3 : le chemin clé API thread le tenant de la clé jusqu'au ContextVar.

    Réplique l'ordre de montage de production (`app/api/main.py`) : TenantContextMiddleware
    ajouté EN PREMIER (couche interne), BearerTokenMiddleware ensuite (couche externe qui
    pose `request.state.tenant_id`). L'endpoint lit `get_current_tenant()` pour prouver que
    le tenant de la clé atteint la couche consommée par la RLS / les quotas / le metering.
    """

    def _make_threaded_app(self, *, validate_return) -> FastAPI:
        from app.db.tenant_context import get_current_tenant
        from app.middleware.auth import BearerTokenMiddleware
        from app.middleware.tenant import TenantContextMiddleware

        app = FastAPI()
        svc = AsyncMock(spec=ApiKeyService)
        svc.validate_key = AsyncMock(return_value=validate_return)
        svc.record_usage = AsyncMock(return_value=None)
        app.state.api_key_service = svc

        @app.get("/whoami")
        async def whoami():
            return {"tenant": str(get_current_tenant())}

        # Ordre identique à production : interne (Tenant) ajouté avant externe (Bearer).
        app.add_middleware(TenantContextMiddleware)
        app.add_middleware(BearerTokenMiddleware, api_key="env-admin-key")
        return app

    def _record(self, tenant_id: uuid.UUID) -> ApiKeyRecord:
        return ApiKeyRecord(
            id=_KEY_ID,
            name="prog",
            role="reader",
            active=True,
            created_at=_NOW,
            last_used_at=None,
            expires_at=None,
            tenant_id=tenant_id,
        )

    @pytest.mark.asyncio
    async def test_cle_valide_thread_son_tenant(self):
        tenant = uuid.uuid4()
        app = self._make_threaded_app(validate_return=self._record(tenant))
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            resp = await c.get("/whoami", headers={"Authorization": "Bearer prog-token"})
        assert resp.status_code == 200
        assert resp.json()["tenant"] == str(tenant)

    @pytest.mark.asyncio
    async def test_cle_du_tenant_legacy_reste_legacy(self):
        app = self._make_threaded_app(validate_return=self._record(LEGACY_TENANT_ID))
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            resp = await c.get("/whoami", headers={"Authorization": "Bearer prog-token"})
        assert resp.status_code == 200
        assert resp.json()["tenant"] == str(LEGACY_TENANT_ID)

    @pytest.mark.asyncio
    async def test_cle_env_admin_sans_record_defaut_legacy(self):
        """Fallback clé env (record None : pas de tenant en DB) → tenant legacy."""
        app = self._make_threaded_app(validate_return=None)
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            resp = await c.get("/whoami", headers={"Authorization": "Bearer env-admin-key"})
        assert resp.status_code == 200
        assert resp.json()["tenant"] == str(LEGACY_TENANT_ID)


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
