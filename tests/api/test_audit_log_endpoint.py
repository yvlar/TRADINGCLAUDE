"""Tests endpoint GET /admin/audit-log — admin only (E2-S3).

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
from app.services.audit_log_service import AuditLogEntry, AuditLogService

_NOW = datetime(2026, 6, 6, 12, 0, 0, tzinfo=timezone.utc)


def _entry(action: str = "watchlist.create") -> AuditLogEntry:
    return AuditLogEntry(
        id=uuid.uuid4(),
        tenant_id=None,
        user_id=None,
        action=action,
        cible_type="watchlist",
        cible_id="abc",
        metadata={"ticker": "BNS"},
        created_at=_NOW,
    )


def _make_app(svc: AsyncMock, *, record=None, inject_record: bool = True) -> FastAPI:
    app = FastAPI()
    app.state.audit_log_service = svc
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
    svc = AsyncMock(spec=AuditLogService)
    svc.list_recent.return_value = [_entry(), _entry("api_key.revoke")]
    app = _make_app(svc, record=None)  # record=None → clé env = admin implicite
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c, svc


@pytest.mark.asyncio
async def test_audit_log_admin_200(admin_client):
    client, svc = admin_client
    resp = await client.get("/admin/audit-log")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 2
    assert data[0]["action"] == "watchlist.create"
    svc.list_recent.assert_awaited_once_with(50)


@pytest.mark.asyncio
async def test_audit_log_limit_propage(admin_client):
    client, svc = admin_client
    resp = await client.get("/admin/audit-log?limit=10")
    assert resp.status_code == 200
    svc.list_recent.assert_awaited_once_with(10)


@pytest.mark.asyncio
async def test_audit_log_limit_invalide_422(admin_client):
    client, _ = admin_client
    resp = await client.get("/admin/audit-log?limit=999")
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_audit_log_reader_403():
    svc = AsyncMock(spec=AuditLogService)
    record = type("Rec", (), {"role": "reader"})()
    app = _make_app(svc, record=record)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        resp = await c.get("/admin/audit-log")
    assert resp.status_code == 403
    svc.list_recent.assert_not_awaited()


@pytest.mark.asyncio
async def test_audit_log_sans_token_401():
    svc = AsyncMock(spec=AuditLogService)
    app = _make_app(svc, inject_record=False)  # aucun api_key_record → 401
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        resp = await c.get("/admin/audit-log")
    assert resp.status_code == 401
