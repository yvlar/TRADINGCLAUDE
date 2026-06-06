"""Boot sans DDL (E2-S2) — le lifespan ne crée plus aucune table.

Le schéma est porté par Alembic ; le démarrage de l'API ne doit émettre aucun DDL,
de sorte qu'un rôle en lecture seule sur le schéma migré puisse booter l'app.
"""
from __future__ import annotations

import os
import types
from contextlib import ExitStack
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# Liste partagée (source unique) — un skill ajouté au lifespan y apparaît, ce qui
# garde ce test aligné sans copie qui dériverait silencieusement.
from tests.conftest import _SKILL_PROMPT_PATCHES


@pytest.mark.asyncio
async def test_lifespan_n_emet_aucun_ddl():
    """Le lifespan ne doit appeler ni execute ni executemany sur le pool (zéro DDL)."""
    from app.api.main import lifespan

    env_vars = {"ANTHROPIC_API_KEY": "sk-ant-test-key"}

    mock_rag_client = AsyncMock()
    mock_rag_client.ensure_collection = AsyncMock()
    mock_rag_client.close = AsyncMock()

    mock_redis_pool = AsyncMock()
    mock_redis_pool.aclose = AsyncMock()

    mock_app = MagicMock()
    mock_app.state = types.SimpleNamespace()

    with ExitStack() as stack:
        stack.enter_context(patch.dict(os.environ, env_vars))
        mock_pool = stack.enter_context(
            patch("asyncpg.create_pool", new_callable=AsyncMock)
        )
        mock_pool.return_value = AsyncMock()
        mock_pool.return_value.close = AsyncMock()
        stack.enter_context(patch("anthropic.AsyncAnthropic", return_value=MagicMock()))
        stack.enter_context(patch("app.api.main.RagClient", return_value=mock_rag_client))
        stack.enter_context(
            patch("app.api.main.aioredis.from_url", return_value=mock_redis_pool)
        )
        for prompt_path in _SKILL_PROMPT_PATCHES:
            stack.enter_context(patch(prompt_path, return_value="prompt-test"))

        async with lifespan(mock_app):
            pool = mock_pool.return_value
            assert mock_app.state.db_pool is pool
            pool.execute.assert_not_called()
            pool.executemany.assert_not_called()
