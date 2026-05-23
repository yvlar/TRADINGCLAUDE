"""
Tests d'evaluation DorseyMoatSkill -- appels Claude REELS sur le golden dataset.

Marqueur @pytest.mark.evals : exclu de la CI standard.
Execution :
  ANTHROPIC_API_KEY=sk-ant-... pytest tests/evals/test_dorsey_evals.py -m evals -v

Le skill utilise claude-sonnet-4-6 (analyse qualitative).

IMPORTANT : ne jamais patcher call_claude_with_retry dans ce module.
"""
from __future__ import annotations

import os

import pytest
import pytest_asyncio

from tests.evals.fixtures import load_dorsey_golden

_GOLDEN_CASES = load_dorsey_golden()

SONNET_MODEL = "claude-sonnet-4-6"


@pytest_asyncio.fixture
async def dorsey_skill():
    """DorseyMoatSkill avec client Anthropic reel -- necessite ANTHROPIC_API_KEY."""
    import anthropic

    from app.skills.base import SkillConfig
    from app.skills.tier2.dorsey_moat.skill import DorseyMoatSkill

    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        pytest.skip("ANTHROPIC_API_KEY absent -- skip evals")

    client = anthropic.AsyncAnthropic(api_key=api_key)
    return DorseyMoatSkill(
        client=client,
        model=SONNET_MODEL,
        config=SkillConfig(timeout_s=120.0, max_retries=2),
        rag_service=None,
    )


def _build_dorsey_input(case: dict):
    from app.skills.tier2.dorsey_moat.schemas import DorseyMoatInput, DorseyRatios

    inp = case["input"]
    ratios = DorseyRatios(**inp["ratios"])
    return DorseyMoatInput(
        ticker=inp["ticker"],
        ratios=ratios,
        earnings_context=None,
    )


@pytest.mark.evals
@pytest.mark.parametrize("case", _GOLDEN_CASES, ids=[c["id"] for c in _GOLDEN_CASES])
@pytest.mark.asyncio
async def test_dorsey_moat_type_dans_allowed(case, dorsey_skill):
    """moat_type doit etre dans la liste des valeurs autorisees."""
    input_data = _build_dorsey_input(case)
    output, _ = await dorsey_skill.execute(input_data)
    allowed = case["expected"]["moat_type_allowed"]
    assert output.moat_type in allowed, (
        f"[{case['id']}] moat_type={output.moat_type!r} pas dans {allowed}"
    )


@pytest.mark.evals
@pytest.mark.parametrize("case", _GOLDEN_CASES, ids=[c["id"] for c in _GOLDEN_CASES])
@pytest.mark.asyncio
async def test_dorsey_sources_identifiees_exactement_5(case, dorsey_skill):
    """Le schema exige exactement 5 sources -- toujours valide."""
    input_data = _build_dorsey_input(case)
    output, _ = await dorsey_skill.execute(input_data)
    assert len(output.sources_identifiees) == 5, (
        f"[{case['id']}] {len(output.sources_identifiees)} sources (attendu 5)"
    )


@pytest.mark.evals
@pytest.mark.parametrize("case", _GOLDEN_CASES, ids=[c["id"] for c in _GOLDEN_CASES])
@pytest.mark.asyncio
async def test_dorsey_sources_min_presentes(case, dorsey_skill):
    """Nombre de sources marquees 'present=True' >= sources_min attendu."""
    input_data = _build_dorsey_input(case)
    output, _ = await dorsey_skill.execute(input_data)
    sources_presentes = sum(1 for s in output.sources_identifiees if s.present)
    expected_min = case["expected"]["sources_min"]
    assert sources_presentes >= expected_min, (
        f"[{case['id']}] {sources_presentes} sources presentes < minimum {expected_min}"
    )


@pytest.mark.evals
@pytest.mark.parametrize("case", _GOLDEN_CASES, ids=[c["id"] for c in _GOLDEN_CASES])
@pytest.mark.asyncio
async def test_dorsey_roic_durability_dans_allowed(case, dorsey_skill):
    """roic_durability doit etre dans la liste des valeurs autorisees."""
    input_data = _build_dorsey_input(case)
    output, _ = await dorsey_skill.execute(input_data)
    allowed = case["expected"]["roic_durability_allowed"]
    assert output.roic_durability in allowed, (
        f"[{case['id']}] roic_durability={output.roic_durability!r} pas dans {allowed}"
    )


@pytest.mark.evals
@pytest.mark.asyncio
async def test_dorsey_concordance_globale_moat_type(dorsey_skill):
    """Taux de concordance moat_type >= 75 % sur tous les cas."""
    concordant = 0
    total = 0
    for case in _GOLDEN_CASES:
        try:
            input_data = _build_dorsey_input(case)
            output, _ = await dorsey_skill.execute(input_data)
            if output.moat_type in case["expected"]["moat_type_allowed"]:
                concordant += 1
            total += 1
        except Exception:
            total += 1

    taux = concordant / total if total > 0 else 0.0
    assert taux >= 0.75, (
        f"Concordance moat_type : {concordant}/{total} = {taux:.0%} < 75 % requis"
    )
