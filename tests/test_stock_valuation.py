"""Tests du skill stock_valuation_triangulation — schemas, skill, orchestrateur."""
from __future__ import annotations

import uuid
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest
from pydantic import ValidationError

from app.orchestrator.core import AnalyzeRequest, Orchestrator
from app.skills.base import UsageDetail
from app.skills.tier2.buffett_quality.schemas import BuffettRatios
from app.skills.tier2.dorsey_moat.schemas import DorseyRatios
from app.skills.tier2.earnings_quality.schemas import EarningsQualityRatios
from app.skills.tier2.stock_valuation.schemas import (
    BuffettContext,
    DorseyContext,
    EarningsContext,
    GrahamContext,
    SensitivityMatrix,
    StockValuationInput,
    StockValuationOutput,
    ValuationMethod,
    ValuationRatios,
)
from app.skills.tier2.stock_valuation.skill import StockValuationSkill

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_3_methodes(
    dcf_val: float | None = 92.0,
    comp_val: float | None = 88.0,
    sect_val: float | None = 95.0,
) -> list[dict]:
    return [
        {"methode": "dcf", "valeur": dcf_val, "hypotheses": "WACC 9%, g 2.5%, FCF 8.5B"},
        {"methode": "comparables", "valeur": comp_val, "hypotheses": "P/B 1.8x médiane pairs"},
        {"methode": "sectoriel", "valeur": sect_val, "hypotheses": "P/B justifié = 1.85x"},
    ]


def _make_matrix_5x5() -> dict:
    return {
        "wacc_range": [7.0, 8.0, 9.0, 10.0, 11.0],
        "growth_range": [1.5, 2.0, 2.5, 3.0, 3.5],
        "values": [
            [110.0, 115.0, 121.0, 128.0, 136.0],
            [100.0, 104.0, 108.0, 113.0, 119.0],
            [91.0, 94.0, 97.0, 100.0, 104.0],
            [83.0, 86.0, 88.0, 91.0, 94.0],
            [76.0, 78.0, 80.0, 82.0, 84.0],
        ],
    }


def _make_matrix_4x4() -> dict:
    return {
        "wacc_range": [8.0, 9.0, 10.0, 11.0],
        "growth_range": [2.0, 2.5, 3.0, 3.5],
        "values": [
            [104.0, 108.0, 113.0, 119.0],
            [94.0, 97.0, 100.0, 104.0],
            [86.0, 88.0, 91.0, 94.0],
            [78.0, 80.0, 82.0, 84.0],
        ],
    }


def _make_valuation_output_dict(
    ticker: str = "BNS",
    verdict: str = "SOUS_EVALUE",
    fourchette_basse: float = 82.0,
    fourchette_centrale: float = 91.5,
    fourchette_haute: float = 100.5,
    matrix: dict | None = None,
) -> dict:
    if matrix is None:
        matrix = _make_matrix_5x5()
    marge = (fourchette_centrale - 80.0) / fourchette_centrale
    return {
        "ticker": ticker,
        "methodes": _make_3_methodes(),
        "fourchette_basse": fourchette_basse,
        "fourchette_centrale": fourchette_centrale,
        "fourchette_haute": fourchette_haute,
        "marge_securite_composite": round(marge, 4),
        "matrice_sensibilite": matrix,
        "verdict": verdict,
        "verdict_detail": f"Analyse valorisation {ticker} — verdict {verdict}.",
        "recommandation_prochaine_etape": ["investment_thesis_builder"],
    }


def _make_usage() -> UsageDetail:
    return UsageDetail(
        tokens_input=800,
        tokens_output=600,
        tokens_cache_read=1200,
        tokens_cache_creation=0,
        cost_usd=0.0072,
        model="claude-sonnet-4-6",
    )


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def ratios_valuation_bns() -> ValuationRatios:
    return ValuationRatios(
        price=80.0,
        eps_ttm=7.25,
        eps_growth_5y=0.06,
        book_value=61.5,
        revenue_bn=38.0,
        roic=0.16,
        net_margin=0.27,
        pe=11.0,
        pb=1.3,
        sector="Financier",
    )


