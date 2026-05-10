"""Tests du skill investment_thesis_builder — schemas, skill, orchestrateur."""
from __future__ import annotations

import json
import uuid
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest
from pydantic import ValidationError

from app.orchestrator.core import AnalyzeRequest, AnalyzeResponse, Orchestrator
from app.skills.base import UsageDetail
from app.skills.tier2.buffett_quality.schemas import (
    BuffettFiltre,
    BuffettQualityOutput,
    BuffettRatios,
)
from app.skills.tier2.dorsey_moat.schemas import (
    DorseyMoatOutput,
    DorseyRatios,
    MoatSource,
)
from app.skills.tier2.stock_valuation.schemas import (
    SensitivityMatrix,
    StockValuationOutput,
    ValuationMethod,
    ValuationRatios,
)
from app.skills.tier2.thesis_builder.schemas import (
    AllSkillContexts,
    ThesisBuilderInput,
    ThesisBuilderOutput,
    ThesisScenario,
)
from app.skills.tier2.thesis_builder.skill import ThesisBuilderSkill


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_scenario(probabilite: float, rendement: float) -> ThesisScenario:
    return ThesisScenario(
        probabilite=probabilite,
        rendement_cible=rendement,
        hypotheses=["Hypothèse test 1", "Hypothèse test 2"],
    )


def _make_thesis_output_dict(
    ticker: str = "BNS",
    bull_prob: float = 0.25,
    base_prob: float = 0.50,
    bear_prob: float = 0.25,
    verdict: str = "ACCUMULER",
    position_size: float = 5.0,
) -> dict:
    return {
        "ticker": ticker,
        "scenario_bull": {
            "probabilite": bull_prob,
            "rendement_cible": 0.80,
            "hypotheses": ["Expansion du moat", "Croissance des revenus au-dessus du consensus"],
        },
        "scenario_base": {
            "probabilite": base_prob,
            "rendement_cible": 0.30,
            "hypotheses": ["Croissance stable des BPA", "Multiple stable à 11×"],
        },
        "scenario_bear": {
            "probabilite": bear_prob,
            "rendement_cible": -0.25,
            "hypotheses": ["Compression des marges", "Pression concurrentielle accrue"],
        },
        "kill_criteria": [
            "ROIC < 12 % pendant 2 années consécutives",
            "Ratio dette nette / EBITDA > 3.0×",
            "Changement de CEO non planifié",
        ],
        "devils_advocate": (
            "Les banques canadiennes font face à une exposition croissante au marché "
            "immobilier résidentiel surévalué ; un choc hypothécaire pourrait éroder "
            "significativement la qualité des actifs et forcer une dilution du capital."
        ),
        "position_size_pct": position_size,
        "verdict_final": verdict,
        "synthese_narrative": (
            "BNS présente un profil d'investissement solide selon l'analyse Graham.\n\n"
            "Le moat de la banque repose sur des switching costs élevés et un réseau "
            "d'agences établi au Canada et en Amérique latine.\n\n"
            "La valorisation actuelle offre une marge de sécurité raisonnable par rapport "
            "à la valeur intrinsèque calculée."
        ),
    }


def _make_usage() -> UsageDetail:
    return UsageDetail(
        tokens_input=900,
        tokens_output=600,
        tokens_cache_read=1800,
        tokens_cache_creation=0,
        cost_usd=0.0072,
        model="claude-sonnet-4-6",
    )


def _make_5_moat_sources() -> list[MoatSource]:
    noms = ["intangibles", "switching_costs", "network_effects", "cost_advantages", "efficient_scale"]
    return [
        MoatSource(source=n, present=(i < 2), intensite="MODÉRÉE" if i < 2 else "ABSENTE", justification="test")
        for i, n in enumerate(noms)
    ]


def _make_4_buffett_filtres() -> list[BuffettFiltre]:
    noms = ["comprehensible", "economics_favorables", "management_fiable", "prix_attractif"]
    return [
        BuffettFiltre(filtre=n, passe=(i < 2), score=1 if i < 2 else 0, justification="test")
        for i, n in enumerate(noms)
    ]


