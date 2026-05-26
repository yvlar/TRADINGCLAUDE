"""Tests Sprint 107/112 — Orchestrator.get_metrics() + get_skill_analyses() enrichis."""
from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.orchestrator.core import Orchestrator


def _build_orchestrator(
    global_row: dict,
    ticker_rows: list[dict],
    skill_rows: list[dict],
    workflow_rows: list[dict],
    daily_rows: list[dict] | None = None,
) -> Orchestrator:
    """Construit un Orchestrator dont le pool renvoie les lignes simulées dans l'ordre des requêtes."""
    pool = MagicMock()
    pool.fetchrow = AsyncMock(return_value=global_row)
    # get_metrics enchaîne 4 fetch : top_tickers, skills, cache_by_workflow, daily_cost
    pool.fetch = AsyncMock(
        side_effect=[ticker_rows, skill_rows, workflow_rows, daily_rows or []]
    )
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
    assert result.daily_cost == {}


@pytest.mark.asyncio
async def test_get_metrics_construit_daily_cost():
    """daily_cost doit mapper chaque jour (YYYY-MM-DD) à son coût total arrondi."""
    orch = _build_orchestrator(
        global_row={"total": 3, "total_cost": 0.03, "avg_cache_hit": 0.4},
        ticker_rows=[],
        skill_rows=[],
        workflow_rows=[],
        daily_rows=[
            {"day": "2026-05-24", "cost": 0.012},
            {"day": "2026-05-25", "cost": 0.018},
        ],
    )

    result = await orch.get_metrics(days=7)

    assert result.daily_cost == {"2026-05-24": 0.012, "2026-05-25": 0.018}


@pytest.mark.asyncio
async def test_get_skill_analyses_mappe_les_entrees():
    """get_skill_analyses retourne les analyses ayant utilisé le skill, triées par date DESC."""
    pool = MagicMock()
    pool.fetch = AsyncMock(
        return_value=[
            {
                "id": "11111111-1111-1111-1111-111111111111",
                "ticker": "BNS.TO",
                "workflow_name": "value_graham",
                "cost_usd": 0.0123,
                "created_at": datetime(2026, 5, 25, 10, 0, tzinfo=timezone.utc),
            },
        ]
    )
    orch = Orchestrator(
        db_pool=pool, graham_skill=MagicMock(), earnings_skill=MagicMock()
    )

    result = await orch.get_skill_analyses(skill="graham_analysis", days=30)

    assert result.skill == "graham_analysis"
    assert result.period_days == 30
    assert len(result.entries) == 1
    entry = result.entries[0]
    assert entry.analysis_id == "11111111-1111-1111-1111-111111111111"
    assert entry.ticker == "BNS.TO"
    assert entry.workflow_name == "value_graham"
    assert entry.cost_usd == 0.0123
    assert entry.created_at == "2026-05-25T10:00:00+00:00"
    # le filtre jsonb @> reçoit bien la liste sérialisée du skill demandé
    assert pool.fetch.await_args.args[2] == '["graham_analysis"]'


@pytest.mark.asyncio
async def test_get_skill_analyses_vide():
    """Aucune analyse → entries vide, pas d'erreur."""
    pool = MagicMock()
    pool.fetch = AsyncMock(return_value=[])
    orch = Orchestrator(
        db_pool=pool, graham_skill=MagicMock(), earnings_skill=MagicMock()
    )

    result = await orch.get_skill_analyses(skill="munger_mental_models", days=90)

    assert result.entries == []
    assert result.period_days == 90
