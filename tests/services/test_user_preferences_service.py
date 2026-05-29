"""Tests unitaires pour user_preferences_service — mock pool asyncpg."""
from __future__ import annotations

import json
import uuid
from unittest.mock import AsyncMock

import pytest

from app.services.user_preferences_service import get_preference, upsert_preference


@pytest.fixture
def mock_pool() -> AsyncMock:
    return AsyncMock()


def _uid() -> str:
    return str(uuid.uuid4())


@pytest.mark.asyncio
async def test_get_preference_absente_renvoie_none(mock_pool: AsyncMock):
    mock_pool.fetchrow.return_value = None
    assert await get_preference(mock_pool, _uid(), "screener") is None


@pytest.mark.asyncio
async def test_get_preference_desérialise_jsonb_str(mock_pool: AsyncMock):
    value = {"sort": {"key": "score", "asc": False}, "filter": ["FORT"]}
    mock_pool.fetchrow.return_value = {"value": json.dumps(value)}

    result = await get_preference(mock_pool, _uid(), "screener")

    assert result == value


@pytest.mark.asyncio
async def test_get_preference_accepte_dict_deja_decode(mock_pool: AsyncMock):
    # Si un codec JSON est enregistré, asyncpg renvoie déjà un dict
    value = {"sort": None, "filter": []}
    mock_pool.fetchrow.return_value = {"value": value}

    assert await get_preference(mock_pool, _uid(), "screener") == value


@pytest.mark.asyncio
async def test_upsert_preference_renvoie_valeur_persistee(mock_pool: AsyncMock):
    value = {"sort": {"key": "ticker", "asc": True}, "filter": []}
    mock_pool.fetchrow.return_value = {"value": json.dumps(value)}

    result = await upsert_preference(mock_pool, _uid(), "screener", value)

    assert result == value
    mock_pool.fetchrow.assert_called_once()
    # Le 3e argument lié est la valeur sérialisée en JSON
    args = mock_pool.fetchrow.call_args.args
    assert json.loads(args[3]) == value
