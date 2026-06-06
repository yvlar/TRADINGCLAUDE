"""Unitaires du middleware ASGI de résolution du tenant de requête (E3-S4)."""
from __future__ import annotations

import uuid

import pytest

from app.db.tenant_context import get_current_tenant
from app.middleware.tenant import TenantContextMiddleware
from app.models.tenant import LEGACY_TENANT_ID


async def _receive():
    return {"type": "http.request"}


async def _send(message):
    pass


@pytest.mark.asyncio
async def test_pose_le_tenant_depuis_scope_state():
    """Le tenant déposé par l'auth (scope['state']['tenant_id']) est posé dans le ContextVar."""
    tenant = uuid.uuid4()
    vu: dict = {}

    async def _app(scope, receive, send):
        vu["tenant"] = get_current_tenant()

    mw = TenantContextMiddleware(_app)
    await mw({"type": "http", "state": {"tenant_id": str(tenant)}}, _receive, _send)

    assert vu["tenant"] == tenant
    # Reset garanti après la requête : le contexte parent retombe au défaut legacy.
    assert get_current_tenant() == LEGACY_TENANT_ID


@pytest.mark.asyncio
async def test_defaut_legacy_sans_tenant_dans_le_scope():
    """Requête non authentifiée / chemin exempté (pas de tenant en state) → legacy."""
    vu: dict = {}

    async def _app(scope, receive, send):
        vu["tenant"] = get_current_tenant()

    mw = TenantContextMiddleware(_app)
    await mw({"type": "http", "state": {}}, _receive, _send)

    assert vu["tenant"] == LEGACY_TENANT_ID


@pytest.mark.asyncio
async def test_reset_meme_si_endpoint_leve():
    """Le reset du ContextVar est garanti (finally) même si l'app downstream lève."""
    async def _app(scope, receive, send):
        raise RuntimeError("boom")

    mw = TenantContextMiddleware(_app)
    scope = {"type": "http", "state": {"tenant_id": str(uuid.uuid4())}}
    with pytest.raises(RuntimeError):
        await mw(scope, _receive, _send)
    assert get_current_tenant() == LEGACY_TENANT_ID


@pytest.mark.asyncio
async def test_passthrough_scope_non_http():
    """Un scope non-http (lifespan/websocket) traverse sans toucher au ContextVar."""
    appele: dict = {}

    async def _app(scope, receive, send):
        appele["ok"] = True

    mw = TenantContextMiddleware(_app)
    await mw({"type": "lifespan"}, _receive, _send)
    assert appele["ok"] is True