def _make_valuation_output(ticker: str = "BNS") -> StockValuationOutput:
    return StockValuationOutput(
        ticker=ticker,
        methodes=[
            ValuationMethod(methode="dcf", valeur=92.0, hypotheses="WACC 8%, g 2%"),
            ValuationMethod(methode="comparables", valeur=88.0, hypotheses="P/E peers 12×"),
            ValuationMethod(methode="sectoriel", valeur=90.0, hypotheses="P/B banques canadiennes"),
        ],
        fourchette_basse=85.0,
        fourchette_centrale=90.0,
        fourchette_haute=96.0,
        marge_securite_composite=0.11,
        matrice_sensibilite=SensitivityMatrix(
            wacc_range=[0.07, 0.08, 0.09],
            growth_range=[0.01, 0.02, 0.03],
            values=[[95.0, 90.0, 85.0], [88.0, 84.0, 80.0], [82.0, 78.0, 74.0]],
        ),
        verdict="SOUS_EVALUE",
        verdict_detail="BNS sous-évalué selon les 3 méthodes.",
        recommandation_prochaine_etape=["investment_thesis_builder"],
    )


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def thesis_output_bns() -> ThesisBuilderOutput:
    """ThesisBuilderOutput valide pour BNS — ACCUMULER."""
    data = _make_thesis_output_dict()
    return ThesisBuilderOutput.model_validate(data)


@pytest.fixture
def dorsey_output_bns() -> DorseyMoatOutput:
    return DorseyMoatOutput(
        ticker="BNS",
        moat_type="NARROW",
        sources_identifiees=_make_5_moat_sources(),
        roic_durability="FORTE",
        verdict_detail="BNS moat NARROW — switching costs et intangibles modérés.",
        drapeaux_rouges=[],
        recommandation_prochaine_etape=["buffett_quality"],
    )


@pytest.fixture
def buffett_output_bns() -> BuffettQualityOutput:
    return BuffettQualityOutput(
        ticker="BNS",
        filtres=_make_4_buffett_filtres(),
        owner_earnings=8.50,
        quality_score=2,
        verdict="QUALITE_CORRECTE",
        verdict_detail="BNS passe 2/4 filtres Buffett.",
        drapeaux_rouges=[],
        recommandation_prochaine_etape=["stock_valuation_triangulation"],
    )


@pytest.fixture
def valuation_output_bns() -> StockValuationOutput:
    return _make_valuation_output("BNS")


@pytest.fixture
def ratios_dorsey_bns() -> DorseyRatios:
    return DorseyRatios(roic=0.16, roic_5y_avg=0.15, gross_margin=0.55, revenue_bn=38.0)


@pytest.fixture
def ratios_buffett_bns() -> BuffettRatios:
    return BuffettRatios(roe=0.15, roic=0.16, eps_ttm=7.25, revenue_bn=38.0, pe=11.0, price=80.0)


@pytest.fixture
def ratios_valuation_bns() -> ValuationRatios:
    return ValuationRatios(price=80.0, eps_ttm=7.25, pe=11.0, pb=1.3, revenue_bn=38.0)


# ---------------------------------------------------------------------------
# Tests schémas
# ---------------------------------------------------------------------------


