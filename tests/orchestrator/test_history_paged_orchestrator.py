"""Tests Sprint 90 — Orchestrator.get_history_paged() (offset/limit + total_count)."""
from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.orchestrator.core import Orchestrator, PagedHistoryResponse


def _build_orchestrator(rows: list[dict], total_count: int) -> Orchestrator:
    """Construit un Orchestrator dont le pool DB renvoie `rows` et `total_count`."""
    pool = MagicMock()
    pool.fetch = AsyncMock(return_value=rows)
    pool.fetchval = AsyncMock(return_value=total_count)
    return Orchestrator(
        db_pool=pool,
        graham_skill=MagicMock(),
        earnings_skill=MagicMock(),
    )


def _row(idx: int) -> dict:
    """Helper : ligne SQL simulée."""
    return {
        "id": f"00000000-0000-0000-0000-{idx:012d}",
        "ticker": "BNS",
        "workflow_name": "value_graham",
        "skills_used": "[\"graham_analysis\"]",
        "cost_usd": 0.004,
        "result": '{"graham": {"defensive_score": 7, "verdict": "CANDIDAT_SOLIDE"}}',
        "created_at": datetime(2026, 5, 10 + idx % 10, 12, 0, tzinfo=timezone.utc),
        "tags": [],
    }


class TestGetHistoryPaged:
    """Tests de la méthode `get_history_paged()` introduite Sprint 90."""

    @pytest.mark.asyncio
    async def test_execute_limit_offset_attendus(self):
        """SELECT doit utiliser LIMIT=page_size et OFFSET=(page-1)*page_size."""
        rows = [_row(i) for i in range(5)]
        orch = _build_orchestrator(rows, total_count=42)

        result = await orch.get_history_paged(ticker="BNS", page=3, page_size=5)

        # Vérifier que fetch a été appelé avec les bons params LIMIT/OFFSET
        call_args = orch._db.fetch.call_args
        sql = call_args.args[0]
        params = call_args.args[1:]
        assert "LIMIT $5 OFFSET $6" in sql
        # ticker, q, from_dt, to_dt, page_size, offset
        assert params[4] == 5  # page_size
        assert params[5] == 10  # offset = (3-1) * 5
        assert isinstance(result, PagedHistoryResponse)
        assert result.page == 3
        assert result.page_size == 5

    @pytest.mark.asyncio
    async def test_total_count_retourne_count_correct(self):
        """total_count doit refléter la valeur retournée par SELECT COUNT(*)."""
        rows = [_row(i) for i in range(10)]
        orch = _build_orchestrator(rows, total_count=137)

        result = await orch.get_history_paged(ticker="BNS", page=1, page_size=10)

        assert result.total_count == 137
        # total_pages = ceil(137/10) = 14
        assert result.total_pages == 14
        # fetchval a été appelé pour COUNT(*)
        orch._db.fetchval.assert_called_once()

    @pytest.mark.asyncio
    async def test_page_2_retourne_entries_attendues(self):
        """Page 2 avec page_size=10 doit utiliser OFFSET=10 et retourner les entries fournies."""
        rows = [_row(i + 10) for i in range(10)]
        orch = _build_orchestrator(rows, total_count=25)

        result = await orch.get_history_paged(ticker="BNS", page=2, page_size=10)

        # Vérifier offset
        call_args = orch._db.fetch.call_args
        params = call_args.args[1:]
        assert params[5] == 10  # offset
        # 10 entries retournées
        assert len(result.entries) == 10
        # total_pages = ceil(25/10) = 3
        assert result.total_pages == 3
