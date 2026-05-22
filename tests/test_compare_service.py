"""Tests unitaires Sprint 80 — CompareService."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.services.compare_service import CompareService


def _make_row(ticker: str, analysis_id: str, result: dict, composite_score: float | None = None, composite_label: str | None = None) -> MagicMock:
    """Simule une Row asyncpg pour analysis_history + composite_score_history."""
    row = MagicMock()
    row.__getitem__ = lambda self, key: {
        "analysis_id": analysis_id,
        "ticker": ticker,
        "result": result,
        "created_at": datetime(2026, 5, 10, 12, 0, 0, tzinfo=timezone.utc),
        "composite_score": composite_score,
        "composite_label": composite_label,
    }[key]
    return row


@pytest.fixture
def mock_pool() -> AsyncMock:
    return AsyncMock()


@pytest.fixture
def service(mock_pool: AsyncMock) -> CompareService:
    return CompareService(db_pool=mock_pool)


@pytest.mark.asyncio
async def test_compare_deux_tickers_présents(service: CompareService, mock_pool: AsyncMock) -> None:
    """compare() retourne une TickerComparison correcte pour 2 tickers en DB."""
    bns_result = {
        "graham": {"verdict": "ACHETER", "defensive_score": 6},
        "buffett_quality": {"verdict": "COMPOUNDER"},
        "dorsey_moat": {"moat_type": "NARROW"},
    }
    td_result = {
        "graham": {"verdict": "CONSERVER", "defensive_score": 5},
    }
    bns_id = str(uuid.uuid4())
    td_id = str(uuid.uuid4())
    mock_pool.fetch.return_value = [
        _make_row("BNS.TO", bns_id, bns_result, 72.5, "FORT"),
        _make_row("TD.TO", td_id, td_result, None, None),
    ]

    response = await service.compare(["BNS.TO", "TD.TO"])

    assert response.tickers == ["BNS.TO", "TD.TO"]
    assert len(response.comparisons) == 2

    bns = response.comparisons[0]
    assert bns.ticker == "BNS.TO"
    assert bns.analysis_id == bns_id
    assert bns.graham_verdict == "ACHETER"
    assert bns.graham_score == 6
    assert bns.buffett_verdict == "COMPOUNDER"
    assert bns.dorsey_moat_type == "NARROW"
    assert bns.composite_score == 72.5
    assert bns.composite_label == "FORT"
    assert bns.created_at is not None

    td = response.comparisons[1]
    assert td.ticker == "TD.TO"
    assert td.graham_verdict == "CONSERVER"
    assert td.composite_score is None
    assert td.composite_label is None


@pytest.mark.asyncio
async def test_compare_ticker_absent_retourne_null(service: CompareService, mock_pool: AsyncMock) -> None:
    """Un ticker absent de l'historique retourne une TickerComparison avec tous champs null."""
    bns_id = str(uuid.uuid4())
    mock_pool.fetch.return_value = [
        _make_row("BNS.TO", bns_id, {"graham": {"verdict": "ACHETER", "defensive_score": 6}}, 70.0, "FORT"),
    ]

    response = await service.compare(["BNS.TO", "FAKE.TO"])

    assert len(response.comparisons) == 2
    absent = next(c for c in response.comparisons if c.ticker == "FAKE.TO")
    assert absent.analysis_id is None
    assert absent.graham_verdict is None
    assert absent.composite_score is None


@pytest.mark.asyncio
async def test_compare_retourne_dans_lordre_des_tickers_demandés(service: CompareService, mock_pool: AsyncMock) -> None:
    """L'ordre des comparisons suit l'ordre des tickers de la requête."""
    td_id = str(uuid.uuid4())
    bns_id = str(uuid.uuid4())
    mock_pool.fetch.return_value = [
        _make_row("BNS.TO", bns_id, {}, None, None),
        _make_row("TD.TO", td_id, {}, None, None),
    ]

    response = await service.compare(["TD.TO", "BNS.TO"])

    assert response.comparisons[0].ticker == "TD.TO"
    assert response.comparisons[1].ticker == "BNS.TO"


@pytest.mark.asyncio
async def test_compare_result_sans_skill_optionnel(service: CompareService, mock_pool: AsyncMock) -> None:
    """Un résultat sans buffett_quality ou dorsey_moat retourne des champs null sans erreur."""
    analysis_id = str(uuid.uuid4())
    mock_pool.fetch.return_value = [
        _make_row("RY.TO", analysis_id, {"graham": {"verdict": "REJETER", "defensive_score": 2}}, None, None),
    ]

    response = await service.compare(["RY.TO", "ABSENT.TO"])

    ry = response.comparisons[0]
    assert ry.buffett_verdict is None
    assert ry.dorsey_moat_type is None
    assert ry.graham_score == 2
