"""Tests Sprint 82 — GET /watchlist/esg-scores."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock

import pytest
import pytest_asyncio

from app.api.main import app as fastapi_app
from app.models.watchlist import WatchlistEntry
from app.services.watchlist_service import WatchlistService


def _make_entry(**kwargs) -> WatchlistEntry:
    defaults = dict(
        id=str(uuid.uuid4()),
        ticker="BNS",
        workflow="value_graham",
        ratios=None,
        score_alerte_min=None,
        created_at=datetime.now(timezone.utc),
        last_analyzed_at=None,
        last_score=None,
        last_verdict=None,
    )
    defaults.update(kwargs)
    return WatchlistEntry(**defaults)


@pytest_asyncio.fixture
async def watchlist_client(client):
    """Injecte un WatchlistService mocké dans l'état de l'application."""
    mock_service = AsyncMock(spec=WatchlistService)
    fastapi_app.state.watchlist_service = mock_service
    yield client, mock_service


# ---------------------------------------------------------------------------
# Test 1 : 200 avec champs ticker/last_esg_score/esg_alert_threshold présents
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_get_esg_scores_200_avec_champs(watchlist_client):
    """GET /watchlist/esg-scores → 200 avec les champs ESG attendus."""
    client, mock_service = watchlist_client
    mock_service.list_entries.return_value = [
        _make_entry(ticker="BNS", last_esg_score=7.5, esg_alert_threshold=5.0)
    ]

    resp = await client.get("/watchlist/esg-scores")

    assert resp.status_code == 200
    data = resp.json()
    assert "entries" in data
    assert len(data["entries"]) == 1
    entry = data["entries"][0]
    assert entry["ticker"] == "BNS"
    assert pytest.approx(entry["last_esg_score"], rel=1e-3) == 7.5
    assert pytest.approx(entry["esg_alert_threshold"], rel=1e-3) == 5.0
    assert "last_analyzed_at" in entry


# ---------------------------------------------------------------------------
# Test 2 : 200 avec liste vide si watchlist vide
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_get_esg_scores_liste_vide(watchlist_client):
    """GET /watchlist/esg-scores → 200 { entries: [] } si watchlist vide."""
    client, mock_service = watchlist_client
    mock_service.list_entries.return_value = []

    resp = await client.get("/watchlist/esg-scores")

    assert resp.status_code == 200
    assert resp.json() == {"entries": []}


# ---------------------------------------------------------------------------
# Test 3 : tri DESC nulls en dernier
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_get_esg_scores_tri_desc_nulls_last(watchlist_client):
    """GET /watchlist/esg-scores → triées par last_esg_score DESC, None en dernier."""
    client, mock_service = watchlist_client
    mock_service.list_entries.return_value = [
        _make_entry(ticker="TD", last_esg_score=None),
        _make_entry(ticker="BNS", last_esg_score=3.0),
        _make_entry(ticker="RY", last_esg_score=11.0),
    ]

    resp = await client.get("/watchlist/esg-scores")

    assert resp.status_code == 200
    tickers = [e["ticker"] for e in resp.json()["entries"]]
    assert tickers == ["RY", "BNS", "TD"]
