"""Tests des modèles Pydantic — validation des inputs et outputs (0 appel réseau)."""
from __future__ import annotations

from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from app.skills.base import Citation
from app.skills.tier2.buffett_quality.schemas import (
    BuffettFiltre,
    BuffettQualityOutput,
)
from app.skills.tier2.canadian_tax.schemas import CanadianTaxInput, CanadianTaxOutput
from app.skills.tier2.dorsey_moat.schemas import DorseyMoatOutput, MoatSource
from app.skills.tier2.earnings_quality.schemas import (
    CScoreDetail,
    CScoreSignal,
    EarningsQualityOutput,
    FScoreCriterion,
    FScoreDetail,
    MScoreDetail,
    SloanDetail,
    ZScoreDetail,
)
from app.skills.tier2.graham_analysis.schemas import (
    GrahamAnalysisInput,
    GrahamAnalysisOutput,
    GrahamCriterion,
    GrahamRatios,
)
from app.skills.tier2.munger_mental.schemas import BiaisCognitif, MungerOutput, ThesisContext
from app.skills.tier2.stock_valuation.schemas import (
    SensitivityMatrix,
    StockValuationOutput,
    ValuationMethod,
    ValuationRatios,
)
from app.skills.tier2.thesis_builder.schemas import ThesisBuilderOutput, ThesisScenario

# ---------------------------------------------------------------------------
# Helpers locaux
# ---------------------------------------------------------------------------


def _f_criteria(scores: list[bool]) -> list[FScoreCriterion]:
    noms = [
        "ROA > 0", "CFO > 0", "ROA en hausse", "CFO > bénéfice net",
        "Désendettement", "Current ratio en hausse", "Pas d'émission d'actions",
        "Marge brute en hausse", "Asset turnover en hausse",
    ]
    return [FScoreCriterion(nom=noms[i], passe=scores[i], detail="test") for i in range(9)]


def _c_signaux(present: list[bool]) -> list[CScoreSignal]:
    noms = [
        "Divergence NI-CFO", "DSO en hausse", "DIO en hausse",
        "Autres actifs courants", "Dépréciation réduite", "Émission d'actions",
    ]
    return [CScoreSignal(nom=noms[i], present=present[i], detail="test") for i in range(6)]


def _moat_sources(intensites: list[str] | None = None) -> list[MoatSource]:
    sources = [
        "intangibles", "switching_costs", "network_effects",
        "cost_advantages", "efficient_scale",
    ]
    if intensites is None:
        intensites = ["ABSENTE"] * 5
    return [
        MoatSource(source=sources[i], present=False, intensite=intensites[i], justification="test")
        for i in range(5)
    ]


def _buffett_filtres(passes: list[bool] | None = None) -> list[BuffettFiltre]:
    noms = [
        "compréhensible", "economics favorables", "management", "prix attractif"
    ]
    if passes is None:
        passes = [False] * 4
    return [
        BuffettFiltre(filtre=noms[i], passe=passes[i], score=int(passes[i]), justification="test")
        for i in range(4)
    ]


def _valuation_methodes() -> list[ValuationMethod]:
    return [
        ValuationMethod(methode="dcf", valeur=90.0, hypotheses="WACC 8%, g 3%"),
        ValuationMethod(methode="comparables", valeur=95.0, hypotheses="EV/EBITDA 12x"),
        ValuationMethod(methode="sectoriel", valeur=88.0, hypotheses="P/BV 1.5x"),
    ]


def _thesis_context() -> ThesisContext:
    return ThesisContext(
        ticker="TEST",
        verdict_final="ACCUMULER",
        position_size_pct=3.0,
        scenario_bull_probabilite=0.30,
        scenario_base_probabilite=0.50,
        scenario_bear_probabilite=0.20,
        synthese_narrative="Thèse de test.",
        kill_criteria=["kill 1", "kill 2"],
        devils_advocate="Argument contre.",
    )


# ---------------------------------------------------------------------------
# Graham (existants, conservés)
# ---------------------------------------------------------------------------

class TestGrahamRatios:
    def test_champs_requis_valides(self):
        ratios = GrahamRatios(
            pe=15.0, pb=1.2, current_ratio=2.5, debt_equity=0.3,
            eps_growth_total=0.40, price=100.0, book_value=83.0,
        )
        assert ratios.pe == 15.0
        assert ratios.pb == 1.2

    def test_current_ratio_none_banque(self, ratios_bns):
        assert ratios_bns.current_ratio is None

    def test_champs_optionnels_absents_par_defaut_none(self):
        ratios = GrahamRatios(
            pe=10.0, pb=1.0, current_ratio=2.0,
            debt_equity=0.2, eps_growth_total=0.5,
            price=50.0, book_value=50.0,
        )
        assert ratios.eps_ttm is None
        assert ratios.revenue_bn is None
        assert ratios.dividend_years is None
        assert ratios.no_deficit_years is None

    def test_champs_optionnels_renseignes(self, ratios_bns):
        assert ratios_bns.eps_ttm == 7.25
        assert ratios_bns.revenue_bn == 38.0
        assert ratios_bns.dividend_years == 190
        assert ratios_bns.no_deficit_years == 10

    def test_pe_null_accepte_societe_deficitaire(self):
        """pe=None est valide depuis Sprint 36 — sociétés sans bénéfices publiables (RIVN, NKLA…)."""
        ratios = GrahamRatios(
            pe=None, pb=1.0, current_ratio=2.0, debt_equity=0.2,
            eps_growth_total=0.3, price=50.0, book_value=50.0,
        )
        assert ratios.pe is None

    def test_pe_negatif_accepte_deficit_explicite(self):
        """pe < 0 est valide — déficit explicite."""
        ratios = GrahamRatios(
            pe=-5.0, pb=1.0, current_ratio=2.0, debt_equity=0.2,
            eps_growth_total=0.3, price=50.0, book_value=50.0,
        )
        assert ratios.pe == -5.0

    def test_pb_manquant_donne_none(self):
        """pb absent → None (Sprint 135) : donnée manquante honnête, jamais 0.0 trompeur."""
        ratios = GrahamRatios(
            pe=10.0, current_ratio=2.0, debt_equity=0.2,
            eps_growth_total=0.3, price=50.0, book_value=50.0,
        )
        assert ratios.pb is None

    def test_eps_growth_negatif_accepte(self):
        ratios = GrahamRatios(
            pe=5.0, pb=0.5, current_ratio=1.5, debt_equity=0.5,
            eps_growth_total=-0.15, price=30.0, book_value=60.0,
        )
        assert ratios.eps_growth_total == -0.15

    def test_eps_growth_years_optionnel_defaut_none(self):
        """eps_growth_years absent → None (horizon inconnu), pas d'erreur."""
        ratios = GrahamRatios(
            pe=11.0, pb=1.3, current_ratio=None, debt_equity=0.45,
            eps_growth_total=0.27, price=80.0, book_value=61.5,
        )
        assert ratios.eps_growth_years is None

    def test_eps_growth_years_renseigne(self):
        """eps_growth_years exposé tel quel (horizon réel du calcul)."""
        ratios = GrahamRatios(
            pe=11.0, pb=1.3, current_ratio=None, debt_equity=0.45,
            eps_growth_total=0.27, eps_growth_years=4, price=80.0, book_value=61.5,
        )
        assert ratios.eps_growth_years == 4

    def test_tracabilite_absente_par_defaut_none(self):
        """ratios_fetched_at / ratios_source absents → None (rétrocompatible analyses persistées)."""
        ratios = GrahamRatios(
            pe=11.0, pb=1.3, current_ratio=None, debt_equity=0.45,
            eps_growth_total=0.27, price=80.0, book_value=61.5,
        )
        assert ratios.ratios_fetched_at is None
        assert ratios.ratios_source is None

    def test_tracabilite_renseignee_et_iso_acceptee(self):
        """ratios_fetched_at accepte une string ISO (round-trip JSONB) et ratios_source un littéral."""
        ratios = GrahamRatios(
            pe=11.0, pb=1.3, current_ratio=None, debt_equity=0.45,
            eps_growth_total=0.27, price=80.0, book_value=61.5,
            ratios_fetched_at="2026-05-30T12:00:00+00:00", ratios_source="Yahoo Finance",
        )
        assert ratios.ratios_source == "Yahoo Finance"
        assert ratios.ratios_fetched_at is not None
        assert ratios.ratios_fetched_at.year == 2026


