"""
Tests d'eval multi-modele : valide que les 3 skills routes vers Haiku retournent
des schemas Pydantic valides sur le golden dataset multi_model_golden.json.

Marqueur @pytest.mark.evals : exclu de la CI standard.
Execution :
  ANTHROPIC_API_KEY=sk-ant-... pytest tests/evals/test_multi_model_evals.py -m evals -v

Skills testes (tous routes vers claude-haiku-4-5-20251001) :
  - earnings_quality  -> EarningsQualitySkill
  - greenblatt_magic_formula -> GreenblattSkill
  - lynch_categories  -> LynchCategoriesSkill

IMPORTANT : ne jamais patcher call_claude_with_retry dans ce module.
"""
from __future__ import annotations

import os

import pytest
import pytest_asyncio

from tests.evals.fixtures import load_multi_model_golden

_GOLDEN_CASES = load_multi_model_golden()
_CASES_EARNINGS = [c for c in _GOLDEN_CASES if c["skill"] == "earnings_quality"]
_CASES_GREENBLATT = [c for c in _GOLDEN_CASES if c["skill"] == "greenblatt_magic_formula"]
_CASES_LYNCH = [c for c in _GOLDEN_CASES if c["skill"] == "lynch_categories"]

HAIKU_MODEL = "claude-haiku-4-5-20251001"


# ---------------------------------------------------------------------------
# Fixtures skills — client reel requis
# ---------------------------------------------------------------------------


def _get_client():
    """Retourne un client Anthropic reel ou skip si cle absente."""
    import anthropic

    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        pytest.skip("ANTHROPIC_API_KEY absent -- skip evals")
    return anthropic.AsyncAnthropic(api_key=api_key)


@pytest_asyncio.fixture
async def earnings_skill():
    from app.skills.base import SkillConfig
    from app.skills.tier2.earnings_quality.skill import EarningsQualitySkill

    client = _get_client()
    return EarningsQualitySkill(
        client=client,
        model=HAIKU_MODEL,
        config=SkillConfig(timeout_s=120.0, max_retries=2),
        rag_service=None,
    )


@pytest_asyncio.fixture
async def greenblatt_skill():
    from app.skills.base import SkillConfig
    from app.skills.tier2.greenblatt.skill import GreenblattSkill

    client = _get_client()
    return GreenblattSkill(
        client=client,
        model=HAIKU_MODEL,
        config=SkillConfig(timeout_s=120.0, max_retries=2),
        rag_service=None,
    )


@pytest_asyncio.fixture
async def lynch_skill():
    from app.skills.base import SkillConfig
    from app.skills.tier2.lynch_categories.skill import LynchCategoriesSkill

    client = _get_client()
    return LynchCategoriesSkill(
        client=client,
        model=HAIKU_MODEL,
        config=SkillConfig(timeout_s=120.0, max_retries=2),
        rag_service=None,
    )


# ---------------------------------------------------------------------------
# Helpers de construction des inputs
# ---------------------------------------------------------------------------


def _build_earnings_input(case: dict):
    from app.skills.tier2.earnings_quality.schemas import (
        EarningsQualityInput,
        EarningsQualityRatios,
    )

    inp = case["input"]
    return EarningsQualityInput(
        ticker=inp["ticker"],
        ratios=EarningsQualityRatios(**inp["ratios"]),
    )


def _build_greenblatt_input(case: dict):
    from app.skills.tier2.greenblatt.schemas import GreenblattInput, GreenblattRatios

    inp = case["input"]
    return GreenblattInput(
        ticker=inp["ticker"],
        greenblatt_ratios=GreenblattRatios(**inp["greenblatt_ratios"]),
    )


def _build_lynch_input(case: dict):
    from app.skills.tier2.lynch_categories.schemas import LynchInput, LynchRatios

    inp = case["input"]
    return LynchInput(
        ticker=inp["ticker"],
        ratios=LynchRatios(**inp["ratios"]),
    )


