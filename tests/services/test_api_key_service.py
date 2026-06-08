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

    @pytest.mark.asyncio
    async def test_create_key_audit_metadata_porte_le_tenant_effectif(self):
        """E4-S10 : la trace d'audit journalise le tenant_id effectif de la clé créée."""
        from app.services.audit_log_service import AuditLogService

        row = _make_row(tenant_id=_TENANT_ID)
        pool = _make_pool(fetchrow_return=row)
        audit = AsyncMock(spec=AuditLogService)
        svc = ApiKeyService(db_pool=pool, audit_log=audit)
        await svc.create_key(name="Marie", tenant_id=_TENANT_ID)
        metadata = audit.record.call_args.kwargs["metadata"]
        assert metadata["tenant_id"] == str(_TENANT_ID)


# ---------------------------------------------------------------------------
# Groupe 3b : tenant_exists()
# ---------------------------------------------------------------------------


class TestTenantExists:

    @pytest.mark.asyncio
    async def test_tenant_exists_vrai_si_ligne_presente(self):
        pool = _make_pool(fetchrow_return={"?column?": 1})
        svc = ApiKeyService(db_pool=pool)
        assert await svc.tenant_exists(_TENANT_ID) is True
        assert "tenants" in str(pool.fetchrow.call_args)

    @pytest.mark.asyncio
    async def test_tenant_exists_faux_si_absent(self):
        pool = _make_pool(fetchrow_return=None)
        svc = ApiKeyService(db_pool=pool)
        assert await svc.tenant_exists(_TENANT_ID) is False


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


# ---------------------------------------------------------------------------
# Groupe 7 : provisionnement de clé par tenant (E4-S10)
# ---------------------------------------------------------------------------


_TENANT_A = uuid.UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")
_TENANT_B = uuid.UUID("bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb")


class _InjectContextASGI:
    """Shim ASGI pur : pose `scope.state` (tenant + record admin) avant TenantContextMiddleware.

    Pure ASGI (et non `@app.middleware`) délibérément : `set_current_tenant` doit s'exécuter
    dans la MÊME tâche que l'endpoint pour que `get_current_tenant()` y soit visible.
    """

    def __init__(self, app, *, tenant_id, api_key_record, user_id=None, user_role=None) -> None:
        self.app = app
        self._tenant_id = tenant_id
        self._record = api_key_record
        self._user_id = user_id
        self._user_role = user_role

    async def __call__(self, scope, receive, send):
        if scope["type"] == "http":
            state = scope.setdefault("state", {})
            state["tenant_id"] = self._tenant_id
            state["api_key_record"] = self._record
            # Chemin JWT (cookie) : pose user_id/user_role comme BearerTokenMiddleware.
            if self._user_id is not None:
                state["user_id"] = self._user_id
                state["user_role"] = self._user_role
        await self.app(scope, receive, send)


def _admin_record(tenant_id: uuid.UUID) -> ApiKeyRecord:
    return ApiKeyRecord(
        id=_KEY_ID, name="admin", role="admin", active=True, created_at=_NOW,
        last_used_at=None, expires_at=None, tenant_id=tenant_id,
    )


def _make_tenant_aware_svc(*, tenant_exists: bool = True) -> AsyncMock:
    """Service mocké dont create_key reflète le tenant_id reçu (None → legacy)."""
    svc = AsyncMock(spec=ApiKeyService)
    svc.tenant_exists = AsyncMock(return_value=tenant_exists)

    async def _create(*, name, role, expires_at, tenant_id):
        effectif = tenant_id if tenant_id is not None else LEGACY_TENANT_ID
        record = ApiKeyRecord(
            id=uuid.uuid4(), name=name, role=role, active=True, created_at=_NOW,
            last_used_at=None, expires_at=expires_at, tenant_id=effectif,
        )
        return ("token-clair-xyz", record)

    svc.create_key = AsyncMock(side_effect=_create)
    return svc


def _make_ctx_app(
    svc: AsyncMock, *, tenant_id, api_key_record, user_id=None, user_role=None
) -> FastAPI:
    from app.middleware.tenant import TenantContextMiddleware

    app = FastAPI()
    app.state.api_key_service = svc
    app.include_router(admin_router)
    # TenantContextMiddleware (interne) lit scope.state["tenant_id"] → ContextVar ;
    # le shim d'injection (externe) doit poser scope.state AVANT → ajouté en dernier.
    app.add_middleware(TenantContextMiddleware)
    app.add_middleware(
        _InjectContextASGI,
        tenant_id=tenant_id,
        api_key_record=api_key_record,
        user_id=user_id,
        user_role=user_role,
    )
    return app