class TestGrahamAnalysisInput:
    def test_construction_valide(self, ratios_msft):
        inp = GrahamAnalysisInput(ticker="MSFT", ratios=ratios_msft)
        assert inp.ticker == "MSFT"
        assert inp.ratios.pe == 34.2

    def test_ticker_manquant_leve_erreur(self, ratios_msft):
        with pytest.raises(ValidationError):
            GrahamAnalysisInput(ratios=ratios_msft)

    def test_ratios_manquants_leve_erreur(self):
        with pytest.raises(ValidationError):
            GrahamAnalysisInput(ticker="MSFT")


class TestGrahamCriterion:
    def test_construction_valide(self):
        c = GrahamCriterion(
            numero=1, nom="Taille suffisante", passe=True,
            valeur_observee="38 G$", seuil="> 700 M$", commentaire="Critère satisfait.",
        )
        assert c.passe is True
        assert c.numero == 1

    def test_passe_false_valide(self):
        c = GrahamCriterion(
            numero=6, nom="P/E modéré", passe=False,
            valeur_observee="34.2", seuil="≤ 15", commentaire="P/E trop élevé.",
        )
        assert c.passe is False


class TestGrahamAnalysisOutput:
    def test_construction_complete_valide(self, graham_output_msft):
        assert graham_output_msft.ticker == "MSFT"
        assert graham_output_msft.defensive_score == 2
        assert graham_output_msft.enterprising_score == 2
        assert len(graham_output_msft.criteria_defensif) == 8
        assert len(graham_output_msft.criteria_entreprenant) == 5

    def test_graham_output_exactement_8_criteria_defensif(self, graham_output_msft):
        assert len(graham_output_msft.criteria_defensif) == 8

    def test_graham_output_exactement_5_criteria_entreprenant(self, graham_output_msft):
        assert len(graham_output_msft.criteria_entreprenant) == 5

    def test_graham_defensive_score_plage_0_8(self, graham_output_msft):
        assert 0 <= graham_output_msft.defensive_score <= 8

    def test_graham_marge_securite_fraction(self, graham_output_msft):
        """marge_securite est une fraction, pas un pourcentage (abs < 2.0)."""
        assert graham_output_msft.marge_securite is not None
        assert abs(graham_output_msft.marge_securite) < 2.0

    def test_citations_vides_par_defaut(self, graham_output_msft):
        assert graham_output_msft.citations == []

    def test_cost_usd_non_nul(self, graham_output_msft):
        assert graham_output_msft.cost_usd > 0.0

    def test_defensive_score_est_computed_field(self):
        from tests.conftest import _make_criteria_defensif, _make_criteria_entreprenant
        obj = GrahamAnalysisOutput(
            ticker="X", profil_applique="LES_DEUX",
            enterprising_score=0,
            criteria_defensif=_make_criteria_defensif(),
            criteria_entreprenant=_make_criteria_entreprenant(),
            drapeaux_rouges=[], verdict="REJETER",
            verdict_detail="Test.", recommandation_prochaine_etape=[],
        )
        assert obj.defensive_score == 0

    def test_model_validator_rejette_7_criteres_defensifs(self):
        from tests.conftest import _make_criteria_defensif, _make_criteria_entreprenant
        with pytest.raises(ValidationError) as exc_info:
            GrahamAnalysisOutput(
                ticker="X", profil_applique="LES_DEUX", defensive_score=0,
                enterprising_score=0,
                criteria_defensif=_make_criteria_defensif()[:7],
                criteria_entreprenant=_make_criteria_entreprenant(),
                drapeaux_rouges=[], verdict="REJETER",
                verdict_detail="Test.", recommandation_prochaine_etape=[],
            )
        assert "criteria_defensif" in str(exc_info.value)

    def test_model_validator_rejette_4_criteres_entrepreneuriaux(self):
        from tests.conftest import _make_criteria_defensif, _make_criteria_entreprenant
        with pytest.raises(ValidationError) as exc_info:
            GrahamAnalysisOutput(
                ticker="X", profil_applique="LES_DEUX", defensive_score=0,
                enterprising_score=0,
                criteria_defensif=_make_criteria_defensif(),
                criteria_entreprenant=_make_criteria_entreprenant()[:4],
                drapeaux_rouges=[], verdict="REJETER",
                verdict_detail="Test.", recommandation_prochaine_etape=[],
            )
        assert "criteria_entreprenant" in str(exc_info.value)


