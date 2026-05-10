"""Tests du skill dorsey_moat — schemas, skill, context enrichment, orchestrateur."""
from __future__ import annotations

import uuid
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest
from pydantic import ValidationError

from app.orchestrator.core import AnalyzeRequest, AnalyzeResponse, Orchestrator
from app.skills.base import UsageDetail
from app.skills.tier2.dorsey_moat.schemas import (
    DorseyMoatInput,
    DorseyMoatOutput,
    DorseyRatios,
    EarningsContext,
    MoatSource,
)
from app.skills.tier2.dorsey_moat.skill import DorseyMoatSkill


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_5_sources(
    intensites: list[str] | None = None,
) -> list[MoatSource]:
    """Génère exactement 5 MoatSource pour les tests."""
    sources_names = [
        "intangibles",
        "switching_costs",
        "network_effects",
        "cost_advantages",
        "efficient_scale",
    ]
    if intensites is None:
        intensites = ["ABSENTE"] * 5
    return [
        MoatSource(
            source=sources_names[i],
            present=(intensites[i] not in {"ABSENTE", "FAIBLE"}),
            intensite=intensites[i],
            justification=f"Justification test pour {sources_names[i]}",
        )
        for i in range(5)
    ]


def _make_usage() -> UsageDetail:
    return UsageDetail(
        tokens_input=800,
        tokens_output=400,
        tokens_cache_read=1200,
        tokens_cache_creation=0,
        cost_usd=0.0058,
        model="claude-sonnet-4-6",
    )


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def ratios_dorsey_bns() -> DorseyRatios:
    """Ratios Dorsey pour BNS — banque canadienne."""
    return DorseyRatios(
        roic=0.16,
        roic_5y_avg=0.15,
        gross_margin=0.55,
        gross_margin_5y_avg=0.54,
        revenue_bn=38.0,
    )


@pytest.fixture
def dorsey_output_bns() -> DorseyMoatOutput:
    """DorseyMoatOutput valide pour BNS — NARROW moat (switching costs bancaires)."""
    return DorseyMoatOutput(
        ticker="BNS",
        moat_type="NARROW",
        sources_identifiees=_make_5_sources(
            ["MODÉRÉE", "MODÉRÉE", "ABSENTE", "FAIBLE", "FAIBLE"]
        ),
        roic_durability="FORTE",
        verdict_detail=(
            "BNS bénéficie d'actifs intangibles (licence BSIF) et de switching costs "
            "modérés (mobilité bancaire limitée). ROIC > 15 % durablement soutenu. "
            "Moat NARROW — protection réelle mais non spectaculaire."
        ),
        drapeaux_rouges=["Pression concurrentielle open banking en cours d'introduction"],
        recommandation_prochaine_etape=["buffett_quality", "stock_valuation_triangulation"],
    )


# ---------------------------------------------------------------------------
# Tests schémas
# ---------------------------------------------------------------------------

