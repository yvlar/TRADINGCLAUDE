"""
Tests CI standard Sprint 54 : validation du golden dataset screener.
Aucun appel Claude — verifie la structure du dataset, la logique de tri,
et la cohérence des seuils de label composite.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from app.services.composite_score import compute_composite_score

_DATASET_PATH = Path(__file__).parent.parent / "evals" / "golden_screener_dataset.json"
_DEFENSIVE_VERDICTS = {"PASSE", "BORDERLINE", "REJETER"}
_GRAHAM_VERDICTS = {"REJETER", "WATCHLIST", "CANDIDAT_SOLIDE", "EXEMPLAIRE"}
_COMPOSITE_LABELS = {"FORT", "MODÉRÉ", "FAIBLE"}


def _load_dataset() -> list[dict]:
    assert _DATASET_PATH.exists(), (
        f"golden_screener_dataset.json introuvable : {_DATASET_PATH}\n"
        "Créer le fichier avec tests/evals/golden_screener_dataset.json"
    )
    return json.loads(_DATASET_PATH.read_text(encoding="utf-8"))


# ---------------------------------------------------------------------------
# Structure du dataset
# ---------------------------------------------------------------------------


class TestGoldenScreenerDatasetStructure:

    def test_exactement_10_cas(self):
        """Le golden dataset contient exactement 10 tickers."""
        cases = _load_dataset()
        assert len(cases) == 10, f"Attendu 10 tickers, trouvé {len(cases)}"

    def test_ids_uniques(self):
        """Aucun ID en doublon dans le dataset."""
        cases = _load_dataset()
        ids = [c["id"] for c in cases]
        assert len(ids) == len(set(ids)), f"IDs en doublon : {ids}"

    def test_champs_obligatoires_presents(self):
        """Chaque entrée contient id, ticker, ratios, expected avec sous-champs requis."""
        cases = _load_dataset()
        for case in cases:
            cid = case.get("id", "?")
            assert "id" in case, f"{cid} : 'id' manquant"
            assert "ticker" in case, f"{cid} : 'ticker' manquant"
            assert "ratios" in case, f"{cid} : 'ratios' manquant"
            assert "expected" in case, f"{cid} : 'expected' manquant"
            exp = case["expected"]
            assert "defensive_score_min" in exp, f"{cid} : 'defensive_score_min' manquant"
            assert "defensive_verdict_allowed" in exp, (
                f"{cid} : 'defensive_verdict_allowed' manquant"
            )
            assert "verdict_allowed" in exp, f"{cid} : 'verdict_allowed' manquant"
            assert "composite_label_allowed" in exp, (
                f"{cid} : 'composite_label_allowed' manquant"
            )

    def test_defensive_score_min_plage_valide(self):
        """defensive_score_min est dans [0, 8] pour chaque cas."""
        cases = _load_dataset()
        for case in cases:
            cid = case["id"]
            score_min = case["expected"]["defensive_score_min"]
            assert 0 <= score_min <= 8, (
                f"{cid} : defensive_score_min={score_min} hors plage [0, 8]"
            )

    def test_defensive_verdict_allowed_valeurs_valides(self):
        """defensive_verdict_allowed ne contient que PASSE, BORDERLINE, REJETER."""
        cases = _load_dataset()
        for case in cases:
            cid = case["id"]
            for v in case["expected"]["defensive_verdict_allowed"]:
                assert v in _DEFENSIVE_VERDICTS, (
                    f"{cid} : defensive_verdict_allowed contient '{v}' invalide "
                    f"(attendu : {_DEFENSIVE_VERDICTS})"
                )

    def test_verdict_allowed_valeurs_valides(self):
        """verdict_allowed ne contient que les verdicts Graham valides."""
        cases = _load_dataset()
        for case in cases:
            cid = case["id"]
            for v in case["expected"]["verdict_allowed"]:
                assert v in _GRAHAM_VERDICTS, (
                    f"{cid} : verdict_allowed contient '{v}' invalide "
                    f"(attendu : {_GRAHAM_VERDICTS})"
                )

    def test_composite_label_allowed_valeurs_valides(self):
        """composite_label_allowed ne contient que FORT, MODÉRÉ, FAIBLE."""
        cases = _load_dataset()
        for case in cases:
            cid = case["id"]
            for v in case["expected"]["composite_label_allowed"]:
                assert v in _COMPOSITE_LABELS, (
                    f"{cid} : composite_label_allowed contient '{v}' invalide "
                    f"(attendu : {_COMPOSITE_LABELS})"
                )

    def test_ratios_pydantic_valides(self):
        """Chaque entrée ratios peut être instanciée comme GrahamRatios sans erreur."""
        from app.skills.tier2.graham_analysis.schemas import GrahamRatios

        cases = _load_dataset()
        for case in cases:
            cid = case["id"]
            try:
                GrahamRatios(**case["ratios"])
            except Exception as exc:
                pytest.fail(f"{cid} ({case['ticker']}) : GrahamRatios invalide — {exc}")


# ---------------------------------------------------------------------------
# Logique de tri et seuils composite
# ---------------------------------------------------------------------------


class TestGoldenScreenerLogique:

    def test_tri_defensive_score_desc_coherent(self):
        """La logique de tri screener classe correctement les entrées par score décroissant."""
        from app.api.endpoints.screen import ScreenEntry

        cases = _load_dataset()

        # Simuler des ScreenEntry avec les score_min du dataset
        entries = [
            ScreenEntry(
                ticker=case["ticker"],
                defensive_score=case["expected"]["defensive_score_min"],
                verdict=case["expected"]["verdict_allowed"][0],
                composite_score=None,
                composite_label=None,
                workflow_utilise="value_graham",
                cost_usd=0.001,
                erreur=None,
            )
            for case in cases
        ]

        def _sort_key(e: ScreenEntry) -> tuple:
            if e.erreur is not None:
                return (1, 0.0, e.ticker)
            if e.composite_score is not None:
                return (0, -e.composite_score, e.ticker)
            if e.defensive_score is not None:
                return (0, -float(e.defensive_score), e.ticker)
            return (0, 0.0, e.ticker)

        entries.sort(key=_sort_key)
        scores = [e.defensive_score for e in entries if e.erreur is None]
        assert scores == sorted(scores, reverse=True), (
            f"Ordre incorrect après tri : "
            f"{[(e.ticker, e.defensive_score) for e in entries]}"
        )

    def test_composite_seuils_passe_fort_borderline_modere_rejeter_faible(self):
        """Seuils composite déterministes : PASSE→FORT, BORDERLINE→MODÉRÉ, REJETER→FAIBLE."""
        passe = compute_composite_score(graham_verdict="PASSE", graham_confidence=1.0)
        borderline = compute_composite_score(graham_verdict="BORDERLINE", graham_confidence=1.0)
        rejeter = compute_composite_score(graham_verdict="REJETER", graham_confidence=1.0)

        assert passe.label == "FORT", (
            f"PASSE → FORT attendu, obtenu {passe.label} (score={passe.score})"
        )
        assert borderline.label == "MODÉRÉ", (
            f"BORDERLINE → MODÉRÉ attendu, obtenu {borderline.label} (score={borderline.score})"
        )
        assert rejeter.label == "FAIBLE", (
            f"REJETER → FAIBLE attendu, obtenu {rejeter.label} (score={rejeter.score})"
        )

    def test_composite_label_allowed_coherent_avec_defensive_verdict(self):
        """composite_label_allowed est cohérent avec defensive_verdict_allowed dans le dataset."""
        cases = _load_dataset()
        # Mapping defensive_verdict → composite_label attendu
        verdict_to_label = {"PASSE": "FORT", "BORDERLINE": "MODÉRÉ", "REJETER": "FAIBLE"}

        for case in cases:
            cid = case["id"]
            allowed_verdicts = case["expected"]["defensive_verdict_allowed"]
            allowed_labels = set(case["expected"]["composite_label_allowed"])

            # Vérifier que chaque verdict_allowed a son label correspondant dans composite_label_allowed
            for verdict in allowed_verdicts:
                expected_label = verdict_to_label[verdict]
                assert expected_label in allowed_labels, (
                    f"{cid} ({case['ticker']}) : defensive_verdict_allowed inclut '{verdict}' "
                    f"mais composite_label_allowed ne contient pas '{expected_label}' "
                    f"(contient : {allowed_labels})"
                )

    def test_distribution_profils_diverse_dans_dataset(self):
        """Le dataset couvre les 3 profils Graham : PASSE/BORDERLINE et REJETER."""
        cases = _load_dataset()

        rejeter_only = sum(
            1 for c in cases
            if c["expected"]["defensive_verdict_allowed"] == ["REJETER"]
        )
        borderline_ou_passe = sum(
            1 for c in cases
            if any(
                v in c["expected"]["defensive_verdict_allowed"]
                for v in ("BORDERLINE", "PASSE")
            )
        )

        assert rejeter_only >= 2, (
            f"Pas assez de cas REJETER exclusif : {rejeter_only} (minimum 2)"
        )
        assert borderline_ou_passe >= 3, (
            f"Pas assez de cas BORDERLINE/PASSE : {borderline_ou_passe} (minimum 3)"
        )
