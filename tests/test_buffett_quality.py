"""Tests du skill buffett_quality — schemas, skill, context enrichment, orchestrateur."""
from __future__ import annotations

import uuid
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest
from pydantic import ValidationError

from app.orchestrator.core import AnalyzeRequest, Orchestrator
from app.skills.base import UsageDetail
from app.skills.tier2.buffett_quality.schemas import (
    BuffettFiltre,
    BuffettQualityInput,
    BuffettQualityOutput,
    BuffettRatios,
    DorseyContext,
)
from app.skills.tier2.buffett_quality.skill import BuffettQualitySkill
from app.skills.tier2.dorsey_moat.schemas import (
    DorseyMoatOutput,
    DorseyRatios,
    MoatSource,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_4_filtres(scores: list[bool] | None = None) -> list[dict]:
    """Génère exactement 4 dicts BuffettFiltre pour les tests."""
    noms = [
        "comprehensible",
        "economics_favorables",
        "management_fiable",
        "prix_attractif",
    ]
    if scores is None:
        scores = [True, True, False, False]
    return [
        {
            "filtre": noms[i],
            "passe": scores[i],
            "score": 1 if scores[i] else 0,
            "justification": f"Justification test pour {noms[i]}",
        }
        for i in range(4)
    ]


def _make_buffett_output_dict(
    ticker: str = "BNS",
    scores: list[bool] | None = None,
    owner_earnings: float | None = 8.50,
    verdict: str = "QUALITE_CORRECTE",
) -> dict:
    filtres = _make_4_filtres(scores)
    quality_score = sum(f["score"] for f in filtres)
    return {
        "ticker": ticker,
        "filtres": filtres,
        "owner_earnings": owner_earnings,
        "quality_score": quality_score,
        "verdict": verdict,
        "verdict_detail": f"Analyse Buffett de {ticker} — {quality_score}/4 filtres passés.",
        "drapeaux_rouges": [],
        "recommandation_prochaine_etape": ["stock_valuation_triangulation"],
    }


def _make_usage() -> UsageDetail:
    return UsageDetail(
        tokens_input=800,
        tokens_output=400,
        tokens_cache_read=1200,
        tokens_cache_creation=0,
        cost_usd=0.0058,
        model="claude-sonnet-4-6",
    )


def _make_5_moat_sources(intensites: list[str] | None = None) -> list[MoatSource]:
    noms = [
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
            source=noms[i],
            present=(intensites[i] not in {"ABSENTE", "FAIBLE"}),
            intensite=intensites[i],
            justification=f"Test {noms[i]}",
        )
        for i in range(5)
    ]


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def ratios_buffett_bns() -> BuffettRatios:
    """Ratios Buffett pour BNS — banque canadienne."""
    return BuffettRatios(
        roe=0.15,
        roe_5y_avg=0.14,
        roic=0.16,
        roic_5y_avg=0.15,
        net_margin=0.27,
        revenue_growth_5y=0.04,
        eps_growth_5y=0.06,
        debt_equity=0.45,
        eps_ttm=7.25,
        revenue_bn=38.0,
        pe=11.0,
        price=80.0,
    )


@pytest.fixture
def ratios_buffett_avec_oe() -> BuffettRatios:
    """Ratios Buffett avec les champs nécessaires au calcul des owner earnings."""
    return BuffettRatios(
        eps_ttm=7.25,
        depreciation_bn=5.0,
        maintenance_capex_bn=2.0,
        revenue_bn=38.0,
        net_margin=0.27,
        pe=11.0,
        price=80.0,
    )