# ---------------------------------------------------------------------------
# Tests schema Pydantic valide (structure de la reponse)
# ---------------------------------------------------------------------------


@pytest.mark.evals
@pytest.mark.parametrize("case", _CASES_EARNINGS, ids=[c["id"] for c in _CASES_EARNINGS])
async def test_earnings_schema_pydantic_valide(case, earnings_skill):
    """EarningsQualityOutput doit etre un schema Pydantic valide (9 criteres F-Score, 6 C-Score)."""
    from app.skills.tier2.earnings_quality.schemas import EarningsQualityOutput

    inp = _build_earnings_input(case)
    output, _ = await earnings_skill.execute(inp)

    assert isinstance(output, EarningsQualityOutput), (
        f"[{case['id']}] Retour attendu EarningsQualityOutput, obtenu {type(output)}"
    )
    assert len(output.f_score.criteria) == 9, (
        f"[{case['id']}] f_score.criteria : attendu 9, recu {len(output.f_score.criteria)}"
    )
    assert len(output.c_score.signaux) == 6, (
        f"[{case['id']}] c_score.signaux : attendu 6, recu {len(output.c_score.signaux)}"
    )
    assert output.verdict in {"AUCUN_SIGNAL", "ATTENTION", "WATCHLIST", "REJETER"}, (
        f"[{case['id']}] verdict invalide : {output.verdict!r}"
    )


@pytest.mark.evals
@pytest.mark.parametrize("case", _CASES_GREENBLATT, ids=[c["id"] for c in _CASES_GREENBLATT])
async def test_greenblatt_schema_pydantic_valide(case, greenblatt_skill):
    """GreenblattOutput doit etre un schema Pydantic valide avec ROC et Earnings Yield positifs."""
    from app.skills.tier2.greenblatt.schemas import GreenblattOutput

    inp = _build_greenblatt_input(case)
    output, _ = await greenblatt_skill.execute(inp)

    assert isinstance(output, GreenblattOutput), (
        f"[{case['id']}] Retour attendu GreenblattOutput, obtenu {type(output)}"
    )
    assert output.roc > 0, f"[{case['id']}] ROC doit etre > 0, obtenu {output.roc}"
    assert output.earnings_yield > 0, (
        f"[{case['id']}] earnings_yield doit etre > 0, obtenu {output.earnings_yield}"
    )
    assert output.verdict in {"TOP_DECILE", "BON", "MOYEN", "EVITER"}, (
        f"[{case['id']}] verdict invalide : {output.verdict!r}"
    )


@pytest.mark.evals
@pytest.mark.parametrize("case", _CASES_LYNCH, ids=[c["id"] for c in _CASES_LYNCH])
async def test_lynch_schema_pydantic_valide(case, lynch_skill):
    """LynchOutput doit etre un schema Pydantic valide avec categorie et score_croissance corrects."""
    from app.skills.tier2.lynch_categories.schemas import LynchOutput

    inp = _build_lynch_input(case)
    output, _ = await lynch_skill.execute(inp)

    categories_valides = {"SLOW_GROWER", "STALWART", "FAST_GROWER", "CYCLICAL", "TURNAROUND", "ASSET_PLAY"}
    verdicts_valides = {"EXCELLENT", "BON", "MOYEN", "EVITER"}

    assert isinstance(output, LynchOutput), (
        f"[{case['id']}] Retour attendu LynchOutput, obtenu {type(output)}"
    )
    assert output.categorie in categories_valides, (
        f"[{case['id']}] categorie invalide : {output.categorie!r}"
    )
    assert output.verdict in verdicts_valides, (
        f"[{case['id']}] verdict invalide : {output.verdict!r}"
    )
    assert 0 <= output.score_croissance <= 5, (
        f"[{case['id']}] score_croissance hors plage [0,5] : {output.score_croissance}"
    )


