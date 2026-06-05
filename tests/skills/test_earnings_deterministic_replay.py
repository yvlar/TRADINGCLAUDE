"""Replay déterministe du golden earnings (Sprint 149) — SANS appel Claude.

Mesure **hors-ligne** que les cinq cadres déterministes (M/Z/F/C/Sloan, désormais tous
substitués post-parse — Sloan fermé au Sprint 148) restent cohérents avec le golden
dataset. C'est la part de l'évaluation qui ne dépend plus du LLM : les libellés
d'interprétation sont calculés en Python, donc reproductibles sans clé API.

La sur-génération de `drapeaux_rouges` (champ libre du LLM, `list[str]`) ne se mesure
**qu'avec un appel Claude réel** : voir `tests/evals/test_earnings_evals.py`
(`test_earnings_drapeaux_rouges_cardinalite`, marqueur `evals`, `ANTHROPIC_API_KEY`
requise — exclu du CI). Ce module verrouille la précondition (5 cadres déterministes
cohérents avec le golden) ; l'eval live mesure le comportement résiduel du LLM.
"""
from __future__ import annotations

import pytest

from app.services.financial_calculations import _sloan_interpretation
from app.skills.tier2.earnings_quality.schemas import EarningsQualityRatios
from app.skills.tier2.earnings_quality.skill import _scores_depuis_ratios, _ScoresDeterministes
from tests.evals.fixtures import load_earnings_golden

_GOLDEN = load_earnings_golden()

# Libellés Sloan valides (system.md:163-165 + DONNEES_MANQUANTES si accrual incalculable).
_LIBELLES_SLOAN_VALIDES = {"qualite_elevee", "neutre", "qualite_degradee", "DONNEES_MANQUANTES"}


def _scores_du_cas(case: dict) -> _ScoresDeterministes:
    """Rejoue les scores déterministes depuis les ratios d'entrée du cas golden."""
    ratios = EarningsQualityRatios(**case["input"]["ratios"])
    return _scores_depuis_ratios(ratios, case["input"].get("is_financial", False))


def test_golden_charge_et_non_vide():
    """Garde-fou : le golden est présent (sinon les paramétrages ci-dessous sont vides)."""
    assert len(_GOLDEN) >= 12


@pytest.mark.parametrize("case", _GOLDEN, ids=[c["id"] for c in _GOLDEN])
def test_z_interpretation_deterministe_coherente_golden(case: dict):
    """Le libellé Z déterministe (Sprint 131) reste dans les valeurs attendues du golden."""
    exp = case["expected"]
    if "z_score_interpretation_allowed" not in exp:
        pytest.skip("Pas de contrainte Z pour ce cas")
    scores = _scores_du_cas(case)
    assert scores.z.interpretation in exp["z_score_interpretation_allowed"], (
        f"[{case['id']}] {case['input']['ticker']} "
        f"Z={scores.z.interpretation!r} pas dans {exp['z_score_interpretation_allowed']}"
    )


@pytest.mark.parametrize("case", _GOLDEN, ids=[c["id"] for c in _GOLDEN])
def test_m_interpretation_deterministe_coherente_golden(case: dict):
    """Le libellé M déterministe (Sprint 131) reste dans les valeurs attendues du golden."""
    exp = case["expected"]
    if "m_score_interpretation_allowed" not in exp:
        pytest.skip("Pas de contrainte M pour ce cas")
    scores = _scores_du_cas(case)
    assert scores.m.interpretation in exp["m_score_interpretation_allowed"], (
        f"[{case['id']}] {case['input']['ticker']} "
        f"M={scores.m.interpretation!r} pas dans {exp['m_score_interpretation_allowed']}"
    )


@pytest.mark.parametrize("case", _GOLDEN, ids=[c["id"] for c in _GOLDEN])
def test_f_score_deterministe_dans_bornes_golden(case: dict):
    """Le F-Score déterministe (Sprint 142) respecte les bornes du golden (tolérance ±1).

    Même tolérance que l'eval live : un F-Score est mécaniquement déprimé quand des
    données T-1 manquent (critères non évaluables comptés 0 — cf. system.md Cadre 6).
    """
    exp = case["expected"]
    if "f_score_min" not in exp and "f_score_max" not in exp:
        pytest.skip("Pas de contrainte F-Score pour ce cas")
    scores = _scores_du_cas(case)
    assert scores.f_score is not None, f"[{case['id']}] F-Score déterministe None inattendu"
    if "f_score_min" in exp:
        assert scores.f_score >= exp["f_score_min"] - 1, (
            f"[{case['id']}] {case['input']['ticker']} "
            f"F-Score={scores.f_score} < min {exp['f_score_min']} (tolérance -1)"
        )
    if "f_score_max" in exp:
        assert scores.f_score <= exp["f_score_max"] + 1, (
            f"[{case['id']}] {case['input']['ticker']} "
            f"F-Score={scores.f_score} > max {exp['f_score_max']} (tolérance +1)"
        )


@pytest.mark.parametrize("case", _GOLDEN, ids=[c["id"] for c in _GOLDEN])
def test_sloan_interpretation_deterministe_label_valide(case: dict):
    """Le libellé Sloan déterministe (Sprint 148) est valide et cohérent avec son accrual."""
    scores = _scores_du_cas(case)
    attendu = None if scores.accrual_ratio is None else _sloan_interpretation(scores.accrual_ratio)
    assert scores.sloan_interpretation == attendu
    if scores.sloan_interpretation is not None:
        assert scores.sloan_interpretation in _LIBELLES_SLOAN_VALIDES


def test_les_cinq_cadres_produisent_un_libelle_sur_tout_le_golden():
    """Méta-mesure (Sprint 149) : sur chaque cas golden, les cadres déterministes
    produisent un libellé — zéro interprétation laissée au LLM quand elle est calculable.

    M/Z sont toujours substitués (libellé non vide, `DONNEES_MANQUANTES`/`non_applicable`
    au pire) ; sur le golden, l'accrual de Sloan est toujours calculable (données NI/CFO/TA
    présentes), donc les cinq cadres sont déterministes — précondition du correctif de
    sur-génération de `drapeaux_rouges`.
    """
    assert _GOLDEN, "golden vide"
    for case in _GOLDEN:
        scores = _scores_du_cas(case)
        assert scores.z.interpretation, f"[{case['id']}] Z sans libellé"
        assert scores.m.interpretation, f"[{case['id']}] M sans libellé"
        assert scores.sloan_interpretation is not None, f"[{case['id']}] Sloan non déterministe"