@pytest.fixture
def buffett_output_bns() -> BuffettQualityOutput:
    """BuffettQualityOutput valide pour BNS — QUALITE_CORRECTE (2/4)."""
    return BuffettQualityOutput(
        ticker="BNS",
        filtres=[
            BuffettFiltre(
                filtre="comprehensible",
                passe=True,
                score=1,
                justification="Banque retail canadienne — modèle compréhensible.",
            ),
            BuffettFiltre(
                filtre="economics_favorables",
                passe=True,
                score=1,
                justification="ROE 15 %, ROIC 16 % sur 5 ans, marge nette 27 %.",
            ),
            BuffettFiltre(
                filtre="management_fiable",
                passe=False,
                score=0,
                justification="Données qualitatives management non fournies.",
            ),
            BuffettFiltre(
                filtre="prix_attractif",
                passe=False,
                score=0,
                justification="P/E 11× raisonnable mais croissance BPA modeste 6 %.",
            ),
        ],
        owner_earnings=8.50,
        quality_score=2,
        verdict="QUALITE_CORRECTE",
        verdict_detail=(
            "BNS passe 2/4 filtres Buffett. Business compréhensible et economics "
            "solides, mais données management incomplètes et croissance limitée."
        ),
        drapeaux_rouges=["Croissance BPA limitée (6 %/an)"],
        recommandation_prochaine_etape=["stock_valuation_triangulation"],
    )


@pytest.fixture
def ratios_dorsey_bns() -> DorseyRatios:
    return DorseyRatios(
        roic=0.16,
        roic_5y_avg=0.15,
        gross_margin=0.55,
        gross_margin_5y_avg=0.54,
        revenue_bn=38.0,
    )


@pytest.fixture
def dorsey_output_bns() -> DorseyMoatOutput:
    """DorseyMoatOutput NARROW pour BNS — utilisé pour le context enrichment."""
    return DorseyMoatOutput(
        ticker="BNS",
        moat_type="NARROW",
        sources_identifiees=_make_5_moat_sources(
            ["MODÉRÉE", "MODÉRÉE", "ABSENTE", "FAIBLE", "FAIBLE"]
        ),
        roic_durability="FORTE",
        verdict_detail="BNS moat NARROW — switching costs et actifs intangibles modérés.",
        drapeaux_rouges=["Open banking pression concurrentielle"],
        recommandation_prochaine_etape=["buffett_quality"],
    )


# ---------------------------------------------------------------------------
# Tests schémas
# ---------------------------------------------------------------------------


