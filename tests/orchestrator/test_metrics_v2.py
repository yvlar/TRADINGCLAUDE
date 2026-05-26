"""Tests Sprint 107 — Orchestrator.get_metrics() enrichi (skills_cost + cache_by_workflow)."""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from app.orchestrator.core import Orchestrator


def _build_orchestrator(
    global_row: dict,
    ticker_rows: list[dict],
    skill_rows: list[dict],
    workflow_rows: list[dict],
) -> Orchestrator:
    """Construit un Orchestrator dont le pool renvoie les lignes simulées dans l'ordre des requêtes."""
    pool = MagicMock()
    pool.fetchrow = AsyncMock(return_value=global_row)
    # get_metrics enchaîne 3 fetch : top_tickers, skills, cache_by_workflow
    pool.fetch = AsyncMock(side_effect=[ticker_rows, skill_rows, workflow_rows])
    return Orchestrator(
        db_pool=pool,
        graham_skill=MagicMock(),
        earnings_skill=MagicMock(),
    )


@pytest.mark.asyncio
async def test_get_metrics_construit_skills_cost():
    """skills_cost doit refléter le coût agrégé par skill renvoyé par la requête SQL."""
    orch = _build_orchestrator(
        global_row={"total": 4, "total_cost": 0.02, "avg_cache_hit": 0.5},
        ticker_rows=[{"ticker": "BNS", "nb": 2, "total_cost": 0.01}],
        skill_rows=[
            {"skill": "graham_analysis", "nb": 4, "cost": 0.012},
            {"skill": "buffett_quality", "nb": 2, "cost": 0.008},
        ],
        workflow_rows=[],
    )

    result = await orch.get_metrics(days=30)

    assert result.skills_cost == {"graham_analysis": 0.012, "buffett_quality": 0.008}
    assert result.skills_usage == {"graham_analysis": 4, "buffett_quality": 2}


@pytest.mark.asyncio
async def test_get_metrics_construit_cache_by_workflow():
    """cache_by_workflow doit mapper chaque workflow_name à son taux de cache moyen arrondi."""
    orch = _build_orchestrator(
        global_row={"total": 3, "total_cost": 0.009, "avg_cache_hit": 0.6},
        ticker_rows=[],
        skill_rows=[],
        workflow_rows=[
            {"workflow_name": "value_graham", "cache_ratio": 0.7234},
            {"workflow_name": "compounder_buffett", "cache_ratio": 0.55},
        ],
    )

    result = await orch.get_metrics(days=7)

    assert result.cache_by_workflow == {
        "value_graham": 0.7234,
        "compounder_buffett": 0.55,
    }


@pytest.mark.asyncio
async def test_get_metrics_champs_vides_par_defaut():
    """Sans skills ni workflows, les nouveaux dicts sont vides (pas None)."""
    orch = _build_orchestrator(
        global_row={"total": 0, "total_cost": 0.0, "avg_cache_hit": 0.0},
        ticker_rows=[],
        skill_rows=[],
        workflow_rows=[],
    )

    result = await orch.get_metrics(days=30)

    assert result.skills_cost == {}
    assert result.cache_by_workflow == {}