class TestDorseySchemas:
    def test_dorsey_ratios_validation_ok(self):
        """DorseyRatios avec un seul champ renseigné est valide."""
        r = DorseyRatios(roic=0.18)
        assert r.roic == pytest.approx(0.18)

    def test_dorsey_ratios_tous_none_valide(self):
        """DorseyRatios entièrement vide est valide (tous optionnels)."""
        r = DorseyRatios()
        assert r.roic is None

    def test_dorsey_ratios_roic_negatif_accepte(self):
        """ROIC négatif est un cas réel et ne doit pas lever ValidationError."""
        r = DorseyRatios(roic=-0.05)
        assert r.roic == pytest.approx(-0.05)

    def test_dorsey_output_valide_se_construit(self, dorsey_output_bns: DorseyMoatOutput):
        assert dorsey_output_bns.ticker == "BNS"
        assert dorsey_output_bns.moat_type == "NARROW"

    def test_dorsey_output_moat_type_invalide_leve_erreur(
        self, dorsey_output_bns: DorseyMoatOutput
    ):
        """@model_validator rejette moat_type hors {WIDE, NARROW, NONE}."""
        data = dorsey_output_bns.model_dump()
        data["moat_type"] = "FORT"
        with pytest.raises(ValidationError, match="moat_type invalide"):
            DorseyMoatOutput.model_validate(data)

    def test_dorsey_output_sources_count_invalide_leve_erreur(
        self, dorsey_output_bns: DorseyMoatOutput
    ):
        """@model_validator rejette si sources_identifiees != 5."""
        data = dorsey_output_bns.model_dump()
        data["sources_identifiees"] = data["sources_identifiees"][:4]
        with pytest.raises(ValidationError, match="attendu 5"):
            DorseyMoatOutput.model_validate(data)

    def test_dorsey_output_roic_durability_invalide_leve_erreur(
        self, dorsey_output_bns: DorseyMoatOutput
    ):
        """@model_validator rejette roic_durability hors {FORTE, MODÉRÉE, FAIBLE}."""
        data = dorsey_output_bns.model_dump()
        data["roic_durability"] = "EXCELLENTE"
        with pytest.raises(ValidationError, match="roic_durability invalide"):
            DorseyMoatOutput.model_validate(data)

    def test_dorsey_output_wide_valide(self, dorsey_output_bns: DorseyMoatOutput):
        data = dorsey_output_bns.model_dump()
        data["moat_type"] = "WIDE"
        out = DorseyMoatOutput.model_validate(data)
        assert out.moat_type == "WIDE"

    def test_dorsey_output_none_valide(self, dorsey_output_bns: DorseyMoatOutput):
        data = dorsey_output_bns.model_dump()
        data["moat_type"] = "NONE"
        out = DorseyMoatOutput.model_validate(data)
        assert out.moat_type == "NONE"

    def test_citations_defaut_vide(self, dorsey_output_bns: DorseyMoatOutput):
        assert dorsey_output_bns.citations == []

    def test_cost_usd_defaut_zero(self, dorsey_output_bns: DorseyMoatOutput):
        assert dorsey_output_bns.cost_usd == 0.0

    def test_earnings_context_optionnel(self, ratios_dorsey_bns: DorseyRatios):
        inp = DorseyMoatInput(ticker="BNS", ratios=ratios_dorsey_bns)
        assert inp.earnings_context is None

    def test_earnings_context_peuple(self, ratios_dorsey_bns: DorseyRatios):
        ctx = EarningsContext(
            verdict="AUCUN_SIGNAL",
            z_score=3.8,
            m_score=-2.1,
            f_score=7,
            drapeaux_rouges=[],
        )
        inp = DorseyMoatInput(
            ticker="BNS", ratios=ratios_dorsey_bns, earnings_context=ctx
        )
        assert inp.earnings_context.f_score == 7


# ---------------------------------------------------------------------------
# Tests skill
# ---------------------------------------------------------------------------

