"""UserService — rattachement tenant à la création de compte (E3-S1)."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock

import pytest

from app.models.tenant import LEGACY_TENANT_ID
from app.services.user_service import UserService


def _fake_row(tenant_id) -> dict:
    return {
        "id": uuid.uuid4(),
        "email": "alice@test.com",
        "role": "reader",
        "tenant_id": tenant_id,
        "created_at": datetime(2026, 1, 1, tzinfo=timezone.utc),
    }


@pytest.fixture
def service() -> tuple[UserService, AsyncMock]:
    pool = AsyncMock()
    return UserService(pool), pool


async def test_create_user_sans_tenant_rattache_au_legacy(service):
    svc, pool = service
    pool.fetchrow.return_value = _fake_row(LEGACY_TENANT_ID)

    result = await svc.create_user("Alice@Test.com", "Password123!")

    # 3ᵉ paramètre positionnel de l'INSERT = tenant_id passé à la requête.
    args = pool.fetchrow.await_args.args
    assert args[3] == LEGACY_TENANT_ID
    assert result["tenant_id"] == LEGACY_TENANT_ID


async def test_create_user_avec_tenant_explicite_respecte(service):
    svc, pool = service
    tenant = uuid.uuid4()
    pool.fetchrow.return_value = _fake_row(tenant)

    await svc.create_user("alice@test.com", "Password123!", tenant_id=tenant)

    args = pool.fetchrow.await_args.args
    assert args[3] == tenant


async def test_create_user_remonte_tenant_id_dans_le_dict(service):
    svc, pool = service
    pool.fetchrow.return_value = _fake_row(LEGACY_TENANT_ID)

    result = await svc.create_user("alice@test.com", "Password123!")

    assert "tenant_id" in result