class TestCitation:
    def test_construction_valide(self):
        c = Citation(
            source=".claude/skills/graham-stock-screening/references/graham-defensif.md",
            extrait="Current ratio ≥ 2.0",
            score=0.87,
        )
        assert c.score == 0.87


# ---------------------------------------------------------------------------
# Earnings Quality
# ---------------------------------------------------------------------------

class TestEarningsQualityOutput:
    def _make_output(self, **overrides) -> EarningsQualityOutput:
        base = dict(
            ticker="TEST",
            is_financial=False,
            m_score=MScoreDetail(
                dsri=None, gmi=None, aqi=None, sgi=1.0, depi=None,
                sgai=None, tata=0.0, lvgi=None, m_score=-2.5,
                interpretation="sous_seuil",
            ),
            z_score=ZScoreDetail(variante="Z_original", z_score=3.0, interpretation="zone_sure"),
            f_score=FScoreDetail(
                criteria=_f_criteria([True] * 9), f_score=9, interpretation="fort"
            ),
            c_score=CScoreDetail(
                signaux=_c_signaux([False] * 6), c_score=0, interpretation="propre"
            ),
            sloan=SloanDetail(accrual_ratio=-0.02, interpretation="qualite_elevee"),
            drapeaux_rouges=[],
            verdict="AUCUN_SIGNAL",
            verdict_detail="Aucun signal.",
            recommandation_prochaine_etape=[],
        )
        base.update(overrides)
        return EarningsQualityOutput(**base)

    def test_earnings_f_score_exactement_9_criteria(self):
        output = self._make_output()
        assert len(output.f_score.criteria) == 9

    def test_earnings_c_score_exactement_6_signaux(self):
        output = self._make_output()
        assert len(output.c_score.signaux) == 6

    def test_earnings_verdict_valide(self):
        verdicts = {"AUCUN_SIGNAL", "ATTENTION", "WATCHLIST", "REJETER"}
        for v in verdicts:
            output = self._make_output(verdict=v)
            assert output.verdict == v

    def test_earnings_verdict_invalide_leve_erreur(self):
        with pytest.raises(ValidationError):
            self._make_output(verdict="INCONNU")

    def test_f_score_7_criteria_leve_erreur(self):
        with pytest.raises(ValidationError):
            self._make_output(
                f_score=FScoreDetail(
                    criteria=_f_criteria([True] * 9)[:7],
                    f_score=7,
                    interpretation="test",
                )
            )

    def test_c_score_5_signaux_leve_erreur(self):
        with pytest.raises(ValidationError):
            self._make_output(
                c_score=CScoreDetail(
                    signaux=_c_signaux([False] * 6)[:5],
                    c_score=0,
                    interpretation="test",
                )
            )


# ---------------------------------------------------------------------------
# Dorsey Moat
# ---------------------------------------------------------------------------

class TestDorseyMoatOutput:
    def _make_output(self, **overrides) -> DorseyMoatOutput:
        base = dict(
            ticker="TEST",
            moat_type="NARROW",
            sources_identifiees=_moat_sources(),
            roic_durability="MODÉRÉE",
            verdict_detail="Test.",
            drapeaux_rouges=[],
            recommandation_prochaine_etape=[],
        )
        base.update(overrides)
        return DorseyMoatOutput(**base)

    def test_dorsey_sources_exactement_5(self):
        output = self._make_output()
        assert len(output.sources_identifiees) == 5

    def test_dorsey_moat_type_valide(self):
        for moat in {"WIDE", "NARROW", "NONE"}:
            output = self._make_output(moat_type=moat)
            assert output.moat_type == moat

    def test_dorsey_moat_type_invalide_leve_erreur(self):
        with pytest.raises(ValidationError):
            self._make_output(moat_type="INCONNU")

    def test_dorsey_roic_durability_valide(self):
        for d in {"FORTE", "MODÉRÉE", "FAIBLE"}:
            output = self._make_output(roic_durability=d)
            assert output.roic_durability == d

    def test_dorsey_roic_durability_invalide_leve_erreur(self):
        with pytest.raises(ValidationError):
            self._make_output(roic_durability="INCONNUE")

    def test_dorsey_4_sources_leve_erreur(self):
        with pytest.raises(ValidationError):
            self._make_output(sources_identifiees=_moat_sources()[:4])


# ---------------------------------------------------------------------------
# Buffett Quality
# ---------------------------------------------------------------------------

class TestBuffettQualityOutput:
    def _make_output(self, **overrides) -> BuffettQualityOutput:
        base = dict(
            ticker="TEST",
            filtres=_buffett_filtres([True, True, False, False]),
            owner_earnings=8.5,
            quality_score=2,
            verdict="QUALITE_CORRECTE",
            verdict_detail="Test.",
            drapeaux_rouges=[],
            recommandation_prochaine_etape=[],
        )
        base.update(overrides)
        return BuffettQualityOutput(**base)

    def test_buffett_filtres_exactement_4(self):
        output = self._make_output()
        assert len(output.filtres) == 4

    def test_buffett_quality_score_plage_0_4(self):
        for score in range(5):
            output = self._make_output(quality_score=score)
            assert 0 <= output.quality_score <= 4

    def test_buffett_verdict_valide(self):
        for v in {"COMPOUNDER", "QUALITE_CORRECTE", "REJETER"}:
            output = self._make_output(verdict=v)
            assert output.verdict == v

    def test_buffett_verdict_invalide_leve_erreur(self):
        with pytest.raises(ValidationError):
            self._make_output(verdict="INCONNU")

    def test_buffett_3_filtres_leve_erreur(self):
        with pytest.raises(ValidationError):
            self._make_output(filtres=_buffett_filtres()[:3])

    def test_buffett_quality_score_hors_plage_leve_erreur(self):
        with pytest.raises(ValidationError):
            self._make_output(quality_score=5)


# ---------------------------------------------------------------------------
# Stock Valuation Triangulation
# ---------------------------------------------------------------------------

