"""Tests Sprint 80 — endpoint POST /compare."""
from __future__ import annotations

import uuid
from unittest.mock import AsyncMock

import pytest
import pytest_asyncio

from app.api.main import app as fastapi_app
from app.services.compare_service import CompareResponse, CompareService, TickerComparison


def _make_comparison(ticker: str, score: float | None = None) -> TickerComparison:
    return TickerComparison(
        ticker=ticker,
        analysis_id=str(uuid.uuid4()),
        graham_verdict="ACHETER",
        graham_score=6,
        buffett_verdict="COMPOUNDER",
        dorsey_moat_type="NARROW",
        composite_score=score,
        composite_label="FORT" if score else None,
        created_at="2026-05-10T12:00:00+00:00",
    )


@pytest_asyncio.fixture
async def compare_client(client):
    """Injecte un CompareService mocké dans l'état de l'application."""
    mock_service = AsyncMock(spec=CompareService)
    fastapi_app.state.compare_service = mock_service
    yield client, mock_service


@pytest.mark.asyncio
async def test_post_compare_deux_tickers_200(compare_client) -> None:
    """POST /compare avec 2 tickers → 200 et la réponse attendue."""
    client, mock_service = compare_client
    mock_service.compare.return_value = CompareResponse(
        tickers=["BNS.TO", "TD.TO"],
        comparisons=[_make_comparison("BNS.TO", 72.5), _make_comparison("TD.TO", 65.0)],
    )

    resp = await client.post("/compare", json={"tickers": ["BNS.TO", "TD.TO"]})

    assert resp.status_code == 200
    data = resp.json()
    assert data["tickers"] == ["BNS.TO", "TD.TO"]
    assert len(data["comparisons"]) == 2
    mock_service.compare.assert_called_once()


@pytest.mark.asyncio
async def test_post_compare_un_ticker_422(compare_client) -> None:
    """POST /compare avec 1 seul ticker → 422 validation error."""
    client, _ = compare_client

    resp = await client.post("/compare", json={"tickers": ["BNS.TO"]})

    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_post_compare_six_tickers_422(compare_client) -> None:
    """POST /compare avec 6 tickers → 422 validation error."""
    client, _ = compare_client

    resp = await client.post("/compare", json={"tickers": ["A", "B", "C", "D", "E", "F"]})

    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_post_compare_cinq_tickers_200(compare_client) -> None:
    """POST /compare avec exactement 5 tickers → 200."""
    client, mock_service = compare_client
    tickers = ["BNS.TO", "TD.TO", "RY.TO", "BMO.TO", "CM.TO"]
    mock_service.compare.return_value = CompareResponse(
        tickers=tickers,
        comparisons=[_make_comparison(t) for t in tickers],
    )

    resp = await client.post("/compare", json={"tickers": tickers})

    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_post_compare_ticker_absent_retourne_null(compare_client) -> None:
    """POST /compare avec un ticker sans analyse → colonne avec null."""
    client, mock_service = compare_client
    mock_service.compare.return_value = CompareResponse(
        tickers=["BNS.TO", "FAKE.TO"],
        comparisons=[
            _make_comparison("BNS.TO", 70.0),
            TickerComparison(ticker="FAKE.TO"),
        ],
    )

    resp = await client.post("/compare", json={"tickers": ["BNS.TO", "FAKE.TO"]})

    assert resp.status_code == 200
    data = resp.json()
    inconnu = next(c for c in data["comparisons"] if c["ticker"] == "FAKE.TO")
    assert inconnu["analysis_id"] is None
    assert inconnu["graham_verdict"] is None
    assert inconnu["composite_score"] is None


@pytest.mark.asyncio
async def test_post_compare_liste_vide_422(compare_client) -> None:
    """POST /compare avec liste vide → 422."""
    client, _ = compare_client

    resp = await client.post("/compare", json={"tickers": []})

    assert resp.status_code == 422
