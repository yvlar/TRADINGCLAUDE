"""Preuve d'intégration du garde S192 sur le chemin de boot API réel (Sprint 199).

S196 a prouvé le garde sur le chemin **worker** (`create_runtime_pool` = 1ᵉʳ `await` d'un
`_execute_*`). Ces tests complètent la preuve sur le **chemin API réel** : le lifespan FastAPI
doit lever `RuntimeError` **avant** `asyncpg.create_pool` quand la DSN est insecure en prod —
même chokepoint (`app/db/pool.py:create_runtime_pool`), même garde (`require_secure_db_url`),
site d'appel différent (`app/api/main.py:169`).

Un refactor futur résolvant la DSN ailleurs (ou court-circuitant `create_runtime_pool` dans
`main.py`) repasserait `test_pool.py`/`test_worker_boot_insecure.py` mais ré-ouvrirait le trou
côté API. Ce sprint pose la preuve d'intégration manquante.

Sans PG dans le conteneur web, seuls `asyncpg.create_pool` et l'aval réseau (RagClient, Redis)
sont patchés. `create_runtime_pool` n'est **pas** mocké — le garde réel est exercé.
Aucune modification de `app/` — sprint de test pur.
"""
from __future__ import annotations

import types
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.api.main import lifespan

_INSECURE_DSN = "postgresql://copilote:copilote@postgres:5432/copilote"
_SECURE_DSN = "postgresql://app_runtime:secret@host:5432/copilote"


@pytest.mark.asyncio
async def test_lifespan_api_refuse_dsn_insecure_avant_create_pool(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """En prod + DSN insecure, le lifespan lève via le garde du chokepoint, sans toucher la DB.

    Preuve que `require_secure_db_url` verrouille le chemin API réel (pas seulement
    le helper isolé de `test_pool.py`) : `asyncpg.create_pool` ne doit jamais être awaité."""
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("APP_DATABASE_URL", _INSECURE_DSN)
    # _get_env("ANTHROPIC_API_KEY") est lu aux lignes 150-168 (sync, avant le 1ᵉʳ await) —
    # doit être défini pour que le RuntimeError du garde soit bien la première exception.
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test")

    mock_app = MagicMock()
    mock_app.state = types.SimpleNamespace()

    with patch(
        "app.db.pool.asyncpg.create_pool", new_callable=AsyncMock
    ) as mock_create_pool:
        # `par défaut` est propre au message du garde insecure-creds — discrimine d'un
        # éventuel RuntimeError de boot API non lié au garde (preuve non vacue).
        with pytest.raises(RuntimeError, match="par défaut"):
            async with lifespan(mock_app):
                pass

    mock_create_pool.assert_not_awaited()


@pytest.mark.asyncio
async def test_lifespan_api_accepte_dsn_secure_en_prod(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Discriminant : en prod, une DSN secure passe le garde et `create_pool` est awaité.

    Confirme que le `RuntimeError` du test précédent vient bien des creds insecure (pas de
    l'env prod en soi). Patche l'aval réseau (RagClient, Redis) et fournit JWT_SECRET_KEY
    (AuthTokenService + PasswordResetService appellent resolve_jwt_secret() — fail-fast en
    prod si absent) pour que le lifespan atteigne `yield` sans I/O réelle."""
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("APP_DATABASE_URL", _SECURE_DSN)
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test")
    monkeypatch.setenv("JWT_SECRET_KEY", "test-secret-at-least-32-chars-for-hs256-signing-ok")

    mock_rag_client = AsyncMock()
    mock_redis_pool = AsyncMock()

    mock_app = MagicMock()
    mock_app.state = types.SimpleNamespace()

    with (
        patch(
            "app.db.pool.asyncpg.create_pool", new_callable=AsyncMock
        ) as mock_create_pool,
        patch("app.api.main.RagClient", return_value=mock_rag_client),
        patch("app.api.main.aioredis.from_url", return_value=mock_redis_pool),
    ):
        async with lifespan(mock_app):
            pass

    mock_create_pool.assert_awaited_once()