class TestStockValuationOutput:
    def _make_output(self, **overrides) -> StockValuationOutput:
        base = dict(
            ticker="TEST",
            methodes=_valuation_methodes(),
            fourchette_basse=80.0,
            fourchette_centrale=91.0,
            fourchette_haute=105.0,
            marge_securite_composite=0.12,
            matrice_sensibilite=SensitivityMatrix(
                wacc_range=[0.07, 0.08, 0.09],
                growth_range=[0.02, 0.03, 0.04],
                values=[[85.0, 90.0, 95.0], [80.0, 85.0, 90.0], [75.0, 80.0, 85.0]],
            ),
            verdict="SOUS_EVALUE",
            verdict_detail="Test.",
            recommandation_prochaine_etape=[],
        )
        base.update(overrides)
        return StockValuationOutput(**base)

    def test_valuation_methodes_exactement_3(self):
        output = self._make_output()
        assert len(output.methodes) == 3

    def test_valuation_fourchette_ordre(self):
        output = self._make_output()
        assert output.fourchette_basse <= output.fourchette_centrale
        assert output.fourchette_centrale <= output.fourchette_haute

    def test_valuation_fourchette_incoherente_leve_erreur(self):
        with pytest.raises(ValidationError):
            self._make_output(fourchette_basse=100.0, fourchette_centrale=80.0)

    def test_valuation_matrice_coherente(self):
        output = self._make_output()
        m = output.matrice_sensibilite
        assert len(m.values) == len(m.wacc_range)
        for row in m.values:
            assert len(row) == len(m.growth_range)

    def test_valuation_verdict_valide(self):
        for v in {"SOUS_EVALUE", "JUSTE_VALEUR", "SUREVALUE"}:
            output = self._make_output(verdict=v)
            assert output.verdict == v

    def test_valuation_verdict_invalide_leve_erreur(self):
        with pytest.raises(ValidationError):
            self._make_output(verdict="INCONNU")

    def test_valuation_2_methodes_leve_erreur(self):
        with pytest.raises(ValidationError):
            self._make_output(methodes=_valuation_methodes()[:2])


# ---------------------------------------------------------------------------
# Thesis Builder
# ---------------------------------------------------------------------------

class TestThesisBuilderOutput:
    def _make_output(self, **overrides) -> ThesisBuilderOutput:
        base = dict(
            ticker="TEST",
            scenario_bull=ThesisScenario(probabilite=0.30, rendement_cible=0.40, hypotheses=["h1"]),
            scenario_base=ThesisScenario(probabilite=0.50, rendement_cible=0.15, hypotheses=["h2"]),
            scenario_bear=ThesisScenario(probabilite=0.20, rendement_cible=-0.20, hypotheses=["h3"]),
            kill_criteria=["kill 1", "kill 2"],
            devils_advocate="Argument contre.",
            position_size_pct=4.0,
            verdict_final="ACCUMULER",
            synthese_narrative="Thèse formelle de test.",
        )
        base.update(overrides)
        return ThesisBuilderOutput(**base)

    def test_thesis_probabilites_somme_1(self):
        output = self._make_output()
        total = (
            output.scenario_bull.probabilite
            + output.scenario_base.probabilite
            + output.scenario_bear.probabilite
        )
        assert abs(total - 1.0) <= 0.01

    def test_thesis_probabilites_ne_sommant_pas_1_leve_erreur(self):
        with pytest.raises(ValidationError):
            self._make_output(
                scenario_bull=ThesisScenario(probabilite=0.50, rendement_cible=0.40, hypotheses=["h"]),
                scenario_base=ThesisScenario(probabilite=0.50, rendement_cible=0.15, hypotheses=["h"]),
                scenario_bear=ThesisScenario(probabilite=0.20, rendement_cible=-0.20, hypotheses=["h"]),
            )

    def test_thesis_position_size_plage_0_10(self):
        for size in [0.0, 2.5, 5.0, 10.0]:
            output = self._make_output(position_size_pct=size)
            assert 0.0 <= output.position_size_pct <= 10.0

    def test_thesis_position_size_hors_plage_leve_erreur(self):
        with pytest.raises(ValidationError):
            self._make_output(position_size_pct=11.0)

    def test_thesis_verdict_valide(self):
        for v in {"ACHETER", "ACCUMULER", "CONSERVER", "VENDRE"}:
            output = self._make_output(verdict_final=v)
            assert output.verdict_final == v

    def test_thesis_verdict_invalide_leve_erreur(self):
        with pytest.raises(ValidationError):
            self._make_output(verdict_final="INCONNU")


# ---------------------------------------------------------------------------
# Munger Mental Models
# ---------------------------------------------------------------------------

class TestMungerOutput:
    def _make_output(self, **overrides) -> MungerOutput:
        base = dict(
            ticker="TEST",
            biais_detectes=[
                BiaisCognitif(
                    nom="Commitment Bias",
                    description="Trop attaché à la thèse initiale.",
                    impact_sur_these="MODERE",
                )
            ],
            inversion_analysis="Qu'est-ce qui ferait échouer la thèse ?",
            lollapalooza_risk=False,
            verdict_comportemental="BIAIS_DETECTE",
            verdict_detail="Un biais détecté, vigilance requise.",
            recommandation_prochaine_etape=[],
        )
        base.update(overrides)
        return MungerOutput(**base)

    def test_munger_biais_impact_valide(self):
        for impact in {"MINEUR", "MODERE", "MAJEUR"}:
            biais = BiaisCognitif(
                nom="Test", description="desc", impact_sur_these=impact
            )
            assert biais.impact_sur_these == impact

    def test_munger_biais_impact_invalide_leve_erreur(self):
        with pytest.raises(ValidationError):
            self._make_output(
                biais_detectes=[
                    BiaisCognitif(nom="Test", description="desc", impact_sur_these="CRITIQUE")
                ]
            )

    def test_munger_verdict_valide(self):
        for v in {"CONFIANCE_JUSTIFIEE", "BIAIS_DETECTE", "ALERTE_ROUGE"}:
            output = self._make_output(verdict_comportemental=v)
            assert output.verdict_comportemental == v

    def test_munger_verdict_invalide_leve_erreur(self):
        with pytest.raises(ValidationError):
            self._make_output(verdict_comportemental="INCONNU")


# ---------------------------------------------------------------------------
# Canadian Tax
# ---------------------------------------------------------------------------