class TestThesisSchemas:
    def test_thesis_scenarios_probabilites_somme_100(self):
        """bull=0.30, base=0.50, bear=0.20 → validation OK (total = 1.0)."""
        data = _make_thesis_output_dict(bull_prob=0.30, base_prob=0.50, bear_prob=0.20)
        out = ThesisBuilderOutput.model_validate(data)
        total = (
            out.scenario_bull.probabilite
            + out.scenario_base.probabilite
            + out.scenario_bear.probabilite
        )
        assert abs(total - 1.0) < 0.001

    def test_thesis_scenarios_probabilites_ne_somment_pas_100_erreur(self):
        """bull=0.40, base=0.50, bear=0.20 → ValidationError (total = 1.10)."""
        data = _make_thesis_output_dict(bull_prob=0.40, base_prob=0.50, bear_prob=0.20)
        with pytest.raises(ValidationError, match="sommer à 1.0"):
            ThesisBuilderOutput.model_validate(data)

    def test_thesis_position_size_range_valide(self):
        """position_size_pct=5.0 → OK."""
        data = _make_thesis_output_dict(position_size=5.0)
        out = ThesisBuilderOutput.model_validate(data)
        assert out.position_size_pct == pytest.approx(5.0)

    def test_thesis_position_size_zero_valide(self):
        """position_size_pct=0.0 → OK (pas de position)."""
        data = _make_thesis_output_dict(position_size=0.0)
        out = ThesisBuilderOutput.model_validate(data)
        assert out.position_size_pct == pytest.approx(0.0)

    def test_thesis_position_size_max_valide(self):
        """position_size_pct=10.0 → OK (maximum autorisé)."""
        data = _make_thesis_output_dict(position_size=10.0)
        out = ThesisBuilderOutput.model_validate(data)
        assert out.position_size_pct == pytest.approx(10.0)

    def test_thesis_position_size_depasse_max_erreur(self):
        """position_size_pct=10.1 → ValidationError."""
        data = _make_thesis_output_dict(position_size=10.1)
        with pytest.raises(ValidationError):
            ThesisBuilderOutput.model_validate(data)

    def test_thesis_position_size_negatif_erreur(self):
        """position_size_pct=-1.0 → ValidationError."""
        data = _make_thesis_output_dict(position_size=-1.0)
        with pytest.raises(ValidationError):
            ThesisBuilderOutput.model_validate(data)

    def test_thesis_kill_criteria_liste_vide_accepte(self):
        """kill_criteria = [] → pas d'erreur Pydantic (liste vide autorisée)."""
        data = _make_thesis_output_dict()
        data["kill_criteria"] = []
        out = ThesisBuilderOutput.model_validate(data)
        assert out.kill_criteria == []

    def test_thesis_verdict_invalide_erreur(self):
        """verdict_final = "PEUT-ETRE" → ValidationError."""
        data = _make_thesis_output_dict(verdict="PEUT-ETRE")
        with pytest.raises(ValidationError, match="verdict_final invalide"):
            ThesisBuilderOutput.model_validate(data)

    def test_thesis_verdict_acheter_valide(self):
        data = _make_thesis_output_dict(verdict="ACHETER")
        out = ThesisBuilderOutput.model_validate(data)
        assert out.verdict_final == "ACHETER"

    def test_thesis_verdict_conserver_valide(self):
        data = _make_thesis_output_dict(verdict="CONSERVER")
        out = ThesisBuilderOutput.model_validate(data)
        assert out.verdict_final == "CONSERVER"

    def test_thesis_verdict_vendre_valide(self):
        data = _make_thesis_output_dict(verdict="VENDRE")
        out = ThesisBuilderOutput.model_validate(data)
        assert out.verdict_final == "VENDRE"

    def test_thesis_output_valide_complet(self, thesis_output_bns: ThesisBuilderOutput):
        """Créer un ThesisBuilderOutput valide avec tous les champs → pas d'erreur."""
        assert thesis_output_bns.ticker == "BNS"
        assert thesis_output_bns.verdict_final == "ACCUMULER"
        assert thesis_output_bns.position_size_pct == pytest.approx(5.0)
        assert len(thesis_output_bns.kill_criteria) == 3
        assert thesis_output_bns.devils_advocate != ""
        assert thesis_output_bns.synthese_narrative != ""

    def test_thesis_citations_defaut_vide(self, thesis_output_bns: ThesisBuilderOutput):
        assert thesis_output_bns.citations == []

    def test_thesis_cost_usd_defaut_zero(self, thesis_output_bns: ThesisBuilderOutput):
        assert thesis_output_bns.cost_usd == pytest.approx(0.0)

    def test_thesis_scenario_bear_rendement_negatif_valide(self):
        """rendement_cible négatif pour bear est un cas réel et doit être accepté."""
        s = ThesisScenario(probabilite=0.25, rendement_cible=-0.40, hypotheses=["test"])
        assert s.rendement_cible == pytest.approx(-0.40)

    def test_thesis_scenario_probabilite_hors_plage_erreur(self):
        """probabilite > 1.0 → ValidationError sur ThesisScenario."""
        with pytest.raises(ValidationError):
            ThesisScenario(probabilite=1.1, rendement_cible=0.5, hypotheses=["test"])

    def test_all_skill_contexts_tous_none_valide(self):
        """AllSkillContexts entièrement vide est valide."""
        ctx = AllSkillContexts()
        assert ctx.graham is None
        assert ctx.earnings_quality is None
        assert ctx.dorsey is None
        assert ctx.buffett is None
        assert ctx.valuation is None

    def test_thesis_builder_input_valide(self):
        inp = ThesisBuilderInput(ticker="BNS", all_contexts=AllSkillContexts())
        assert inp.ticker == "BNS"

    def test_thesis_probabilite_tolerance_01(self):
        """Tolérance de 0.01 : bull=0.25, base=0.50, bear=0.256 → total=1.006 → OK."""
        data = _make_thesis_output_dict(bull_prob=0.25, base_prob=0.50, bear_prob=0.256)
        out = ThesisBuilderOutput.model_validate(data)
        assert out is not None

    def test_thesis_probabilite_depasse_tolerance_erreur(self):
        """bull=0.25, base=0.50, bear=0.27 → total=1.02 > tolérance 0.01 → ValidationError."""
        data = _make_thesis_output_dict(bull_prob=0.25, base_prob=0.50, bear_prob=0.27)
        with pytest.raises(ValidationError, match="sommer à 1.0"):
            ThesisBuilderOutput.model_validate(data)


