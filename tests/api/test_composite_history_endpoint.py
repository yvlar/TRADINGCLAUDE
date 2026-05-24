"""Tests CI pour l'endpoint GET /composite-history/{ticker} — sans DB réelle."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock

import pytest

from app.api.main import app as fastapi_app
from app.services.composite_history_service import (
    CompositeHistoryPoint,
    CompositeHistoryService,
)


def _make_point(ticker: str = "BNS", score: float = 72.5, label: str = "FORT") -> CompositeHistoryPoint:
    return CompositeHistoryPoint(
        id=str(uuid.uuid4()),
        ticker=ticker,
        score=score,
        label=label,
        workflow="value_graham",
        recorded_at=datetime(2026, 5, 14, 10, 0, 0, tzinfo=timezone.utc),
    )


# ---------------------------------------------------------------------------
# Test 1 : GET /composite-history/{ticker} retourne 200 et une liste
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_composite_history_retourne_200_et_liste(client):
    """L'endpoint doit retourner 200 avec une liste JSON valide."""
    mock_service = AsyncMock(spec=CompositeHistoryService)
    mock_service.get_history.return_value = [_make_point()]
    fastapi_app.state.composite_history_service = mock_service

    resp = await client.get("/composite-history/BNS")

    assert resp.status_code == 200
    body = resp.json()
    assert isinstance(body, list)
    assert len(body) == 1
    assert body[0]["ticker"] == "BNS"
    assert body[0]["score"] == 72.5
    assert body[0]["label"] == "FORT"


# ---------------------------------------------------------------------------
# Test 2 : structure des champs CompositeHistoryPoint vérifiée
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_composite_history_structure_champs(client):
    """La réponse doit contenir les champs id, ticker, score, label, workflow, recorded_at."""
    mock_service = AsyncMock(spec=CompositeHistoryService)
    mock_service.get_history.return_value = [_make_point("TD", score=55.0, label="MODERE")]
    fastapi_app.state.composite_history_service = mock_service

    resp = await client.get("/composite-history/TD")

    assert resp.status_code == 200
    body = resp.json()
    assert len(body) == 1
    point = body[0]
    assert "id" in point
    assert "ticker" in point
    assert "score" in point
    assert "label" in point
    assert "workflow" in point
    assert "recorded_at" in point
    assert point["score"] == 55.0
    assert point["label"] == "MODERE"


# ---------------------------------------------------------------------------
# Test 3 : liste vide → 200 avec []
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_composite_history_liste_vide(client):
    """Aucun historique pour un ticker valide → 200 avec liste vide."""
    mock_service = AsyncMock(spec=CompositeHistoryService)
    mock_service.get_history.return_value = []
    fastapi_app.state.composite_history_service = mock_service

    resp = await client.get("/composite-history/AAPL")

    assert resp.status_code == 200
    assert resp.json() == []


# ---------------------------------------------------------------------------
# Test 4 : paramètre limit transmis au service
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_composite_history_limit_transmis_au_service(client):
    """Le paramètre ?limit=30 doit être transmis à CompositeHistoryService.get_history()."""
    mock_service = AsyncMock(spec=CompositeHistoryService)
    mock_service.get_history.return_value = []
    fastapi_app.state.composite_history_service = mock_service

    resp = await client.get("/composite-history/TD?limit=30")

    assert resp.status_code == 200
    mock_service.get_history.assert_called_once_with(ticker="TD", limit=30)


# ---------------------------------------------------------------------------
# Test 5 : plusieurs points retournés avec labels variés
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_composite_history_plusieurs_points(client):
    """Plusieurs points d'historique avec labels FORT/MODERE/FAIBLE retournés correctement."""
    mock_service = AsyncMock(spec=CompositeHistoryService)
    mock_service.get_history.return_value = [
        _make_point("RY", score=75.0, label="FORT"),
        _make_point("RY", score=48.0, label="MODERE"),
        _make_point("RY", score=32.0, label="FAIBLE"),
    ]
    fastapi_app.state.composite_history_service = mock_service

    resp = await client.get("/composite-history/RY")

    assert resp.status_code == 200
    body = resp.json()
    assert len(body) == 3
    labels = [p["label"] for p in body]
    assert "FORT" in labels
    assert "MODERE" in labels
    assert "FAIBLE" in labels
