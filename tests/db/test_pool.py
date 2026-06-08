"""Tests du helper `create_runtime_pool` (Sprint 187).

Verrouille l'invariant de sécurité RLS en un point : tout pool runtime résout la DSN
`app_runtime` ET câble `setup=apply_tenant_context` — impossible de diverger.
"""
from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from app.db.pool import create_runtime_pool
from app.db.tenant_context import apply_tenant_context

_FAKE_DSN = "postgresql://app_runtime:secret@host:5432/copilote"


@pytest.mark.asyncio
async def test_create_runtime_pool_cable_dsn_runtime_et_setup_tenant():
    """L'invariant indissociable : DSN `resolve_app_database_url()` + `setup=apply_tenant_context`."""
    sentinel_pool = object()
    with (
        patch("app.db.pool.resolve_app_database_url", return_value=_FAKE_DSN) as mock_resolve,
        patch(
            "app.db.pool.asyncpg.create_pool",
            new_callable=AsyncMock,
            return_value=sentinel_pool,
        ) as mock_create,
    ):
        pool = await create_runtime_pool(min_size=2, max_size=10)

    assert pool is sentinel_pool
    mock_resolve.assert_called_once()
    mock_create.assert_awaited_once()
    args, kwargs = mock_create.call_args
    # DSN runtime passée en positionnel, hook tenant câblé en `setup` — les deux, toujours.
    assert args[0] == _FAKE_DSN
    assert kwargs["setup"] is apply_tenant_context
    assert kwargs["min_size"] == 2
    assert kwargs["max_size"] == 10


@pytest.mark.asyncio
async def test_create_runtime_pool_propage_les_tailles_workers():
    """Les tailles fournies par l'appelant (1/3 pour les workers) atteignent `create_pool`."""
    with (
        patch("app.db.pool.resolve_app_database_url", return_value=_FAKE_DSN),
        patch("app.db.pool.asyncpg.create_pool", new_callable=AsyncMock) as mock_create,
    ):
        await create_runtime_pool(min_size=1, max_size=3)

    _, kwargs = mock_create.call_args
    assert kwargs["min_size"] == 1
    assert kwargs["max_size"] == 3
    assert kwargs["setup"] is apply_tenant_context
