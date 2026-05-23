"""
Tests d'evaluation EarningsQuality -- appels Claude REELS sur le golden dataset.

Marqueur @pytest.mark.evals : exclu de la CI standard.
Execution :
  ANTHROPIC_API_KEY=sk-ant-... pytest tests/evals/test_earnings_evals.py -m evals -v

Le skill utilise Haiku (claude-haiku-4-5-20251001) depuis Sprint 44.
Ces evals valident que Haiku calcule correctement M-Score / Z-Score / F-Score.

IMPORTANT : ne jamais patcher call_claude_with_retry dans ce module.
"""
from __future__ import annotations

import os

import pytest
import pytest_asyncio

from tests.evals.fixtures import load_earnings_golden

_GOLDEN_CASES = load_earnings_golden()

HAIKU_MODEL = "claude-haiku-4-5-20251001"


@pytest_asyncio.fixture
async def earnings_skill():
    """EarningsQualitySkill avec client Anthropic reel -- necessite ANTHROPIC_API_KEY."""
    import anthropic

    from app.skills.base import SkillConfig
    from app.skills.tier2.earnings_quality.skill import EarningsQualitySkill

    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        pytest.skip("ANTHROPIC_API_KEY absent -- skip evals")

    client = anthropic.AsyncAnthropic(api_key=api_key)
    return EarningsQualitySkill(
        client=client,
        model=HAIKU_MODEL,
        config=SkillConfig(timeout_s=120.0, max_retries=2),
        rag_service=None,
    )


def _build_input(case: dict):
    """Construit un EarningsQualityInput depuis un cas golden."""
    from app.skills.tier2.earnings_quality.schemas import (
        EarningsQualityInput,
        EarningsQualityRatios,
    )

    inp = case["input"]
    ratios = EarningsQualityRatios(**inp["ratios"])
    return EarningsQualityInput(
        ticker=inp["ticker"],
        ratios=ratios,
    )


# ---------------------------------------------------------------------------
# Tests par cas individuel
# ---------------------------------------------------------------------------

@pytest.mark.evals
@pytest.mark.parametrize("case", _GOLDEN_CASES, ids=[c["id"] for c in _GOLDEN_CASES])
async def test_earnings_verdict_dans_valeurs_attendues(case, earnings_skill):
    """Le verdict doit etre dans la liste des verdicts autorises."""
    inp = _build_input(case)
    output, _ = await earnings_skill.execute(inp)
    exp = case["expected"]

    allowed = exp.get("verdict_allowed", [])
    assert output.verdict in allowed, (
        f"[{case['id']}] {case['input']['ticker']} "
        f"verdict={output.verdict!r} pas dans {allowed}"
    )


@pytest.mark.evals
@pytest.mark.parametrize("case", _GOLDEN_CASES, ids=[c["id"] for c in _GOLDEN_CASES])
async def test_earnings_f_score_dans_plage(case, earnings_skill):
    """Le F-Score doit respecter les bornes attendues (tolerance +-1)."""
    exp = case["expected"]
    if "f_score_min" not in exp and "f_score_max" not in exp:
        pytest.skip("Pas de contrainte F-Score pour ce cas")

    inp = _build_input(case)
    output, _ = await earnings_skill.execute(inp)

    if "f_score_min" in exp:
        min_attendu = exp["f_score_min"] - 1  # tolerance +-1
        assert output.f_score.f_score >= min_attendu, (
            f"[{case['id']}] {case['input']['ticker']} "
            f"F-Score={output.f_score.f_score} < min attendu {min_attendu}"
        )

    if "f_score_max" in exp:
        max_attendu = exp["f_score_max"] + 1  # tolerance +-1
        assert output.f_score.f_score <= max_attendu, (
            f"[{case['id']}] {case['input']['ticker']} "
            f"F-Score={output.f_score.f_score} > max attendu {max_attendu}"
        )


