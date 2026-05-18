"""
Tests d'evaluation BuffettQualitySkill -- appels Claude REELS sur le golden dataset.

Marqueur @pytest.mark.evals : exclu de la CI standard.
Execution :
  ANTHROPIC_API_KEY=sk-ant-... pytest tests/evals/test_buffett_evals.py -m evals -v

Le skill utilise claude-sonnet-4-6 (analyse qualitative).

IMPORTANT : ne jamais patcher call_claude_with_retry dans ce module.
"""
from __future__ import annotations

import os

import pytest
import pytest_asyncio

from tests.evals.fixtures import load_buffett_golden

_GOLDEN_CASES = load_buffett_golden()

SONNET_MODEL = "claude-sonnet-4-6"


@pytest_asyncio.fixture
async def buffett_skill():
    """BuffettQualitySkill avec client Anthropic reel -- necessite ANTHROPIC_API_KEY."""
    import anthropic
    from app.skills.base import SkillConfig
    from app.skills.tier2.buffett_quality.skill import BuffettQualitySkill

    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        pytest.skip("ANTHROPIC_API_KEY absent -- skip evals")

    client = anthropic.AsyncAnthropic(api_key=api_key)
    return BuffettQualitySkill(
        client=client,
        model=SONNET_MODEL,
        config=SkillConfig(timeout_s=120.0, max_retries=2),
        rag_service=None,
    )


def _build_buffett_input(case: dict):
    from app.skills.tier2.buffett_quality.schemas import (
        BuffettQualityInput,
        BuffettRatios,
        DorseyContext,
    )

    inp = case["input"]
    ratios = BuffettRatios(**inp["ratios"])

    dorsey_ctx = None
    if inp.get("dorsey_context"):
        dorsey_ctx = DorseyContext(**inp["dorsey_context"])

    return BuffettQualityInput(
        ticker=inp["ticker"],
        ratios=ratios,
        dorsey_context=dorsey_ctx,
    )


@pytest.mark.evals
@pytest.mark.parametrize("case", _GOLDEN_CASES, ids=[c["id"] for c in _GOLDEN_CASES])
@pytest.mark.asyncio
async def test_buffett_verdict_dans_allowed(case, buffett_skill):
    """verdict doit etre dans la liste des valeurs autorisees."""
    input_data = _build_buffett_input(case)
    output, _ = await buffett_skill.execute(input_data)
    allowed = case["expected"]["verdict_allowed"]
    assert output.verdict in allowed, (
        f"[{case['id']}] verdict={output.verdict!r} pas dans {allowed}"
    )


@pytest.mark.evals
@pytest.mark.parametrize("case", _GOLDEN_CASES, ids=[c["id"] for c in _GOLDEN_CASES])
@pytest.mark.asyncio
async def test_buffett_filtres_exactement_4(case, buffett_skill):
    """Le schema exige exactement 4 filtres Buffett -- toujours valide."""
    input_data = _build_buffett_input(case)
    output, _ = await buffett_skill.execute(input_data)
    assert len(output.filtres) == 4, (
        f"[{case['id']}] {len(output.filtres)} filtres (attendu 4)"
    )


@pytest.mark.evals
@pytest.mark.parametrize("case", _GOLDEN_CASES, ids=[c["id"] for c in _GOLDEN_CASES])
@pytest.mark.asyncio
async def test_buffett_quality_score_min(case, buffett_skill):
    """quality_score doit etre >= minimum attendu."""
    input_data = _build_buffett_input(case)
    output, _ = await buffett_skill.execute(input_data)
    expected_min = case["expected"]["quality_score_min"]
    assert output.quality_score >= expected_min, (
        f"[{case['id']}] quality_score={output.quality_score} < minimum {expected_min}"
    )


@pytest.mark.evals
@pytest.mark.parametrize("case", _GOLDEN_CASES, ids=[c["id"] for c in _GOLDEN_CASES])
@pytest.mark.asyncio
async def test_buffett_quality_score_dans_plage(case, buffett_skill):
    """quality_score doit etre dans [0, 4]."""
    input_data = _build_buffett_input(case)
    output, _ = await buffett_skill.execute(input_data)
    assert 0 <= output.quality_score <= 4, (
        f"[{case['id']}] quality_score={output.quality_score} hors plage [0,4]"
    )


@pytest.mark.evals
@pytest.mark.asyncio
async def test_buffett_concordance_globale_verdict(buffett_skill):
    """Taux de concordance verdict >= 75 % sur tous les cas."""
    concordant = 0
    total = 0
    for case in _GOLDEN_CASES:
        try:
            input_data = _build_buffett_input(case)
            output, _ = await buffett_skill.execute(input_data)
            if output.verdict in case["expected"]["verdict_allowed"]:
                concordant += 1
            total += 1
        except Exception:
            total += 1

    taux = concordant / total if total > 0 else 0.0
    assert taux >= 0.75, (
        f"Concordance verdict : {concordant}/{total} = {taux:.0%} < 75 % requis"
    )