class TestDorseyMoatSkill:
    @pytest.fixture
    def skill(self) -> DorseyMoatSkill:
        return DorseyMoatSkill(client=MagicMock(), model="claude-sonnet-4-6")

    def test_skill_id(self, skill: DorseyMoatSkill):
        assert skill.skill_id == "dorsey_moat"

    def test_tier(self, skill: DorseyMoatSkill):
        assert skill.tier == 2

    def test_system_prompt_charge_et_cache(self, skill: DorseyMoatSkill):
        blocks = skill.get_system_prompt()
        assert blocks[0]["cache_control"]["type"] == "ephemeral"
        assert len(blocks[0]["text"]) > 1024

    def test_system_prompt_contient_dorsey(self, skill: DorseyMoatSkill):
        text = skill.get_system_prompt()[0]["text"]
        assert "Dorsey" in text

    def test_system_prompt_contient_switching_costs(self, skill: DorseyMoatSkill):
        text = skill.get_system_prompt()[0]["text"]
        assert "switching_costs" in text

    def test_system_prompt_contient_seuil_roic(self, skill: DorseyMoatSkill):
        text = skill.get_system_prompt()[0]["text"]
        assert "15 %" in text

    def test_build_user_message_sans_context(
        self, skill: DorseyMoatSkill, ratios_dorsey_bns: DorseyRatios
    ):
        """Sans earnings_context, le message contient ticker et ratios JSON."""
        inp = DorseyMoatInput(ticker="BNS", ratios=ratios_dorsey_bns)
        msg = skill._build_user_message(inp, citations=[])
        assert "BNS" in msg
        assert "roic" in msg
        assert "Contexte earnings_quality" not in msg

    def test_build_user_message_avec_context(
        self, skill: DorseyMoatSkill, ratios_dorsey_bns: DorseyRatios
    ):
        """Avec earnings_context, le message mentionne la section contexte."""
        ctx = EarningsContext(
            verdict="ATTENTION",
            z_score=2.1,
            m_score=-1.8,
            f_score=5,
            drapeaux_rouges=["Accruals élevés"],
        )
        inp = DorseyMoatInput(
            ticker="BNS", ratios=ratios_dorsey_bns, earnings_context=ctx
        )
        msg = skill._build_user_message(inp, citations=[])
        assert "Contexte earnings_quality" in msg
        assert "ATTENTION" in msg
        assert "Accruals élevés" in msg

    @pytest.mark.asyncio
    async def test_get_citations_rag_absent(self):
        """DorseyMoatSkill instancié avec rag_service=None → get_citations() retourne []."""
        skill = DorseyMoatSkill(
            client=MagicMock(), model="claude-sonnet-4-6", rag_service=None
        )
        citations = await skill.get_citations("test query")
        assert citations == []

    @pytest.mark.asyncio
    async def test_execute_mock_claude(
        self,
        ratios_dorsey_bns: DorseyRatios,
        dorsey_output_bns: DorseyMoatOutput,
    ):
        """execute() retourne (DorseyMoatOutput, UsageDetail) avec cost_usd > 0."""
        mock_response = MagicMock()
        mock_response.content = [MagicMock(text=dorsey_output_bns.model_dump_json())]
        mock_response.usage = SimpleNamespace(
            input_tokens=800,
            output_tokens=400,
            cache_read_input_tokens=1200,
            cache_creation_input_tokens=0,
        )
        mock_client = MagicMock()
        mock_client.messages = AsyncMock()
        mock_client.messages.create.return_value = mock_response

        skill = DorseyMoatSkill(client=mock_client, model="claude-sonnet-4-6")
        inp = DorseyMoatInput(ticker="BNS", ratios=ratios_dorsey_bns)
        output, usage = await skill.execute(inp)

        assert isinstance(output, DorseyMoatOutput)
        assert isinstance(usage, UsageDetail)
        assert usage.cost_usd > 0
        assert output.cost_usd == usage.cost_usd

    @pytest.mark.asyncio
    async def test_execute_cost_usd_injecte_dans_output(
        self,
        ratios_dorsey_bns: DorseyRatios,
        dorsey_output_bns: DorseyMoatOutput,
    ):
        mock_response = MagicMock()
        mock_response.content = [MagicMock(text=dorsey_output_bns.model_dump_json())]
        mock_response.usage = SimpleNamespace(
            input_tokens=800,
            output_tokens=400,
            cache_read_input_tokens=0,
            cache_creation_input_tokens=1500,
        )
        mock_client = MagicMock()
        mock_client.messages = AsyncMock()
        mock_client.messages.create.return_value = mock_response

        skill = DorseyMoatSkill(client=mock_client, model="claude-sonnet-4-6")
        inp = DorseyMoatInput(ticker="BNS", ratios=ratios_dorsey_bns)
        output, usage = await skill.execute(inp)

        assert output.cost_usd == usage.cost_usd

    @pytest.mark.asyncio
    async def test_execute_avec_earnings_context(
        self,
        ratios_dorsey_bns: DorseyRatios,
        dorsey_output_bns: DorseyMoatOutput,
    ):
        """execute() transmet le contexte earnings dans le message utilisateur."""
        mock_response = MagicMock()
        mock_response.content = [MagicMock(text=dorsey_output_bns.model_dump_json())]
        mock_response.usage = SimpleNamespace(
            input_tokens=900,
            output_tokens=400,
            cache_read_input_tokens=1200,
            cache_creation_input_tokens=0,
        )
        mock_client = MagicMock()
        mock_client.messages = AsyncMock()
        mock_client.messages.create.return_value = mock_response

        skill = DorseyMoatSkill(client=mock_client, model="claude-sonnet-4-6")
        ctx = EarningsContext(
            verdict="AUCUN_SIGNAL",
            z_score=4.12,
            m_score=None,
            f_score=8,
            drapeaux_rouges=[],
        )
        inp = DorseyMoatInput(
            ticker="BNS", ratios=ratios_dorsey_bns, earnings_context=ctx
        )
        await skill.execute(inp)

        call_kwargs = mock_client.messages.create.call_args.kwargs
        user_content = call_kwargs["messages"][0]["content"]
        assert "Contexte earnings_quality" in user_content
        assert "AUCUN_SIGNAL" in user_content


