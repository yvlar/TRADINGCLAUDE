"""Tests du skill earnings_quality — schemas, skill, context enrichment."""
from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest
from pydantic import ValidationError


def _earnings_tool_use_response(output: "EarningsQualityOutput", **usage_overrides) -> MagicMock:
    """Construit une réponse Anthropic simulée avec bloc tool_use pour earnings_quality."""
    mock_block = MagicMock()
    mock_block.type = "tool_use"
    mock_block.input = output.model_dump(exclude={"confidence_score"})
    mock_response = MagicMock()
    mock_response.content = [mock_block]
    mock_response.stop_reason = "tool_use"
    defaults = dict(
        input_tokens=800,
        output_tokens=600,
        cache_read_input_tokens=0,
        cache_creation_input_tokens=1500,
    )
    defaults.update(usage_overrides)
    mock_response.usage = SimpleNamespace(**defaults)
    return mock_response

from app.skills.base import UsageDetail
from app.skills.tier2.earnings_quality.schemas import (
    EarningsQualityInput,
    EarningsQualityOutput,
    EarningsQualityRatios,
    GrahamContext,
)
from app.skills.tier2.earnings_quality.skill import EarningsQualitySkill


class TestEarningsQualitySchemas:
    def test_output_valide_se_construit(self, earnings_output_msft: EarningsQualityOutput):
        assert earnings_output_msft.ticker == "MSFT"

    def test_f_score_8_criteres_leve_erreur(self, earnings_output_msft: EarningsQualityOutput):
        """@model_validator rejette si f_score.criteria != 9."""
        data = earnings_output_msft.model_dump()
        data["f_score"]["criteria"] = data["f_score"]["criteria"][:8]
        with pytest.raises(ValidationError):
            EarningsQualityOutput.model_validate(data)

    def test_c_score_5_signaux_leve_erreur(self, earnings_output_msft: EarningsQualityOutput):
        """@model_validator rejette si c_score.signaux != 6."""
        data = earnings_output_msft.model_dump()
        data["c_score"]["signaux"] = data["c_score"]["signaux"][:5]
        with pytest.raises(ValidationError):
            EarningsQualityOutput.model_validate(data)

    def test_verdict_invalide_leve_erreur(self, earnings_output_msft: EarningsQualityOutput):
        data = earnings_output_msft.model_dump()
        data["verdict"] = "INCONNU"
        with pytest.raises(ValidationError):
            EarningsQualityOutput.model_validate(data)

    def test_graham_context_optionnel(self, ratios_earnings_msft: EarningsQualityRatios):
        inp = EarningsQualityInput(ticker="MSFT", ratios=ratios_earnings_msft)
        assert inp.graham_context is None

    def test_graham_context_peuple(self, ratios_earnings_msft: EarningsQualityRatios):
        ctx = GrahamContext(
            verdict="CANDIDAT_SOLIDE",
            defensive_score=6,
            marge_securite=0.18,
            drapeaux_rouges=[],
        )
        inp = EarningsQualityInput(
            ticker="MSFT", ratios=ratios_earnings_msft, graham_context=ctx
        )
        assert inp.graham_context.defensive_score == 6

    def test_verdict_aucun_signal_accepte(self, earnings_output_msft: EarningsQualityOutput):
        assert earnings_output_msft.verdict == "AUCUN_SIGNAL"

    def test_verdict_rejeter_accepte(self, earnings_output_msft: EarningsQualityOutput):
        data = earnings_output_msft.model_dump()
        data["verdict"] = "REJETER"
        output = EarningsQualityOutput.model_validate(data)
        assert output.verdict == "REJETER"

    def test_is_financial_defaut_false(self, earnings_output_msft: EarningsQualityOutput):
        assert earnings_output_msft.is_financial is False

    def test_citations_defaut_vide(self, earnings_output_msft: EarningsQualityOutput):
        assert earnings_output_msft.citations == []

    def test_cost_usd_defaut_zero(self, earnings_output_msft: EarningsQualityOutput):
        assert earnings_output_msft.cost_usd == 0.0

    def test_z_score_infini_rejete(self, earnings_output_msft: EarningsQualityOutput):
        """Un z_score non fini (inf) produit par le LLM est rejeté avant persistance."""
        data = earnings_output_msft.model_dump()
        data["z_score"]["z_score"] = float("inf")
        with pytest.raises(ValidationError):
            EarningsQualityOutput.model_validate(data)

    def test_m_score_nan_rejete(self, earnings_output_msft: EarningsQualityOutput):
        """Un m_score NaN produit par le LLM est rejeté avant persistance."""
        data = earnings_output_msft.model_dump()
        data["m_score"]["m_score"] = float("nan")
        with pytest.raises(ValidationError):
            EarningsQualityOutput.model_validate(data)

    def test_accrual_ratio_infini_rejete(self, earnings_output_msft: EarningsQualityOutput):
        """Tout ratio float|None exposé rejette NaN/inf (réflexe généralisé)."""
        data = earnings_output_msft.model_dump()
        data["sloan"]["accrual_ratio"] = float("-inf")
        with pytest.raises(ValidationError):
            EarningsQualityOutput.model_validate(data)

    def test_z_score_hors_plage_rejete(self, earnings_output_msft: EarningsQualityOutput):
        """Un z_score fini mais invraisemblable (|Z| > 50) est rejeté."""
        data = earnings_output_msft.model_dump()
        data["z_score"]["z_score"] = 999.0
        with pytest.raises(ValidationError):
            EarningsQualityOutput.model_validate(data)

    def test_m_score_hors_plage_rejete(self, earnings_output_msft: EarningsQualityOutput):
        """Un m_score fini mais invraisemblable (|M| > 20) est rejeté."""
        data = earnings_output_msft.model_dump()
        data["m_score"]["m_score"] = -75.0
        with pytest.raises(ValidationError):
            EarningsQualityOutput.model_validate(data)

    def test_score_plausible_accepte(self, earnings_output_msft: EarningsQualityOutput):
        """Un z_score/m_score dans les bornes plausibles passe sans erreur (pas de régression)."""
        data = earnings_output_msft.model_dump()
        data["z_score"]["z_score"] = 3.5
        data["m_score"]["m_score"] = -2.1
        output = EarningsQualityOutput.model_validate(data)
        assert output.z_score.z_score == 3.5
        assert output.m_score.m_score == -2.1


