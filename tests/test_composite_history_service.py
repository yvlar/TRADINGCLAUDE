"""Tests CI pour CompositeHistoryService — aucun appel DB réel (asyncpg mocké)."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock

import pytest
from fastapi import HTTPException

from app.api.main import app as fastapi_app
from app.services.composite_history_service import (
    CompositeHistoryPoint,
    CompositeHistoryService,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_row(
    ticker: str = "BNS",
    score: float = 72.5,
    label: str = "FORT",
    workflow: str = "value_graham",
    recorded_at: datetime | None = None,
) -> dict:
    """Simule une ligne asyncpg.Record sous forme de dict."""
    return {
        "id": uuid.uuid4(),
        "ticker": ticker,
        "score": score,
        "label": label,
        "workflow": workflow,
        "recorded_at": recorded_at or datetime.now(timezone.utc),
    }


def _make_mock_pool(fetch_return=None, execute_return="INSERT 1") -> AsyncMock:
    pool = AsyncMock()
    pool.execute = AsyncMock(return_value=execute_return)
    pool.fetch = AsyncMock(return_value=fetch_return or [])
    return pool


# ---------------------------------------------------------------------------
# Test 1 : CompositeHistoryPoint — schéma Pydantic valide
# ---------------------------------------------------------------------------

def test_composite_history_point_schema_valide():
    """CompositeHistoryPoint doit accepter tous les champs requis sans erreur."""
    point = CompositeHistoryPoint(
        id=str(uuid.uuid4()),
        ticker="BNS",
        score=72.5,
        label="FORT",
        workflow="value_graham",
        recorded_at=datetime.now(timezone.utc),
    )
    assert point.ticker == "BNS"
    assert point.score == 72.5
    assert point.label == "FORT"
    assert point.workflow == "value_graham"
    assert isinstance(point.recorded_at, datetime)


# ---------------------------------------------------------------------------
# Test 2 : record() insère correctement avec pool mocké
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_record_insere_correctement():
    """record() doit appeler pool.execute avec les bons paramètres."""
    pool = _make_mock_pool()
    service = CompositeHistoryService(db_pool=pool)

    await service.record(ticker="BNS", score=72.5, label="FORT", workflow="value_graham")

    pool.execute.assert_called_once()
    call_args = pool.execute.call_args
    # Les paramètres positionnels : sql, ticker, score, label, workflow
    assert call_args.args[1] == "BNS"
    assert call_args.args[2] == 72.5
    assert call_args.args[3] == "FORT"
    assert call_args.args[4] == "value_graham"


# ---------------------------------------------------------------------------
# Test 3 : get_history() retourne une liste triée ASC depuis la DB
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_get_history_retourne_liste_asc():
    """get_history() doit retourner les points dans l'ordre retourné par la DB (ASC)."""
    now = datetime.now(timezone.utc)
    rows = [
        _make_row(score=60.0, label="MODÉRÉ", recorded_at=datetime(2026, 1, 1, tzinfo=timezone.utc)),
        _make_row(score=72.5, label="FORT", recorded_at=datetime(2026, 3, 1, tzinfo=timezone.utc)),
    ]
    pool = _make_mock_pool(fetch_return=rows)
    service = CompositeHistoryService(db_pool=pool)

    result = await service.get_history(ticker="BNS", limit=90)

    assert len(result) == 2
    assert result[0].score == 60.0
    assert result[1].score == 72.5
    assert all(isinstance(p, CompositeHistoryPoint) for p in result)


# ---------------------------------------------------------------------------
# Test 4 : get_history() — limite par défaut 90, max 365 honorés
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_get_history_limite_par_defaut():
    """get_history() doit passer limit=90 par défaut à la requête DB."""
    pool = _make_mock_pool(fetch_return=[])
    service = CompositeHistoryService(db_pool=pool)

    await service.get_history(ticker="BNS")

    pool.fetch.assert_called_once()
    call_args = pool.fetch.call_args
    # $2 = limit dans la requête
    assert call_args.args[2] == 90


@pytest.mark.asyncio
async def test_get_history_limite_custom():
    """get_history() doit passer la limite personnalisée à la requête DB."""
    pool = _make_mock_pool(fetch_return=[])
    service = CompositeHistoryService(db_pool=pool)

    await service.get_history(ticker="BNS", limit=365)

    pool.fetch.assert_called_once()
    assert pool.fetch.call_args.args[2] == 365


# ---------------------------------------------------------------------------
# Test 5 : ticker invalide → HTTPException 422
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_record_ticker_invalide_leve_exception():
    """record() doit lever HTTPException 422 si le ticker est invalide."""
    pool = _make_mock_pool()
    service = CompositeHistoryService(db_pool=pool)

    with pytest.raises(HTTPException) as exc_info:
        await service.record(ticker="DROP TABLE; --", score=50.0, label="FAIBLE", workflow="value_graham")

    assert exc_info.value.status_code == 422
    pool.execute.assert_not_called()


@pytest.mark.asyncio
async def test_get_history_ticker_invalide_leve_exception():
    """get_history() doit lever HTTPException 422 si le ticker est invalide."""
    pool = _make_mock_pool()
    service = CompositeHistoryService(db_pool=pool)

    with pytest.raises(HTTPException) as exc_info:
        await service.get_history(ticker="")

    assert exc_info.value.status_code == 422
    pool.fetch.assert_not_called()


# ---------------------------------------------------------------------------
# Test 6 : endpoint GET /composite-history/{ticker} — intégration
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_endpoint_composite_history_retourne_json_valide(client):
    """GET /composite-history/BNS doit retourner 200 avec une liste JSON."""
    mock_service = AsyncMock(spec=CompositeHistoryService)
    mock_service.get_history.return_value = [
        CompositeHistoryPoint(
            id=str(uuid.uuid4()),
            ticker="BNS",
            score=72.5,
            label="FORT",
            workflow="value_graham",
            recorded_at=datetime(2026, 5, 14, 12, 0, 0, tzinfo=timezone.utc),
        )
    ]
    fastapi_app.state.composite_history_service = mock_service

    resp = await client.get("/composite-history/BNS")

    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    assert len(data) == 1
    assert data[0]["ticker"] == "BNS"
    assert data[0]["score"] == 72.5
    assert data[0]["label"] == "FORT"
    mock_service.get_history.assert_called_once_with(ticker="BNS", limit=90)


@pytest.mark.asyncio
async def test_endpoint_composite_history_limit_query(client):
    """GET /composite-history/BNS?limit=30 doit transmettre limit=30 au service."""
    mock_service = AsyncMock(spec=CompositeHistoryService)
    mock_service.get_history.return_value = []
    fastapi_app.state.composite_history_service = mock_service

    resp = await client.get("/composite-history/BNS?limit=30")

    assert resp.status_code == 200
    mock_service.get_history.assert_called_once_with(ticker="BNS", limit=30)


@pytest.mark.asyncio
async def test_endpoint_composite_history_vide(client):
    """GET /composite-history/AAPL sans historique doit retourner une liste vide."""
    mock_service = AsyncMock(spec=CompositeHistoryService)
    mock_service.get_history.return_value = []
    fastapi_app.state.composite_history_service = mock_service

    resp = await client.get("/composite-history/AAPL")

    assert resp.status_code == 200
    assert resp.json() == []
