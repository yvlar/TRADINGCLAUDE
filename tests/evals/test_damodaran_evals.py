"""
Tests d'evaluation DamodararNarrativeSkill -- appels Claude REELS sur le golden dataset.

Marqueur @pytest.mark.evals : exclu de la CI standard.
Execution :
  ANTHROPIC_API_KEY=sk-ant-... pytest tests/evals/test_damodaran_evals.py -m evals -v

Le skill utilise claude-sonnet-4-6 (analyse qualitative narrative).

IMPORTANT : ne jamais patcher call_claude_with_retry dans ce module.
"""
from __future__ import annotations

import os

import pytest
import pytest_asyncio

from tests.evals.fixtures import load_damodaran_golden

_GOLDEN_CASES = load_damodaran_golden()

SONNET_MODEL = "claude-sonnet-4-6"


@pytest_asyncio.fixture
async def damodaran_skill():
    """DamodararNarrativeSkill avec client Anthropic reel -- necessite ANTHROPIC_API_KEY."""
    import anthropic
    from app.skills.base import SkillConfig
    from app.skills.tier2.damodaran_narrative.skill import DamodararNarrativeSkill

    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        pytest.skip("ANTHROPIC_API_KEY absent -- skip evals")

    client = anthropic.AsyncAnthropic(api_key=api_key)
    return DamodararNarrativeSkill(
        client=client,
        model=SONNET_MODEL,
        config=SkillConfig(timeout_s=120.0, max_retries=2),
        rag_service=None,
    )


def _build_damodaran_input(case: dict):
    from app.skills.tier2.damodaran_narrative.schemas import (
        DamodararInput,
        DamodararRatios,
    )

    inp = case["input"]
    ratios = DamodararRatios(**inp["ratios"])
    return DamodararInput(
        ticker=inp["ticker"],
        narrative_text=inp["narrative_text"],
        damodaran_ratios=ratios,
    )


@pytest.mark.evals
@pytest.mark.parametrize("case", _GOLDEN_CASES, ids=[c["id"] for c in _GOLDEN_CASES])
@pytest.mark.asyncio
async def test_damodaran_verdict_dans_allowed(case, damodaran_skill):
    """verdict doit etre dans la liste des valeurs autorisees."""
    input_data = _build_damodaran_input(case)
    output, _ = await damodaran_skill.execute(input_data)
    allowed = case["expected"]["verdict_allowed"]
    assert output.verdict in allowed, (
        f"[{case['id']}] verdict={output.verdict!r} pas dans {allowed}"
    )


@pytest.mark.evals
@pytest.mark.parametrize("case", _GOLDEN_CASES, ids=[c["id"] for c in _GOLDEN_CASES])
@pytest.mark.asyncio
async def test_damodaran_test_coherence_dans_allowed(case, damodaran_skill):
    """test_coherence doit etre dans la liste des valeurs autorisees."""
    input_data = _build_damodaran_input(case)
    output, _ = await damodaran_skill.execute(input_data)
    allowed = case["expected"]["test_coherence_allowed"]
    assert output.test_coherence in allowed, (
        f"[{case['id']}] test_coherence={output.test_coherence!r} pas dans {allowed}"
    )


@pytest.mark.evals
@pytest.mark.parametrize("case", _GOLDEN_CASES, ids=[c["id"] for c in _GOLDEN_CASES])
@pytest.mark.asyncio
async def test_damodaran_narrative_strength_min(case, damodaran_skill):
    """narrative_strength >= minimum attendu."""
    input_data = _build_damodaran_input(case)
    output, _ = await damodaran_skill.execute(input_data)
    expected_min = case["expected"]["narrative_strength_min"]
    assert output.narrative_strength >= expected_min, (
        f"[{case['id']}] narrative_strength={output.narrative_strength} < minimum {expected_min}"
    )


@pytest.mark.evals
@pytest.mark.parametrize("case", _GOLDEN_CASES, ids=[c["id"] for c in _GOLDEN_CASES])
@pytest.mark.asyncio
async def test_damodaran_narrative_strength_dans_plage(case, damodaran_skill):
    """narrative_strength doit etre dans [0, 10]."""
    input_data = _build_damodaran_input(case)
    output, _ = await damodaran_skill.execute(input_data)
    assert 0 <= output.narrative_strength <= 10, (
        f"[{case['id']}] narrative_strength={output.narrative_strength} hors [0,10]"
    )


@pytest.mark.evals
@pytest.mark.asyncio
async def test_damodaran_concordance_globale_verdict(damodaran_skill):
    """Taux de concordance verdict >= 75 % sur tous les cas."""
    concordant = 0
    total = 0
    for case in _GOLDEN_CASES:
        try:
            input_data = _build_damodaran_input(case)
            output, _ = await damodaran_skill.execute(input_data)
            if output.verdict in case["expected"]["verdict_allowed"]:
                concordant += 1
            total += 1
        except Exception:
            total += 1

    taux = concordant / total if total > 0 else 0.0
    assert taux >= 0.75, (
        f"Concordance verdict : {concordant}/{total} = {taux:.0%} < 75 % requis"
    )