class TestEarningsQualitySkill:
    @pytest.fixture
    def skill(self) -> EarningsQualitySkill:
        return EarningsQualitySkill(client=MagicMock(), model="claude-sonnet-4-6")

    def test_skill_id(self, skill: EarningsQualitySkill):
        assert skill.skill_id == "earnings_quality"

    def test_tier(self, skill: EarningsQualitySkill):
        assert skill.tier == 2

    def test_system_prompt_charge_et_cache(self, skill: EarningsQualitySkill):
        blocks = skill.get_system_prompt()
        assert blocks[0]["cache_control"]["type"] == "ephemeral"
        assert len(blocks[0]["text"]) > 1024

    def test_system_prompt_contient_beneish(self, skill: EarningsQualitySkill):
        text = skill.get_system_prompt()[0]["text"]
        assert "Beneish" in text

    def test_system_prompt_contient_piotroski(self, skill: EarningsQualitySkill):
        text = skill.get_system_prompt()[0]["text"]
        assert "Piotroski" in text

    def test_system_prompt_contient_altman(self, skill: EarningsQualitySkill):
        text = skill.get_system_prompt()[0]["text"]
        assert "Altman" in text

    @pytest.mark.asyncio
    async def test_execute_retourne_tuple(
        self,
        ratios_earnings_msft: EarningsQualityRatios,
        earnings_output_msft: EarningsQualityOutput,
    ):
        """execute() retourne (EarningsQualityOutput, UsageDetail)."""
        mock_response = _earnings_tool_use_response(
            earnings_output_msft,
            cache_read_input_tokens=1200,
            cache_creation_input_tokens=0,
        )
        mock_client = MagicMock()
        mock_client.messages = AsyncMock()
        mock_client.messages.create.return_value = mock_response

        skill = EarningsQualitySkill(client=mock_client, model="claude-sonnet-4-6")
        inp = EarningsQualityInput(ticker="MSFT", ratios=ratios_earnings_msft)
        output, usage = await skill.execute(inp)

        assert isinstance(output, EarningsQualityOutput)
        assert isinstance(usage, UsageDetail)
        assert usage.tokens_cache_read == 1200

    @pytest.mark.asyncio
    async def test_execute_sans_rag_fonctionne(
        self,
        ratios_earnings_msft: EarningsQualityRatios,
        earnings_output_msft: EarningsQualityOutput,
    ):
        """EarningsQualitySkill(rag_service=None) doit fonctionner."""
        mock_client = MagicMock()
        mock_client.messages = AsyncMock()
        mock_client.messages.create.return_value = _earnings_tool_use_response(earnings_output_msft)

        skill = EarningsQualitySkill(client=mock_client, model="claude-sonnet-4-6", rag_service=None)
        inp = EarningsQualityInput(ticker="MSFT", ratios=ratios_earnings_msft)
        output, usage = await skill.execute(inp)

        assert output.ticker == "MSFT"
        assert usage.tokens_cache_creation == 1500

    @pytest.mark.asyncio
    async def test_user_message_contient_contexte_graham(
        self,
        ratios_earnings_msft: EarningsQualityRatios,
        earnings_output_msft: EarningsQualityOutput,
    ):
        """Si graham_context fourni, le message utilisateur le mentionne."""
        mock_client = MagicMock()
        mock_client.messages = AsyncMock()
        mock_client.messages.create.return_value = _earnings_tool_use_response(earnings_output_msft)

        skill = EarningsQualitySkill(client=mock_client, model="claude-sonnet-4-6")
        ctx = GrahamContext(
            verdict="CANDIDAT_SOLIDE",
            defensive_score=6,
            marge_securite=0.18,
            drapeaux_rouges=["P/E élevé"],
        )
        inp = EarningsQualityInput(
            ticker="MSFT", ratios=ratios_earnings_msft, graham_context=ctx
        )
        await skill.execute(inp)

        call_kwargs = mock_client.messages.create.call_args.kwargs
        user_content = call_kwargs["messages"][0]["content"]
        assert "CANDIDAT_SOLIDE" in user_content
        assert "P/E élevé" in user_content

    @pytest.mark.asyncio
    async def test_user_message_sans_contexte_graham_ne_mentionne_pas_verdict(
        self,
        ratios_earnings_msft: EarningsQualityRatios,
        earnings_output_msft: EarningsQualityOutput,
    ):
        """Sans graham_context, le message ne contient pas de section Contexte Graham."""
        mock_client = MagicMock()
        mock_client.messages = AsyncMock()
        mock_client.messages.create.return_value = _earnings_tool_use_response(earnings_output_msft)

        skill = EarningsQualitySkill(client=mock_client, model="claude-sonnet-4-6")
        inp = EarningsQualityInput(ticker="MSFT", ratios=ratios_earnings_msft)
        await skill.execute(inp)

        call_kwargs = mock_client.messages.create.call_args.kwargs
        user_content = call_kwargs["messages"][0]["content"]
        assert "Contexte Graham" not in user_content

    @pytest.mark.asyncio
    async def test_execute_cost_usd_injecte_dans_output(
        self,
        ratios_earnings_msft: EarningsQualityRatios,
        earnings_output_msft: EarningsQualityOutput,
    ):
        """execute() injecte cost_usd dans l'output même si le bloc tool_use retourne 0.0."""
        mock_client = MagicMock()
        mock_client.messages = AsyncMock()
        mock_client.messages.create.return_value = _earnings_tool_use_response(earnings_output_msft)

        skill = EarningsQualitySkill(client=mock_client, model="claude-sonnet-4-6")
        inp = EarningsQualityInput(ticker="MSFT", ratios=ratios_earnings_msft)
        output, usage = await skill.execute(inp)

        assert output.cost_usd == usage.cost_usd
