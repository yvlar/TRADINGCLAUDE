"""
Tests d'evaluation StockValuation -- appels Claude REELS sur le golden dataset.

Marqueur @pytest.mark.evals : exclu de la CI standard.
Execution :
  ANTHROPIC_API_KEY=sk-ant-... pytest tests/evals/test_valuation_evals.py -m evals -v

Ces evals valident le Sprint 132 (ossature DCF deterministe) contre Claude reel :
- la valeur DCF par action et la matrice de sensibilite produites par le modele sont
  ECRASEES par l'ossature Python (substitution post-parse) ; on verifie que la
  substitution survit a un aller-retour tool-use reel (le modele n'a pas renomme la
  methode, le champ existe, l'injection a matche) ;
- le gate sectoriel (financieres / REIT) laisse le bloc LLM intact ;
- le verdict reste dans les valeurs attendues.

Le skill utilise le modele par defaut CLAUDE_MODEL (sonnet) -- jamais hardcode.

IMPORTANT : ne jamais patcher call_claude_with_retry dans ce module.
"""
from __future__ import annotations

import os

import pytest
import pytest_asyncio

from tests.evals.fixtures import load_valuation_golden

_GOLDEN_CASES = load_valuation_golden()

# Modele lu depuis l'environnement (api-architecture.md : jamais hardcode).
_VALUATION_MODEL = os.environ.get("CLAUDE_MODEL", "claude-sonnet-4-6")

_VALID_VERDICTS = {"SOUS_EVALUE", "JUSTE_VALEUR", "SUREVALUE"}


@pytest_asyncio.fixture
async def valuation_skill():
    """StockValuationSkill avec client Anthropic reel -- necessite ANTHROPIC_API_KEY."""
    import anthropic

    from app.skills.base import SkillConfig
    from app.skills.tier2.stock_valuation.skill import StockValuationSkill

    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        pytest.skip("ANTHROPIC_API_KEY absent -- skip evals")

    client = anthropic.AsyncAnthropic(api_key=api_key)
    return StockValuationSkill(
        client=client,
        model=_VALUATION_MODEL,
        config=SkillConfig(timeout_s=120.0, max_retries=2),
        rag_service=None,
    )


def _build_input(case: dict):
    """Construit un StockValuationInput depuis un cas golden."""
    from app.skills.tier2.stock_valuation.schemas import (
        StockValuationInput,
        ValuationRatios,
    )

    inp = case["input"]
    return StockValuationInput(
        ticker=inp["ticker"],
        ratios=ValuationRatios(**inp["ratios"]),
    )


def _ratios(case: dict):
    """Reconstruit les ValuationRatios du cas (pour recalcul deterministe en local)."""
    from app.skills.tier2.stock_valuation.schemas import ValuationRatios

    return ValuationRatios(**case["input"]["ratios"])


# ---------------------------------------------------------------------------
# Validite structurelle de la sortie
# ---------------------------------------------------------------------------


@pytest.mark.evals
@pytest.mark.parametrize("case", _GOLDEN_CASES, ids=[c["id"] for c in _GOLDEN_CASES])
async def test_valuation_output_valide(case, valuation_skill):
    """Trois methodes, fourchette monotone, verdict dans l'ensemble valide."""
    output, _ = await valuation_skill.execute(_build_input(case))
    tk = case["input"]["ticker"]

    assert len(output.methodes) == 3, f"[{case['id']}] {tk} : attendu 3 methodes"
    assert output.fourchette_basse <= output.fourchette_centrale <= output.fourchette_haute, (
        f"[{case['id']}] {tk} : fourchette non monotone "
        f"({output.fourchette_basse} / {output.fourchette_centrale} / {output.fourchette_haute})"
    )
    assert output.verdict in _VALID_VERDICTS, (
        f"[{case['id']}] {tk} : verdict invalide {output.verdict!r}"
    )