class TestBuffettSchemas:
    def test_buffett_ratios_validation_ok(self):
        """BuffettRatios avec un seul champ renseigné est valide."""
        r = BuffettRatios(roe=0.18)
        assert r.roe == pytest.approx(0.18)
        assert r.roic is None

    def test_buffett_ratios_tous_none_valide(self):
        """BuffettRatios entièrement vide est valide (tous optionnels)."""
        r = BuffettRatios()
        assert r.roe is None

    def test_buffett_ratios_roe_negatif_accepte(self):
        """ROE négatif est un cas réel (perte) et ne doit pas lever ValidationError."""
        r = BuffettRatios(roe=-0.05)
        assert r.roe == pytest.approx(-0.05)

    def test_buffett_output_valide_se_construit(self, buffett_output_bns: BuffettQualityOutput):
        assert buffett_output_bns.ticker == "BNS"
        assert buffett_output_bns.quality_score == 2
        assert buffett_output_bns.verdict == "QUALITE_CORRECTE"

    def test_buffett_output_verdict_invalide_leve_erreur(
        self, buffett_output_bns: BuffettQualityOutput
    ):
        """@model_validator rejette verdict hors {COMPOUNDER, QUALITE_CORRECTE, REJETER}."""
        data = buffett_output_bns.model_dump()
        data["verdict"] = "EXCELLENT"
        with pytest.raises(ValidationError, match="verdict invalide"):
            BuffettQualityOutput.model_validate(data)

    def test_buffett_output_filtres_count_invalide_leve_erreur(
        self, buffett_output_bns: BuffettQualityOutput
    ):
        """@model_validator rejette si filtres != 4."""
        data = buffett_output_bns.model_dump()
        data["filtres"] = data["filtres"][:3]
        with pytest.raises(ValidationError, match="attendu 4"):
            BuffettQualityOutput.model_validate(data)

    def test_buffett_output_quality_score_hors_plage_leve_erreur(
        self, buffett_output_bns: BuffettQualityOutput
    ):
        """@model_validator rejette quality_score > 4."""
        data = buffett_output_bns.model_dump()
        data["quality_score"] = 5
        with pytest.raises(ValidationError, match="hors plage"):
            BuffettQualityOutput.model_validate(data)

    def test_buffett_output_quality_score_negatif_leve_erreur(
        self, buffett_output_bns: BuffettQualityOutput
    ):
        data = buffett_output_bns.model_dump()
        data["quality_score"] = -1
        with pytest.raises(ValidationError, match="hors plage"):
            BuffettQualityOutput.model_validate(data)

    def test_buffett_output_compounder_valide(self, buffett_output_bns: BuffettQualityOutput):
        data = buffett_output_bns.model_dump()
        data["filtres"] = _make_4_filtres([True, True, True, True])
        data["quality_score"] = 4
        data["verdict"] = "COMPOUNDER"
        out = BuffettQualityOutput.model_validate(data)
        assert out.verdict == "COMPOUNDER"

    def test_buffett_output_rejeter_valide(self, buffett_output_bns: BuffettQualityOutput):
        data = buffett_output_bns.model_dump()
        data["filtres"] = _make_4_filtres([False, False, False, False])
        data["quality_score"] = 0
        data["verdict"] = "REJETER"
        out = BuffettQualityOutput.model_validate(data)
        assert out.verdict == "REJETER"

    def test_citations_defaut_vide(self, buffett_output_bns: BuffettQualityOutput):
        assert buffett_output_bns.citations == []

    def test_cost_usd_defaut_zero(self, buffett_output_bns: BuffettQualityOutput):
        assert buffett_output_bns.cost_usd == 0.0

    def test_owner_earnings_peut_etre_none(self, buffett_output_bns: BuffettQualityOutput):
        data = buffett_output_bns.model_dump()
        data["owner_earnings"] = None
        out = BuffettQualityOutput.model_validate(data)
        assert out.owner_earnings is None

    def test_dorsey_context_optionnel(self, ratios_buffett_bns: BuffettRatios):
        inp = BuffettQualityInput(ticker="BNS", ratios=ratios_buffett_bns)
        assert inp.dorsey_context is None

    def test_dorsey_context_peuple(self, ratios_buffett_bns: BuffettRatios):
        ctx = DorseyContext(
            moat_type="NARROW",
            sources=["switching_costs", "intangibles"],
            roic_durability="FORTE",
        )
        inp = BuffettQualityInput(
            ticker="BNS", ratios=ratios_buffett_bns, dorsey_context=ctx
        )
        assert inp.dorsey_context.moat_type == "NARROW"
        assert "switching_costs" in inp.dorsey_context.sources


# ---------------------------------------------------------------------------
# Tests skill
# ---------------------------------------------------------------------------


