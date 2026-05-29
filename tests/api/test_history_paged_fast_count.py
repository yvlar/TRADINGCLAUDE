"""Tests Sprint 96 — fast_count=True via pg_class.reltuples dans get_history_paged()."""
from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.orchestrator.core import Orchestrator


def _build_orchestrator(rows: list[dict], total_count: int) -> Orchestrator:
    pool = MagicMock()
    pool.fetch = AsyncMock(return_value=rows)
    pool.fetchval = AsyncMock(return_value=total_count)
    return Orchestrator(
        db_pool=pool,
        graham_skill=MagicMock(),
        earnings_skill=MagicMock(),
    )


def _row(idx: int) -> dict:
    return {
        "id": f"00000000-0000-0000-0000-{idx:012d}",
        "ticker": "BNS",
        "workflow_name": "value_graham",
        "skills_used": '["graham_analysis"]',
        "cost_usd": 0.004,
        "result": '{"graham": {"defensive_score": 7, "verdict": "CANDIDAT_SOLIDE"}}',
        "created_at": datetime(2026, 5, 10 + idx % 10, 12, 0, tzinfo=timezone.utc),
        "tags": [],
    }


class TestFastCount:
    @pytest.mark.asyncio
    async def test_fast_count_false_appelle_select_count(self):
        """fast_count=False doit appeler fetchval avec SELECT COUNT(*)."""
        orch = _build_orchestrator([_row(0)], total_count=5)

        await orch.get_history_paged(ticker="BNS", page=1, page_size=10, fast_count=False)

        sql = orch._db.fetchval.call_args.args[0]
        assert "COUNT(*)" in sql
        assert "pg_class" not in sql

    @pytest.mark.asyncio
    async def test_fast_count_true_sans_filtre_appelle_pg_class(self):
        """fast_count=True sans filtre doit appeler fetchval avec pg_class.reltuples."""
        orch = _build_orchestrator([_row(0)], total_count=50000)

        result = await orch.get_history_paged(ticker=None, q=None, page=1, page_size=10, fast_count=True)

        sql = orch._db.fetchval.call_args.args[0]
        assert "pg_class" in sql
        assert "reltuples" in sql
        assert "COUNT(*)" not in sql
        assert result.total_count == 50000

    @pytest.mark.asyncio
    async def test_fast_count_true_avec_filtre_ticker_retombe_sur_count(self):
        """fast_count=True avec filtre ticker doit retomber sur SELECT COUNT(*) exact."""
        orch = _build_orchestrator([_row(0)], total_count=3)

        await orch.get_history_paged(ticker="BNS", q=None, page=1, page_size=10, fast_count=True)

        sql = orch._db.fetchval.call_args.args[0]
        assert "COUNT(*)" in sql
        assert "pg_class" not in sql
