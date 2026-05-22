"""Tests Sprint 89 — EsgHistoryService (aucun appel DB reel — asyncpg mocke)."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock

import pytest

from app.services.esg_history_service import EsgHistoryPoint, EsgHistoryService


def _make_row(
    ticker: str = "BNS",
    score: float = 7.5,
    verdict: str = "ESG_MODERE",
    recorded_at: datetime | None = None,
) -> dict:
    """Simule une ligne asyncpg.Record sous forme de dict."""
    return {
        "id": uuid.uuid4().int >> 64,
        "ticker": ticker,
        "score": score,
        "verdict": verdict,
        "recorded_at": recorded_at or datetime.now(timezone.utc),
    }


def _make_mock_pool(fetch_return=None, execute_return: str = "INSERT 1") -> AsyncMock:
    pool = AsyncMock()
    pool.execute = AsyncMock(return_value=execute_return)
    pool.fetch = AsyncMock(return_value=fetch_return or [])
    return pool


# ---------------------------------------------------------------------------
# Test 1 : record() calcule le bon verdict via esg_verdict() (FORT/MODERE/FAIBLE)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_record_calcule_verdict_fort_modere_faible():
    """record() doit calculer le verdict via esg_verdict() : >=10 FORT, >=5 MODERE, sinon FAIBLE."""
    pool = _make_mock_pool()
    service = EsgHistoryService(db_pool=pool)

    # FORT
    await service.record(ticker="BNS", score=12.0)
    assert pool.execute.await_args.args[3] == "ESG_FORT"

    # MODERE
    pool.execute.reset_mock()
    await service.record(ticker="BNS", score=7.0)
    assert pool.execute.await_args.args[3] == "ESG_MODERE"

    # FAIBLE
    pool.execute.reset_mock()
    await service.record(ticker="BNS", score=3.0)
    assert pool.execute.await_args.args[3] == "ESG_FAIBLE"


# ---------------------------------------------------------------------------
# Test 2 : record() insere dans la table avec les bons parametres
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_record_insere_dans_la_table():
    """record() doit appeler pool.execute avec ticker, score et verdict en $1, $2, $3."""
    pool = _make_mock_pool()
    service = EsgHistoryService(db_pool=pool)

    await service.record(ticker="RY", score=11.5)

    pool.execute.assert_awaited_once()
    call_args = pool.execute.await_args
    # call_args.args[0] = SQL, [1] = ticker, [2] = score, [3] = verdict
    assert call_args.args[1] == "RY"
    assert call_args.args[2] == pytest.approx(11.5)
    assert call_args.args[3] == "ESG_FORT"


# ---------------------------------------------------------------------------
# Test 3 : get_history() retourne les points tries DESC (par recorded_at)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_get_history_tri_desc():
    """get_history() doit retourner les points dans l'ordre retourne par la DB (DESC)."""
    rows = [
        _make_row(score=11.0, verdict="ESG_FORT", recorded_at=datetime(2026, 5, 1, tzinfo=timezone.utc)),
        _make_row(score=7.0, verdict="ESG_MODERE", recorded_at=datetime(2026, 4, 1, tzinfo=timezone.utc)),
        _make_row(score=3.0, verdict="ESG_FAIBLE", recorded_at=datetime(2026, 3, 1, tzinfo=timezone.utc)),
    ]
    pool = _make_mock_pool(fetch_return=rows)
    service = EsgHistoryService(db_pool=pool)

    result = await service.get_history(ticker="BNS", limit=100)

    assert len(result) == 3
    assert all(isinstance(p, EsgHistoryPoint) for p in result)
    assert result[0].score == 11.0
    assert result[1].score == 7.0
    assert result[2].score == 3.0
    # Verifie que limit est passe a la DB
    pool.fetch.assert_awaited_once()
    assert pool.fetch.await_args.args[2] == 100
