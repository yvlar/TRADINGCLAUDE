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
_INSECURE_DSN = "postgresql://copilote:copilote@postgres:5432/copilote"


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


@pytest.mark.asyncio
async def test_create_runtime_pool_refuse_dsn_insecure_avant_create_pool(
    monkeypatch: pytest.MonkeyPatch,
):
    """Changement de comportement S192 : tout pool runtime (API + workers) refuse une DSN
    aux identifiants par défaut hors dev — le garde `require_secure_db_url` est désormais dans
    le chokepoint, plus au seul boot API. Le pool ne doit jamais être créé."""
    monkeypatch.setenv("APP_ENV", "production")
    with (
        patch("app.db.pool.resolve_app_database_url", return_value=_INSECURE_DSN),
        patch("app.db.pool.asyncpg.create_pool", new_callable=AsyncMock) as mock_create,
    ):
        with pytest.raises(RuntimeError, match="PostgreSQL"):
            await create_runtime_pool(min_size=1, max_size=3)

    mock_create.assert_not_awaited()


@pytest.mark.asyncio
async def test_create_runtime_pool_accepte_dsn_secure_en_prod(monkeypatch: pytest.MonkeyPatch):
    """Happy-path hors dev : une DSN secure passe le garde et le pool est créé, kwargs S187 préservés."""
    monkeypatch.setenv("APP_ENV", "production")
    sentinel_pool = object()
    with (
        patch("app.db.pool.resolve_app_database_url", return_value=_FAKE_DSN),
        patch(
            "app.db.pool.asyncpg.create_pool",
            new_callable=AsyncMock,
            return_value=sentinel_pool,
        ) as mock_create,
    ):
        pool = await create_runtime_pool(min_size=2, max_size=10)

    assert pool is sentinel_pool
    mock_create.assert_awaited_once()
    args, kwargs = mock_create.call_args
    assert args[0] == _FAKE_DSN
    assert kwargs["setup"] is apply_tenant_context