# ---------------------------------------------------------------------------
# Tests skill
# ---------------------------------------------------------------------------


class TestThesisBuilderSkill:
    @pytest.fixture
    def skill(self) -> ThesisBuilderSkill:
        return ThesisBuilderSkill(client=MagicMock(), model="claude-sonnet-4-6")

    def test_skill_id(self, skill: ThesisBuilderSkill):
        assert skill.skill_id == "investment_thesis_builder"

    def test_tier(self, skill: ThesisBuilderSkill):
        assert skill.tier == 2

    def test_system_prompt_charge_et_cache(self, skill: ThesisBuilderSkill):
        blocks = skill.get_system_prompt()
        assert blocks[0]["cache_control"]["type"] == "ephemeral"
        assert len(blocks[0]["text"]) > 1024

    def test_system_prompt_contient_kill_criteria(self, skill: ThesisBuilderSkill):
        text = skill.get_system_prompt()[0]["text"]
        assert "kill" in text.lower() or "Kill" in text

    def test_system_prompt_contient_verdicts(self, skill: ThesisBuilderSkill):
        text = skill.get_system_prompt()[0]["text"]
        assert "ACHETER" in text
        assert "ACCUMULER" in text
        assert "CONSERVER" in text
        assert "VENDRE" in text

    def test_system_prompt_contient_probabilite_contrainte(self, skill: ThesisBuilderSkill):
        text = skill.get_system_prompt()[0]["text"]
        assert "1.0" in text

    def test_build_user_message_contient_ticker(self, skill: ThesisBuilderSkill):
        """_build_user_message(input) → message contient le ticker."""
        inp = ThesisBuilderInput(ticker="BNS", all_contexts=AllSkillContexts())
        msg = skill._build_user_message(inp, citations=[])
        assert "BNS" in msg

    def test_build_user_message_contient_graham_verdict(
        self,
        skill: ThesisBuilderSkill,
        graham_output_msft,
    ):
        """all_contexts.graham présent → message contient le verdict Graham."""
        ctx = AllSkillContexts(graham=graham_output_msft)
        inp = ThesisBuilderInput(ticker="MSFT", all_contexts=ctx)
        msg = skill._build_user_message(inp, citations=[])
        assert "graham_analysis" in msg
        assert graham_output_msft.verdict in msg

    def test_build_user_message_sans_contexte(self, skill: ThesisBuilderSkill):
        """Sans aucun contexte, le message contient quand même le ticker et la demande JSON."""
        inp = ThesisBuilderInput(ticker="TEST", all_contexts=AllSkillContexts())
        msg = skill._build_user_message(inp, citations=[])
        assert "TEST" in msg
        assert "JSON" in msg or "json" in msg

    def test_build_user_message_avec_dorsey(
        self,
        skill: ThesisBuilderSkill,
        dorsey_output_bns: DorseyMoatOutput,
    ):
        """Avec dorsey context → message mentionne le moat type."""
        ctx = AllSkillContexts(dorsey=dorsey_output_bns)
        inp = ThesisBuilderInput(ticker="BNS", all_contexts=ctx)
        msg = skill._build_user_message(inp, citations=[])
        assert "dorsey_moat" in msg
        assert dorsey_output_bns.moat_type in msg

    def test_build_user_message_avec_buffett(
        self,
        skill: ThesisBuilderSkill,
        buffett_output_bns: BuffettQualityOutput,
    ):
        """Avec buffett context → message mentionne le verdict Buffett."""
        ctx = AllSkillContexts(buffett=buffett_output_bns)
        inp = ThesisBuilderInput(ticker="BNS", all_contexts=ctx)
        msg = skill._build_user_message(inp, citations=[])
        assert "buffett_quality" in msg
        assert buffett_output_bns.verdict in msg

    def test_build_user_message_avec_valuation(
        self,
        skill: ThesisBuilderSkill,
        valuation_output_bns: StockValuationOutput,
    ):
        """Avec valuation context → message mentionne la fourchette centrale."""
        ctx = AllSkillContexts(valuation=valuation_output_bns)
        inp = ThesisBuilderInput(ticker="BNS", all_contexts=ctx)
        msg = skill._build_user_message(inp, citations=[])
        assert "stock_valuation_triangulation" in msg
        assert str(valuation_output_bns.fourchette_centrale) in msg

    @pytest.mark.asyncio
    async def test_get_citations_rag_absent(self):
        """ThesisBuilderSkill instancié avec rag_service=None → get_citations() retourne []."""
        skill = ThesisBuilderSkill(
            client=MagicMock(), model="claude-sonnet-4-6", rag_service=None
        )
        citations = await skill.get_citations("test query")
        assert citations == []

    @pytest.mark.asyncio
    async def test_execute_mock_claude(
        self,
        thesis_output_bns: ThesisBuilderOutput,
        graham_output_msft,
    ):
        """execute() retourne (ThesisBuilderOutput, UsageDetail) avec cost_usd > 0."""
        mock_response = MagicMock()
        mock_response.content = [MagicMock(text=thesis_output_bns.model_dump_json())]
        mock_response.usage = SimpleNamespace(
            input_tokens=900,
            output_tokens=600,
            cache_read_input_tokens=1800,
            cache_creation_input_tokens=0,
        )
        mock_client = MagicMock()
        mock_client.messages = AsyncMock()
        mock_client.messages.create.return_value = mock_response

        skill = ThesisBuilderSkill(client=mock_client, model="claude-sonnet-4-6")
        ctx = AllSkillContexts(graham=graham_output_msft)
        inp = ThesisBuilderInput(ticker="BNS", all_contexts=ctx)
        output, usage = await skill.execute(inp)

        assert isinstance(output, ThesisBuilderOutput)
        assert isinstance(usage, UsageDetail)
        assert usage.cost_usd > 0
        assert output.cost_usd == usage.cost_usd

    @pytest.mark.asyncio
    async def test_execute_cost_usd_injecte_dans_output(
        self,
        thesis_output_bns: ThesisBuilderOutput,
    ):
        """output.cost_usd reflète exactement le coût calculé depuis usage."""
        mock_response = MagicMock()
        mock_response.content = [MagicMock(text=thesis_output_bns.model_dump_json())]
        mock_response.usage = SimpleNamespace(
            input_tokens=900,
            output_tokens=600,
            cache_read_input_tokens=0,
            cache_creation_input_tokens=2000,
        )
        mock_client = MagicMock()
        mock_client.messages = AsyncMock()
        mock_client.messages.create.return_value = mock_response

        skill = ThesisBuilderSkill(client=mock_client, model="claude-sonnet-4-6")
        inp = ThesisBuilderInput(ticker="BNS", all_contexts=AllSkillContexts())
        output, usage = await skill.execute(inp)

        assert output.cost_usd == pytest.approx(usage.cost_usd)

    @pytest.mark.asyncio
    async def test_execute_retourne_tuple_output_usage(
        self,
        thesis_output_bns: ThesisBuilderOutput,
    ):
        """execute() retourne bien un tuple (ThesisBuilderOutput, UsageDetail)."""
        mock_response = MagicMock()
        mock_response.content = [MagicMock(text=thesis_output_bns.model_dump_json())]
        mock_response.usage = SimpleNamespace(
            input_tokens=500,
            output_tokens=400,
            cache_read_input_tokens=1500,
            cache_creation_input_tokens=0,
        )
        mock_client = MagicMock()
        mock_client.messages = AsyncMock()
        mock_client.messages.create.return_value = mock_response

        skill = ThesisBuilderSkill(client=mock_client, model="claude-sonnet-4-6")
        inp = ThesisBuilderInput(ticker="TEST", all_contexts=AllSkillContexts())
        result = await skill.execute(inp)

        assert len(result) == 2
        assert isinstance(result[0], ThesisBuilderOutput)
        assert isinstance(result[1], UsageDetail)