@pytest.mark.evals
@pytest.mark.parametrize("case", _GOLDEN_CASES, ids=[c["id"] for c in _GOLDEN_CASES])
async def test_earnings_z_score_interpretation(case, earnings_skill):
    """L'interpretation Z-Score doit etre dans les valeurs attendues."""
    exp = case["expected"]
    if "z_score_interpretation_allowed" not in exp:
        pytest.skip("Pas de contrainte Z-Score pour ce cas")

    inp = _build_input(case)
    output, _ = await earnings_skill.execute(inp)

    allowed = exp["z_score_interpretation_allowed"]
    assert output.z_score.interpretation in allowed, (
        f"[{case['id']}] {case['input']['ticker']} "
        f"z_score.interpretation={output.z_score.interpretation!r} pas dans {allowed}"
    )


@pytest.mark.evals
@pytest.mark.parametrize("case", _GOLDEN_CASES, ids=[c["id"] for c in _GOLDEN_CASES])
async def test_earnings_m_score_interpretation(case, earnings_skill):
    """L'interpretation M-Score doit etre dans les valeurs attendues."""
    exp = case["expected"]
    if "m_score_interpretation_allowed" not in exp:
        pytest.skip("Pas de contrainte M-Score pour ce cas")

    inp = _build_input(case)
    output, _ = await earnings_skill.execute(inp)

    allowed = exp["m_score_interpretation_allowed"]
    assert output.m_score.interpretation in allowed, (
        f"[{case['id']}] {case['input']['ticker']} "
        f"m_score.interpretation={output.m_score.interpretation!r} pas dans {allowed}"
    )


@pytest.mark.evals
@pytest.mark.parametrize("case", _GOLDEN_CASES, ids=[c["id"] for c in _GOLDEN_CASES])
async def test_earnings_drapeaux_rouges_cardinalite(case, earnings_skill):
    """Le nombre de drapeaux rouges doit respecter les bornes."""
    exp = case["expected"]
    if "drapeaux_rouges_min" not in exp and "drapeaux_rouges_max" not in exp:
        pytest.skip("Pas de contrainte drapeaux_rouges pour ce cas")

    inp = _build_input(case)
    output, _ = await earnings_skill.execute(inp)
    nb = len(output.drapeaux_rouges)

    if "drapeaux_rouges_min" in exp:
        assert nb >= exp["drapeaux_rouges_min"], (
            f"[{case['id']}] {case['input']['ticker']} "
            f"drapeaux_rouges={nb} < min attendu {exp['drapeaux_rouges_min']}"
        )

    if "drapeaux_rouges_max" in exp:
        assert nb <= exp["drapeaux_rouges_max"], (
            f"[{case['id']}] {case['input']['ticker']} "
            f"drapeaux_rouges={nb} > max attendu {exp['drapeaux_rouges_max']}"
        )


# ---------------------------------------------------------------------------
# Tests de taux de concordance global (drift metrics)
# ---------------------------------------------------------------------------

@pytest.mark.evals
async def test_earnings_taux_concordance_verdict(earnings_skill):
    """Taux de concordance verdict sur tous les cas : >= 80 % requis."""
    resultats = []
    for case in _GOLDEN_CASES:
        inp = _build_input(case)
        output, _ = await earnings_skill.execute(inp)
        concordance = output.verdict in case["expected"].get("verdict_allowed", [])
        resultats.append((case["id"], case["input"]["ticker"], concordance, output.verdict))

    nb_ok = sum(1 for _, _, ok, _ in resultats if ok)
    taux = nb_ok / len(resultats) if resultats else 0.0

    echecs = [(id_, ticker, verdict) for id_, ticker, ok, verdict in resultats if not ok]
    assert taux >= 0.80, (
        f"Taux de concordance verdict : {taux:.0%} ({nb_ok}/{len(resultats)}) < 80 % requis. "
        f"Echecs : {echecs}"
    )