class TestProvisionnementParTenant:

    @pytest.mark.asyncio
    async def test_sans_tenant_id_inchange_tenant_courant(self):
        """Absent → create_key reçoit tenant_id=None (comportement rétrocompatible)."""
        svc = _make_tenant_aware_svc()
        app = _make_ctx_app(svc, tenant_id=str(_TENANT_A), api_key_record=_admin_record(_TENANT_A))
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            resp = await c.post("/admin/keys", json={"name": "K"})
        assert resp.status_code == 201
        assert svc.create_key.call_args.kwargs["tenant_id"] is None
        svc.tenant_exists.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_tenant_id_egal_courant_admin_db_201(self):
        """Admin DB provisionnant pour SON tenant → 201, clé rattachée à ce tenant."""
        svc = _make_tenant_aware_svc()
        app = _make_ctx_app(svc, tenant_id=str(_TENANT_A), api_key_record=_admin_record(_TENANT_A))
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            resp = await c.post("/admin/keys", json={"name": "K", "tenant_id": str(_TENANT_A)})
        assert resp.status_code == 201
        assert resp.json()["key"]["tenant_id"] == str(_TENANT_A)

    @pytest.mark.asyncio
    async def test_tenant_id_different_admin_db_403(self):
        """Admin DB tentant un tenant arbitraire → 403, aucune création."""
        svc = _make_tenant_aware_svc()
        app = _make_ctx_app(svc, tenant_id=str(_TENANT_A), api_key_record=_admin_record(_TENANT_A))
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            resp = await c.post("/admin/keys", json={"name": "K", "tenant_id": str(_TENANT_B)})
        assert resp.status_code == 403
        svc.create_key.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_tenant_id_arbitraire_cle_env_201(self):
        """Clé env / super-admin (record None) exemptée → provisionne pour tout tenant."""
        svc = _make_tenant_aware_svc()
        app = _make_ctx_app(svc, tenant_id=str(LEGACY_TENANT_ID), api_key_record=None)
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            resp = await c.post("/admin/keys", json={"name": "K", "tenant_id": str(_TENANT_B)})
        assert resp.status_code == 201
        assert resp.json()["key"]["tenant_id"] == str(_TENANT_B)

    @pytest.mark.asyncio
    async def test_tenant_id_inexistant_404_pas_500(self):
        """Tenant cible absent → 404 propre (pas de violation FK 500), aucune création."""
        svc = _make_tenant_aware_svc(tenant_exists=False)
        app = _make_ctx_app(svc, tenant_id=str(LEGACY_TENANT_ID), api_key_record=None)
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            resp = await c.post("/admin/keys", json={"name": "K", "tenant_id": str(_TENANT_B)})
        assert resp.status_code == 404
        svc.create_key.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_jwt_admin_tenant_id_egal_courant_201(self):
        """Admin web (JWT, api_key_record=None mais user_id posé) pour SON tenant → 201."""
        svc = _make_tenant_aware_svc()
        app = _make_ctx_app(
            svc, tenant_id=str(_TENANT_A), api_key_record=None,
            user_id=str(uuid.uuid4()), user_role="admin",
        )
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            resp = await c.post("/admin/keys", json={"name": "K", "tenant_id": str(_TENANT_A)})
        assert resp.status_code == 201
        assert resp.json()["key"]["tenant_id"] == str(_TENANT_A)

    @pytest.mark.asyncio
    async def test_jwt_admin_tenant_id_arbitraire_403(self):
        """Admin web (JWT) N'EST PAS exempté du verrou cross-tenant → 403, aucune création."""
        svc = _make_tenant_aware_svc()
        app = _make_ctx_app(
            svc, tenant_id=str(_TENANT_A), api_key_record=None,
            user_id=str(uuid.uuid4()), user_role="admin",
        )
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            resp = await c.post("/admin/keys", json={"name": "K", "tenant_id": str(_TENANT_B)})
        assert resp.status_code == 403
        svc.create_key.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_jwt_reader_refuse_403(self):
        """Utilisateur web non-admin (JWT reader) ne doit pas atteindre create_key → 403."""
        svc = _make_tenant_aware_svc()
        app = _make_ctx_app(
            svc, tenant_id=str(_TENANT_A), api_key_record=None,
            user_id=str(uuid.uuid4()), user_role="reader",
        )
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            resp = await c.post("/admin/keys", json={"name": "K"})
        assert resp.status_code == 403
        svc.create_key.assert_not_awaited()


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
