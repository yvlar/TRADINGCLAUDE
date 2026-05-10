"""Tests Sprint 23 — Watchlist persistante."""
from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio

from app.api.main import app as fastapi_app
from app.models.watchlist import WatchlistCreate, WatchlistEntry
from app.services.watchlist_service import WatchlistService
from app.workers.tasks import _execute_watchlist_analysis


def _make_entry(
    ticker: str = "BNS",
    entry_id: str | None = None,
    score_alerte_min: int | None = None,
) -> WatchlistEntry:
    return WatchlistEntry(
        id=entry_id or str(uuid.uuid4()),
        ticker=ticker,
        workflow="value_graham",
        ratios=None,
        score_alerte_min=score_alerte_min,
        created_at=datetime.now(timezone.utc),
        last_analyzed_at=None,
        last_score=None,
        last_verdict=None,
    )


@pytest_asyncio.fixture
async def watchlist_client(client):
    """Ajoute un WatchlistService entièrement mocké à l'état de l'application."""
    mock_service = AsyncMock(spec=WatchlistService)
    fastapi_app.state.watchlist_service = mock_service
    yield client, mock_service


@pytest.mark.asyncio
async def test_watchlist_add_entry(watchlist_client):
    """POST /watchlist → 201 avec l'entrée créée incluant un UUID."""
    client, mock_service = watchlist_client
    entry = _make_entry()
    mock_service.add_entry.return_value = entry

    resp = await client.post(
        "/watchlist",
        json={"ticker": "BNS", "workflow": "value_graham"},
    )

    assert resp.status_code == 201
    data = resp.json()
    assert data["ticker"] == "BNS"
    assert "id" in data
    mock_service.add_entry.assert_called_once()


@pytest.mark.asyncio
async def test_watchlist_list_entries(watchlist_client):
    """GET /watchlist → liste de toutes les entrées."""
    client, mock_service = watchlist_client
    entries = [_make_entry("BNS"), _make_entry("MSFT")]
    mock_service.list_entries.return_value = entries

    resp = await client.get("/watchlist")

    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 2
    assert data[0]["ticker"] == "BNS"
    assert data[1]["ticker"] == "MSFT"


@pytest.mark.asyncio
async def test_watchlist_delete_entry(watchlist_client):
    """DELETE /watchlist/{id} → 204 si l'entrée existe."""
    client, mock_service = watchlist_client
    entry_id = str(uuid.uuid4())
    mock_service.delete_entry.return_value = True

    resp = await client.delete(f"/watchlist/{entry_id}")

    assert resp.status_code == 204
    mock_service.delete_entry.assert_called_once_with(entry_id)


@pytest.mark.asyncio
async def test_watchlist_delete_inconnu_404(watchlist_client):
    """DELETE /watchlist/{id} → 404 si l'entrée est introuvable."""
    client, mock_service = watchlist_client
    mock_service.delete_entry.return_value = False

    resp = await client.delete("/watchlist/bad-id")

    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_watchlist_manual_analyze(watchlist_client):
    """POST /watchlist/{id}/analyze → job_id retourné immédiatement."""
    client, mock_service = watchlist_client
    entry = _make_entry()
    mock_service.get_entry.return_value = entry

    with patch("app.api.endpoints.watchlist.run_full_analysis") as mock_task:
        resp = await client.post(f"/watchlist/{entry.id}/analyze")

    assert resp.status_code == 200
    data = resp.json()
    assert "job_id" in data
    mock_task.delay.assert_called_once()


@pytest.mark.asyncio
async def test_watchlist_celery_task_mock():
    """run_watchlist_analysis traite toutes les entrées de la watchlist."""
    id_bns = uuid.UUID("550e8400-e29b-41d4-a716-446655440000")
    id_msft = uuid.UUID("550e8400-e29b-41d4-a716-446655440001")

    mock_orchestrator = AsyncMock()
    mock_response = MagicMock()
    mock_response.graham = None
    mock_orchestrator.run_company_analysis.return_value = mock_response

    mock_pool = AsyncMock()
    mock_pool.fetch.return_value = [
        {
            "id": id_bns,
            "ticker": "BNS",
            "workflow": "value_graham",
            "ratios": None,
            "score_alerte_min": None,
        },
        {
            "id": id_msft,
            "ticker": "MSFT",
            "workflow": "value_graham",
            "ratios": None,
            "score_alerte_min": None,
        },
    ]
    mock_pool.execute = AsyncMock()
    mock_pool.close = AsyncMock()

    with patch("app.workers.tasks._build_orchestrator", return_value=(mock_orchestrator, mock_pool)):
        await _execute_watchlist_analysis()

    assert mock_orchestrator.run_company_analysis.call_count == 2
    assert mock_pool.execute.call_count == 2
    mock_pool.close.assert_called_once()


@pytest.mark.asyncio
async def test_watchlist_alerte_score_bas(caplog):
    """WARNING loggué si last_score < score_alerte_min."""
    entry_id = uuid.UUID("550e8400-e29b-41d4-a716-446655440000")

    mock_orchestrator = AsyncMock()
    mock_response = MagicMock()
    mock_graham = MagicMock()
    mock_graham.defensive_score = 2
    mock_graham.verdict = "REJETER"
    mock_response.graham = mock_graham
    mock_orchestrator.run_company_analysis.return_value = mock_response

    mock_pool = AsyncMock()
    mock_pool.fetch.return_value = [
        {
            "id": entry_id,
            "ticker": "BNS",
            "workflow": "value_graham",
            "ratios": None,
            "score_alerte_min": 5,  # 2 < 5 → WARNING attendu
        }
    ]
    mock_pool.execute = AsyncMock()
    mock_pool.close = AsyncMock()

    with patch("app.workers.tasks._build_orchestrator", return_value=(mock_orchestrator, mock_pool)):
        with caplog.at_level(logging.WARNING, logger="app.workers.tasks"):
            await _execute_watchlist_analysis()

    warning_messages = [r.message for r in caplog.records if r.levelno == logging.WARNING]
    assert any("ALERTE" in msg for msg in warning_messages)
