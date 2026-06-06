"""Tests de l'Orchestrator — workflow company_analysis avec skills et DB mockés."""
from __future__ import annotations

import json
import uuid
from unittest.mock import AsyncMock

import pytest

from app.models.tenant import LEGACY_TENANT_ID
from app.orchestrator.core import AnalyzeRequest, AnalyzeResponse, Orchestrator
from app.skills.base import UsageDetail
from app.skills.tier2.earnings_quality.schemas import EarningsQualityInput
from app.skills.tier2.earnings_quality.skill import EarningsQualitySkill
from app.skills.tier2.graham_analysis.skill import GrahamAnalysisSkill


def _make_usage() -> UsageDetail:
    """Crée un UsageDetail de test avec des tokens non-zéro."""
    return UsageDetail(
        tokens_input=1000,
        tokens_output=200,
        tokens_cache_read=0,
        tokens_cache_creation=1500,
        cost_usd=0.0056,
        model="claude-sonnet-4-6",
    )


@pytest.fixture
def mock_usage() -> UsageDetail:
    """UsageDetail mocké avec des tokens non-zéro."""
    return _make_usage()


@pytest.fixture
def mock_db_pool(graham_output_msft):
    """Pool asyncpg mocké retournant un UUID fixe sur fetchrow."""
    pool = AsyncMock()
    pool.fetchrow.return_value = {"id": uuid.UUID("550e8400-e29b-41d4-a716-446655440000")}
    return pool


@pytest.fixture
def db_pool_mock(mock_db_pool):
    """Alias de mock_db_pool pour les tests de context enrichment."""
    return mock_db_pool


@pytest.fixture
def mock_graham_skill(graham_output_msft, mock_usage):
    """GrahamAnalysisSkill mocké — execute retourne le tuple (output, usage)."""
    skill = AsyncMock(spec=GrahamAnalysisSkill)
    skill.execute.return_value = (graham_output_msft, mock_usage)
    return skill


@pytest.fixture
def mock_earnings_skill(earnings_output_msft, mock_usage):
    """EarningsQualitySkill mocké — execute retourne le tuple (output, usage)."""
    skill = AsyncMock(spec=EarningsQualitySkill)
    skill.execute.return_value = (earnings_output_msft, mock_usage)
    return skill


@pytest.fixture
def orchestrator(mock_db_pool, mock_graham_skill, mock_earnings_skill):
    """Orchestrateur avec dépendances mockées."""
    return Orchestrator(
        db_pool=mock_db_pool,
        graham_skill=mock_graham_skill,
        earnings_skill=mock_earnings_skill,
    )


@pytest.fixture
def request_msft(ratios_msft):
    return AnalyzeRequest(ticker="MSFT", ratios=ratios_msft)