class TestCanadianTaxSchemas:
    def _make_output(self, **overrides) -> CanadianTaxOutput:
        base = dict(
            ticker="TEST",
            compte_recommande="CELI",
            justification_fiscale="Action de croissance → CELI prioritaire.",
            impact_retenue_us=None,
            strategie_smith_manoeuvre=False,
            taux_inclusion_gain_capital=0.50,
            recommandation_prochaine_etape=[],
        )
        base.update(overrides)
        return CanadianTaxOutput(**base)

    def test_tax_compte_recommande_valide(self):
        for compte in {"CELI", "REER", "CELIAPP", "NON_ENREGISTRE"}:
            output = self._make_output(compte_recommande=compte)
            assert output.compte_recommande == compte

    def test_tax_compte_invalide_leve_erreur(self):
        with pytest.raises(ValidationError):
            self._make_output(compte_recommande="BROKERAGE")

    def test_tax_province_invalide_leve_erreur(self):
        with pytest.raises(ValidationError):
            CanadianTaxInput(
                ticker="TEST",
                position_size_pct=3.0,
                verdict_final="ACCUMULER",
                province="XX",
            )

    def test_tax_province_valide_acceptee(self):
        for province in {"QC", "ON", "BC", "AB"}:
            inp = CanadianTaxInput(
                ticker="TEST",
                position_size_pct=3.0,
                verdict_final="ACCUMULER",
                province=province,
            )
            assert inp.province == province

    def test_tax_taux_inclusion_fraction(self):
        output = self._make_output()
        assert 0 < output.taux_inclusion_gain_capital <= 1.0

    def test_tax_taux_inclusion_50_pct(self):
        output = self._make_output(taux_inclusion_gain_capital=0.50)
        assert output.taux_inclusion_gain_capital == 0.50


# ---------------------------------------------------------------------------
# Sprint 37 — Validateurs GrahamRatios (WARNING, jamais HTTP 422)
# ---------------------------------------------------------------------------

class TestGrahamRatiosValidateurs:
    """Les validateurs logguent un WARNING mais ne lèvent jamais de ValidationError."""

    def test_pe_negatif_loggue_warning_sans_erreur(self, caplog):
        import logging
        with caplog.at_level(logging.WARNING, logger="app.skills.tier2.graham_analysis.schemas"):
            ratios = GrahamRatios(
                pe=-5.0, pb=1.0, current_ratio=2.0, debt_equity=0.2,
                eps_growth_total=0.3, price=50.0, book_value=50.0,
            )
        assert ratios.pe == -5.0
        assert "P/E négatif" in caplog.text

    def test_pb_negatif_loggue_warning_sans_erreur(self, caplog):
        import logging
        with caplog.at_level(logging.WARNING, logger="app.skills.tier2.graham_analysis.schemas"):
            ratios = GrahamRatios(
                pe=10.0, pb=-0.5, current_ratio=1.5, debt_equity=0.3,
                eps_growth_total=0.2, price=50.0, book_value=-25.0,
            )
        assert ratios.pb == -0.5
        assert "P/B négatif" in caplog.text

    def test_eps_growth_suspect_loggue_warning_sans_erreur(self, caplog):
        import logging
        with caplog.at_level(logging.WARNING, logger="app.skills.tier2.graham_analysis.schemas"):
            ratios = GrahamRatios(
                pe=15.0, pb=2.0, current_ratio=2.0, debt_equity=0.2,
                eps_growth_total=6.5, price=100.0, book_value=50.0,
            )
        assert ratios.eps_growth_total == 6.5
        assert "eps_growth_total" in caplog.text

    def test_triangle_pe_incoherent_loggue_warning_sans_erreur(self, caplog):
        import logging
        with caplog.at_level(logging.WARNING, logger="app.skills.tier2.graham_analysis.schemas"):
            # pe=15.0, price/eps_ttm = 100/3 ≈ 33.3 → écart > 15 %
            ratios = GrahamRatios(
                pe=15.0, pb=1.5, current_ratio=2.0, debt_equity=0.2,
                eps_growth_total=0.3, price=100.0, book_value=66.0,
                eps_ttm=3.0,
            )
        assert ratios.pe == 15.0
        assert "incohérence P/E" in caplog.text

    def test_triangle_coherent_aucun_warning(self, caplog):
        import logging
        with caplog.at_level(logging.WARNING, logger="app.skills.tier2.graham_analysis.schemas"):
            # pe=10.0, price/eps_ttm = 100/10 = 10.0 → cohérent
            ratios = GrahamRatios(
                pe=10.0, pb=1.5, current_ratio=2.0, debt_equity=0.2,
                eps_growth_total=0.3, price=100.0, book_value=66.0,
                eps_ttm=10.0,
            )
        assert ratios.pe == 10.0
        assert "incohérence P/E" not in caplog.text

    def test_incoherence_ne_rejette_pas_la_requete(self):
        """Données aberrantes → WARNING uniquement, jamais de ValidationError."""
        ratios = GrahamRatios(
            pe=15.0, pb=1.5, current_ratio=2.0, debt_equity=0.2,
            eps_growth_total=10.0,  # 1000 % — très suspect
            price=100.0, book_value=66.0,
            eps_ttm=1.0,  # pe_calcule = 100.0 ≠ 15.0
        )
        assert ratios is not None  # aucune exception

    def test_ratios_normaux_aucun_warning(self, caplog):
        import logging
        with caplog.at_level(logging.WARNING, logger="app.skills.tier2.graham_analysis.schemas"):
            GrahamRatios(
                pe=12.0, pb=1.2, current_ratio=2.5, debt_equity=0.3,
                eps_growth_total=0.45, price=60.0, book_value=50.0,
                eps_ttm=5.0,  # 60/5 = 12.0 = pe → cohérent
            )
        assert caplog.text == ""


# ---------------------------------------------------------------------------
# Sprint 37 — confidence_score Graham
# ---------------------------------------------------------------------------

