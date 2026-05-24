"""Tests Sprint 91 — PATCH /watchlist/{id}/price-threshold et WatchlistService.update_price_threshold()."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock

import pytest
import pytest_asyncio

from app.api.main import app as fastapi_app
from app.models.watchlist import WatchlistEntry
from app.services.watchlist_service import WatchlistService


def _make_watchlist_entry(entry_id: str, price_alert_threshold_pct: float = 0.10) -> WatchlistEntry:
    return WatchlistEntry(
        id=entry_id,
        ticker="BNS",
        workflow="value_graham",
        created_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
        price_alert_threshold_pct=price_alert_threshold_pct,
    )


@pytest_asyncio.fixture
async def watchlist_client(client):
    """Injecte un WatchlistService mocké dans l'état de l'application."""
    mock_service = AsyncMock(spec=WatchlistService)
    fastapi_app.state.watchlist_service = mock_service
    yield client, mock_service


@pytest.mark.asyncio
async def test_update_price_threshold_appel_sql_correct() -> None:
    """update_price_threshold() exécute UPDATE watchlist avec les bons paramètres."""
    mock_pool = AsyncMock()
    mock_pool.execute = AsyncMock(return_value="UPDATE 1")
    service = WatchlistService(mock_pool)

    await service.update_price_threshold("entry-id-123", 0.05)

    mock_pool.execute.assert_called_once()
    args = mock_pool.execute.call_args[0]
    assert "UPDATE watchlist SET price_alert_threshold_pct" in args[0]
    assert args[1] == "entry-id-123"
    assert args[2] == 0.05


@pytest.mark.asyncio
async def test_patch_price_threshold_200(watchlist_client) -> None:
    """PATCH /watchlist/{id}/price-threshold → 200 avec le nouveau seuil dans la réponse."""
    client, mock_service = watchlist_client
    entry_id = str(uuid.uuid4())
    initial = _make_watchlist_entry(entry_id, price_alert_threshold_pct=0.10)
    # après la mise à jour : 5% → 0.05
    updated = _make_watchlist_entry(entry_id, price_alert_threshold_pct=0.05)
    mock_service.get_entry.side_effect = [initial, updated]
    mock_service.update_price_threshold.return_value = None

    resp = await client.patch(
        f"/watchlist/{entry_id}/price-threshold",
        json={"threshold": 5.0},
    )

    assert resp.status_code == 200
    data = resp.json()
    assert data["price_alert_threshold_pct"] == pytest.approx(0.05)
    mock_service.update_price_threshold.assert_called_once_with(entry_id, pytest.approx(0.05))


@pytest.mark.asyncio
async def test_patch_price_threshold_404_id_inexistant(watchlist_client) -> None:
    """PATCH /watchlist/{id}/price-threshold → 404 si l'entrée est introuvable."""
    client, mock_service = watchlist_client
    mock_service.get_entry.return_value = None

    resp = await client.patch(
        f"/watchlist/{uuid.uuid4()}/price-threshold",
        json={"threshold": 10.0},
    )

    assert resp.status_code == 404
