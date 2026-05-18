"""
Tests CI standard Sprint 55 : validation du golden dataset multi-modele.
Aucun appel Claude -- verifie la structure du dataset, que les skills sont bien
les skills Haiku, et que les inputs Pydantic sont valides.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

_DATASET_PATH = Path(__file__).parent / "evals" / "fixtures" / "multi_model_golden.json"

HAIKU_SKILLS = {"earnings_quality", "greenblatt_magic_formula", "lynch_categories"}

_VERDICTS_EARNINGS = {"AUCUN_SIGNAL", "ATTENTION", "WATCHLIST", "REJETER"}
_VERDICTS_GREENBLATT = {"TOP_DECILE", "BON", "MOYEN", "EVITER"}
_VERDICTS_LYNCH = {"EXCELLENT", "BON", "MOYEN", "EVITER"}
_CATEGORIES_LYNCH = {"SLOW_GROWER", "STALWART", "FAST_GROWER", "CYCLICAL", "TURNAROUND", "ASSET_PLAY"}


def _load_dataset() -> list[dict]:
    assert _DATASET_PATH.exists(), (
        f"multi_model_golden.json introuvable : {_DATASET_PATH}"
    )
    return json.loads(_DATASET_PATH.read_text(encoding="utf-8"))


# ---------------------------------------------------------------------------
# Structure du dataset
# ---------------------------------------------------------------------------


class TestMultiModelDatasetStructure:

    def test_exactement_6_cas(self):
        """Le golden dataset multi-modele contient exactement 6 cas."""
        cases = _load_dataset()
        assert len(cases) == 6, f"Attendu 6 cas, trouve {len(cases)}"

    def test_ids_uniques(self):
        """Aucun ID en doublon dans le dataset."""
        cases = _load_dataset()
        ids = [c["id"] for c in cases]
        assert len(ids) == len(set(ids)), f"IDs en doublon : {ids}"

    def test_champs_obligatoires_presents(self):
        """Chaque entree contient id, skill, model_haiku, ticker, input, expected."""
        cases = _load_dataset()
        for case in cases:
            cid = case.get("id", "?")
            for champ in ("id", "skill", "model_haiku", "ticker", "input", "expected"):
                assert champ in case, f"{cid} : champ '{champ}' manquant"
            assert "verdict_allowed" in case["expected"], (
                f"{cid} : 'verdict_allowed' manquant dans expected"
            )

    def test_skills_sont_haiku_skills(self):
        """Chaque entree reference un skill Haiku connu."""
        cases = _load_dataset()
        for case in cases:
            cid = case["id"]
            assert case["skill"] in HAIKU_SKILLS, (
                f"{cid} : skill '{case['skill']}' n'est pas dans HAIKU_SKILLS {HAIKU_SKILLS}"
            )

    def test_model_haiku_correct(self):
        """Tous les cas referencent le modele Haiku attendu."""
        cases = _load_dataset()
        for case in cases:
            assert case["model_haiku"] == "claude-haiku-4-5-20251001", (
                f"{case['id']} : model_haiku='{case['model_haiku']}' != 'claude-haiku-4-5-20251001'"
            )

    def test_2_cas_par_skill_haiku(self):
        """Chaque skill Haiku est represente par exactement 2 cas."""
        cases = _load_dataset()
        from collections import Counter
        comptage = Counter(c["skill"] for c in cases)
        for skill in HAIKU_SKILLS:
            assert comptage[skill] == 2, (
                f"Skill '{skill}' : attendu 2 cas, trouve {comptage[skill]}"
            )

    def test_verdict_allowed_non_vide(self):
        """La liste verdict_allowed est non vide pour chaque cas."""
        cases = _load_dataset()
        for case in cases:
            cid = case["id"]
            allowed = case["expected"].get("verdict_allowed", [])
            assert len(allowed) >= 1, f"{cid} : verdict_allowed vide"

    def test_verdict_allowed_valeurs_valides(self):
        """Les verdicts expected sont valides selon le skill concerne."""
        cases = _load_dataset()
        skill_to_verdicts = {
            "earnings_quality": _VERDICTS_EARNINGS,
            "greenblatt_magic_formula": _VERDICTS_GREENBLATT,
            "lynch_categories": _VERDICTS_LYNCH,
        }
        for case in cases:
            cid = case["id"]
            skill = case["skill"]
            verdicts_valides = skill_to_verdicts.get(skill, set())
            for v in case["expected"].get("verdict_allowed", []):
                assert v in verdicts_valides, (
                    f"{cid} ({skill}) : verdict_allowed contient '{v}' invalide "
                    f"(attendu parmi {verdicts_valides})"
                )


# ---------------------------------------------------------------------------
# Validation schemas Pydantic des inputs (sans appel Claude)
# ---------------------------------------------------------------------------


class TestMultiModelSchemaPydantic:

    def test_earnings_quality_inputs_pydantic_valides(self):
        """Les inputs earnings_quality peuvent etre instancies sans erreur."""
        from app.skills.tier2.earnings_quality.schemas import (
            EarningsQualityInput,
            EarningsQualityRatios,
        )

        cases = _load_dataset()
        earnings_cases = [c for c in cases if c["skill"] == "earnings_quality"]
        assert len(earnings_cases) == 2, "Attendu exactement 2 cas earnings_quality"

        for case in earnings_cases:
            cid = case["id"]
            inp = case["input"]
            try:
                ratios = EarningsQualityRatios(**inp["ratios"])
                obj = EarningsQualityInput(ticker=inp["ticker"], ratios=ratios)
                assert obj.ticker == inp["ticker"], f"{cid} : ticker incorrect"
            except Exception as exc:
                pytest.fail(f"{cid} ({inp['ticker']}) : EarningsQualityInput invalide — {exc}")

    def test_greenblatt_inputs_pydantic_valides(self):
        """Les inputs greenblatt_magic_formula peuvent etre instancies sans erreur."""
        from app.skills.tier2.greenblatt.schemas import GreenblattInput, GreenblattRatios

        cases = _load_dataset()
        greenblatt_cases = [c for c in cases if c["skill"] == "greenblatt_magic_formula"]
        assert len(greenblatt_cases) == 2, "Attendu exactement 2 cas greenblatt_magic_formula"

        for case in greenblatt_cases:
            cid = case["id"]
            inp = case["input"]
            try:
                ratios = GreenblattRatios(**inp["greenblatt_ratios"])
                obj = GreenblattInput(ticker=inp["ticker"], greenblatt_ratios=ratios)
                assert obj.ticker == inp["ticker"], f"{cid} : ticker incorrect"
                capital = ratios.net_working_capital + ratios.net_fixed_assets
                assert capital > 0, f"{cid} : NWC + NFA doit etre > 0, obtenu {capital}"
                assert ratios.enterprise_value > 0, f"{cid} : enterprise_value doit etre > 0"
            except Exception as exc:
                pytest.fail(f"{cid} ({inp['ticker']}) : GreenblattInput invalide — {exc}")

    def test_lynch_inputs_pydantic_valides(self):
        """Les inputs lynch_categories peuvent etre instancies sans erreur."""
        from app.skills.tier2.lynch_categories.schemas import LynchInput, LynchRatios

        cases = _load_dataset()
        lynch_cases = [c for c in cases if c["skill"] == "lynch_categories"]
        assert len(lynch_cases) == 2, "Attendu exactement 2 cas lynch_categories"

        for case in lynch_cases:
            cid = case["id"]
            inp = case["input"]
            try:
                ratios = LynchRatios(**inp["ratios"])
                obj = LynchInput(ticker=inp["ticker"], ratios=ratios)
                assert obj.ticker == inp["ticker"], f"{cid} : ticker incorrect"
                assert ratios.pe > 0, f"{cid} : pe doit etre > 0"
            except Exception as exc:
                pytest.fail(f"{cid} ({inp['ticker']}) : LynchInput invalide — {exc}")


# ---------------------------------------------------------------------------
# Tests de coherence logique du dataset
# ---------------------------------------------------------------------------


class TestMultiModelLogique:

    def test_greenblatt_roc_min_coherent_avec_inputs(self):
        """
        Les seuils roc_min dans expected sont coherents avec les inputs Greenblatt.
        MCD doit avoir ROC eleve (> 30 %), INTC doit avoir ROC faible (< 10 %).
        """
        cases = _load_dataset()
        greenblatt_cases = [c for c in cases if c["skill"] == "greenblatt_magic_formula"]

        for case in greenblatt_cases:
            cid = case["id"]
            gr = case["input"]["greenblatt_ratios"]
            capital = gr["net_working_capital"] + gr["net_fixed_assets"]
            roc_calcule = gr["ebit"] / capital if capital > 0 else 0.0
            roc_min = case["expected"].get("roc_min")
            if roc_min is not None:
                assert roc_calcule >= roc_min, (
                    f"{cid} ({case['ticker']}) : ROC calcule {roc_calcule:.2%} < roc_min {roc_min:.2%}"
                )

    def test_lynch_peg_min_coherent_avec_inputs(self):
        """
        Le PEG calcule depuis les inputs Lynch respecte le peg_min du expected.
        SHOP (PEG ~2.6) et BCE (PEG ~14) doivent depasser leur seuil respectif.
        """
        cases = _load_dataset()
        lynch_cases = [c for c in cases if c["skill"] == "lynch_categories"]

        for case in lynch_cases:
            cid = case["id"]
            ratios = case["input"]["ratios"]
            pe = ratios["pe"]
            eps_growth = ratios["eps_growth_5y"]
            peg_min = case["expected"].get("peg_min")

            if peg_min is not None and eps_growth > 0:
                peg_calcule = pe / (eps_growth * 100)
                assert peg_calcule >= peg_min, (
                    f"{cid} ({case['ticker']}) : PEG calcule {peg_calcule:.2f} < peg_min {peg_min:.2f}"
                )

    def test_cas_contrastants_par_skill(self):
        """
        Pour chaque skill, les 2 cas ont des verdicts expected differents (couverture contrastee).
        Permet de detecter si le dataset ne teste qu'un seul scenario.
        """
        cases = _load_dataset()
        for skill in HAIKU_SKILLS:
            skill_cases = [c for c in cases if c["skill"] == skill]
            assert len(skill_cases) == 2, f"Skill {skill} : attendu 2 cas"

            verdicts_0 = set(skill_cases[0]["expected"].get("verdict_allowed", []))
            verdicts_1 = set(skill_cases[1]["expected"].get("verdict_allowed", []))
            intersection = verdicts_0 & verdicts_1

            assert intersection != verdicts_0 or intersection != verdicts_1, (
                f"Skill {skill} : les 2 cas ont des verdict_allowed identiques {verdicts_0} "
                "-- dataset non contrastant"
            )