class TestGrahamConfidenceScore:
    def test_confidence_score_tous_criteres_evalues(self, graham_output_msft):
        """valeur_observee='test' sur 13 critères → confidence = 1.0."""
        assert graham_output_msft.confidence_score == 1.0

    def test_confidence_score_avec_donnees_manquantes(self):
        from tests.conftest import _make_criteria_defensif, _make_criteria_entreprenant
        criteria = _make_criteria_defensif()
        # Marquer 2 critères défensifs comme données manquantes
        criteria[0] = GrahamCriterion(
            numero=1, nom="Taille", passe=False,
            valeur_observee="DONNÉES_MANQUANTES", seuil="> 700 M$", commentaire="inconnu",
        )
        criteria[1] = GrahamCriterion(
            numero=2, nom="Solidité", passe=False,
            valeur_observee="DONNÉES_MANQUANTES", seuil="≥ 2.0", commentaire="inconnu",
        )
        output = GrahamAnalysisOutput(
            ticker="TEST", profil_applique="LES_DEUX",
            enterprising_score=0,
            criteria_defensif=criteria,
            criteria_entreprenant=_make_criteria_entreprenant(),
            drapeaux_rouges=[], verdict="REJETER",
            verdict_detail="Test.", recommandation_prochaine_etape=[],
        )
        # 6 défensifs "test" + 5 entrepreneuriaux "test" = 11/13
        assert output.confidence_score == round(11 / 13, 2)

    def test_confidence_score_plage_0_1(self, graham_output_msft):
        assert 0.0 <= graham_output_msft.confidence_score <= 1.0


# ---------------------------------------------------------------------------
# Sprint 37 — confidence_score Buffett
# ---------------------------------------------------------------------------

class TestBuffettConfidenceScore:
    def _make_output(self, **overrides) -> "BuffettQualityOutput":
        base = dict(
            ticker="TEST",
            filtres=_buffett_filtres([True, True, False, False]),
            owner_earnings=8.5,
            quality_score=2,
            verdict="QUALITE_CORRECTE",
            verdict_detail="Test.",
            drapeaux_rouges=[],
            recommandation_prochaine_etape=[],
        )
        base.update(overrides)
        from app.skills.tier2.buffett_quality.schemas import BuffettQualityOutput
        return BuffettQualityOutput(**base)

    def test_confidence_score_present(self):
        output = self._make_output()
        assert hasattr(output, "confidence_score")

    def test_confidence_score_default_zero(self):
        """Par défaut 0.0 — sera calculé par execute() en production."""
        output = self._make_output()
        assert output.confidence_score == 0.0

    def test_confidence_score_settable(self):
        output = self._make_output()
        output.confidence_score = 0.75
        assert output.confidence_score == 0.75

    def test_confidence_score_plage_0_1_apres_set(self):
        output = self._make_output()
        output.confidence_score = 0.89
        assert 0.0 <= output.confidence_score <= 1.0


# ---------------------------------------------------------------------------
# Sprint 37 — confidence_score EarningsQuality
# ---------------------------------------------------------------------------

class TestEarningsConfidenceScore:
    def _make_output(self, **overrides) -> EarningsQualityOutput:
        base = dict(
            ticker="TEST",
            is_financial=False,
            m_score=MScoreDetail(
                dsri=None, gmi=None, aqi=None, sgi=1.0, depi=None,
                sgai=None, tata=0.0, lvgi=None, m_score=-2.5,
                interpretation="sous_seuil",
            ),
            z_score=ZScoreDetail(variante="Z_original", z_score=3.0, interpretation="zone_sure"),
            f_score=FScoreDetail(
                criteria=_f_criteria([True] * 9), f_score=9, interpretation="fort"
            ),
            c_score=CScoreDetail(
                signaux=_c_signaux([False] * 6), c_score=0, interpretation="propre"
            ),
            sloan=SloanDetail(accrual_ratio=-0.02, interpretation="qualite_elevee"),
            drapeaux_rouges=[],
            verdict="AUCUN_SIGNAL",
            verdict_detail="Aucun signal.",
            recommandation_prochaine_etape=[],
        )
        base.update(overrides)
        return EarningsQualityOutput(**base)

    def test_confidence_score_tous_cadres_calculables(self):
        """m_score, z_score, sloan tous non-None → confidence = 1.0."""
        output = self._make_output()
        assert output.confidence_score == 1.0

    def test_confidence_score_mscore_manquant(self):
        """m_score=None, z_score, sloan présents → 4/5 = 0.8."""
        output = self._make_output(
            m_score=MScoreDetail(
                dsri=None, gmi=None, aqi=None, sgi=None, depi=None,
                sgai=None, tata=None, lvgi=None, m_score=None,
                interpretation="données_insuffisantes",
            )
        )
        assert output.confidence_score == round(4 / 5, 2)

    def test_confidence_score_deux_cadres_manquants(self):
        """m_score=None, sloan=None → 3/5 = 0.6."""
        output = self._make_output(
            m_score=MScoreDetail(
                dsri=None, gmi=None, aqi=None, sgi=None, depi=None,
                sgai=None, tata=None, lvgi=None, m_score=None,
                interpretation="données_insuffisantes",
            ),
            sloan=SloanDetail(accrual_ratio=None, interpretation="données_insuffisantes"),
        )
        assert output.confidence_score == round(3 / 5, 2)

    def test_confidence_score_plage_0_1(self):
        output = self._make_output()
        assert 0.0 <= output.confidence_score <= 1.0


# ---------------------------------------------------------------------------
# Sprint 37 — confidence_score Dorsey
# ---------------------------------------------------------------------------

class TestDorseyConfidenceScore:
    def _make_output(self, **overrides) -> "DorseyMoatOutput":
        base = dict(
            ticker="TEST",
            moat_type="NARROW",
            sources_identifiees=_moat_sources(),
            roic_durability="MODÉRÉE",
            verdict_detail="Test.",
            drapeaux_rouges=[],
            recommandation_prochaine_etape=[],
        )
        base.update(overrides)
        from app.skills.tier2.dorsey_moat.schemas import DorseyMoatOutput
        return DorseyMoatOutput(**base)

    def test_confidence_score_present(self):
        output = self._make_output()
        assert hasattr(output, "confidence_score")

    def test_confidence_score_default_zero(self):
        """Par défaut 0.0 — sera calculé par execute() en production."""
        output = self._make_output()
        assert output.confidence_score == 0.0

    def test_confidence_score_settable(self):
        output = self._make_output()
        output.confidence_score = 0.58
        assert output.confidence_score == 0.58

    def test_confidence_score_plage_0_1_apres_set(self):
        output = self._make_output()
        output.confidence_score = 0.42
        assert 0.0 <= output.confidence_score <= 1.0


# ---------------------------------------------------------------------------
# Sprint 37 — inter_skill_conflicts dans AnalyzeResponse
# ---------------------------------------------------------------------------

