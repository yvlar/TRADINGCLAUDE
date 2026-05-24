"""Tests de routing multi-modele -- Sprint 44.

Verifie que les skills mecaniques/quantitatifs utilisent Haiku et que les skills
qualitatifs conservent Sonnet, a la fois au niveau unitaire et via le lifespan.
"""
from __future__ import annotations

import os
import types
from contextlib import ExitStack
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

HAIKU_MODEL = "claude-haiku-4-5-20251001"
SONNET_MODEL = "claude-sonnet-4-6"

_SKILL_PROMPT_PATCHES = [
    "app.skills.tier2.graham_analysis.skill.GrahamAnalysisSkill._load_system_prompt",
    "app.skills.tier2.earnings_quality.skill.EarningsQualitySkill._load_system_prompt",
    "app.skills.tier2.dorsey_moat.skill.DorseyMoatSkill._load_system_prompt",
    "app.skills.tier2.buffett_quality.skill.BuffettQualitySkill._load_system_prompt",
    "app.skills.tier2.stock_valuation.skill.StockValuationSkill._load_system_prompt",
    "app.skills.tier2.thesis_builder.skill.ThesisBuilderSkill._load_system_prompt",
    "app.skills.tier2.munger_mental.skill.MungerMentalSkill._load_system_prompt",
    "app.skills.tier2.canadian_tax.skill.CanadianTaxSkill._load_system_prompt",
    "app.skills.tier2.lynch_categories.skill.LynchCategoriesSkill._load_system_prompt",
    "app.skills.tier2.fisher_scuttlebutt.skill.FisherScuttlebuttSkill._load_system_prompt",
    "app.skills.tier2.klarman_margin.skill.KlarmanMarginSkill._load_system_prompt",
    "app.skills.tier2.greenblatt.skill.GreenblattSkill._load_system_prompt",
    "app.skills.tier2.damodaran_narrative.skill.DamodararNarrativeSkill._load_system_prompt",
    "app.skills.tier2.marks_cycles.skill.MarksCyclesSkill._load_system_prompt",
    "app.skills.tier2.pabrai_dhandho.skill.PabraiDhandhoSkill._load_system_prompt",
]


def _make_skill(cls, class_path: str, model: str):
    with patch(f"{class_path}._load_system_prompt", return_value="prompt-test"):
        return cls(client=MagicMock(), model=model)


# ---------------------------------------------------------------------------
# Tests unitaires -- constructeur de chaque skill
# ---------------------------------------------------------------------------

def test_earnings_quality_accepte_haiku():
    from app.skills.tier2.earnings_quality.skill import EarningsQualitySkill
    skill = _make_skill(
        EarningsQualitySkill,
        "app.skills.tier2.earnings_quality.skill.EarningsQualitySkill",
        HAIKU_MODEL,
    )
    assert skill._model == HAIKU_MODEL


def test_greenblatt_accepte_haiku():
    from app.skills.tier2.greenblatt.skill import GreenblattSkill
    skill = _make_skill(
        GreenblattSkill,
        "app.skills.tier2.greenblatt.skill.GreenblattSkill",
        HAIKU_MODEL,
    )
    assert skill._model == HAIKU_MODEL


def test_lynch_accepte_haiku():
    from app.skills.tier2.lynch_categories.skill import LynchCategoriesSkill
    skill = _make_skill(
        LynchCategoriesSkill,
        "app.skills.tier2.lynch_categories.skill.LynchCategoriesSkill",
        HAIKU_MODEL,
    )
    assert skill._model == HAIKU_MODEL


def test_graham_accepte_sonnet():
    from app.skills.tier2.graham_analysis.skill import GrahamAnalysisSkill
    skill = _make_skill(
        GrahamAnalysisSkill,
        "app.skills.tier2.graham_analysis.skill.GrahamAnalysisSkill",
        SONNET_MODEL,
    )
    assert skill._model == SONNET_MODEL