class TestBuffettQualitySkill:
    @pytest.fixture
    def skill(self) -> BuffettQualitySkill:
        return BuffettQualitySkill(client=MagicMock(), model="claude-sonnet-4-6")

    def test_skill_id(self, skill: BuffettQualitySkill):
        assert skill.skill_id == "buffett_quality"

    def test_tier(self, skill: BuffettQualitySkill):
        assert skill.tier == 2

    def test_system_prompt_charge_et_cache(self, skill: BuffettQualitySkill):
        blocks = skill.get_system_prompt()
        assert blocks[0]["cache_control"]["type"] == "ephemeral"
        assert len(blocks[0]["text"]) > 1024

    def test_system_prompt_contient_buffett(self, skill: BuffettQualitySkill):
        text = skill.get_system_prompt()[0]["text"]
        assert "Buffett" in text

    def test_system_prompt_contient_owner_earnings(self, skill: BuffettQualitySkill):
        text = skill.get_system_prompt()[0]["text"]
        assert "owner_earnings" in text.lower() or "Owner Earnings" in text

    def test_system_prompt_contient_compounder(self, skill: BuffettQualitySkill):
        text = skill.get_system_prompt()[0]["text"]
        assert "COMPOUNDER" in text

    def test_system_prompt_contient_seuil_roic(self, skill: BuffettQualitySkill):
        text = skill.get_system_prompt()[0]["text"]
        assert "15 %" in text

    def test_build_user_message_sans_context(
        self, skill: BuffettQualitySkill, ratios_buffett_bns: BuffettRatios
    ):
        """Sans dorsey_context, le message contient ticker et ratios JSON."""
        inp = BuffettQualityInput(ticker="BNS", ratios=ratios_buffett_bns)
        msg = skill._build_user_message(inp, citations=[])
        assert "BNS" in msg
        assert "roe" in msg
        assert "Contexte dorsey_moat" not in msg

    def test_build_user_message_avec_context(
        self, skill: BuffettQualitySkill, ratios_buffett_bns: BuffettRatios
    ):
        """Avec dorsey_context, le message mentionne la section contexte."""
        ctx = DorseyContext(
            moat_type="WIDE",
            sources=["switching_costs", "network_effects"],
            roic_durability="FORTE",
        )
        inp = BuffettQualityInput(
            ticker="BNS", ratios=ratios_buffett_bns, dorsey_context=ctx
        )
        msg = skill._build_user_message(inp, citations=[])
        assert "Contexte dorsey_moat" in msg
        assert "WIDE" in msg
        assert "switching_costs" in msg

    def test_build_user_message_context_sans_sources(
        self, skill: BuffettQualitySkill, ratios_buffett_bns: BuffettRatios
    ):
        """DorseyContext avec sources vide s'affiche sans erreur."""
        ctx = DorseyContext(moat_type="NONE", sources=[], roic_durability="FAIBLE")
        inp = BuffettQualityInput(
            ticker="TEST", ratios=ratios_buffett_bns, dorsey_context=ctx
        )
        msg = skill._build_user_message(inp, citations=[])
        assert "NONE" in msg
        assert "aucune" in msg

    @pytest.mark.asyncio
    async def test_get_citations_rag_absent(self):
        """BuffettQualitySkill instancié avec rag_service=None → get_citations() retourne []."""
        skill = BuffettQualitySkill(
            client=MagicMock(), model="claude-sonnet-4-6", rag_service=None
        )
        citations = await skill.get_citations("test query")
        assert citations == []

    @pytest.mark.asyncio
    async def test_execute_mock_claude(
        self,
        ratios_buffett_bns: BuffettRatios,
        buffett_output_bns: BuffettQualityOutput,
    ):
        """execute() retourne (BuffettQualityOutput, UsageDetail) avec cost_usd > 0."""
        mock_response = MagicMock()
        mock_block = MagicMock()
        mock_block.type = "tool_use"
        mock_block.input = buffett_output_bns.model_dump(exclude={"citations", "cost_usd"})
        mock_response.content = [mock_block]
        mock_response.stop_reason = "tool_use"
        mock_response.usage = SimpleNamespace(
            input_tokens=800,
            output_tokens=400,
            cache_read_input_tokens=1200,
            cache_creation_input_tokens=0,
        )
        mock_client = MagicMock()
        mock_client.messages = AsyncMock()
        mock_client.messages.create.return_value = mock_response

        skill = BuffettQualitySkill(client=mock_client, model="claude-sonnet-4-6")
        inp = BuffettQualityInput(ticker="BNS", ratios=ratios_buffett_bns)
        output, usage = await skill.execute(inp)

        assert isinstance(output, BuffettQualityOutput)
        assert isinstance(usage, UsageDetail)
        assert usage.cost_usd > 0
        assert output.cost_usd == usage.cost_usd

    @pytest.mark.asyncio
    async def test_execute_cost_usd_injecte_dans_output(
        self,
        ratios_buffett_bns: BuffettRatios,
        buffett_output_bns: BuffettQualityOutput,
    ):
        mock_response = MagicMock()
        mock_block = MagicMock()
        mock_block.type = "tool_use"
        mock_block.input = buffett_output_bns.model_dump(exclude={"citations", "cost_usd"})
        mock_response.content = [mock_block]
        mock_response.stop_reason = "tool_use"
        mock_response.usage = SimpleNamespace(
            input_tokens=800,
            output_tokens=400,
            cache_read_input_tokens=0,
            cache_creation_input_tokens=1500,
        )
        mock_client = MagicMock()
        mock_client.messages = AsyncMock()
        mock_client.messages.create.return_value = mock_response

        skill = BuffettQualitySkill(client=mock_client, model="claude-sonnet-4-6")
        inp = BuffettQualityInput(ticker="BNS", ratios=ratios_buffett_bns)
        output, usage = await skill.execute(inp)

        assert output.cost_usd == usage.cost_usd

    @pytest.mark.asyncio
    async def test_execute_avec_dorsey_context(
        self,
        ratios_buffett_bns: BuffettRatios,
        buffett_output_bns: BuffettQualityOutput,
    ):
        """execute() transmet le contexte dorsey dans le message utilisateur."""
        mock_response = MagicMock()
        mock_block = MagicMock()
        mock_block.type = "tool_use"
        mock_block.input = buffett_output_bns.model_dump(exclude={"citations", "cost_usd"})
        mock_response.content = [mock_block]
        mock_response.stop_reason = "tool_use"
        mock_response.usage = SimpleNamespace(
            input_tokens=900,
            output_tokens=400,
            cache_read_input_tokens=1200,
            cache_creation_input_tokens=0,
        )
        mock_client = MagicMock()
        mock_client.messages = AsyncMock()
        mock_client.messages.create.return_value = mock_response

        skill = BuffettQualitySkill(client=mock_client, model="claude-sonnet-4-6")
        ctx = DorseyContext(
            moat_type="WIDE",
            sources=["switching_costs"],
            roic_durability="FORTE",
        )
        inp = BuffettQualityInput(
            ticker="BNS", ratios=ratios_buffett_bns, dorsey_context=ctx
        )
        await skill.execute(inp)

        call_kwargs = mock_client.messages.create.call_args.kwargs
        user_content = call_kwargs["messages"][0]["content"]
        assert "Contexte dorsey_moat" in user_content
        assert "WIDE" in user_content

    @pytest.mark.asyncio
    async def test_owner_earnings_present_dans_output(
        self,
        ratios_buffett_avec_oe: BuffettRatios,
    ):
        """owner_earnings non None si eps_ttm, depreciation_bn, maintenance_capex_bn fournis."""
        output_data = _make_buffett_output_dict(
            ticker="BNS",
            scores=[True, True, False, False],
            owner_earnings=8.50,
            verdict="QUALITE_CORRECTE",
        )
        mock_response = MagicMock()
        mock_block = MagicMock()
        mock_block.type = "tool_use"
        mock_block.input = output_data
        mock_response.content = [mock_block]
        mock_response.stop_reason = "tool_use"
        mock_response.usage = SimpleNamespace(
            input_tokens=800,
            output_tokens=400,
            cache_read_input_tokens=1200,
            cache_creation_input_tokens=0,
        )
        mock_client = MagicMock()
        mock_client.messages = AsyncMock()
        mock_client.messages.create.return_value = mock_response

        skill = BuffettQualitySkill(client=mock_client, model="claude-sonnet-4-6")
        inp = BuffettQualityInput(ticker="BNS", ratios=ratios_buffett_avec_oe)
        output, _ = await skill.execute(inp)

        assert output.owner_earnings is not None
        assert output.owner_earnings == pytest.approx(8.50)