class TestOrchestratorRunCompanyAnalysis:
    @pytest.mark.asyncio
    async def test_retourne_analyze_response(self, orchestrator, request_msft):
        result = await orchestrator.run_company_analysis(request_msft)
        assert isinstance(result, AnalyzeResponse)

    @pytest.mark.asyncio
    async def test_ticker_correct_dans_reponse(self, orchestrator, request_msft):
        result = await orchestrator.run_company_analysis(request_msft)
        assert result.ticker == "MSFT"

    @pytest.mark.asyncio
    async def test_workflow_name_correct(self, orchestrator, request_msft):
        result = await orchestrator.run_company_analysis(request_msft)
        assert result.workflow == "value_graham"  # défaut depuis Sprint 17

    @pytest.mark.asyncio
    async def test_skills_applied_contient_graham(self, orchestrator, request_msft):
        result = await orchestrator.run_company_analysis(request_msft)
        assert result.skills_applied == ["graham_analysis"]

    @pytest.mark.asyncio
    async def test_cost_usd_non_nul(self, orchestrator, request_msft):
        result = await orchestrator.run_company_analysis(request_msft)
        assert result.cost_usd > 0.0

    @pytest.mark.asyncio
    async def test_analysis_id_est_uuid_valide(self, orchestrator, request_msft):
        result = await orchestrator.run_company_analysis(request_msft)
        parsed = uuid.UUID(result.analysis_id)
        assert str(parsed) == result.analysis_id

    @pytest.mark.asyncio
    async def test_graham_output_correct(self, orchestrator, request_msft):
        result = await orchestrator.run_company_analysis(request_msft)
        assert result.graham.ticker == "MSFT"
        assert result.graham.verdict == "REJETER"

    @pytest.mark.asyncio
    async def test_earnings_quality_none_sans_earnings_ratios(self, orchestrator, request_msft):
        result = await orchestrator.run_company_analysis(request_msft)
        assert result.earnings_quality is None

    @pytest.mark.asyncio
    async def test_graham_skill_execute_appele_une_fois(
        self, orchestrator, mock_graham_skill, request_msft
    ):
        await orchestrator.run_company_analysis(request_msft)
        mock_graham_skill.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_graham_skill_recoit_bon_ticker(
        self, orchestrator, mock_graham_skill, request_msft
    ):
        await orchestrator.run_company_analysis(request_msft)
        call_args = mock_graham_skill.execute.call_args[0][0]
        assert call_args.ticker == "MSFT"

    @pytest.mark.asyncio
    async def test_persist_appele_avec_fetchrow(
        self, orchestrator, mock_db_pool, request_msft
    ):
        await orchestrator.run_company_analysis(request_msft)
        mock_db_pool.fetchrow.assert_called_once()

    @pytest.mark.asyncio
    async def test_persist_insert_bon_ticker(
        self, orchestrator, mock_db_pool, request_msft
    ):
        await orchestrator.run_company_analysis(request_msft)
        args = mock_db_pool.fetchrow.call_args[0]
        assert "MSFT" in args

    @pytest.mark.asyncio
    async def test_persist_insert_workflow_dans_args(
        self, orchestrator, mock_db_pool, request_msft
    ):
        await orchestrator.run_company_analysis(request_msft)
        args = mock_db_pool.fetchrow.call_args[0]
        # workflow = défaut "value_graham" si non spécifié dans request
        assert "value_graham" in args

    @pytest.mark.asyncio
    async def test_created_at_non_vide(self, orchestrator, request_msft):
        result = await orchestrator.run_company_analysis(request_msft)
        assert result.created_at != ""
        assert "2026" in result.created_at or "T" in result.created_at

    @pytest.mark.asyncio
    async def test_persist_appele_avec_vrais_tokens(
        self, orchestrator, mock_db_pool, request_msft
    ):
        """_persist reçoit la somme des usages — tokens agrégés persistés en DB."""
        await orchestrator.run_company_analysis(request_msft)
        args = mock_db_pool.fetchrow.call_args[0]
        # args[0]=SQL, [1]=ticker, [2]=workflow, [3..5]=JSON×3
        # [6]=cost_usd, [7]=tokens_input, [8]=tokens_output,
        # [9]=tokens_cache_read, [10]=tokens_cache_creation
        assert args[7] == 1000   # tokens_input
        assert args[8] == 200    # tokens_output
        assert args[10] == 1500  # tokens_cache_creation

    @pytest.mark.asyncio
    async def test_persist_tenant_legacy_par_defaut(
        self, orchestrator, mock_db_pool, request_msft
    ):
        """Sans threading tenant (E3-S4), l'analyse persistée atterrit sur le legacy."""
        await orchestrator.run_company_analysis(request_msft)
        args = mock_db_pool.fetchrow.call_args[0]
        assert args[-1] == LEGACY_TENANT_ID  # dernier binding = tenant_id

    @pytest.mark.asyncio
    async def test_persist_input_data_contient_earnings_valuation(
        self, orchestrator, mock_db_pool, ratios_msft, ratios_earnings_msft
    ):
        """input_data persisté porte les sous-clés earnings/valuation fournies par la requête."""
        from app.skills.tier2.stock_valuation.schemas import ValuationRatios

        req = AnalyzeRequest(
            ticker="MSFT",
            ratios=ratios_msft,
            earnings_ratios=ratios_earnings_msft,
            valuation_ratios=ValuationRatios(ratios_source="Yahoo Finance"),
        )
        await orchestrator.run_company_analysis(req)
        payload = json.loads(mock_db_pool.fetchrow.call_args[0][4])  # [4] = input_data
        assert "earnings_ratios" in payload
        assert "valuation_ratios" in payload
        assert payload["valuation_ratios"]["ratios_source"] == "Yahoo Finance"

    @pytest.mark.asyncio
    async def test_exception_skill_se_propage(
        self, mock_db_pool, mock_earnings_skill, request_msft
    ):
        """Si le skill lève une exception, elle remonte à l'appelant."""
        skill_en_erreur = AsyncMock(spec=GrahamAnalysisSkill)
        skill_en_erreur.execute.side_effect = RuntimeError("Erreur API Claude simulée")
        orchestrateur = Orchestrator(
            db_pool=mock_db_pool,
            graham_skill=skill_en_erreur,
            earnings_skill=mock_earnings_skill,
        )

        with pytest.raises(RuntimeError, match="Erreur API Claude simulée"):
            await orchestrateur.run_company_analysis(request_msft)

    @pytest.mark.asyncio
    async def test_exception_db_se_propage(
        self, mock_graham_skill, mock_earnings_skill, request_msft
    ):
        """Si la DB lève une exception, elle remonte à l'appelant."""
        pool_en_erreur = AsyncMock()
        pool_en_erreur.fetchrow.side_effect = ConnectionError("DB indisponible")
        orchestrateur = Orchestrator(
            db_pool=pool_en_erreur,
            graham_skill=mock_graham_skill,
            earnings_skill=mock_earnings_skill,
        )

        with pytest.raises(ConnectionError, match="DB indisponible"):
            await orchestrateur.run_company_analysis(request_msft)