# ---------------------------------------------------------------------------
# Coeur Sprint 132 : substitution DCF deterministe sur appel reel
# ---------------------------------------------------------------------------


@pytest.mark.evals
@pytest.mark.parametrize("case", _GOLDEN_CASES, ids=[c["id"] for c in _GOLDEN_CASES])
async def test_valuation_dcf_deterministe(case, valuation_skill):
    """La valeur DCF + la matrice de la sortie doivent egaler l'ossature Python (Sprint 132)."""
    from app.skills.tier2.stock_valuation.skill import _dcf_depuis_ratios

    if not case["expected"].get("dcf_applicable", False):
        pytest.skip("DCF inapplicable (financiere / REIT) -- couvert par test_secteur_exclut_dcf")

    attendu = _dcf_depuis_ratios(_ratios(case))
    assert attendu.applicable and attendu.per_share is not None, (
        f"[{case['id']}] cas mal forme : DCF attendu applicable mais non calculable"
    )

    output, _ = await valuation_skill.execute(_build_input(case))
    tk = case["input"]["ticker"]

    methode_dcf = next((m for m in output.methodes if m.methode == "dcf"), None)
    assert methode_dcf is not None, (
        f"[{case['id']}] {tk} : aucune methode 'dcf' dans la sortie ({[m.methode for m in output.methodes]})"
    )
    assert methode_dcf.valeur == pytest.approx(attendu.per_share), (
        f"[{case['id']}] {tk} : valeur DCF {methode_dcf.valeur} != ossature Python "
        f"{attendu.per_share} (substitution deterministe rompue)"
    )

    matrice = output.matrice_sensibilite
    assert matrice.wacc_range == pytest.approx(attendu.wacc_range), (
        f"[{case['id']}] {tk} : wacc_range de la matrice != ossature Python"
    )
    assert matrice.growth_range == pytest.approx(attendu.growth_range), (
        f"[{case['id']}] {tk} : growth_range de la matrice != ossature Python"
    )
    for i, row in enumerate(matrice.values):
        assert row == pytest.approx(attendu.values[i]), (
            f"[{case['id']}] {tk} : ligne {i} de la matrice != ossature Python"
        )


# ---------------------------------------------------------------------------
# Gate sectoriel : financieres / REIT -> DCF non substitue (verification pure)
# ---------------------------------------------------------------------------


@pytest.mark.evals
@pytest.mark.parametrize("case", _GOLDEN_CASES, ids=[c["id"] for c in _GOLDEN_CASES])
async def test_valuation_secteur_exclut_dcf(case):
    """Pour une financiere / REIT, l'ossature DCF est inapplicable (methode sectorielle prime)."""
    from app.skills.tier2.stock_valuation.skill import _dcf_depuis_ratios

    if case["expected"].get("dcf_applicable", False):
        pytest.skip("DCF applicable -- non concerne par le gate sectoriel")

    dcf = _dcf_depuis_ratios(_ratios(case))
    assert dcf.applicable is False, (
        f"[{case['id']}] {case['input']['ticker']} : secteur "
        f"{case['input']['ratios'].get('sector')!r} devrait exclure le DCF"
    )


# ---------------------------------------------------------------------------
# Verdict directionnel (golden dataset)
# ---------------------------------------------------------------------------


@pytest.mark.evals
@pytest.mark.parametrize("case", _GOLDEN_CASES, ids=[c["id"] for c in _GOLDEN_CASES])
async def test_valuation_verdict_dans_valeurs_attendues(case, valuation_skill):
    """Le verdict doit etre dans la liste des verdicts autorises du golden."""
    allowed = case["expected"].get("verdict_allowed", [])
    if not allowed:
        pytest.skip("Pas de contrainte de verdict pour ce cas")

    output, _ = await valuation_skill.execute(_build_input(case))
    assert output.verdict in allowed, (
        f"[{case['id']}] {case['input']['ticker']} : verdict={output.verdict!r} "
        f"pas dans {allowed}"
    )