# ---------------------------------------------------------------------------
# Tests concordance verdict / categorie vs expected
# ---------------------------------------------------------------------------


@pytest.mark.evals
@pytest.mark.parametrize("case", _CASES_EARNINGS, ids=[c["id"] for c in _CASES_EARNINGS])
async def test_earnings_verdict_dans_valeurs_attendues(case, earnings_skill):
    """Le verdict EarningsQuality doit etre dans la liste des verdicts autorises."""
    inp = _build_earnings_input(case)
    output, _ = await earnings_skill.execute(inp)
    allowed = case["expected"].get("verdict_allowed", [])
    assert output.verdict in allowed, (
        f"[{case['id']}] {case['ticker']} verdict={output.verdict!r} pas dans {allowed}"
    )


@pytest.mark.evals
@pytest.mark.parametrize("case", _CASES_GREENBLATT, ids=[c["id"] for c in _CASES_GREENBLATT])
async def test_greenblatt_verdict_dans_valeurs_attendues(case, greenblatt_skill):
    """Le verdict Greenblatt doit etre dans la liste des verdicts autorises."""
    inp = _build_greenblatt_input(case)
    output, _ = await greenblatt_skill.execute(inp)
    allowed = case["expected"].get("verdict_allowed", [])
    assert output.verdict in allowed, (
        f"[{case['id']}] {case['ticker']} verdict={output.verdict!r} pas dans {allowed}"
    )


@pytest.mark.evals
@pytest.mark.parametrize("case", _CASES_LYNCH, ids=[c["id"] for c in _CASES_LYNCH])
async def test_lynch_categorie_dans_valeurs_attendues(case, lynch_skill):
    """La categorie Lynch doit etre dans la liste des categories autorisees."""
    inp = _build_lynch_input(case)
    output, _ = await lynch_skill.execute(inp)
    allowed = case["expected"].get("categorie_allowed", [])
    assert output.categorie in allowed, (
        f"[{case['id']}] {case['ticker']} categorie={output.categorie!r} pas dans {allowed}"
    )


# ---------------------------------------------------------------------------
# Test de taux de concordance global (drift metrics multi-modele)
# ---------------------------------------------------------------------------


@pytest.mark.evals
async def test_taux_concordance_global_haiku_skills(
    earnings_skill, greenblatt_skill, lynch_skill
):
    """
    Taux de concordance verdict >= 50 % sur l'ensemble du golden dataset multi-modele.
    Seuil permissif car le dataset couvre 3 skills differents avec des modeles differents.
    """
    resultats = []

    for case in _CASES_EARNINGS:
        inp = _build_earnings_input(case)
        output, _ = await earnings_skill.execute(inp)
        ok = output.verdict in case["expected"].get("verdict_allowed", [])
        resultats.append((case["id"], case["ticker"], "earnings_quality", ok, output.verdict))

    for case in _CASES_GREENBLATT:
        inp = _build_greenblatt_input(case)
        output, _ = await greenblatt_skill.execute(inp)
        ok = output.verdict in case["expected"].get("verdict_allowed", [])
        resultats.append((case["id"], case["ticker"], "greenblatt_magic_formula", ok, output.verdict))

    for case in _CASES_LYNCH:
        inp = _build_lynch_input(case)
        output, _ = await lynch_skill.execute(inp)
        ok = output.verdict in case["expected"].get("verdict_allowed", [])
        resultats.append((case["id"], case["ticker"], "lynch_categories", ok, output.verdict))

    nb_ok = sum(1 for *_, ok, _ in resultats if ok)
    taux = nb_ok / len(resultats) if resultats else 0.0
    echecs = [(id_, ticker, skill, v) for id_, ticker, skill, ok, v in resultats if not ok]

    assert taux >= 0.50, (
        f"Taux concordance global Haiku : {taux:.0%} ({nb_ok}/{len(resultats)}) < 50 % requis. "
        f"Echecs : {echecs}"
    )
