"""Tests Sprint 73 — recherche full-text GET /history avec paramètre q."""
from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from app.api.main import app
from app.orchestrator.core import HistoryEntry, HistoryResponse

# ── entrées réutilisées dans plusieurs tests ────────────────────────────────
_ENTRY_BNS = HistoryEntry(
    analysis_id="aaaaaaaa-0000-0000-0000-000000000001",
    ticker="BNS",
    workflow="value_graham",
    skills_applied=["graham_analysis"],
    cost_usd=0.004,
    defensive_score=7,
    graham_verdict="CANDIDAT_SOLIDE",
    earnings_verdict="QUALITE_ACCEPTABLE",
    created_at="2026-05-10T12:00:00+00:00",
)
_ENTRY_TD = HistoryEntry(
    analysis_id="bbbbbbbb-0000-0000-0000-000000000002",
    ticker="TD",
    workflow="value_graham",
    skills_applied=["graham_analysis"],
    cost_usd=0.003,
    defensive_score=6,
    graham_verdict="A_SURVEILLER",
    earnings_verdict=None,
    created_at="2026-05-09T10:00:00+00:00",
)


class TestHistorySearchEndpoint:
    """Tests de l'endpoint GET /history avec le paramètre q (Sprint 73)."""

    @pytest.mark.asyncio
    async def test_q_seul_retourne_200(self, client):
        """q sans ticker doit retourner 200 (recherche cross-ticker)."""
        app.state.orchestrator.get_history = AsyncMock(
            return_value=HistoryResponse(ticker=None, entries=[_ENTRY_BNS, _ENTRY_TD], next_before=None)
        )
        r = await client.get("/history?q=CANDIDAT")
        assert r.status_code == 200

    @pytest.mark.asyncio
    async def test_q_seul_ticker_null_dans_reponse(self, client):
        """Quand q est fourni sans ticker, response.ticker est null."""
        app.state.orchestrator.get_history = AsyncMock(
            return_value=HistoryResponse(ticker=None, entries=[], next_before=None)
        )
        r = await client.get("/history?q=ACHAT")
        assert r.json()["ticker"] is None

    @pytest.mark.asyncio
    async def test_q_et_ticker_retourne_200(self, client):
        """q + ticker combinés doivent retourner 200."""
        app.state.orchestrator.get_history = AsyncMock(
            return_value=HistoryResponse(ticker="BNS", entries=[_ENTRY_BNS], next_before=None)
        )
        r = await client.get("/history?ticker=BNS&q=CANDIDAT")
        assert r.status_code == 200

    @pytest.mark.asyncio
    async def test_ni_ticker_ni_q_retourne_422(self, client):
        """Sans ticker ni q, l'endpoint retourne 422."""
        r = await client.get("/history")
        assert r.status_code == 422

    @pytest.mark.asyncio
    async def test_q_seul_retourne_entries_cross_ticker(self, client):
        """Résultats cross-ticker renvoyés quand q seul est fourni."""
        app.state.orchestrator.get_history = AsyncMock(
            return_value=HistoryResponse(ticker=None, entries=[_ENTRY_BNS, _ENTRY_TD], next_before=None)
        )
        r = await client.get("/history?q=value_graham")
        data = r.json()
        tickers = [e["ticker"] for e in data["entries"]]
        assert "BNS" in tickers
        assert "TD" in tickers

    @pytest.mark.asyncio
    async def test_q_passe_a_orchestrateur(self, client):
        """Le paramètre q doit être transmis à orchestrator.get_history()."""
        mock_get = AsyncMock(
            return_value=HistoryResponse(ticker=None, entries=[], next_before=None)
        )
        app.state.orchestrator.get_history = mock_get
        await client.get("/history?q=ACHAT")
        mock_get.assert_called_once()
        call_kwargs = mock_get.call_args.kwargs
        assert call_kwargs.get("q") == "ACHAT"
        assert call_kwargs.get("ticker") is None

    @pytest.mark.asyncio
    async def test_ticker_et_q_passes_a_orchestrateur(self, client):
        """ticker et q sont tous deux transmis quand fournis ensemble."""
        mock_get = AsyncMock(
            return_value=HistoryResponse(ticker="BNS", entries=[], next_before=None)
        )
        app.state.orchestrator.get_history = mock_get
        await client.get("/history?ticker=BNS&q=CANDIDAT")
        call_kwargs = mock_get.call_args.kwargs
        assert call_kwargs.get("ticker") == "BNS"
        assert call_kwargs.get("q") == "CANDIDAT"

    @pytest.mark.asyncio
    async def test_q_avec_limit_valide_retourne_200(self, client):
        """q avec limit valide doit fonctionner."""
        app.state.orchestrator.get_history = AsyncMock(
            return_value=HistoryResponse(ticker=None, entries=[], next_before=None)
        )
        r = await client.get("/history?q=graham&limit=5")
        assert r.status_code == 200

    @pytest.mark.asyncio
    async def test_q_avec_limit_invalide_retourne_422(self, client):
        """q avec limit hors plage doit retourner 422."""
        r = await client.get("/history?q=test&limit=0")
        assert r.status_code == 422
