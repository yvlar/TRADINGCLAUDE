"""Tests Sprint 79 — filtre par plage de dates GET /history."""
from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import AsyncMock

import pytest

from app.api.main import app
from app.orchestrator.core import HistoryEntry, HistoryResponse

_ENTRY_2026_01 = HistoryEntry(
    analysis_id="cccccccc-0000-0000-0000-000000000001",
    ticker="BNS",
    workflow="value_graham",
    skills_applied=["graham_analysis"],
    cost_usd=0.004,
    defensive_score=7,
    graham_verdict="CANDIDAT_SOLIDE",
    earnings_verdict=None,
    created_at="2026-01-15T12:00:00+00:00",
)
_ENTRY_2026_04 = HistoryEntry(
    analysis_id="dddddddd-0000-0000-0000-000000000002",
    ticker="BNS",
    workflow="value_graham",
    skills_applied=["graham_analysis"],
    cost_usd=0.003,
    defensive_score=6,
    graham_verdict="A_SURVEILLER",
    earnings_verdict=None,
    created_at="2026-04-20T10:00:00+00:00",
)


class TestHistoryFilterDates:
    """Tests de l'endpoint GET /history avec les paramètres from_dt et to_dt (Sprint 79)."""

    @pytest.mark.asyncio
    async def test_from_dt_seul_retourne_200(self, client):
        """from_dt seul doit retourner 200."""
        app.state.orchestrator.get_history = AsyncMock(
            return_value=HistoryResponse(ticker="BNS", entries=[_ENTRY_2026_04], next_before=None)
        )
        r = await client.get("/history?ticker=BNS&from_dt=2026-03-01")
        assert r.status_code == 200

    @pytest.mark.asyncio
    async def test_to_dt_seul_retourne_200(self, client):
        """to_dt seul doit retourner 200."""
        app.state.orchestrator.get_history = AsyncMock(
            return_value=HistoryResponse(ticker="BNS", entries=[_ENTRY_2026_01], next_before=None)
        )
        r = await client.get("/history?ticker=BNS&to_dt=2026-02-28")
        assert r.status_code == 200

    @pytest.mark.asyncio
    async def test_from_dt_et_to_dt_passes_a_orchestrateur(self, client):
        """from_dt et to_dt sont transmis à orchestrator.get_history() sous forme datetime."""
        mock_get = AsyncMock(
            return_value=HistoryResponse(ticker="BNS", entries=[], next_before=None)
        )
        app.state.orchestrator.get_history = mock_get
        await client.get("/history?ticker=BNS&from_dt=2026-01-01&to_dt=2026-05-18")
        mock_get.assert_called_once()
        kwargs = mock_get.call_args.kwargs
        assert isinstance(kwargs.get("from_dt"), datetime)
        assert isinstance(kwargs.get("to_dt"), datetime)
        assert kwargs["from_dt"].year == 2026
        assert kwargs["from_dt"].month == 1
        assert kwargs["to_dt"].month == 5

    @pytest.mark.asyncio
    async def test_from_dt_invalide_retourne_422(self, client):
        """Un format from_dt invalide doit retourner 422."""
        r = await client.get("/history?ticker=BNS&from_dt=not-a-date")
        assert r.status_code == 422

    @pytest.mark.asyncio
    async def test_to_dt_invalide_retourne_422(self, client):
        """Un format to_dt invalide doit retourner 422."""
        r = await client.get("/history?ticker=BNS&to_dt=31/12/2026")
        assert r.status_code == 422