# ---------------------------------------------------------------------------
# Tests intégration orchestrateur
# ---------------------------------------------------------------------------

class TestOrchestratorDorsey:
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
    def mock_dorsey_skill(self, dorsey_output_bns):
        skill = AsyncMock(spec=DorseyMoatSkill)
        skill.execute.return_value = (dorsey_output_bns, _make_usage())
        return skill

    @pytest.mark.asyncio
    async def test_orchestrator_avec_dorsey(
        self,
        mock_db_pool,
        mock_graham_skill,
        mock_earnings_skill,
        mock_dorsey_skill,
        ratios_msft,
        ratios_earnings_msft,
        ratios_dorsey_bns,
    ):
        """Avec dorsey_ratios fournis → response.dorsey non None, skills_applied contient dorsey_moat."""
        orchestrator = Orchestrator(
            db_pool=mock_db_pool,
            graham_skill=mock_graham_skill,
            earnings_skill=mock_earnings_skill,
            dorsey_skill=mock_dorsey_skill,
        )
        req = AnalyzeRequest(
            ticker="BNS",
            ratios=ratios_msft,
            earnings_ratios=ratios_earnings_msft,
            dorsey_ratios=ratios_dorsey_bns,
        )
        response = await orchestrator.run_company_analysis(req)

        assert response.dorsey is not None
        assert "dorsey_moat" in response.skills_applied
        mock_dorsey_skill.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_orchestrator_sans_dorsey_ratios(
        self,
        mock_db_pool,
        mock_graham_skill,
        mock_earnings_skill,
        mock_dorsey_skill,
        ratios_msft,
        ratios_earnings_msft,
    ):
        """Sans dorsey_ratios → response.dorsey est None, skill non appelé."""
        orchestrator = Orchestrator(
            db_pool=mock_db_pool,
            graham_skill=mock_graham_skill,
            earnings_skill=mock_earnings_skill,
            dorsey_skill=mock_dorsey_skill,
        )
        req = AnalyzeRequest(
            ticker="MSFT",
            ratios=ratios_msft,
            earnings_ratios=ratios_earnings_msft,
        )
        response = await orchestrator.run_company_analysis(req)

        assert response.dorsey is None
        assert "dorsey_moat" not in response.skills_applied
        mock_dorsey_skill.execute.assert_not_called()

    @pytest.mark.asyncio
    async def test_orchestrator_dorsey_sans_skill_instancie(
        self,
        mock_db_pool,
        mock_graham_skill,
        mock_earnings_skill,
        ratios_msft,
        ratios_dorsey_bns,
    ):
        """dorsey_ratios fourni mais dorsey_skill=None → dorsey absent sans erreur."""
        orchestrator = Orchestrator(
            db_pool=mock_db_pool,
            graham_skill=mock_graham_skill,
            earnings_skill=mock_earnings_skill,
            dorsey_skill=None,
        )
        req = AnalyzeRequest(
            ticker="BNS",
            ratios=ratios_msft,
            dorsey_ratios=ratios_dorsey_bns,
        )
        response = await orchestrator.run_company_analysis(req)

        assert response.dorsey is None
        assert "dorsey_moat" not in response.skills_applied

    @pytest.mark.asyncio
    async def test_cost_usd_somme_trois_skills(
        self,
        mock_db_pool,
        graham_output_msft,
        earnings_output_msft,
        dorsey_output_bns,
        ratios_msft,
        ratios_earnings_msft,
        ratios_dorsey_bns,
    ):
        """cost_usd = somme des trois appels Claude."""
        u1 = UsageDetail(
            tokens_input=500, tokens_output=200,
            tokens_cache_read=0, tokens_cache_creation=1500,
            cost_usd=0.003, model="claude-sonnet-4-6",
        )
        u2 = UsageDetail(
            tokens_input=800, tokens_output=600,
            tokens_cache_read=1200, tokens_cache_creation=0,
            cost_usd=0.004, model="claude-sonnet-4-6",
        )
        u3 = UsageDetail(
            tokens_input=700, tokens_output=400,
            tokens_cache_read=1200, tokens_cache_creation=0,
            cost_usd=0.005, model="claude-sonnet-4-6",
        )
        mock_graham = AsyncMock()
        mock_graham.execute.return_value = (graham_output_msft, u1)
        mock_earnings = AsyncMock()
        mock_earnings.execute.return_value = (earnings_output_msft, u2)
        mock_dorsey = AsyncMock(spec=DorseyMoatSkill)
        mock_dorsey.execute.return_value = (dorsey_output_bns, u3)

        orchestrator = Orchestrator(
            db_pool=mock_db_pool,
            graham_skill=mock_graham,
            earnings_skill=mock_earnings,
            dorsey_skill=mock_dorsey,
        )
        req = AnalyzeRequest(
            ticker="BNS",
            ratios=ratios_msft,
            earnings_ratios=ratios_earnings_msft,
            dorsey_ratios=ratios_dorsey_bns,
        )
        response = await orchestrator.run_company_analysis(req)

        assert abs(response.cost_usd - 0.012) < 1e-9

    @pytest.mark.asyncio
    async def test_earnings_context_passe_a_dorsey(
        self,
        mock_db_pool,
        graham_output_msft,
        earnings_output_msft,
        dorsey_output_bns,
        ratios_msft,
        ratios_earnings_msft,
        ratios_dorsey_bns,
    ):
        """L'orchestrateur passe le verdict earnings_quality à DorseyMoatSkill."""
        mock_graham = AsyncMock()
        mock_graham.execute.return_value = (graham_output_msft, _make_usage())
        mock_earnings = AsyncMock()
        mock_earnings.execute.return_value = (earnings_output_msft, _make_usage())
        mock_dorsey = AsyncMock(spec=DorseyMoatSkill)
        mock_dorsey.execute.return_value = (dorsey_output_bns, _make_usage())

        orchestrator = Orchestrator(
            db_pool=mock_db_pool,
            graham_skill=mock_graham,
            earnings_skill=mock_earnings,
            dorsey_skill=mock_dorsey,
        )
        req = AnalyzeRequest(
            ticker="BNS",
            ratios=ratios_msft,
            earnings_ratios=ratios_earnings_msft,
            dorsey_ratios=ratios_dorsey_bns,
        )
        await orchestrator.run_company_analysis(req)

        call_args = mock_dorsey.execute.call_args
        dorsey_input: DorseyMoatInput = call_args.args[0]
        assert dorsey_input.earnings_context is not None
        assert dorsey_input.earnings_context.verdict == earnings_output_msft.verdict

    @pytest.mark.asyncio
    async def test_dorsey_sans_earnings_pas_de_context(
        self,
        mock_db_pool,
        graham_output_msft,
        dorsey_output_bns,
        ratios_msft,
        ratios_dorsey_bns,
    ):
        """Sans earnings_ratios, earnings_context est None dans DorseyMoatInput."""
        mock_graham = AsyncMock()
        mock_graham.execute.return_value = (graham_output_msft, _make_usage())
        mock_earnings = AsyncMock()
        mock_dorsey = AsyncMock(spec=DorseyMoatSkill)
        mock_dorsey.execute.return_value = (dorsey_output_bns, _make_usage())

        orchestrator = Orchestrator(
            db_pool=mock_db_pool,
            graham_skill=mock_graham,
            earnings_skill=mock_earnings,
            dorsey_skill=mock_dorsey,
        )
        req = AnalyzeRequest(
            ticker="BNS",
            ratios=ratios_msft,
            dorsey_ratios=ratios_dorsey_bns,
        )
        await orchestrator.run_company_analysis(req)

        call_args = mock_dorsey.execute.call_args
        dorsey_input: DorseyMoatInput = call_args.args[0]
        assert dorsey_input.earnings_context is None
