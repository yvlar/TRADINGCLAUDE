"""Tests Sprint 94 — détection dégradation ESG watchlist."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock

import pytest
import pytest_asyncio

from app.api.main import app as fastapi_app
from app.models.watchlist import WatchlistEntry
from app.services.esg_history_service import EsgHistoryService
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
        esg_alert_threshold=5.0,
        last_esg_score=None,
    )
    defaults.update(kwargs)
    return WatchlistEntry(**defaults)


def _make_mock_pool(fetchrow_return=None) -> AsyncMock:
    pool = AsyncMock()
    pool.fetchrow = AsyncMock(return_value=fetchrow_return)
    return pool


# ---------------------------------------------------------------------------
# Test 1 : get_latest_previous retourne None si moins de 2 entrées
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_get_latest_previous_retourne_none_si_moins_de_deux_entrees():
    """get_latest_previous() retourne None si la table contient < 2 entrées pour le ticker."""
    pool = _make_mock_pool(fetchrow_return=None)
    service = EsgHistoryService(db_pool=pool)

    result = await service.get_latest_previous("BNS")

    assert result is None
    pool.fetchrow.assert_awaited_once()


# ---------------------------------------------------------------------------
# Test 2 : get_latest_previous retourne le 2e enregistrement le plus récent
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_get_latest_previous_retourne_deuxieme_score():
    """get_latest_previous() retourne le score de la 2e entrée la plus récente."""
    pool = _make_mock_pool(fetchrow_return={"score": 9.0})
    service = EsgHistoryService(db_pool=pool)

    result = await service.get_latest_previous("RY")

    assert result == pytest.approx(9.0)
    # Vérifie OFFSET 1 présent dans la requête SQL
    sql = pool.fetchrow.await_args.args[0]
    assert "OFFSET 1" in sql.upper()


# ---------------------------------------------------------------------------
# Test 3 : check_esg_degradation retourne False si dégradation < seuil
# ---------------------------------------------------------------------------

def test_check_esg_degradation_faux_si_degradation_inferieure_au_seuil():
    """check_esg_degradation() retourne False quand la baisse est inférieure au seuil."""
    entry = _make_entry(last_esg_score=8.0, esg_alert_threshold=5.0)
    # baisse de 3.0 < seuil 5.0 → pas d'alerte
    result = WatchlistService.check_esg_degradation(entry, previous_score=11.0)
    assert result is False


# ---------------------------------------------------------------------------
# Test 4 : check_esg_degradation retourne True si dégradation > seuil
# ---------------------------------------------------------------------------

def test_check_esg_degradation_vrai_si_degradation_superieure_au_seuil():
    """check_esg_degradation() retourne True quand la baisse dépasse le seuil."""
    entry = _make_entry(last_esg_score=6.0, esg_alert_threshold=5.0)
    # baisse de 6.0 (12.0 - 6.0) > seuil 5.0 → alerte
    result = WatchlistService.check_esg_degradation(entry, previous_score=12.0)
    assert result is True


# ---------------------------------------------------------------------------
# Test 5 : POST /watchlist/check-esg-degradation → 200 {"triggered": N}
# ---------------------------------------------------------------------------

@pytest_asyncio.fixture
async def esg_degradation_client(client):
    """Injecte les services mockés pour l'endpoint check-esg-degradation."""
    mock_watchlist_service = AsyncMock(spec=WatchlistService)
    mock_esg_history_service = AsyncMock(spec=EsgHistoryService)
    mock_webhook_service = AsyncMock()
    mock_slack_service = AsyncMock()
    mock_webhook_service.send_esg_alert = AsyncMock(return_value=True)
    mock_slack_service.send_esg_alert = AsyncMock(return_value=True)

    fastapi_app.state.watchlist_service = mock_watchlist_service
    fastapi_app.state.esg_history_service = mock_esg_history_service
    fastapi_app.state.webhook_service = mock_webhook_service
    fastapi_app.state.slack_service = mock_slack_service
    # force bypass admin check en mode dev (API_KEY absent + api_key_service=None)
    fastapi_app.state.api_key_service = None

    yield client, mock_watchlist_service, mock_esg_history_service


@pytest.mark.asyncio
async def test_post_check_esg_degradation_retourne_triggered(esg_degradation_client):
    """POST /watchlist/check-esg-degradation → 200 avec triggered=1 si 1 alerte détectée."""
    client, mock_wl, mock_esg_hist = esg_degradation_client

    # 1 entrée watchlist avec last_esg_score = 6.0 (seuil 5.0)
    mock_wl.list_entries.return_value = [
        _make_entry(ticker="BNS", last_esg_score=6.0, esg_alert_threshold=5.0)
    ]
    # previous_score = 12.0 → baisse de 6.0 > seuil 5.0 → alerte
    mock_esg_hist.get_latest_previous = AsyncMock(return_value=12.0)

    resp = await client.post("/watchlist/check-esg-degradation")

    assert resp.status_code == 200
    data = resp.json()
    assert "triggered" in data
    assert data["triggered"] == 1
