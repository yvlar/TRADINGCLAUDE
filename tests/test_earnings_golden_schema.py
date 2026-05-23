"""
Validation du schema earnings_golden.json -- aucun appel Claude.

Ces tests font partie de la CI standard (pas de marqueur evals).
Ils garantissent que le fichier JSON est bien forme avant d'executer les evals reels.
"""
from __future__ import annotations

from app.skills.tier2.earnings_quality.schemas import (
    EarningsQualityInput,
    EarningsQualityRatios,
)
from tests.evals.fixtures import load_earnings_golden

_CASES = load_earnings_golden()

_VERDICTS_VALIDES = {"AUCUN_SIGNAL", "ATTENTION", "WATCHLIST", "REJETER"}
_Z_INTERPS_VALIDES = {
    "zone_sure", "zone_grise", "zone_danger", "non_applicable", "DONNEES_MANQUANTES"
}
_M_INTERPS_VALIDES = {
    "non_manipulateur", "zone_grise", "manipulateur", "non_applicable", "DONNEES_MANQUANTES"
}


def test_golden_dataset_contient_20_cas():
    """Le dataset doit contenir exactement 20 cas."""
    assert len(_CASES) == 20, f"Attendu 20 cas, obtenu {len(_CASES)}"


def test_golden_ids_uniques():
    """Chaque cas doit avoir un id unique."""
    ids = [c["id"] for c in _CASES]
    assert len(ids) == len(set(ids)), f"IDs dupliques : {[i for i in ids if ids.count(i) > 1]}"


def test_golden_champs_obligatoires():
    """Chaque cas doit avoir id, description, input, expected."""
    for case in _CASES:
        for champ in ("id", "description", "input", "expected"):
            assert champ in case, f"Champ '{champ}' manquant dans cas {case.get('id', '?')}"


def test_golden_input_pydantic_valide():
    """Chaque input doit etre validable par EarningsQualityInput."""
    erreurs = []
    for case in _CASES:
        try:
            inp = case["input"]
            ratios = EarningsQualityRatios(**inp["ratios"])
            EarningsQualityInput(
                ticker=inp["ticker"],
                ratios=ratios,
            )
        except Exception as e:
            erreurs.append(f"{case['id']} ({inp.get('ticker', '?')}): {e}")

    assert not erreurs, "Inputs invalides :\n" + "\n".join(erreurs)


def test_golden_verdict_allowed_valides():
    """Tous les verdicts dans verdict_allowed doivent etre des valeurs legales."""
    erreurs = []
    for case in _CASES:
        verdicts = case["expected"].get("verdict_allowed", [])
        for v in verdicts:
            if v not in _VERDICTS_VALIDES:
                erreurs.append(f"{case['id']} : verdict '{v}' inconnu")

    assert not erreurs, "\n".join(erreurs)


def test_golden_z_score_interps_valides():
    """Toutes les interpretations Z-Score dans expected doivent etre legales."""
    erreurs = []
    for case in _CASES:
        interps = case["expected"].get("z_score_interpretation_allowed", [])
        for i in interps:
            if i not in _Z_INTERPS_VALIDES:
                erreurs.append(f"{case['id']} : z_score.interpretation '{i}' inconnue")

    assert not erreurs, "\n".join(erreurs)


def test_golden_m_score_interps_valides():
    """Toutes les interpretations M-Score dans expected doivent etre legales."""
    erreurs = []
    for case in _CASES:
        interps = case["expected"].get("m_score_interpretation_allowed", [])
        for i in interps:
            if i not in _M_INTERPS_VALIDES:
                erreurs.append(f"{case['id']} : m_score.interpretation '{i}' inconnue")

    assert not erreurs, "\n".join(erreurs)


def test_golden_institutions_financieres_marquees():
    """Les cas is_financial=True doivent exister (au moins 3 cas requis)."""
    financieres = [c for c in _CASES if c["input"].get("is_financial")]
    assert len(financieres) >= 3, (
        f"Attendu >= 3 institutions financieres, obtenu {len(financieres)}"
    )


def test_golden_distribution_verdicts_attendus():
    """Le dataset doit couvrir les cas positifs ET negatifs."""
    has_clean = any("AUCUN_SIGNAL" in c["expected"].get("verdict_allowed", []) for c in _CASES)
    has_reject = any(
        any(v in {"WATCHLIST", "REJETER"} for v in c["expected"].get("verdict_allowed", []))
        for c in _CASES
    )
    assert has_clean, "Dataset doit contenir des cas 'propres' (verdict AUCUN_SIGNAL)"
    assert has_reject, "Dataset doit contenir des cas a signal fort (WATCHLIST/REJETER)"


def test_golden_f_score_bornes_coherentes():
    """Les bornes F-Score dans expected doivent etre coherentes (min <= max)."""
    erreurs = []
    for case in _CASES:
        exp = case["expected"]
        f_min = exp.get("f_score_min")
        f_max = exp.get("f_score_max")
        if f_min is not None and f_max is not None:
            if f_min > f_max:
                erreurs.append(
                    f"{case['id']} : f_score_min={f_min} > f_score_max={f_max}"
                )

    assert not erreurs, "\n".join(erreurs)
