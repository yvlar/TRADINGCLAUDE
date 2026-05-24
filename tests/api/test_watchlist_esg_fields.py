"""Tests Sprint 77 — champs ESG sur WatchlistEntry et update_esg_score()."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock

import pytest

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


# ---------------------------------------------------------------------------
# Test 1 : WatchlistEntry — valeurs par défaut ESG
# ---------------------------------------------------------------------------

def test_watchlist_entry_esg_defaults():
    entry = _make_entry()
    assert entry.esg_alert_threshold == 5.0
    assert entry.last_esg_score is None


# ---------------------------------------------------------------------------
# Test 2 : WatchlistEntry — champs ESG configurés
# ---------------------------------------------------------------------------

def test_watchlist_entry_esg_champs_configures():
    entry = _make_entry(esg_alert_threshold=8.0, last_esg_score=3.5)
    assert entry.esg_alert_threshold == 8.0
    assert entry.last_esg_score == 3.5


# ---------------------------------------------------------------------------
# Test 3 : Détection alerte ESG — score sous le seuil
# ---------------------------------------------------------------------------

def test_watchlist_entry_alerte_esg_sous_seuil():
    entry = _make_entry(esg_alert_threshold=5.0, last_esg_score=3.0)
    assert entry.last_esg_score < entry.esg_alert_threshold


# ---------------------------------------------------------------------------
# Test 4 : Pas d'alerte ESG — score au-dessus du seuil
# ---------------------------------------------------------------------------

def test_watchlist_entry_pas_alerte_esg_dessus_seuil():
    entry = _make_entry(esg_alert_threshold=5.0, last_esg_score=8.0)
    assert entry.last_esg_score >= entry.esg_alert_threshold


# ---------------------------------------------------------------------------
# Test 5 : update_esg_score() — appel SQL avec bons paramètres
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_update_esg_score_appel_execute():
    mock_pool = AsyncMock()
    mock_pool.execute = AsyncMock()
    service = WatchlistService(db_pool=mock_pool)

    entry_id = str(uuid.uuid4())
    await service.update_esg_score(entry_id, 6.5)

    mock_pool.execute.assert_awaited_once()
    call_args = mock_pool.execute.call_args
    sql = call_args[0][0]
    assert "last_esg_score" in sql
    assert "watchlist" in sql


# ---------------------------------------------------------------------------
# Test 6 : update_esg_score() — accepte None (reset du score)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_update_esg_score_none():
    mock_pool = AsyncMock()
    mock_pool.execute = AsyncMock()
    service = WatchlistService(db_pool=mock_pool)

    entry_id = str(uuid.uuid4())
    await service.update_esg_score(entry_id, None)

    mock_pool.execute.assert_awaited_once()
    call_args = mock_pool.execute.call_args
    # Le deuxième argument positionnel est None
    assert call_args[0][2] is None


# ---------------------------------------------------------------------------
# Test 7 : WatchlistEntry — last_esg_score = 0 (score minimum valide)
# ---------------------------------------------------------------------------

def test_watchlist_entry_esg_score_zero():
    entry = _make_entry(last_esg_score=0.0)
    assert entry.last_esg_score == 0.0
    assert entry.last_esg_score < entry.esg_alert_threshold


# ---------------------------------------------------------------------------
# Test 8 : WatchlistEntry — last_esg_score = 15 (score maximum)
# ---------------------------------------------------------------------------

def test_watchlist_entry_esg_score_maximum():
    entry = _make_entry(last_esg_score=15.0, esg_alert_threshold=5.0)
    assert entry.last_esg_score == 15.0
    assert entry.last_esg_score >= entry.esg_alert_threshold