# ---------------------------------------------------------------------------
# Tests intégration orchestrateur
# ---------------------------------------------------------------------------


class TestOrchestratorThesis:
    @pytest.fixture
    def mock_db_pool(self):
        pool = AsyncMock()
        pool.fetchrow.return_value = {
            "id": uuid.UUID("550e8400-e29b-41d4-a716-446655440000")
        }
        return pool

    @pytest.fixture
    def mock_graham_skill(self, graham_output_msft):
        skill = AsyncMock()
        skill.execute.return_value = (graham_output_msft, _make_usage())
        return skill

    @pytest.fixture
    def mock_earnings_skill(self, earnings_output_msft):
        skill = AsyncMock()
        skill.execute.return_value = (earnings_output_msft, _make_usage())
        return skill

    @pytest.fixture
    def mock_thesis_skill(self, thesis_output_bns):
        skill = AsyncMock(spec=ThesisBuilderSkill)
        skill.execute.return_value = (thesis_output_bns, _make_usage())
        return skill

    @pytest.mark.asyncio
    async def test_orchestrator_avec_thesis(
        self,
        mock_db_pool,
        mock_graham_skill,
        mock_earnings_skill,
        mock_thesis_skill,
        ratios_msft,
    ):
        """thesis_ratios=True + skill disponible → thesis présent dans response,
        skills_applied contient 'investment_thesis_builder'."""
        orchestrator = Orchestrator(
            db_pool=mock_db_pool,
            graham_skill=mock_graham_skill,
            earnings_skill=mock_earnings_skill,
            thesis_skill=mock_thesis_skill,
        )
        req = AnalyzeRequest(
            ticker="BNS",
            ratios=ratios_msft,
            thesis_ratios=True,
        )
        response = await orchestrator.run_company_analysis(req)

        assert response.thesis is not None
        assert "investment_thesis_builder" in response.skills_applied
        mock_thesis_skill.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_orchestrator_sans_thesis(
        self,
        mock_db_pool,
        mock_graham_skill,
        mock_earnings_skill,
        mock_thesis_skill,
        ratios_msft,
    ):
        """thesis_ratios=False (défaut) → thesis = None dans response, skill non appelé."""
        orchestrator = Orchestrator(
            db_pool=mock_db_pool,
            graham_skill=mock_graham_skill,
            earnings_skill=mock_earnings_skill,
            thesis_skill=mock_thesis_skill,
        )
        req = AnalyzeRequest(
            ticker="MSFT",
            ratios=ratios_msft,
        )
        response = await orchestrator.run_company_analysis(req)

        assert response.thesis is None
        assert "investment_thesis_builder" not in response.skills_applied
        mock_thesis_skill.execute.assert_not_called()

    @pytest.mark.asyncio
    async def test_thesis_skill_absent_pas_erreur(
        self,
        mock_db_pool,
        mock_graham_skill,
        mock_earnings_skill,
        ratios_msft,
    ):
        """thesis_ratios=True mais thesis_skill=None → thesis = None, pas d'erreur levée."""
        orchestrator = Orchestrator(
            db_pool=mock_db_pool,
            graham_skill=mock_graham_skill,
            earnings_skill=mock_earnings_skill,
            thesis_skill=None,
        )
        req = AnalyzeRequest(
            ticker="BNS",
            ratios=ratios_msft,
            thesis_ratios=True,
        )
        response = await orchestrator.run_company_analysis(req)

        assert response.thesis is None
        assert "investment_thesis_builder" not in response.skills_applied

    @pytest.mark.asyncio
    async def test_orchestrator_thesis_recoit_graham_context(
        self,
        mock_db_pool,
        graham_output_msft,
        earnings_output_msft,
        thesis_output_bns,
        ratios_msft,
    ):
        """L'orchestrateur passe graham_output dans AllSkillContexts du thesis_builder."""
        mock_graham = AsyncMock()
        mock_graham.execute.return_value = (graham_output_msft, _make_usage())
        mock_earnings = AsyncMock()
        mock_earnings.execute.return_value = (earnings_output_msft, _make_usage())
        mock_thesis = AsyncMock(spec=ThesisBuilderSkill)
        mock_thesis.execute.return_value = (thesis_output_bns, _make_usage())

        orchestrator = Orchestrator(
            db_pool=mock_db_pool,
            graham_skill=mock_graham,
            earnings_skill=mock_earnings,
            thesis_skill=mock_thesis,
        )
        req = AnalyzeRequest(
            ticker="BNS",
            ratios=ratios_msft,
            thesis_ratios=True,
        )
        await orchestrator.run_company_analysis(req)

        call_args = mock_thesis.execute.call_args
        thesis_input: ThesisBuilderInput = call_args.args[0]
        assert thesis_input.all_contexts.graham is not None
        assert thesis_input.all_contexts.graham.verdict == graham_output_msft.verdict

    @pytest.mark.asyncio
    async def test_cost_usd_inclut_thesis(
        self,
        mock_db_pool,
        graham_output_msft,
        thesis_output_bns,
        ratios_msft,
    ):
        """cost_usd total inclut le coût du thesis_builder quand activé."""
        u_graham = UsageDetail(
            tokens_input=500, tokens_output=200,
            tokens_cache_read=0, tokens_cache_creation=1500,
            cost_usd=0.003, model="claude-sonnet-4-6",
        )
        u_thesis = UsageDetail(
            tokens_input=900, tokens_output=600,
            tokens_cache_read=1800, tokens_cache_creation=0,
            cost_usd=0.0072, model="claude-sonnet-4-6",
        )
        mock_graham = AsyncMock()
        mock_graham.execute.return_value = (graham_output_msft, u_graham)
        mock_earnings = AsyncMock()
        mock_thesis = AsyncMock(spec=ThesisBuilderSkill)
        mock_thesis.execute.return_value = (thesis_output_bns, u_thesis)

        orchestrator = Orchestrator(
            db_pool=mock_db_pool,
            graham_skill=mock_graham,
            earnings_skill=mock_earnings,
            thesis_skill=mock_thesis,
        )
        req = AnalyzeRequest(
            ticker="BNS",
            ratios=ratios_msft,
            thesis_ratios=True,
        )
        response = await orchestrator.run_company_analysis(req)

        assert abs(response.cost_usd - (0.003 + 0.0072)) < 1e-9

    @pytest.mark.asyncio
    async def test_analyze_request_thesis_ratios_defaut_false(self, ratios_msft):
        """thesis_ratios est False par défaut dans AnalyzeRequest."""
        req = AnalyzeRequest(ticker="BNS", ratios=ratios_msft)
        assert req.thesis_ratios is False

    @pytest.mark.asyncio
    async def test_analyze_response_thesis_defaut_none(self, graham_output_msft):
        """thesis est None par défaut dans AnalyzeResponse."""
        resp = AnalyzeResponse(
            analysis_id="123",
            ticker="BNS",
            workflow="company_analysis",
            skills_applied=["graham_analysis"],
            graham=graham_output_msft,
            cost_usd=0.003,
            created_at="2026-05-08T10:00:00+00:00",
        )
        assert resp.thesis is None
