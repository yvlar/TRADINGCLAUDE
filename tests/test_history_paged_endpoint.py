"""Tests Sprint 90 — Endpoint GET /history-paged (validation + intégration)."""
from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from app.api.main import app
from app.orchestrator.core import HistoryEntry, PagedHistoryResponse


_ENTRY = HistoryEntry(
    analysis_id="aaaaaaaa-0000-0000-0000-000000000001",
    ticker="BNS",
    workflow="value_graham",
    skills_applied=["graham_analysis"],
    cost_usd=0.004,
    defensive_score=7,
    graham_verdict="CANDIDAT_SOLIDE",
    earnings_verdict=None,
    created_at="2026-05-10T12:00:00+00:00",
)


class TestHistoryPagedEndpoint:
    """Tests Sprint 90 du nouvel endpoint GET /history-paged."""

    @pytest.mark.asyncio
    async def test_200_avec_page_et_page_size(self, client):
        """GET /history-paged avec page=1&page_size=10 retourne 200 et le corps PagedHistoryResponse."""
        app.state.orchestrator.get_history_paged = AsyncMock(
            return_value=PagedHistoryResponse(
                ticker="BNS",
                q=None,
                entries=[_ENTRY],
                page=1,
                page_size=10,
                total_count=1,
                total_pages=1,
            )
        )
        r = await client.get("/history-paged?ticker=BNS&page=1&page_size=10")
        assert r.status_code == 200
        body = r.json()
        assert body["page"] == 1
        assert body["page_size"] == 10
        assert body["total_count"] == 1
        assert body["total_pages"] == 1
        assert len(body["entries"]) == 1

    @pytest.mark.asyncio
    async def test_page_inferieure_1_retourne_422(self, client):
        """page=0 doit retourner 422."""
        r = await client.get("/history-paged?ticker=BNS&page=0&page_size=10")
        assert r.status_code == 422

    @pytest.mark.asyncio
    async def test_page_size_superieur_50_retourne_422(self, client):
        """page_size>50 doit retourner 422."""
        r = await client.get("/history-paged?ticker=BNS&page=1&page_size=51")
        assert r.status_code == 422

    @pytest.mark.asyncio
    async def test_total_pages_calcule_correctement(self, client):
        """total_pages doit refléter ceil(total_count/page_size)."""
        # 25 analyses, page_size=10 → total_pages=3
        app.state.orchestrator.get_history_paged = AsyncMock(
            return_value=PagedHistoryResponse(
                ticker="BNS",
                q=None,
                entries=[_ENTRY] * 10,
                page=1,
                page_size=10,
                total_count=25,
                total_pages=3,
            )
        )
        r = await client.get("/history-paged?ticker=BNS&page=1&page_size=10")
        assert r.status_code == 200
        body = r.json()
        assert body["total_count"] == 25
        assert body["total_pages"] == 3