class TestContextEnrichment:
    @pytest.mark.asyncio
    async def test_earnings_skill_recoit_graham_context(
        self,
        db_pool_mock,
        graham_output_msft,
        earnings_output_msft,
        ratios_msft,
        ratios_earnings_msft,
    ):
        """L'orchestrateur passe le verdict Graham à earnings_quality."""
        mock_graham = AsyncMock()
        mock_graham.execute.return_value = (graham_output_msft, _make_usage())

        mock_earnings = AsyncMock()
        mock_earnings.execute.return_value = (earnings_output_msft, _make_usage())

        orchestrator = Orchestrator(
            db_pool=db_pool_mock,
            graham_skill=mock_graham,
            earnings_skill=mock_earnings,
        )
        req = AnalyzeRequest(
            ticker="MSFT", ratios=ratios_msft, earnings_ratios=ratios_earnings_msft
        )
        await orchestrator.run_company_analysis(req)

        call_args = mock_earnings.execute.call_args
        earnings_input: EarningsQualityInput = call_args.args[0]
        assert earnings_input.graham_context is not None
        assert earnings_input.graham_context.verdict == graham_output_msft.verdict

    @pytest.mark.asyncio
    async def test_graham_context_defensive_score_transmis(
        self,
        db_pool_mock,
        graham_output_msft,
        earnings_output_msft,
        ratios_msft,
        ratios_earnings_msft,
    ):
        """L'orchestrateur transmet le defensive_score Graham dans le contexte."""
        mock_graham = AsyncMock()
        mock_graham.execute.return_value = (graham_output_msft, _make_usage())

        mock_earnings = AsyncMock()
        mock_earnings.execute.return_value = (earnings_output_msft, _make_usage())

        orchestrator = Orchestrator(
            db_pool=db_pool_mock,
            graham_skill=mock_graham,
            earnings_skill=mock_earnings,
        )
        req = AnalyzeRequest(
            ticker="MSFT", ratios=ratios_msft, earnings_ratios=ratios_earnings_msft
        )
        await orchestrator.run_company_analysis(req)

        call_args = mock_earnings.execute.call_args
        earnings_input: EarningsQualityInput = call_args.args[0]
        assert earnings_input.graham_context.defensive_score == graham_output_msft.defensive_score

    @pytest.mark.asyncio
    async def test_sans_earnings_ratios_workflow_reste_graham(
        self,
        db_pool_mock,
        graham_output_msft,
        ratios_msft,
    ):
        """Sans earnings_ratios, earnings_quality n'est pas appelé."""
        mock_graham = AsyncMock()
        mock_graham.execute.return_value = (graham_output_msft, _make_usage())
        mock_earnings = AsyncMock()

        orchestrator = Orchestrator(
            db_pool=db_pool_mock,
            graham_skill=mock_graham,
            earnings_skill=mock_earnings,
        )
        req = AnalyzeRequest(ticker="MSFT", ratios=ratios_msft)
        response = await orchestrator.run_company_analysis(req)

        mock_earnings.execute.assert_not_called()
        assert response.earnings_quality is None
        assert "earnings_quality" not in response.skills_applied

    @pytest.mark.asyncio
    async def test_avec_earnings_skills_applied_complet(
        self,
        db_pool_mock,
        graham_output_msft,
        earnings_output_msft,
        ratios_msft,
        ratios_earnings_msft,
    ):
        """Avec earnings_ratios, skills_applied contient les deux skills."""
        mock_graham = AsyncMock()
        mock_graham.execute.return_value = (graham_output_msft, _make_usage())

        mock_earnings = AsyncMock()
        mock_earnings.execute.return_value = (earnings_output_msft, _make_usage())

        orchestrator = Orchestrator(
            db_pool=db_pool_mock,
            graham_skill=mock_graham,
            earnings_skill=mock_earnings,
        )
        req = AnalyzeRequest(
            ticker="MSFT", ratios=ratios_msft, earnings_ratios=ratios_earnings_msft
        )
        response = await orchestrator.run_company_analysis(req)

        assert response.skills_applied == ["graham_analysis", "earnings_quality"]
        assert response.earnings_quality is not None

    @pytest.mark.asyncio
    async def test_cost_usd_est_somme_des_skills(
        self,
        db_pool_mock,
        graham_output_msft,
        earnings_output_msft,
        ratios_msft,
        ratios_earnings_msft,
    ):
        """cost_usd de la réponse = somme des deux appels Claude."""
        usage1 = UsageDetail(
            tokens_input=500, tokens_output=200,
            tokens_cache_read=0, tokens_cache_creation=1500,
            cost_usd=0.003, model="claude-sonnet-4-6",
        )
        usage2 = UsageDetail(
            tokens_input=800, tokens_output=600,
            tokens_cache_read=1200, tokens_cache_creation=0,
            cost_usd=0.004, model="claude-sonnet-4-6",
        )
        mock_graham = AsyncMock()
        mock_graham.execute.return_value = (graham_output_msft, usage1)

        mock_earnings = AsyncMock()
        mock_earnings.execute.return_value = (earnings_output_msft, usage2)

        orchestrator = Orchestrator(
            db_pool=db_pool_mock,
            graham_skill=mock_graham,
            earnings_skill=mock_earnings,
        )
        req = AnalyzeRequest(
            ticker="MSFT", ratios=ratios_msft, earnings_ratios=ratios_earnings_msft
        )
        response = await orchestrator.run_company_analysis(req)

        assert abs(response.cost_usd - 0.007) < 1e-9
