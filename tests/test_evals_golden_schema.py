"""
Tests CI standard : validation des schemas JSON des golden datasets Sprint 49.
Aucun appel Claude -- verifie uniquement la structure des fixtures.
"""
from __future__ import annotations

from tests.evals.fixtures import load_buffett_golden, load_damodaran_golden, load_dorsey_golden

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_DORSEY_VERDICTS = {"WIDE", "NARROW", "NONE"}
_BUFFETT_VERDICTS = {"COMPOUNDER", "QUALITE_CORRECTE", "REJETER"}
_DAMODARAN_VERDICTS = {
    "NARRATIVE_FORTE",
    "NARRATIVE_ACCEPTABLE",
    "NARRATIVE_FAIBLE",
    "NARRATIVE_INCOHERENTE",
}
_DAMODARAN_COHERENCES = {"POSSIBLE", "PLAUSIBLE", "PROBABLE", "INCOHERENT"}


# ---------------------------------------------------------------------------
# Tests Dorsey golden
# ---------------------------------------------------------------------------


class TestDorseyGoldenSchema:

    def test_dorsey_exactement_15_cas(self):
        cases = load_dorsey_golden()
        assert len(cases) == 15, f"Attendu 15 cas, trouve {len(cases)}"

    def test_dorsey_ids_uniques(self):
        cases = load_dorsey_golden()
        ids = [c["id"] for c in cases]
        assert len(ids) == len(set(ids)), "IDs en doublon dans dorsey_golden.json"

    def test_dorsey_champs_obligatoires(self):
        for case in load_dorsey_golden():
            cid = case["id"]
            assert "input" in case, f"{cid} : champ 'input' manquant"
            assert "expected" in case, f"{cid} : champ 'expected' manquant"
            assert "ticker" in case["input"], f"{cid} : 'ticker' manquant dans input"
            assert "ratios" in case["input"], f"{cid} : 'ratios' manquant dans input"
            exp = case["expected"]
            assert "moat_type_allowed" in exp, f"{cid} : 'moat_type_allowed' manquant"
            assert "sources_min" in exp, f"{cid} : 'sources_min' manquant"

    def test_dorsey_moat_type_allowed_valides(self):
        for case in load_dorsey_golden():
            for v in case["expected"]["moat_type_allowed"]:
                assert v in _DORSEY_VERDICTS, (
                    f"{case['id']} : moat_type_allowed contient '{v}' invalide"
                )

    def test_dorsey_moat_type_allowed_non_vide(self):
        for case in load_dorsey_golden():
            assert len(case["expected"]["moat_type_allowed"]) >= 1, (
                f"{case['id']} : moat_type_allowed vide"
            )

    def test_dorsey_sources_min_coherent(self):
        for case in load_dorsey_golden():
            sources_min = case["expected"]["sources_min"]
            assert 0 <= sources_min <= 5, (
                f"{case['id']} : sources_min={sources_min} hors plage [0,5]"
            )

    def test_dorsey_distribution_wide_narrow_none(self):
        cases = load_dorsey_golden()
        wide_count = sum(1 for c in cases if "WIDE" in c["expected"]["moat_type_allowed"])
        narrow_count = sum(1 for c in cases if "NARROW" in c["expected"]["moat_type_allowed"])
        none_count = sum(1 for c in cases if "NONE" in c["expected"]["moat_type_allowed"])
        assert wide_count >= 3, f"Pas assez de cas WIDE : {wide_count}"
        assert narrow_count >= 3, f"Pas assez de cas NARROW : {narrow_count}"
        assert none_count >= 2, f"Pas assez de cas NONE : {none_count}"

    def test_dorsey_ratios_input_valides(self):
        from app.skills.tier2.dorsey_moat.schemas import DorseyRatios
        for case in load_dorsey_golden():
            DorseyRatios(**case["input"]["ratios"])


# ---------------------------------------------------------------------------
# Tests Buffett golden
# ---------------------------------------------------------------------------