# ---------------------------------------------------------------------------
# Tests intégration orchestrateur
# ---------------------------------------------------------------------------


class TestOrchestratorBuffett:
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
        from app.skills.tier2.dorsey_moat.skill import DorseyMoatSkill
        skill = AsyncMock(spec=DorseyMoatSkill)
        skill.execute.return_value = (dorsey_output_bns, _make_usage())
        return skill

    @pytest.fixture
    def mock_buffett_skill(self, buffett_output_bns):
        skill = AsyncMock(spec=BuffettQualitySkill)
        skill.execute.return_value = (buffett_output_bns, _make_usage())
        return skill

    @pytest.mark.asyncio
    async def test_orchestrator_avec_buffett(
        self,
        mock_db_pool,
        mock_graham_skill,
        mock_earnings_skill,
        mock_dorsey_skill,
        mock_buffett_skill,
        ratios_msft,
        ratios_earnings_msft,
        ratios_dorsey_bns,
        ratios_buffett_bns,
    ):
        """Avec buffett_ratios fournis → response.buffett non None, skills_applied contient buffett_quality."""
        orchestrator = Orchestrator(
            db_pool=mock_db_pool,
            graham_skill=mock_graham_skill,
            earnings_skill=mock_earnings_skill,
            dorsey_skill=mock_dorsey_skill,
            buffett_skill=mock_buffett_skill,
        )
        req = AnalyzeRequest(
            ticker="BNS",
            ratios=ratios_msft,
            workflow="compounder_buffett",
            earnings_ratios=ratios_earnings_msft,
            dorsey_ratios=ratios_dorsey_bns,
            buffett_ratios=ratios_buffett_bns,
        )
        response = await orchestrator.run_company_analysis(req)

        assert response.buffett is not None
        assert "buffett_quality" in response.skills_applied
        mock_buffett_skill.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_orchestrator_sans_buffett(
        self,
        mock_db_pool,
        mock_graham_skill,
        mock_earnings_skill,
        mock_dorsey_skill,
        mock_buffett_skill,
        ratios_msft,
        ratios_earnings_msft,
    ):
        """Sans buffett_ratios → response.buffett est None, skill non appelé."""
        orchestrator = Orchestrator(
            db_pool=mock_db_pool,
            graham_skill=mock_graham_skill,
            earnings_skill=mock_earnings_skill,
            dorsey_skill=mock_dorsey_skill,
            buffett_skill=mock_buffett_skill,
        )
        req = AnalyzeRequest(
            ticker="MSFT",
            ratios=ratios_msft,
            workflow="compounder_buffett",
            earnings_ratios=ratios_earnings_msft,
        )
        response = await orchestrator.run_company_analysis(req)

        assert response.buffett is None
        assert "buffett_quality" not in response.skills_applied
        mock_buffett_skill.execute.assert_not_called()

    @pytest.mark.asyncio
    async def test_orchestrator_buffett_sans_skill_instancie(
        self,
        mock_db_pool,
        mock_graham_skill,
        mock_earnings_skill,
        ratios_msft,
        ratios_buffett_bns,
    ):
        """buffett_ratios fourni mais buffett_skill=None → buffett absent sans erreur."""
        orchestrator = Orchestrator(
            db_pool=mock_db_pool,
            graham_skill=mock_graham_skill,
            earnings_skill=mock_earnings_skill,
            buffett_skill=None,
        )
        req = AnalyzeRequest(
            ticker="BNS",
            ratios=ratios_msft,
            workflow="compounder_buffett",
            buffett_ratios=ratios_buffett_bns,
        )
        response = await orchestrator.run_company_analysis(req)

        assert response.buffett is None
        assert "buffett_quality" not in response.skills_applied

    @pytest.mark.asyncio
    async def test_dorsey_context_passe_a_buffett(
        self,
        mock_db_pool,
        graham_output_msft,
        earnings_output_msft,
        dorsey_output_bns,
        buffett_output_bns,
        ratios_msft,
        ratios_earnings_msft,
        ratios_dorsey_bns,
        ratios_buffett_bns,
    ):
        """L'orchestrateur passe le moat_type dorsey à BuffettQualityInput."""
        from app.skills.tier2.dorsey_moat.skill import DorseyMoatSkill

        mock_graham = AsyncMock()
        mock_graham.execute.return_value = (graham_output_msft, _make_usage())
        mock_earnings = AsyncMock()
        mock_earnings.execute.return_value = (earnings_output_msft, _make_usage())
        mock_dorsey = AsyncMock(spec=DorseyMoatSkill)
        mock_dorsey.execute.return_value = (dorsey_output_bns, _make_usage())
        mock_buffett = AsyncMock(spec=BuffettQualitySkill)
        mock_buffett.execute.return_value = (buffett_output_bns, _make_usage())

        orchestrator = Orchestrator(
            db_pool=mock_db_pool,
            graham_skill=mock_graham,
            earnings_skill=mock_earnings,
            dorsey_skill=mock_dorsey,
            buffett_skill=mock_buffett,
        )
        req = AnalyzeRequest(
            ticker="BNS",
            ratios=ratios_msft,
            workflow="compounder_buffett",
            earnings_ratios=ratios_earnings_msft,
            dorsey_ratios=ratios_dorsey_bns,
            buffett_ratios=ratios_buffett_bns,
        )
        await orchestrator.run_company_analysis(req)

        call_args = mock_buffett.execute.call_args
        buffett_input: BuffettQualityInput = call_args.args[0]
        assert buffett_input.dorsey_context is not None
        assert buffett_input.dorsey_context.moat_type == dorsey_output_bns.moat_type

    @pytest.mark.asyncio
    async def test_buffett_sans_dorsey_pas_de_context(
        self,
        mock_db_pool,
        graham_output_msft,
        buffett_output_bns,
        ratios_msft,
        ratios_buffett_bns,
    ):
        """Sans dorsey_ratios, dorsey_context est None dans BuffettQualityInput."""
        mock_graham = AsyncMock()
        mock_graham.execute.return_value = (graham_output_msft, _make_usage())
        mock_earnings = AsyncMock()
        mock_buffett = AsyncMock(spec=BuffettQualitySkill)
        mock_buffett.execute.return_value = (buffett_output_bns, _make_usage())

        orchestrator = Orchestrator(
            db_pool=mock_db_pool,
            graham_skill=mock_graham,
            earnings_skill=mock_earnings,
            buffett_skill=mock_buffett,
        )
        req = AnalyzeRequest(
            ticker="BNS",
            ratios=ratios_msft,
            workflow="compounder_buffett",
            buffett_ratios=ratios_buffett_bns,
        )
        await orchestrator.run_company_analysis(req)

        call_args = mock_buffett.execute.call_args
        buffett_input: BuffettQualityInput = call_args.args[0]
        assert buffett_input.dorsey_context is None

    @pytest.mark.asyncio
    async def test_cost_usd_somme_quatre_skills(
        self,
        mock_db_pool,
        graham_output_msft,
        earnings_output_msft,
        dorsey_output_bns,
        buffett_output_bns,
        ratios_msft,
        ratios_earnings_msft,
        ratios_dorsey_bns,
        ratios_buffett_bns,
    ):
        """cost_usd = somme des quatre appels Claude."""
        from app.skills.tier2.dorsey_moat.skill import DorseyMoatSkill

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
        u4 = UsageDetail(
            tokens_input=750, tokens_output=450,
            tokens_cache_read=1200, tokens_cache_creation=0,
            cost_usd=0.006, model="claude-sonnet-4-6",
        )
        mock_graham = AsyncMock()
        mock_graham.execute.return_value = (graham_output_msft, u1)
        mock_earnings = AsyncMock()
        mock_earnings.execute.return_value = (earnings_output_msft, u2)
        mock_dorsey = AsyncMock(spec=DorseyMoatSkill)
        mock_dorsey.execute.return_value = (dorsey_output_bns, u3)
        mock_buffett = AsyncMock(spec=BuffettQualitySkill)
        mock_buffett.execute.return_value = (buffett_output_bns, u4)

        orchestrator = Orchestrator(
            db_pool=mock_db_pool,
            graham_skill=mock_graham,
            earnings_skill=mock_earnings,
            dorsey_skill=mock_dorsey,
            buffett_skill=mock_buffett,
        )
        req = AnalyzeRequest(
            ticker="BNS",
            ratios=ratios_msft,
            workflow="compounder_buffett",
            earnings_ratios=ratios_earnings_msft,
            dorsey_ratios=ratios_dorsey_bns,
            buffett_ratios=ratios_buffett_bns,
        )
        response = await orchestrator.run_company_analysis(req)

        assert abs(response.cost_usd - 0.018) < 1e-9