class TestInterSkillConflicts:
    def test_inter_skill_conflicts_field_present_par_defaut_vide(self):
        from app.orchestrator.core import AnalyzeResponse
        resp = AnalyzeResponse(
            analysis_id="test-id",
            ticker="TEST",
            workflow="value_graham",
            skills_applied=[],
            cost_usd=0.0,
            created_at="2026-01-01T00:00:00",
        )
        assert hasattr(resp, "inter_skill_conflicts")
        assert resp.inter_skill_conflicts == []

    def test_detect_conflict_graham_rejeter_buffett_compounder(self):
        from app.orchestrator.core import _detect_inter_skill_conflicts
        from app.skills.tier2.buffett_quality.schemas import BuffettFiltre, BuffettQualityOutput
        from tests.conftest import _make_criteria_defensif, _make_criteria_entreprenant

        # Graham REJETER : tous critères passe=False → defensive_score=0 → REJETER
        graham = GrahamAnalysisOutput(
            ticker="TEST", profil_applique="LES_DEUX",
            enterprising_score=0,
            criteria_defensif=_make_criteria_defensif(),
            criteria_entreprenant=_make_criteria_entreprenant(),
            drapeaux_rouges=[], verdict="REJETER",
            verdict_detail="Test.", recommandation_prochaine_etape=[],
        )
        assert graham.defensive_verdict == "REJETER"

        buffett = BuffettQualityOutput(
            ticker="TEST",
            filtres=[
                BuffettFiltre(filtre="compréhensible", passe=True, score=1, justification="OK"),
                BuffettFiltre(filtre="economics", passe=True, score=1, justification="OK"),
                BuffettFiltre(filtre="management", passe=True, score=1, justification="OK"),
                BuffettFiltre(filtre="prix", passe=True, score=1, justification="OK"),
            ],
            owner_earnings=8.5, quality_score=4, verdict="COMPOUNDER",
            verdict_detail="Compounder.", drapeaux_rouges=[],
            recommandation_prochaine_etape=[],
        )

        conflicts = _detect_inter_skill_conflicts(graham, buffett, None, None)
        assert len(conflicts) == 1
        assert "graham=REJETER" in conflicts[0]
        assert "buffett=COMPOUNDER" in conflicts[0]

    def test_detect_conflict_earnings_rejeter_buffett_compounder(self):
        from app.orchestrator.core import _detect_inter_skill_conflicts
        from app.skills.tier2.buffett_quality.schemas import BuffettFiltre, BuffettQualityOutput

        buffett = BuffettQualityOutput(
            ticker="TEST",
            filtres=[
                BuffettFiltre(filtre="compréhensible", passe=True, score=1, justification="OK"),
                BuffettFiltre(filtre="economics", passe=True, score=1, justification="OK"),
                BuffettFiltre(filtre="management", passe=True, score=1, justification="OK"),
                BuffettFiltre(filtre="prix", passe=True, score=1, justification="OK"),
            ],
            owner_earnings=8.5, quality_score=4, verdict="COMPOUNDER",
            verdict_detail="Compounder.", drapeaux_rouges=[],
            recommandation_prochaine_etape=[],
        )
        # earnings REJETER
        earnings = EarningsQualityOutput(
            ticker="TEST", is_financial=False,
            m_score=MScoreDetail(
                dsri=None, gmi=None, aqi=None, sgi=1.0, depi=None,
                sgai=None, tata=0.0, lvgi=None, m_score=-1.0,
                interpretation="manipulation_possible",
            ),
            z_score=ZScoreDetail(variante="Z_original", z_score=1.0, interpretation="zone_danger"),
            f_score=FScoreDetail(criteria=_f_criteria([False] * 9), f_score=0, interpretation="faible"),
            c_score=CScoreDetail(signaux=_c_signaux([True] * 6), c_score=6, interpretation="risque"),
            sloan=SloanDetail(accrual_ratio=0.15, interpretation="accruals_elevees"),
            drapeaux_rouges=["manipulation détectée"],
            verdict="REJETER",
            verdict_detail="Rejeter.",
            recommandation_prochaine_etape=[],
        )

        conflicts = _detect_inter_skill_conflicts(None, buffett, earnings, None)
        assert any("earnings_quality=REJETER" in c for c in conflicts)

    def test_aucun_conflict_si_verdicts_coherents(self):
        from app.orchestrator.core import _detect_inter_skill_conflicts
        # Pas de contradictions → liste vide
        conflicts = _detect_inter_skill_conflicts(None, None, None, None)
        assert conflicts == []

    def test_aucun_conflict_si_graham_none(self):
        from app.orchestrator.core import _detect_inter_skill_conflicts
        conflicts = _detect_inter_skill_conflicts(None, None, None, None)
        assert conflicts == []


# ---------------------------------------------------------------------------
# Sprint 139 — traçabilité source+date sur AnalyzeResponse
# ---------------------------------------------------------------------------

class TestAnalyzeResponseTracabilite:
    def test_tracabilite_absente_par_defaut_none(self):
        """ratios_fetched_at / ratios_source absents → None (rétrocompat analyses anciennes)."""
        from app.orchestrator.core import AnalyzeResponse
        resp = AnalyzeResponse(
            analysis_id="test-id",
            ticker="TEST",
            workflow="value_graham",
            skills_applied=[],
            cost_usd=0.0,
            created_at="2026-01-01T00:00:00",
        )
        assert resp.ratios_fetched_at is None
        assert resp.ratios_source is None

    def test_tracabilite_renseignee(self):
        from app.orchestrator.core import AnalyzeResponse
        resp = AnalyzeResponse(
            analysis_id="test-id",
            ticker="TEST",
            workflow="value_graham",
            skills_applied=[],
            cost_usd=0.0,
            created_at="2026-01-01T00:00:00",
            ratios_fetched_at="2026-05-30T12:00:00+00:00",
            ratios_source="Yahoo Finance",
        )
        assert resp.ratios_fetched_at == "2026-05-30T12:00:00+00:00"
        assert resp.ratios_source == "Yahoo Finance"


