"""Tests Sprint 89 — GET /esg-history/{ticker}."""
from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import AsyncMock

import pytest

from app.api.main import app as fastapi_app
from app.services.esg_history_service import EsgHistoryPoint, EsgHistoryService


def _make_point(
    ticker: str = "BNS",
    score: float = 7.5,
    verdict: str = "ESG_MODERE",
    recorded_at: datetime | None = None,
) -> EsgHistoryPoint:
    return EsgHistoryPoint(
        id="1",
        ticker=ticker,
        score=score,
        verdict=verdict,
        recorded_at=recorded_at or datetime(2026, 5, 14, 12, 0, 0, tzinfo=timezone.utc),
    )


# ---------------------------------------------------------------------------
# Test 1 : 200 avec points retournes
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_endpoint_esg_history_200_avec_points(client):
    """GET /esg-history/BNS → 200 avec format {ticker, points: [...]}."""
    mock_service = AsyncMock(spec=EsgHistoryService)
    mock_service.get_history.return_value = [
        _make_point(score=11.0, verdict="ESG_FORT"),
        _make_point(score=7.5, verdict="ESG_MODERE"),
    ]
    fastapi_app.state.esg_history_service = mock_service

    resp = await client.get("/esg-history/BNS")

    assert resp.status_code == 200
    data = resp.json()
    assert data["ticker"] == "BNS"
    assert "points" in data
    assert len(data["points"]) == 2
    assert data["points"][0]["score"] == 11.0
    assert data["points"][0]["verdict"] == "ESG_FORT"
    mock_service.get_history.assert_awaited_once_with(ticker="BNS", limit=100)


# ---------------------------------------------------------------------------
# Test 2 : 404 si aucun point pour le ticker
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_endpoint_esg_history_404_si_vide(client):
    """GET /esg-history/AAPL → 404 si aucun point en historique."""
    mock_service = AsyncMock(spec=EsgHistoryService)
    mock_service.get_history.return_value = []
    fastapi_app.state.esg_history_service = mock_service

    resp = await client.get("/esg-history/AAPL")

    assert resp.status_code == 404
    assert "Aucun historique ESG" in resp.json()["detail"]


# ---------------------------------------------------------------------------
# Test 3 : format de reponse — champs ticker, points avec id/score/verdict/recorded_at
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_endpoint_esg_history_format_reponse(client):
    """GET /esg-history/RY → chaque point a id, ticker, score, verdict, recorded_at."""
    mock_service = AsyncMock(spec=EsgHistoryService)
    mock_service.get_history.return_value = [
        _make_point(ticker="RY", score=10.0, verdict="ESG_FORT"),
    ]
    fastapi_app.state.esg_history_service = mock_service

    resp = await client.get("/esg-history/RY?limit=50")

    assert resp.status_code == 200
    data = resp.json()
    assert data["ticker"] == "RY"
    pt = data["points"][0]
    for field in ("id", "ticker", "score", "verdict", "recorded_at"):
        assert field in pt
    # le parametre limit a bien ete passe au service
    mock_service.get_history.assert_awaited_once_with(ticker="RY", limit=50)
