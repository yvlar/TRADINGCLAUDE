"""Tests endpoint GET /admin/tenants — admin only (Sprint 204).

App minimale avec admin_router, sans middleware d'auth réel : on simule
request.state.api_key_record pour exercer _require_admin en isolation.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock

import pytest
import pytest_asyncio
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from app.api.endpoints.admin import router as admin_router
from app.models.tenant import TenantAdminEntry
from app.services.tenant_admin_service import TenantAdminService

_NOW = datetime(2026, 6, 6, 12, 0, 0, tzinfo=timezone.utc)


def _entry(name: str = "Acme", *, stripe: str | None = "cus_abc123") -> TenantAdminEntry:
    return TenantAdminEntry(
        id=uuid.uuid4(),
        name=name,
        slug=name.lower(),
        plan="pro",
        stripe_customer_id=stripe,
        created_at=_NOW,
    )


def _make_app(svc: AsyncMock, *, record=None, inject_record: bool = True) -> FastAPI:
    app = FastAPI()
    app.state.tenant_admin_service = svc
    app.state.api_key_service = object()  # présent → pas de bypass dev

    @app.middleware("http")
    async def inject(request, call_next):
        if inject_record:
            request.state.api_key_record = record
        return await call_next(request)

    app.include_router(admin_router)
    return app


@pytest_asyncio.fixture
async def admin_client():
    svc = AsyncMock(spec=TenantAdminService)
    svc.list_tenants.return_value = [_entry("Acme"), _entry("Globex", stripe=None)]
    app = _make_app(svc, record=None)  # record=None → clé env = admin implicite
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c, svc


@pytest.mark.asyncio
async def test_tenants_admin_200(admin_client):
    client, svc = admin_client
    resp = await client.get("/admin/tenants")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 2
    assert data[0]["name"] == "Acme"
    assert data[0]["stripe_customer_id"] == "cus_abc123"
    assert data[1]["stripe_customer_id"] is None  # tenant sans abonnement
    svc.list_tenants.assert_awaited_once_with(100)


@pytest.mark.asyncio
async def test_tenants_limit_propage(admin_client):
    client, svc = admin_client
    resp = await client.get("/admin/tenants?limit=10")
    assert resp.status_code == 200
    svc.list_tenants.assert_awaited_once_with(10)


@pytest.mark.asyncio
async def test_tenants_limit_invalide_422(admin_client):
    client, _ = admin_client
    resp = await client.get("/admin/tenants?limit=999")
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_tenants_reader_403():
    svc = AsyncMock(spec=TenantAdminService)
    record = type("Rec", (), {"role": "reader"})()
    app = _make_app(svc, record=record)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        resp = await c.get("/admin/tenants")
    assert resp.status_code == 403
    svc.list_tenants.assert_not_awaited()


@pytest.mark.asyncio
async def test_tenants_sans_token_401():
    svc = AsyncMock(spec=TenantAdminService)
    app = _make_app(svc, inject_record=False)  # aucun api_key_record → 401
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        resp = await c.get("/admin/tenants")
    assert resp.status_code == 401
    svc.list_tenants.assert_not_awaited()