class TestRatiosTraceHelper:
    """Helper unifié _ratios_trace — identique pour les trois schémas ratios (Sprint 153)."""

    _HORODATAGE = datetime(2026, 5, 30, 12, 0, 0, tzinfo=timezone.utc)

    def test_ratios_none_retourne_none_none(self):
        from app.orchestrator.core import _ratios_trace
        assert _ratios_trace(None) == (None, None)

    def test_graham_extrait_date_iso_et_source(self):
        from app.orchestrator.core import _ratios_trace
        ratios = GrahamRatios(
            pe=11.0, pb=1.3, current_ratio=None, debt_equity=0.45,
            eps_growth_total=0.27, price=80.0, book_value=61.5,
            ratios_fetched_at=self._HORODATAGE, ratios_source="Yahoo Finance",
        )
        fetched, source = _ratios_trace(ratios)
        assert fetched is not None and fetched.startswith("2026-05-30T12:00:00")
        assert source == "Yahoo Finance"

    def test_graham_sans_horodatage_retourne_none_none(self):
        from app.orchestrator.core import _ratios_trace
        ratios = GrahamRatios(
            pe=11.0, pb=1.3, current_ratio=None, debt_equity=0.45,
            eps_growth_total=0.27, price=80.0, book_value=61.5,
        )
        assert _ratios_trace(ratios) == (None, None)

    def test_earnings_extrait_date_iso_et_source(self, ratios_earnings_msft):
        from app.orchestrator.core import _ratios_trace
        ratios = ratios_earnings_msft.model_copy(
            update={"ratios_fetched_at": self._HORODATAGE, "ratios_source": "Yahoo Finance"}
        )
        fetched, source = _ratios_trace(ratios)
        assert fetched is not None and fetched.startswith("2026-05-30T12:00:00")
        assert source == "Yahoo Finance"

    def test_earnings_sans_horodatage_retourne_none_none(self, ratios_earnings_msft):
        from app.orchestrator.core import _ratios_trace
        assert _ratios_trace(ratios_earnings_msft) == (None, None)

    def test_valuation_extrait_date_iso_et_source(self):
        from app.orchestrator.core import _ratios_trace
        ratios = ValuationRatios(
            pe=34.2, ratios_fetched_at=self._HORODATAGE, ratios_source="Yahoo Finance",
        )
        fetched, source = _ratios_trace(ratios)
        assert fetched is not None and fetched.startswith("2026-05-30T12:00:00")
        assert source == "Yahoo Finance"

    def test_valuation_sans_horodatage_retourne_none_none(self):
        from app.orchestrator.core import _ratios_trace
        assert _ratios_trace(ValuationRatios(pe=34.2)) == (None, None)

    def test_source_sans_date_conserve_la_source(self):
        """Honnêteté None : source présente sans date → (None, source) — jamais de date factice."""
        from app.orchestrator.core import _ratios_trace
        ratios = ValuationRatios(pe=34.2, ratios_source="Yahoo Finance")
        assert _ratios_trace(ratios) == (None, "Yahoo Finance")


class TestRequestRatiosTraces:
    """Helper partagé par les 4 points de construction d'AnalyzeResponse (sync, stream, caches)."""

    def test_requete_sans_ratios_donne_tous_champs_none(self):
        from app.orchestrator.core import AnalyzeRequest, _request_ratios_traces

        traces = _request_ratios_traces(AnalyzeRequest(ticker="MSFT"))
        assert traces == {
            "ratios_fetched_at": None,
            "ratios_source": None,
            "earnings_ratios_fetched_at": None,
            "earnings_ratios_source": None,
            "valuation_ratios_fetched_at": None,
            "valuation_ratios_source": None,
            "ratios_provenance": None,
        }

    def test_provenance_graham_threadee_dans_la_reponse(self):
        """La provenance par ratio Graham (repli yfinance) est threadée jusqu'à AnalyzeResponse (Sprint 150)."""
        from app.orchestrator.core import AnalyzeRequest, _request_ratios_traces

        graham = GrahamRatios(
            pe=11.0, pb=1.3, current_ratio=None, debt_equity=0.45,
            eps_growth_total=0.27, price=80.0, book_value=61.5,
            ratios_provenance={"pb": "priceToBook", "debt_equity": "totalDebt"},
        )
        traces = _request_ratios_traces(AnalyzeRequest(ticker="MSFT", ratios=graham))
        assert traces["ratios_provenance"] == {"pb": "priceToBook", "debt_equity": "totalDebt"}

    def test_trois_skills_horodates_remplissent_les_six_champs(self, ratios_earnings_msft):
        from datetime import datetime, timezone

        from app.orchestrator.core import AnalyzeRequest, _request_ratios_traces

        graham = GrahamRatios(
            pe=11.0, pb=1.3, current_ratio=None, debt_equity=0.45,
            eps_growth_total=0.27, price=80.0, book_value=61.5,
            ratios_fetched_at=datetime(2026, 5, 20, 9, 0, 0, tzinfo=timezone.utc),
            ratios_source="Yahoo Finance",
        )
        earnings = ratios_earnings_msft.model_copy(
            update={
                "ratios_fetched_at": datetime(2026, 5, 21, 9, 0, 0, tzinfo=timezone.utc),
                "ratios_source": "Yahoo Finance",
            }
        )
        valuation = ValuationRatios(
            pe=34.2,
            ratios_fetched_at=datetime(2026, 5, 22, 9, 0, 0, tzinfo=timezone.utc),
            ratios_source="Yahoo Finance",
        )
        traces = _request_ratios_traces(
            AnalyzeRequest(
                ticker="MSFT", ratios=graham, earnings_ratios=earnings, valuation_ratios=valuation
            )
        )
        assert traces["ratios_fetched_at"].startswith("2026-05-20")
        assert traces["earnings_ratios_fetched_at"].startswith("2026-05-21")
        assert traces["valuation_ratios_fetched_at"].startswith("2026-05-22")
        assert (
            traces["ratios_source"]
            == traces["earnings_ratios_source"]
            == traces["valuation_ratios_source"]
            == "Yahoo Finance"
        )

    def test_source_presente_sans_date_donne_date_none_source_conservee(self):
        from app.orchestrator.core import AnalyzeRequest, _request_ratios_traces

        graham = GrahamRatios(
            pe=11.0, pb=1.3, current_ratio=None, debt_equity=0.45,
            eps_growth_total=0.27, price=80.0, book_value=61.5,
            ratios_source="Yahoo Finance",
        )
        traces = _request_ratios_traces(AnalyzeRequest(ticker="MSFT", ratios=graham))
        assert traces["ratios_fetched_at"] is None
        assert traces["ratios_source"] == "Yahoo Finance"