@pytest.fixture
def valuation_output_bns() -> StockValuationOutput:
    return StockValuationOutput(
        ticker="BNS",
        methodes=[
            ValuationMethod(methode="dcf", valeur=None, hypotheses="DCF inapplicable aux banques"),
            ValuationMethod(methode="comparables", valeur=85.0, hypotheses="P/B 1.7x médiane TD/RBC/BMO"),
            ValuationMethod(methode="sectoriel", valeur=95.0, hypotheses="P/B justifié 1.85x × book 61.5$"),
        ],
        fourchette_basse=82.0,
        fourchette_centrale=91.5,
        fourchette_haute=100.5,
        marge_securite_composite=0.126,
        matrice_sensibilite=SensitivityMatrix(**_make_matrix_5x5()),
        verdict="SOUS_EVALUE",
        verdict_detail="BNS à 80$ sous la fourchette centrale de 91.5$.",
        recommandation_prochaine_etape=["investment_thesis_builder"],
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
def ratios_buffett_bns() -> BuffettRatios:
    return BuffettRatios(
        roe=0.15,
        roe_5y_avg=0.14,
        roic=0.16,
        net_margin=0.27,
        revenue_growth_5y=0.04,
        eps_growth_5y=0.06,
        debt_equity=0.45,
        eps_ttm=7.25,
        revenue_bn=38.0,
        pe=11.0,
        price=80.0,
    )


# ---------------------------------------------------------------------------
# Tests schémas
# ---------------------------------------------------------------------------


class TestValuationSchemas:
    def test_valuation_ratios_validation_ok(self):
        """ValuationRatios avec price seul → valide."""
        r = ValuationRatios(price=80.0)
        assert r.price == pytest.approx(80.0)
        assert r.eps_ttm is None

    def test_valuation_ratios_tous_none_valide(self):
        """ValuationRatios entièrement vide est valide (tous optionnels)."""
        r = ValuationRatios()
        assert r.price is None
        assert r.sector is None

    def test_valuation_output_valide_se_construit(self, valuation_output_bns: StockValuationOutput):
        assert valuation_output_bns.ticker == "BNS"
        assert valuation_output_bns.verdict == "SOUS_EVALUE"
        assert len(valuation_output_bns.methodes) == 3

    def test_valuation_output_verdict_invalide_leve_erreur(
        self, valuation_output_bns: StockValuationOutput
    ):
        """@model_validator rejette verdict hors {SOUS_EVALUE, JUSTE_VALEUR, SUREVALUE}."""
        data = valuation_output_bns.model_dump()
        data["verdict"] = "NEUTRE"
        with pytest.raises(ValidationError, match="verdict invalide"):
            StockValuationOutput.model_validate(data)

    def test_valuation_output_methodes_count_invalide_leve_erreur(
        self, valuation_output_bns: StockValuationOutput
    ):
        """@model_validator rejette si methodes != 3."""
        data = valuation_output_bns.model_dump()
        data["methodes"] = data["methodes"][:2]
        with pytest.raises(ValidationError, match="attendu 3"):
            StockValuationOutput.model_validate(data)

    def test_valuation_fourchette_incoherente_basse_sup_centrale_leve_erreur(
        self, valuation_output_bns: StockValuationOutput
    ):
        """fourchette_basse > fourchette_centrale → ValueError."""
        data = valuation_output_bns.model_dump()
        data["fourchette_basse"] = 100.0
        data["fourchette_centrale"] = 90.0
        with pytest.raises(ValidationError, match="fourchette_basse"):
            StockValuationOutput.model_validate(data)

    def test_valuation_fourchette_centrale_sup_haute_leve_erreur(
        self, valuation_output_bns: StockValuationOutput
    ):
        """fourchette_centrale > fourchette_haute → ValueError."""
        data = valuation_output_bns.model_dump()
        data["fourchette_centrale"] = 110.0
        data["fourchette_haute"] = 100.0
        with pytest.raises(ValidationError, match="fourchette_centrale"):
            StockValuationOutput.model_validate(data)

    def test_valuation_matrice_shape_invalide_leve_erreur(
        self, valuation_output_bns: StockValuationOutput
    ):
        """values avec 3 lignes mais wacc_range len 4 → ValueError."""
        data = valuation_output_bns.model_dump()
        data["matrice_sensibilite"]["wacc_range"] = [8.0, 9.0, 10.0, 11.0]
        data["matrice_sensibilite"]["values"] = [
            [100.0, 104.0, 108.0, 113.0],
            [91.0, 94.0, 97.0, 100.0],
            [83.0, 86.0, 88.0, 91.0],
            # manque une ligne
        ]
        with pytest.raises(ValidationError, match="lignes"):
            StockValuationOutput.model_validate(data)

    def test_valuation_matrice_colonnes_invalides_leve_erreur(
        self, valuation_output_bns: StockValuationOutput
    ):
        """values[0] avec mauvais nombre de colonnes → ValueError."""
        data = valuation_output_bns.model_dump()
        # 5 lignes mais la première n'a que 3 colonnes vs growth_range len 5
        data["matrice_sensibilite"]["values"][0] = [110.0, 115.0, 121.0]
        with pytest.raises(ValidationError, match="colonnes"):
            StockValuationOutput.model_validate(data)

    def test_valuation_output_juste_valeur_valide(self, valuation_output_bns: StockValuationOutput):
        data = valuation_output_bns.model_dump()
        data["verdict"] = "JUSTE_VALEUR"
        out = StockValuationOutput.model_validate(data)
        assert out.verdict == "JUSTE_VALEUR"

    def test_valuation_output_surevalue_valide(self, valuation_output_bns: StockValuationOutput):
        data = valuation_output_bns.model_dump()
        data["verdict"] = "SUREVALUE"
        out = StockValuationOutput.model_validate(data)
        assert out.verdict == "SUREVALUE"

    def test_citations_defaut_vide(self, valuation_output_bns: StockValuationOutput):
        assert valuation_output_bns.citations == []

    def test_cost_usd_defaut_zero(self, valuation_output_bns: StockValuationOutput):
        assert valuation_output_bns.cost_usd == 0.0

    def test_valuation_methode_valeur_peut_etre_none(
        self, valuation_output_bns: StockValuationOutput
    ):
        """ValuationMethod.valeur = None (DCF inapplicable) est valide."""
        data = valuation_output_bns.model_dump()
        data["methodes"][0]["valeur"] = None
        out = StockValuationOutput.model_validate(data)
        assert out.methodes[0].valeur is None

    def test_valuation_matrice_4x4_valide(self, valuation_output_bns: StockValuationOutput):
        """Une matrice 4×4 est valide."""
        data = valuation_output_bns.model_dump()
        data["matrice_sensibilite"] = _make_matrix_4x4()
        out = StockValuationOutput.model_validate(data)
        assert len(out.matrice_sensibilite.wacc_range) == 4
        assert len(out.matrice_sensibilite.growth_range) == 4
        assert len(out.matrice_sensibilite.values) == 4

    def test_graham_context_optionnel(self, ratios_valuation_bns: ValuationRatios):
        inp = StockValuationInput(ticker="BNS", ratios=ratios_valuation_bns)
        assert inp.graham_context is None
        assert inp.buffett_context is None

    def test_buffett_context_peuple(self, ratios_valuation_bns: ValuationRatios):
        ctx = BuffettContext(quality_score=3, verdict="COMPOUNDER", owner_earnings=8.5)
        inp = StockValuationInput(
            ticker="BNS", ratios=ratios_valuation_bns, buffett_context=ctx
        )
        assert inp.buffett_context.quality_score == 3
        assert inp.buffett_context.verdict == "COMPOUNDER"


# ---------------------------------------------------------------------------
# Tests skill
# ---------------------------------------------------------------------------


class TestStockValuationSkill:
    @pytest.fixture
    def skill(self) -> StockValuationSkill:
        return StockValuationSkill(client=MagicMock(), model="claude-sonnet-4-6")

    def test_skill_id(self, skill: StockValuationSkill):
        assert skill.skill_id == "stock_valuation_triangulation"

    def test_tier(self, skill: StockValuationSkill):
        assert skill.tier == 2

    def test_system_prompt_charge_et_cache(self, skill: StockValuationSkill):
        blocks = skill.get_system_prompt()
        assert blocks[0]["cache_control"]["type"] == "ephemeral"
        assert len(blocks[0]["text"]) > 1024

    def test_system_prompt_contient_dcf(self, skill: StockValuationSkill):
        text = skill.get_system_prompt()[0]["text"]
        assert "DCF" in text

    def test_system_prompt_contient_wacc(self, skill: StockValuationSkill):
        text = skill.get_system_prompt()[0]["text"]
        assert "WACC" in text

    def test_system_prompt_contient_verdict_sous_evalue(self, skill: StockValuationSkill):
        text = skill.get_system_prompt()[0]["text"]
        assert "SOUS_EVALUE" in text

    def test_system_prompt_contient_matrice_sensibilite(self, skill: StockValuationSkill):
        text = skill.get_system_prompt()[0]["text"]
        assert "matrice" in text.lower() or "sensibilité" in text.lower() or "sensitivity" in text.lower()

    def test_build_user_message_sans_context(
        self, skill: StockValuationSkill, ratios_valuation_bns: ValuationRatios
    ):
        """Sans aucun contexte, le message contient ticker + ratios JSON."""
        inp = StockValuationInput(ticker="BNS", ratios=ratios_valuation_bns)
        msg = skill._build_user_message(inp, citations=[])
        assert "BNS" in msg
        assert "price" in msg
        assert "Contexte graham" not in msg
        assert "Contexte buffett" not in msg

    def test_build_user_message_avec_buffett_context(
        self, skill: StockValuationSkill, ratios_valuation_bns: ValuationRatios
    ):
        """Avec buffett_context, le message mentionne la section contexte buffett_quality."""
        ctx = BuffettContext(quality_score=3, verdict="COMPOUNDER", owner_earnings=8.5)
        inp = StockValuationInput(
            ticker="BNS", ratios=ratios_valuation_bns, buffett_context=ctx
        )
        msg = skill._build_user_message(inp, citations=[])
        assert "Contexte buffett_quality" in msg
        assert "3" in msg  # quality_score
        assert "COMPOUNDER" in msg

    def test_build_user_message_avec_tous_contexts(
        self, skill: StockValuationSkill, ratios_valuation_bns: ValuationRatios
    ):
        """Avec tous les contextes, le message les mentionne tous."""
        graham = GrahamContext(
            verdict="CANDIDAT_SOLIDE",
            defensive_score=6,
            marge_securite=0.15,
            valeur_intrinseque_simple=92.0,
        )
        earnings = EarningsContext(verdict="AUCUN_SIGNAL", z_score=4.1, f_score=8)
        dorsey = DorseyContext(moat_type="NARROW", roic_durability="FORTE")
        buffett = BuffettContext(quality_score=3, verdict="QUALITE_CORRECTE", owner_earnings=8.5)
        inp = StockValuationInput(
            ticker="BNS",
            ratios=ratios_valuation_bns,
            graham_context=graham,
            earnings_context=earnings,
            dorsey_context=dorsey,
            buffett_context=buffett,
        )
        msg = skill._build_user_message(inp, citations=[])
        assert "Contexte graham_analysis" in msg
        assert "Contexte earnings_quality" in msg
        assert "Contexte dorsey_moat" in msg
        assert "Contexte buffett_quality" in msg

    @pytest.mark.asyncio
    async def test_get_citations_rag_absent(self):
        """StockValuationSkill instancié avec rag_service=None → get_citations() retourne []."""
        skill = StockValuationSkill(
            client=MagicMock(), model="claude-sonnet-4-6", rag_service=None
        )
        citations = await skill.get_citations("test query")
        assert citations == []

    @pytest.mark.asyncio
    async def test_execute_mock_claude(
        self,
        ratios_valuation_bns: ValuationRatios,
        valuation_output_bns: StockValuationOutput,
    ):
        """execute() retourne (StockValuationOutput, UsageDetail) avec cost_usd > 0."""
        mock_response = MagicMock()
        mock_block = MagicMock()
        mock_block.type = "tool_use"
        mock_block.input = valuation_output_bns.model_dump(exclude={"citations", "cost_usd"})
        mock_response.content = [mock_block]
        mock_response.stop_reason = "tool_use"
        mock_response.usage = SimpleNamespace(
            input_tokens=900,
            output_tokens=600,
            cache_read_input_tokens=1500,
            cache_creation_input_tokens=0,
        )
        mock_client = MagicMock()
        mock_client.messages = AsyncMock()
        mock_client.messages.create.return_value = mock_response

        skill = StockValuationSkill(client=mock_client, model="claude-sonnet-4-6")
        inp = StockValuationInput(ticker="BNS", ratios=ratios_valuation_bns)
        output, usage = await skill.execute(inp)

        assert isinstance(output, StockValuationOutput)
        assert isinstance(usage, UsageDetail)
        assert usage.cost_usd > 0
        assert output.cost_usd == usage.cost_usd

    @pytest.mark.asyncio
    async def test_execute_cost_usd_injecte_dans_output(
        self,
        ratios_valuation_bns: ValuationRatios,
        valuation_output_bns: StockValuationOutput,
    ):
        mock_response = MagicMock()
        mock_block = MagicMock()
        mock_block.type = "tool_use"
        mock_block.input = valuation_output_bns.model_dump(exclude={"citations", "cost_usd"})
        mock_response.content = [mock_block]
        mock_response.stop_reason = "tool_use"
        mock_response.usage = SimpleNamespace(
            input_tokens=900,
            output_tokens=600,
            cache_read_input_tokens=0,
            cache_creation_input_tokens=1500,
        )
        mock_client = MagicMock()
        mock_client.messages = AsyncMock()
        mock_client.messages.create.return_value = mock_response

        skill = StockValuationSkill(client=mock_client, model="claude-sonnet-4-6")
        inp = StockValuationInput(ticker="BNS", ratios=ratios_valuation_bns)
        output, usage = await skill.execute(inp)

        assert output.cost_usd == usage.cost_usd

    @pytest.mark.asyncio
    async def test_execute_avec_buffett_context(
        self,
        ratios_valuation_bns: ValuationRatios,
        valuation_output_bns: StockValuationOutput,
    ):
        """execute() transmet le contexte buffett dans le message utilisateur."""
        mock_response = MagicMock()
        mock_block = MagicMock()
        mock_block.type = "tool_use"
        mock_block.input = valuation_output_bns.model_dump(exclude={"citations", "cost_usd"})
        mock_response.content = [mock_block]
        mock_response.stop_reason = "tool_use"
        mock_response.usage = SimpleNamespace(
            input_tokens=900,
            output_tokens=600,
            cache_read_input_tokens=1200,
            cache_creation_input_tokens=0,
        )
        mock_client = MagicMock()
        mock_client.messages = AsyncMock()
        mock_client.messages.create.return_value = mock_response

        skill = StockValuationSkill(client=mock_client, model="claude-sonnet-4-6")
        ctx = BuffettContext(quality_score=4, verdict="COMPOUNDER", owner_earnings=9.0)
        inp = StockValuationInput(
            ticker="BNS", ratios=ratios_valuation_bns, buffett_context=ctx
        )
        await skill.execute(inp)

        call_kwargs = mock_client.messages.create.call_args.kwargs
        user_content = call_kwargs["messages"][0]["content"]
        assert "Contexte buffett_quality" in user_content
        assert "COMPOUNDER" in user_content

    def test_valuation_matrice_4x4_ou_5x5(self, valuation_output_bns: StockValuationOutput):
        """La matrice de sensibilité doit être 4×4 ou 5×5."""
        matrix = valuation_output_bns.matrice_sensibilite
        assert len(matrix.wacc_range) in {4, 5}
        assert len(matrix.growth_range) in {4, 5}
        assert len(matrix.values) == len(matrix.wacc_range)
        for row in matrix.values:
            assert len(row) == len(matrix.growth_range)

    def test_valuation_marge_securite_calcul(self, valuation_output_bns: StockValuationOutput):
        """marge_securite_composite = (fourchette_centrale - prix) / fourchette_centrale."""
        prix = 80.0
        fourchette_centrale = valuation_output_bns.fourchette_centrale
        marge_attendue = (fourchette_centrale - prix) / fourchette_centrale
        # La valeur est calculée par Claude et retournée dans l'output
        assert isinstance(valuation_output_bns.marge_securite_composite, float)
        # Vérifie que la marge dans l'output est cohérente avec la formule
        assert abs(valuation_output_bns.marge_securite_composite - marge_attendue) < 0.01


# ---------------------------------------------------------------------------
# Tests intégration orchestrateur
# ---------------------------------------------------------------------------


class TestOrchestratorValuation:
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
    def mock_dorsey_skill(self):
        from app.skills.tier2.dorsey_moat.schemas import DorseyMoatOutput, MoatSource
        from app.skills.tier2.dorsey_moat.skill import DorseyMoatSkill
        dorsey_out = DorseyMoatOutput(
            ticker="BNS",
            moat_type="NARROW",
            sources_identifiees=[
                MoatSource(source="intangibles", present=True, intensite="MODÉRÉE", justification="test"),
                MoatSource(source="switching_costs", present=True, intensite="MODÉRÉE", justification="test"),
                MoatSource(source="network_effects", present=False, intensite="ABSENTE", justification="test"),
                MoatSource(source="cost_advantages", present=False, intensite="FAIBLE", justification="test"),
                MoatSource(source="efficient_scale", present=False, intensite="FAIBLE", justification="test"),
            ],
            roic_durability="FORTE",
            verdict_detail="NARROW moat pour BNS",
            drapeaux_rouges=[],
            recommandation_prochaine_etape=["buffett_quality"],
        )
        skill = AsyncMock(spec=DorseyMoatSkill)
        skill.execute.return_value = (dorsey_out, _make_usage())
        return skill

    @pytest.fixture
    def mock_buffett_skill(self):
        from app.skills.tier2.buffett_quality.schemas import (
            BuffettFiltre,
            BuffettQualityOutput,
        )
        from app.skills.tier2.buffett_quality.skill import BuffettQualitySkill
        buffett_out = BuffettQualityOutput(
            ticker="BNS",
            filtres=[
                BuffettFiltre(filtre="comprehensible", passe=True, score=1, justification="test"),
                BuffettFiltre(filtre="economics_favorables", passe=True, score=1, justification="test"),
                BuffettFiltre(filtre="management_fiable", passe=False, score=0, justification="test"),
                BuffettFiltre(filtre="prix_attractif", passe=False, score=0, justification="test"),
            ],
            owner_earnings=8.5,
            quality_score=2,
            verdict="QUALITE_CORRECTE",
            verdict_detail="2/4 filtres passés.",
            drapeaux_rouges=[],
            recommandation_prochaine_etape=["stock_valuation_triangulation"],
        )
        skill = AsyncMock(spec=BuffettQualitySkill)
        skill.execute.return_value = (buffett_out, _make_usage())
        return skill

    @pytest.fixture
    def mock_valuation_skill(self, valuation_output_bns):
        skill = AsyncMock(spec=StockValuationSkill)
        skill.execute.return_value = (valuation_output_bns, _make_usage())
        return skill

    @pytest.fixture
    def ratios_earnings_bns(self) -> EarningsQualityRatios:
        return EarningsQualityRatios(
            sales_t=38000,
            sales_t1=36000,
            cogs_t=12000,
            cogs_t1=11500,
            net_income_t=10200,
            cfo_t=11000,
            receivables_t=4500,
            receivables_t1=4200,
            current_assets_t=95000,
            current_liabilities_t=88000,
            total_assets_t=1_100_000,
            total_assets_t1=1_050_000,
        )

    @pytest.mark.asyncio
    async def test_orchestrator_avec_valuation(
        self,
        mock_db_pool,
        mock_graham_skill,
        mock_earnings_skill,
        mock_dorsey_skill,
        mock_buffett_skill,
        mock_valuation_skill,
        ratios_msft,
        ratios_earnings_bns,
        ratios_dorsey_bns,
        ratios_buffett_bns,
        ratios_valuation_bns,
    ):
        """Avec valuation_ratios → response.valuation non None, skills_applied contient stock_valuation_triangulation."""
        orchestrator = Orchestrator(
            db_pool=mock_db_pool,
            graham_skill=mock_graham_skill,
            earnings_skill=mock_earnings_skill,
            dorsey_skill=mock_dorsey_skill,
            buffett_skill=mock_buffett_skill,
            valuation_skill=mock_valuation_skill,
        )
        req = AnalyzeRequest(
            ticker="BNS",
            ratios=ratios_msft,
            workflow="compounder_buffett",
            earnings_ratios=ratios_earnings_bns,
            dorsey_ratios=ratios_dorsey_bns,
            buffett_ratios=ratios_buffett_bns,
            valuation_ratios=ratios_valuation_bns,
        )
        response = await orchestrator.run_company_analysis(req)

        assert response.valuation is not None
        assert "stock_valuation_triangulation" in response.skills_applied
        mock_valuation_skill.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_orchestrator_sans_valuation(
        self,
        mock_db_pool,
        mock_graham_skill,
        mock_earnings_skill,
        mock_dorsey_skill,
        mock_buffett_skill,
        mock_valuation_skill,
        ratios_msft,
        ratios_earnings_bns,
    ):
        """Sans valuation_ratios → response.valuation est None, skill non appelé."""
        orchestrator = Orchestrator(
            db_pool=mock_db_pool,
            graham_skill=mock_graham_skill,
            earnings_skill=mock_earnings_skill,
            dorsey_skill=mock_dorsey_skill,
            buffett_skill=mock_buffett_skill,
            valuation_skill=mock_valuation_skill,
        )
        req = AnalyzeRequest(
            ticker="BNS",
            ratios=ratios_msft,
            earnings_ratios=ratios_earnings_bns,
        )
        response = await orchestrator.run_company_analysis(req)

        assert response.valuation is None
        assert "stock_valuation_triangulation" not in response.skills_applied
        mock_valuation_skill.execute.assert_not_called()

    @pytest.mark.asyncio
    async def test_buffett_context_passe_a_valuation(
        self,
        mock_db_pool,
        graham_output_msft,
        earnings_output_msft,
        ratios_msft,
        ratios_earnings_bns,
        ratios_dorsey_bns,
        ratios_buffett_bns,
        ratios_valuation_bns,
        valuation_output_bns,
    ):
        """L'orchestrateur transmet le quality_score Buffett à StockValuationInput."""
        from app.skills.tier2.buffett_quality.schemas import (
            BuffettFiltre,
            BuffettQualityOutput,
        )
        from app.skills.tier2.buffett_quality.skill import BuffettQualitySkill
        from app.skills.tier2.dorsey_moat.schemas import DorseyMoatOutput, MoatSource
        from app.skills.tier2.dorsey_moat.skill import DorseyMoatSkill

        buffett_out = BuffettQualityOutput(
            ticker="BNS",
            filtres=[
                BuffettFiltre(filtre="comprehensible", passe=True, score=1, justification="t"),
                BuffettFiltre(filtre="economics_favorables", passe=True, score=1, justification="t"),
                BuffettFiltre(filtre="management_fiable", passe=True, score=1, justification="t"),
                BuffettFiltre(filtre="prix_attractif", passe=False, score=0, justification="t"),
            ],
            owner_earnings=9.0,
            quality_score=3,
            verdict="COMPOUNDER",
            verdict_detail="3/4 filtres.",
            drapeaux_rouges=[],
            recommandation_prochaine_etape=["stock_valuation_triangulation"],
        )
        dorsey_out = DorseyMoatOutput(
            ticker="BNS",
            moat_type="WIDE",
            sources_identifiees=[
                MoatSource(source="intangibles", present=True, intensite="FORTE", justification="t"),
                MoatSource(source="switching_costs", present=True, intensite="FORTE", justification="t"),
                MoatSource(source="network_effects", present=False, intensite="ABSENTE", justification="t"),
                MoatSource(source="cost_advantages", present=False, intensite="ABSENTE", justification="t"),
                MoatSource(source="efficient_scale", present=False, intensite="ABSENTE", justification="t"),
            ],
            roic_durability="FORTE",
            verdict_detail="WIDE moat",
            drapeaux_rouges=[],
            recommandation_prochaine_etape=[],
        )

        mock_graham = AsyncMock()
        mock_graham.execute.return_value = (graham_output_msft, _make_usage())
        mock_earnings = AsyncMock()
        mock_earnings.execute.return_value = (earnings_output_msft, _make_usage())
        mock_dorsey = AsyncMock(spec=DorseyMoatSkill)
        mock_dorsey.execute.return_value = (dorsey_out, _make_usage())
        mock_buffett = AsyncMock(spec=BuffettQualitySkill)
        mock_buffett.execute.return_value = (buffett_out, _make_usage())
        mock_valuation = AsyncMock(spec=StockValuationSkill)
        mock_valuation.execute.return_value = (valuation_output_bns, _make_usage())

        orchestrator = Orchestrator(
            db_pool=mock_db_pool,
            graham_skill=mock_graham,
            earnings_skill=mock_earnings,
            dorsey_skill=mock_dorsey,
            buffett_skill=mock_buffett,
            valuation_skill=mock_valuation,
        )
        req = AnalyzeRequest(
            ticker="BNS",
            ratios=ratios_msft,
            workflow="compounder_buffett",
            earnings_ratios=ratios_earnings_bns,
            dorsey_ratios=ratios_dorsey_bns,
            buffett_ratios=ratios_buffett_bns,
            valuation_ratios=ratios_valuation_bns,
        )
        await orchestrator.run_company_analysis(req)

        call_args = mock_valuation.execute.call_args
        val_input: StockValuationInput = call_args.args[0]
        assert val_input.buffett_context is not None
        assert val_input.buffett_context.quality_score == 3
        assert val_input.buffett_context.verdict == "COMPOUNDER"
        assert val_input.buffett_context.owner_earnings == pytest.approx(9.0)

    @pytest.mark.asyncio
    async def test_valuation_sans_buffett_pas_de_buffett_context(
        self,
        mock_db_pool,
        graham_output_msft,
        ratios_msft,
        ratios_valuation_bns,
        valuation_output_bns,
    ):
        """Sans buffett_ratios → buffett_context est None dans StockValuationInput."""
        mock_graham = AsyncMock()
        mock_graham.execute.return_value = (graham_output_msft, _make_usage())
        mock_earnings = AsyncMock()
        mock_valuation = AsyncMock(spec=StockValuationSkill)
        mock_valuation.execute.return_value = (valuation_output_bns, _make_usage())

        orchestrator = Orchestrator(
            db_pool=mock_db_pool,
            graham_skill=mock_graham,
            earnings_skill=mock_earnings,
            valuation_skill=mock_valuation,
        )
        req = AnalyzeRequest(
            ticker="BNS",
            ratios=ratios_msft,
            valuation_ratios=ratios_valuation_bns,
        )
        await orchestrator.run_company_analysis(req)

        call_args = mock_valuation.execute.call_args
        val_input: StockValuationInput = call_args.args[0]
        assert val_input.buffett_context is None

    @pytest.mark.asyncio
    async def test_valuation_workflow_complet_5_skills(
        self,
        mock_db_pool,
        mock_graham_skill,
        mock_earnings_skill,
        mock_dorsey_skill,
        mock_buffett_skill,
        mock_valuation_skill,
        ratios_msft,
        ratios_earnings_bns,
        ratios_dorsey_bns,
        ratios_buffett_bns,
        ratios_valuation_bns,
    ):
        """graham + earnings + dorsey + buffett + valuation → 5 skills dans skills_applied."""
        u1 = UsageDetail(tokens_input=500, tokens_output=200, tokens_cache_read=0, tokens_cache_creation=1500, cost_usd=0.003, model="claude-sonnet-4-6")
        u2 = UsageDetail(tokens_input=800, tokens_output=600, tokens_cache_read=1200, tokens_cache_creation=0, cost_usd=0.004, model="claude-sonnet-4-6")
        u3 = UsageDetail(tokens_input=700, tokens_output=400, tokens_cache_read=1200, tokens_cache_creation=0, cost_usd=0.005, model="claude-sonnet-4-6")
        u4 = UsageDetail(tokens_input=750, tokens_output=450, tokens_cache_read=1200, tokens_cache_creation=0, cost_usd=0.006, model="claude-sonnet-4-6")
        u5 = UsageDetail(tokens_input=900, tokens_output=600, tokens_cache_read=1500, tokens_cache_creation=0, cost_usd=0.007, model="claude-sonnet-4-6")

        from app.skills.tier2.buffett_quality.schemas import BuffettFiltre, BuffettQualityOutput
        from app.skills.tier2.buffett_quality.skill import BuffettQualitySkill
        from app.skills.tier2.dorsey_moat.schemas import DorseyMoatOutput, MoatSource
        from app.skills.tier2.dorsey_moat.skill import DorseyMoatSkill

        dorsey_out = DorseyMoatOutput(
            ticker="BNS",
            moat_type="NARROW",
            sources_identifiees=[MoatSource(source=n, present=False, intensite="ABSENTE", justification="t") for n in ["intangibles", "switching_costs", "network_effects", "cost_advantages", "efficient_scale"]],
            roic_durability="MODÉRÉE",
            verdict_detail="test",
            drapeaux_rouges=[],
            recommandation_prochaine_etape=[],
        )
        buffett_out = BuffettQualityOutput(
            ticker="BNS",
            filtres=[BuffettFiltre(filtre=n, passe=False, score=0, justification="t") for n in ["comprehensible", "economics_favorables", "management_fiable", "prix_attractif"]],
            owner_earnings=None,
            quality_score=0,
            verdict="REJETER",
            verdict_detail="0/4",
            drapeaux_rouges=[],
            recommandation_prochaine_etape=[],
        )

        mock_g = AsyncMock(); mock_g.execute.return_value = (mock_graham_skill.execute.return_value[0], u1)
        mock_e = AsyncMock(); mock_e.execute.return_value = (mock_earnings_skill.execute.return_value[0], u2)
        mock_d = AsyncMock(spec=DorseyMoatSkill); mock_d.execute.return_value = (dorsey_out, u3)
        mock_b = AsyncMock(spec=BuffettQualitySkill); mock_b.execute.return_value = (buffett_out, u4)
        mock_v = AsyncMock(spec=StockValuationSkill); mock_v.execute.return_value = (mock_valuation_skill.execute.return_value[0], u5)

        orchestrator = Orchestrator(
            db_pool=mock_db_pool,
            graham_skill=mock_g,
            earnings_skill=mock_e,
            dorsey_skill=mock_d,
            buffett_skill=mock_b,
            valuation_skill=mock_v,
        )
        req = AnalyzeRequest(
            ticker="BNS",
            ratios=ratios_msft,
            workflow="compounder_buffett",
            earnings_ratios=ratios_earnings_bns,
            dorsey_ratios=ratios_dorsey_bns,
            buffett_ratios=ratios_buffett_bns,
            valuation_ratios=ratios_valuation_bns,
        )
        response = await orchestrator.run_company_analysis(req)

        assert response.skills_applied == [
            "graham_analysis",
            "earnings_quality",
            "dorsey_moat",
            "buffett_quality",
            "stock_valuation_triangulation",
        ]
        assert abs(response.cost_usd - (0.003 + 0.004 + 0.005 + 0.006 + 0.007)) < 1e-9
