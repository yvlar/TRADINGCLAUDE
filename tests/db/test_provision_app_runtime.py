"""Tests du provisionnement du mot de passe `app_runtime` (Ops S182)."""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.db.provision_app_runtime import _extract_password, provision


def test_extract_password_decode_le_percent_encoding():
    assert _extract_password("postgresql://app_runtime:s3%40cret@host:5432/db") == "s3@cret"


def test_extract_password_none_si_absent():
    assert _extract_password("postgresql://app_runtime@host:5432/db") is None


@pytest.mark.asyncio
async def test_provision_noop_si_app_database_url_absente(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.delenv("APP_DATABASE_URL", raising=False)
    with patch("app.db.provision_app_runtime.asyncpg.connect", new_callable=AsyncMock) as mock_connect:
        assert await provision() is False
        mock_connect.assert_not_called()


@pytest.mark.asyncio
async def test_provision_noop_si_url_sans_mot_de_passe(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("APP_DATABASE_URL", "postgresql://app_runtime@host:5432/db")
    with patch("app.db.provision_app_runtime.asyncpg.connect", new_callable=AsyncMock) as mock_connect:
        assert await provision() is False
        mock_connect.assert_not_called()


@pytest.mark.asyncio
async def test_provision_pose_le_mot_de_passe_via_parametre_lie(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("APP_DATABASE_URL", "postgresql://app_runtime:s3cr3t@host:5432/db")
    monkeypatch.setenv("DATABASE_URL", "postgresql://copilote:copilote@host:5432/db")

    conn = AsyncMock()
    # conn.transaction() est synchrone et renvoie un context manager async → MagicMock(→ AsyncMock)
    # qui supporte nativement le protocole `async with`.
    conn.transaction = MagicMock(return_value=AsyncMock())
    with patch(
        "app.db.provision_app_runtime.asyncpg.connect", new_callable=AsyncMock, return_value=conn
    ):
        assert await provision() is True

    calls = conn.execute.await_args_list
    # 1ʳᵉ exécution : mot de passe en PARAMÈTRE LIÉ (jamais dans le texte SQL).
    assert calls[0].args[0] == "SELECT set_config('app.provision_pwd', $1, true)"
    assert calls[0].args[1] == "s3cr3t"
    # 2ᵉ exécution : le mot de passe n'apparaît pas dans le texte SQL (lu via current_setting).
    do_sql = calls[1].args[0]
    assert "ALTER ROLE app_runtime LOGIN PASSWORD %L" in do_sql
    assert "current_setting('app.provision_pwd')" in do_sql
    assert "s3cr3t" not in do_sql
    conn.close.assert_awaited_once()
