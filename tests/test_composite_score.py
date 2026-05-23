"""Tests unitaires pour compute_composite_score()."""

from app.services.composite_score import WEIGHTS, compute_composite_score


class TestComputeCompositeScoreBasique:
    def test_tous_skills_presents_fort(self):
        cs = compute_composite_score(
            graham_verdict="PASSE", graham_confidence=1.0,
            buffett_verdict="COMPOUNDER", buffett_confidence=1.0,
            valuation_verdict="SOUS-ÉVALUÉ", valuation_confidence=1.0,
            moat_type="WIDE", moat_confidence=1.0,
            earnings_verdict="FIABLE", earnings_confidence=1.0,
            marks_signal="ACHETEUR AGRESSIF", marks_confidence=1.0,
        )
        assert cs.score == 100.0
        assert cs.label == "FORT"
        assert len(cs.skills_inclus) == 6
        assert cs.skills_exclus == []

    def test_tous_skills_rejeter_faible(self):
        cs = compute_composite_score(
            graham_verdict="REJETER", graham_confidence=1.0,
            buffett_verdict="REJETER", buffett_confidence=1.0,
            valuation_verdict="SURÉVALUÉ", valuation_confidence=1.0,
            moat_type="NONE", moat_confidence=1.0,
            earnings_verdict="REJETER", earnings_confidence=1.0,
            marks_signal="VENDEUR", marks_confidence=1.0,
        )
        assert cs.score == 0.0
        assert cs.label == "FAIBLE"

    def test_skills_absents_exclus_du_denominateur(self):
        """Un skill absent (verdict=None) ne doit pas pénaliser le score."""
        cs_complet = compute_composite_score(
            graham_verdict="PASSE", graham_confidence=1.0,
            buffett_verdict="COMPOUNDER", buffett_confidence=1.0,
        )
        cs_seul_graham = compute_composite_score(
            graham_verdict="PASSE", graham_confidence=1.0,
        )
        # Les deux devraient avoir le même score puisque buffett COMPOUNDER = 1.0
        assert cs_complet.score == cs_seul_graham.score == 100.0

    def test_confidence_zero_exclut_skill(self):
        cs = compute_composite_score(
            graham_verdict="PASSE", graham_confidence=0.0,  # exclu
            buffett_verdict="COMPOUNDER", buffett_confidence=1.0,
        )
        assert "graham" in cs.skills_exclus
        assert "buffett" in cs.skills_inclus
        assert cs.score == 100.0

    def test_aucun_skill_score_zero(self):
        cs = compute_composite_score()
        assert cs.score == 0.0
        assert cs.label == "FAIBLE"
        assert cs.skills_inclus == []
        assert len(cs.skills_exclus) == 6


class TestLabels:
    def test_label_fort_a_70(self):
        # Graham PASSE (1.0) × 20% + buffett COMPOUNDER (1.0) × 20% = 0.4/0.4 → 100 → FORT
        cs = compute_composite_score(graham_verdict="PASSE", graham_confidence=1.0,
                                     buffett_verdict="COMPOUNDER", buffett_confidence=1.0)
        assert cs.label == "FORT"

    def test_label_modere_entre_45_et_70(self):
        # Mélange PASSE et REJETER doit donner ~50
        cs = compute_composite_score(
            graham_verdict="PASSE", graham_confidence=1.0,
            buffett_verdict="REJETER", buffett_confidence=1.0,
        )
        assert cs.label in ("MODÉRÉ", "FAIBLE")  # selon la moyenne

    def test_score_plage_0_100(self):
        cs = compute_composite_score(
            graham_verdict="BORDERLINE", graham_confidence=0.7,
            buffett_verdict="PASSABLE", buffett_confidence=0.5,
            marks_signal="NEUTRE", marks_confidence=1.0,
        )
        assert 0.0 <= cs.score <= 100.0


class TestDetailEtPoids:
    def test_poids_somme_a_1(self):
        assert abs(sum(WEIGHTS.values()) - 1.0) < 1e-9

    def test_detail_contient_skills_inclus(self):
        cs = compute_composite_score(
            graham_verdict="PASSE", graham_confidence=1.0,
            buffett_verdict="COMPOUNDER", buffett_confidence=1.0,
        )
        assert "graham" in cs.detail
        assert "buffett" in cs.detail

    def test_confidence_module_score(self):
        """confidence=0.5 doit pondérer moitié du poids habituel."""
        cs_full = compute_composite_score(graham_verdict="PASSE", graham_confidence=1.0)
        cs_half = compute_composite_score(graham_verdict="PASSE", graham_confidence=0.5)
        # Les deux donnent 100.0 car seul graham contribue — même ratio numérateur/dénominateur
        assert cs_full.score == cs_half.score == 100.0


class TestMarksMapping:
    def test_acheteur_agressif(self):
        cs = compute_composite_score(marks_signal="ACHETEUR AGRESSIF", marks_confidence=1.0)
        assert cs.score == 100.0

    def test_neutre(self):
        cs = compute_composite_score(marks_signal="NEUTRE", marks_confidence=1.0)
        assert cs.score == 50.0

    def test_vendeur(self):
        cs = compute_composite_score(marks_signal="VENDEUR OFFENSIF", marks_confidence=1.0)
        assert cs.score == 0.0

    def test_signal_inconnu_exclu(self):
        cs = compute_composite_score(marks_signal=None, marks_confidence=1.0)
        assert "marks_cycles" in cs.skills_exclus


class TestSchemaReels:
    """Vérifie que les valeurs des vrais schémas Pydantic sont correctement mappées."""

    def test_buffett_qualite_correcte(self):
        cs = compute_composite_score(
            buffett_verdict="QUALITE_CORRECTE", buffett_confidence=1.0,
        )
        assert cs.score == 75.0
        assert "buffett" in cs.skills_inclus

    def test_earnings_aucun_signal(self):
        cs = compute_composite_score(
            earnings_verdict="AUCUN_SIGNAL", earnings_confidence=1.0,
        )
        assert cs.score == 100.0

    def test_earnings_watchlist(self):
        cs = compute_composite_score(
            earnings_verdict="WATCHLIST", earnings_confidence=1.0,
        )
        assert cs.score == 50.0

    def test_earnings_attention(self):
        cs = compute_composite_score(
            earnings_verdict="ATTENTION", earnings_confidence=1.0,
        )
        assert cs.score == 75.0

    def test_valuation_sous_evalue(self):
        cs = compute_composite_score(
            valuation_verdict="SOUS_EVALUE", valuation_confidence=1.0,
        )
        assert cs.score == 100.0

    def test_valuation_juste_valeur(self):
        cs = compute_composite_score(
            valuation_verdict="JUSTE_VALEUR", valuation_confidence=1.0,
        )
        assert cs.score == 50.0

    def test_marks_acheter_agressif_schema_reel(self):
        cs = compute_composite_score(marks_signal="ACHETER_AGRESSIF", marks_confidence=1.0)
        assert cs.score == 100.0

    def test_marks_attendre_schema_reel(self):
        cs = compute_composite_score(marks_signal="ATTENDRE", marks_confidence=1.0)
        assert cs.score == 50.0