class TestBuffettGoldenSchema:

    def test_buffett_exactement_15_cas(self):
        cases = load_buffett_golden()
        assert len(cases) == 15, f"Attendu 15 cas, trouve {len(cases)}"

    def test_buffett_ids_uniques(self):
        cases = load_buffett_golden()
        ids = [c["id"] for c in cases]
        assert len(ids) == len(set(ids)), "IDs en doublon dans buffett_golden.json"

    def test_buffett_champs_obligatoires(self):
        for case in load_buffett_golden():
            cid = case["id"]
            assert "input" in case, f"{cid} : champ 'input' manquant"
            assert "expected" in case, f"{cid} : champ 'expected' manquant"
            assert "ticker" in case["input"], f"{cid} : 'ticker' manquant dans input"
            assert "ratios" in case["input"], f"{cid} : 'ratios' manquant dans input"
            exp = case["expected"]
            assert "verdict_allowed" in exp, f"{cid} : 'verdict_allowed' manquant"
            assert "quality_score_min" in exp, f"{cid} : 'quality_score_min' manquant"

    def test_buffett_verdict_allowed_valides(self):
        for case in load_buffett_golden():
            for v in case["expected"]["verdict_allowed"]:
                assert v in _BUFFETT_VERDICTS, (
                    f"{case['id']} : verdict_allowed contient '{v}' invalide"
                )

    def test_buffett_quality_score_min_coherent(self):
        for case in load_buffett_golden():
            qmin = case["expected"]["quality_score_min"]
            assert 0 <= qmin <= 4, (
                f"{case['id']} : quality_score_min={qmin} hors plage [0,4]"
            )

    def test_buffett_distribution_verdicts(self):
        cases = load_buffett_golden()
        compounder_count = sum(1 for c in cases if "COMPOUNDER" in c["expected"]["verdict_allowed"])
        qualite_count = sum(1 for c in cases if "QUALITE_CORRECTE" in c["expected"]["verdict_allowed"])
        rejeter_count = sum(1 for c in cases if "REJETER" in c["expected"]["verdict_allowed"])
        assert compounder_count >= 3, f"Pas assez de COMPOUNDER : {compounder_count}"
        assert qualite_count >= 3, f"Pas assez de QUALITE_CORRECTE : {qualite_count}"
        assert rejeter_count >= 2, f"Pas assez de REJETER : {rejeter_count}"

    def test_buffett_ratios_input_valides(self):
        from app.skills.tier2.buffett_quality.schemas import BuffettRatios
        for case in load_buffett_golden():
            BuffettRatios(**case["input"]["ratios"])

    def test_buffett_dorsey_context_valide_si_present(self):
        from app.skills.tier2.buffett_quality.schemas import DorseyContext
        for case in load_buffett_golden():
            ctx = case["input"].get("dorsey_context")
            if ctx:
                DorseyContext(**ctx)


# ---------------------------------------------------------------------------
# Tests Damodaran golden
# ---------------------------------------------------------------------------


class TestDamodararGoldenSchema:

    def test_damodaran_exactement_15_cas(self):
        cases = load_damodaran_golden()
        assert len(cases) == 15, f"Attendu 15 cas, trouve {len(cases)}"

    def test_damodaran_ids_uniques(self):
        cases = load_damodaran_golden()
        ids = [c["id"] for c in cases]
        assert len(ids) == len(set(ids)), "IDs en doublon dans damodaran_golden.json"

    def test_damodaran_champs_obligatoires(self):
        for case in load_damodaran_golden():
            cid = case["id"]
            assert "input" in case, f"{cid} : 'input' manquant"
            assert "expected" in case, f"{cid} : 'expected' manquant"
            inp = case["input"]
            assert "ticker" in inp, f"{cid} : 'ticker' manquant dans input"
            assert "narrative_text" in inp, f"{cid} : 'narrative_text' manquant"
            assert "ratios" in inp, f"{cid} : 'ratios' manquant dans input"
            exp = case["expected"]
            assert "verdict_allowed" in exp, f"{cid} : 'verdict_allowed' manquant"
            assert "test_coherence_allowed" in exp, f"{cid} : 'test_coherence_allowed' manquant"

    def test_damodaran_verdict_allowed_valides(self):
        for case in load_damodaran_golden():
            for v in case["expected"]["verdict_allowed"]:
                assert v in _DAMODARAN_VERDICTS, (
                    f"{case['id']} : verdict_allowed contient '{v}' invalide"
                )

    def test_damodaran_test_coherence_allowed_valides(self):
        for case in load_damodaran_golden():
            for v in case["expected"]["test_coherence_allowed"]:
                assert v in _DAMODARAN_COHERENCES, (
                    f"{case['id']} : test_coherence_allowed contient '{v}' invalide"
                )

    def test_damodaran_narrative_strength_min_coherent(self):
        for case in load_damodaran_golden():
            ns_min = case["expected"]["narrative_strength_min"]
            assert 0 <= ns_min <= 10, (
                f"{case['id']} : narrative_strength_min={ns_min} hors [0,10]"
            )

    def test_damodaran_narrative_text_non_vide(self):
        for case in load_damodaran_golden():
            text = case["input"]["narrative_text"]
            assert len(text) >= 50, (
                f"{case['id']} : narrative_text trop court ({len(text)} chars)"
            )

    def test_damodaran_ratios_input_valides(self):
        from app.skills.tier2.damodaran_narrative.schemas import DamodararRatios
        for case in load_damodaran_golden():
            DamodararRatios(**case["input"]["ratios"])

    def test_damodaran_distribution_profils(self):
        cases = load_damodaran_golden()
        forte_count = sum(1 for c in cases if "NARRATIVE_FORTE" in c["expected"]["verdict_allowed"])
        faible_count = sum(
            1 for c in cases if any(
                v in c["expected"]["verdict_allowed"]
                for v in ["NARRATIVE_FAIBLE", "NARRATIVE_INCOHERENTE"]
            )
        )
        assert forte_count >= 3, f"Pas assez de NARRATIVE_FORTE : {forte_count}"
        assert faible_count >= 2, f"Pas assez de cas faibles/incoherents : {faible_count}"