def test_dorsey_accepte_sonnet():
    from app.skills.tier2.dorsey_moat.skill import DorseyMoatSkill
    skill = _make_skill(
        DorseyMoatSkill,
        "app.skills.tier2.dorsey_moat.skill.DorseyMoatSkill",
        SONNET_MODEL,
    )
    assert skill._model == SONNET_MODEL


def test_buffett_accepte_sonnet():
    from app.skills.tier2.buffett_quality.skill import BuffettQualitySkill
    skill = _make_skill(
        BuffettQualitySkill,
        "app.skills.tier2.buffett_quality.skill.BuffettQualitySkill",
        SONNET_MODEL,
    )
    assert skill._model == SONNET_MODEL


def test_damodaran_accepte_sonnet():
    from app.skills.tier2.damodaran_narrative.skill import DamodararNarrativeSkill
    skill = _make_skill(
        DamodararNarrativeSkill,
        "app.skills.tier2.damodaran_narrative.skill.DamodararNarrativeSkill",
        SONNET_MODEL,
    )
    assert skill._model == SONNET_MODEL


def test_marks_accepte_sonnet():
    from app.skills.tier2.marks_cycles.skill import MarksCyclesSkill
    skill = _make_skill(
        MarksCyclesSkill,
        "app.skills.tier2.marks_cycles.skill.MarksCyclesSkill",
        SONNET_MODEL,
    )
    assert skill._model == SONNET_MODEL


# ---------------------------------------------------------------------------
# Test d'integration -- lifespan main.py assigne les bons modeles
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_routing_lifespan_haiku_sur_skills_mecaniques():
    """Le lifespan de main.py doit assigner Haiku aux 3 skills mecaniques."""
    from app.api.main import lifespan

    env_vars = {
        "ANTHROPIC_API_KEY": "sk-ant-test-key",
        "CLAUDE_MODEL": SONNET_MODEL,
        "CLAUDE_HAIKU_MODEL": HAIKU_MODEL,
    }

    mock_rag_client = AsyncMock()
    mock_rag_client.ensure_collection = AsyncMock()
    mock_rag_client.close = AsyncMock()

    mock_redis_pool = AsyncMock()
    mock_redis_pool.aclose = AsyncMock()

    mock_app = MagicMock()
    mock_app.state = types.SimpleNamespace()

    with ExitStack() as stack:
        stack.enter_context(patch.dict(os.environ, env_vars))
        mock_pool = stack.enter_context(
            patch("asyncpg.create_pool", new_callable=AsyncMock)
        )
        mock_pool.return_value = AsyncMock()
        mock_pool.return_value.close = AsyncMock()
        stack.enter_context(
            patch("anthropic.AsyncAnthropic", return_value=MagicMock())
        )
        stack.enter_context(
            patch("app.api.main.RagClient", return_value=mock_rag_client)
        )
        stack.enter_context(
            patch("app.api.main.aioredis.from_url", return_value=mock_redis_pool)
        )
        for prompt_path in _SKILL_PROMPT_PATCHES:
            stack.enter_context(patch(prompt_path, return_value="prompt-test"))

        async with lifespan(mock_app):
            orchestrator = mock_app.state.orchestrator
            # Skills mecaniques -> Haiku
            assert orchestrator._earnings._model == HAIKU_MODEL, (
                f"earnings_quality doit utiliser {HAIKU_MODEL}"
            )
            assert orchestrator._greenblatt._model == HAIKU_MODEL, (
                f"greenblatt doit utiliser {HAIKU_MODEL}"
            )
            assert orchestrator._lynch._model == HAIKU_MODEL, (
                f"lynch_categories doit utiliser {HAIKU_MODEL}"
            )
            # Skills qualitatifs -> Sonnet
            assert orchestrator._graham._model == SONNET_MODEL
            assert orchestrator._dorsey._model == SONNET_MODEL
            assert orchestrator._buffett._model == SONNET_MODEL
            assert orchestrator._damodaran._model == SONNET_MODEL
            assert orchestrator._marks._model == SONNET_MODEL
            assert orchestrator._munger._model == SONNET_MODEL
            assert orchestrator._thesis._model == SONNET_MODEL
