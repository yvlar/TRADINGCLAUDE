"""Tests — garde anti-doublon de la watchlist (parité service réel ↔ E2E, BUG-005)."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock

import pytest
import pytest_asyncio

from app.api.main import app as fastapi_app
from app.models.watchlist import WatchlistCreate, WatchlistEntry
from app.services.watchlist_service import DuplicateWatchlistError, WatchlistService


def _entry(ticker: str = "BNS") -> WatchlistEntry:
    return WatchlistEntry(
        id=str(uuid.uuid4()),
        ticker=ticker,
        workflow="value_graham",
        ratios=None,
        score_alerte_min=None,
        created_at=datetime.now(timezone.utc),
    )


@pytest.mark.asyncio
async def test_service_refuse_doublon_ticker_workflow():
    """fetchval renvoie 1 (déjà présent) → DuplicateWatchlistError, aucun INSERT."""
    pool = AsyncMock()
    pool.fetchval = AsyncMock(return_value=1)
    pool.fetchrow = AsyncMock()
    service = WatchlistService(db_pool=pool)

    with pytest.raises(DuplicateWatchlistError):
        await service.add_entry(WatchlistCreate(ticker="bns", workflow="value_graham"))

    pool.fetchval.assert_awaited_once()
    pool.fetchrow.assert_not_called()  # pas d'insertion


@pytest.mark.asyncio
async def test_service_insere_si_absent():
    """fetchval renvoie None (absent) → INSERT exécuté, entrée retournée."""
    pool = AsyncMock()
    pool.fetchval = AsyncMock(return_value=None)
    pool.fetchrow = AsyncMock(return_value={
        "id": uuid.uuid4(), "ticker": "BNS", "workflow": "value_graham",
        "ratios": None, "score_alerte_min": None,
        "created_at": datetime.now(timezone.utc), "last_analyzed_at": None,
        "last_score": None, "last_verdict": None, "last_intrinsic_value": None,
        "last_price_checked": None, "price_alert_threshold_pct": 0.10,
        "last_composite_score": None, "composite_alert_threshold": None,
        "esg_alert_threshold": None, "last_esg_score": None,
    })
    service = WatchlistService(db_pool=pool)

    result = await service.add_entry(WatchlistCreate(ticker="bns", workflow="value_graham"))

    assert result.ticker == "BNS"
    pool.fetchrow.assert_awaited_once()


@pytest.mark.asyncio
async def test_service_course_toctou_violation_unique():
    """Course gagnée par une requête concurrente → l'INSERT lève UniqueViolationError
    et le service la traduit en DuplicateWatchlistError (filet de sécurité TOCTOU)."""
    import asyncpg

    pool = AsyncMock()
    pool.fetchval = AsyncMock(return_value=None)  # SELECT voit « absent »…
    pool.fetchrow = AsyncMock(side_effect=asyncpg.UniqueViolationError("dup"))  # …mais l'index bloque
    service = WatchlistService(db_pool=pool)

    with pytest.raises(DuplicateWatchlistError):
        await service.add_entry(WatchlistCreate(ticker="bns", workflow="value_graham"))


@pytest_asyncio.fixture
async def watchlist_client(client):
    mock_service = AsyncMock(spec=WatchlistService)
    fastapi_app.state.watchlist_service = mock_service
    yield client, mock_service


@pytest.mark.asyncio
async def test_endpoint_doublon_renvoie_409(watchlist_client):
    """L'endpoint traduit DuplicateWatchlistError en HTTP 409."""
    client, mock_service = watchlist_client
    mock_service.add_entry.side_effect = DuplicateWatchlistError("déjà présent")

    resp = await client.post("/watchlist", json={"ticker": "BNS", "workflow": "value_graham"})

    assert resp.status_code == 409
    assert "déjà présent" in resp.json()["detail"]


@pytest.mark.asyncio
async def test_endpoint_ajout_normal_201(watchlist_client):
    """Sans doublon, l'endpoint répond 201 normalement."""
    client, mock_service = watchlist_client
    mock_service.add_entry.return_value = _entry()

    resp = await client.post("/watchlist", json={"ticker": "BNS", "workflow": "value_graham"})

    assert resp.status_code == 201
