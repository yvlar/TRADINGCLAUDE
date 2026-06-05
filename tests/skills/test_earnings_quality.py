"""Tests du skill earnings_quality — schemas, skill, context enrichment."""
from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest
from pydantic import ValidationError


def _earnings_tool_use_response(
    output: "EarningsQualityOutput | None" = None,
    *,
    data: dict | None = None,
    **usage_overrides,
) -> MagicMock:
    """Construit une réponse Anthropic simulée avec bloc tool_use pour earnings_quality.

    `data` permet d'injecter un payload LLM déjà « empoisonné » (champ mutilé) sans repasser
    par un EarningsQualityOutput valide ; sinon le dump de `output` est utilisé.
    """
    mock_block = MagicMock()
    mock_block.type = "tool_use"
    mock_block.input = data if data is not None else output.model_dump(exclude={"confidence_score"})
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
from app.skills.tier2.earnings_quality.skill import (
    EarningsQualitySkill,
    _coerce_payload_llm,
    _str_vers_liste,
)


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

    def test_tracabilite_absente_par_defaut_none(
        self, ratios_earnings_msft: EarningsQualityRatios
    ):
        """ratios_fetched_at / ratios_source absents → None (rétrocompatible, Sprint 138)."""
        assert ratios_earnings_msft.ratios_fetched_at is None
        assert ratios_earnings_msft.ratios_source is None

    def test_tracabilite_renseignee_et_iso_acceptee(self):
        """ratios_fetched_at accepte une string ISO et ratios_source un littéral (Sprint 138)."""
        r = EarningsQualityRatios(
            sales_t=1.0, sales_t1=1.0, cogs_t=1.0, cogs_t1=1.0,
            net_income_t=1.0, cfo_t=1.0, receivables_t=1.0, receivables_t1=1.0,
            total_assets_t=1.0, total_assets_t1=1.0,
            current_assets_t=1.0, current_liabilities_t=1.0,
            ratios_fetched_at="2026-05-30T12:00:00+00:00", ratios_source="Yahoo Finance",
        )
        assert r.ratios_source == "Yahoo Finance"
        assert r.ratios_fetched_at is not None
        assert r.ratios_fetched_at.year == 2026

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

    def test_z_score_deterministe_eleve_accepte(self, earnings_output_msft: EarningsQualityOutput):
        """Sprint 128 : un Z déterministe élevé (société très peu endettée, X4 grand) n'est
        plus rejeté — borne élargie pour ne pas supprimer earnings_quality des plus saines."""
        data = earnings_output_msft.model_dump()
        data["z_score"]["z_score"] = 120.0
        output = EarningsQualityOutput.model_validate(data)
        assert output.z_score.z_score == 120.0


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
    async def test_scores_python_priment_sur_bloc_llm(
        self,
        ratios_earnings_msft: EarningsQualityRatios,
        earnings_output_msft: EarningsQualityOutput,
    ):
        """Le bloc LLM renvoie des scores aberrants → les valeurs Python déterministes les écrasent."""
        from app.services.financial_calculations import (
            altman_z_score,
            sloan_accrual_ratio,
        )

        # Le LLM « hallucine » des scores différents de la réalité calculée.
        data = earnings_output_msft.model_dump(exclude={"confidence_score"})
        data["z_score"]["z_score"] = 1.23
        data["sloan"]["accrual_ratio"] = 0.99
        mock_block = MagicMock()
        mock_block.type = "tool_use"
        mock_block.input = data
        mock_response = MagicMock()
        mock_response.content = [mock_block]
        mock_response.stop_reason = "tool_use"
        mock_response.usage = SimpleNamespace(
            input_tokens=800, output_tokens=600,
            cache_read_input_tokens=0, cache_creation_input_tokens=1500,
        )

        mock_client = MagicMock()
        mock_client.messages = AsyncMock()
        mock_client.messages.create.return_value = mock_response

        skill = EarningsQualitySkill(client=mock_client, model="claude-sonnet-4-6")
        inp = EarningsQualityInput(ticker="MSFT", ratios=ratios_earnings_msft)
        output, _ = await skill.execute(inp)

        z_attendu = altman_z_score(
            current_assets=ratios_earnings_msft.current_assets_t,
            current_liabilities=ratios_earnings_msft.current_liabilities_t,
            retained_earnings=ratios_earnings_msft.retained_earnings_t,
            ebit=ratios_earnings_msft.ebit_t,
            total_assets=ratios_earnings_msft.total_assets_t,
            total_liabilities=ratios_earnings_msft.total_liabilities_t,
            sales=ratios_earnings_msft.sales_t,
            market_value_equity=ratios_earnings_msft.market_cap_t,
        )
        sloan_attendu = sloan_accrual_ratio(
            net_income_t=ratios_earnings_msft.net_income_t,
            cfo_t=ratios_earnings_msft.cfo_t,
            total_assets_t=ratios_earnings_msft.total_assets_t,
            total_assets_t1=ratios_earnings_msft.total_assets_t1,
        )
        assert output.z_score.z_score == pytest.approx(z_attendu)
        assert output.z_score.z_score != 1.23
        assert output.sloan.accrual_ratio == pytest.approx(sloan_attendu)

    @pytest.mark.asyncio
    async def test_indices_m_et_termes_z_python_priment_sur_bloc_llm(
        self,
        ratios_earnings_msft: EarningsQualityRatios,
        earnings_output_msft: EarningsQualityOutput,
    ):
        """Sprint 131 : les indices DSRI… du M et les termes X1-X5 du Z calculés en Python
        écrasent les valeurs du bloc LLM et sont persistés dans l'output."""
        from app.services.financial_calculations import (
            altman_z_score_detail,
            beneish_m_score_detail,
        )

        data = earnings_output_msft.model_dump(exclude={"confidence_score"})
        # Le LLM « hallucine » des sous-composantes aberrantes.
        data["m_score"]["dsri"] = 99.0
        data["z_score"]["x1"] = 99.0
        mock_block = MagicMock()
        mock_block.type = "tool_use"
        mock_block.input = data
        mock_response = MagicMock()
        mock_response.content = [mock_block]
        mock_response.stop_reason = "tool_use"
        mock_response.usage = SimpleNamespace(
            input_tokens=800, output_tokens=600,
            cache_read_input_tokens=0, cache_creation_input_tokens=1500,
        )
        mock_client = MagicMock()
        mock_client.messages = AsyncMock()
        mock_client.messages.create.return_value = mock_response

        skill = EarningsQualitySkill(client=mock_client, model="claude-sonnet-4-6")
        inp = EarningsQualityInput(ticker="MSFT", ratios=ratios_earnings_msft)
        output, _ = await skill.execute(inp)

        m_attendu = beneish_m_score_detail(
            receivables_t=ratios_earnings_msft.receivables_t,
            receivables_t1=ratios_earnings_msft.receivables_t1,
            sales_t=ratios_earnings_msft.sales_t,
            sales_t1=ratios_earnings_msft.sales_t1,
            cogs_t=ratios_earnings_msft.cogs_t,
            cogs_t1=ratios_earnings_msft.cogs_t1,
            current_assets_t=ratios_earnings_msft.current_assets_t,
            current_assets_t1=ratios_earnings_msft.current_assets_t1,
            ppe_net_t=ratios_earnings_msft.ppe_net_t,
            ppe_net_t1=ratios_earnings_msft.ppe_net_t1,
            total_assets_t=ratios_earnings_msft.total_assets_t,
            total_assets_t1=ratios_earnings_msft.total_assets_t1,
            depreciation_t=ratios_earnings_msft.depreciation_t,
            depreciation_t1=ratios_earnings_msft.depreciation_t1,
            sga_t=ratios_earnings_msft.sga_t,
            sga_t1=ratios_earnings_msft.sga_t1,
            net_income_t=ratios_earnings_msft.net_income_t,
            cfo_t=ratios_earnings_msft.cfo_t,
            ltd_t=ratios_earnings_msft.ltd_t,
            ltd_t1=ratios_earnings_msft.ltd_t1,
            current_liabilities_t=ratios_earnings_msft.current_liabilities_t,
            current_liabilities_t1=ratios_earnings_msft.current_liabilities_t1,
        )
        z_attendu = altman_z_score_detail(
            current_assets=ratios_earnings_msft.current_assets_t,
            current_liabilities=ratios_earnings_msft.current_liabilities_t,
            retained_earnings=ratios_earnings_msft.retained_earnings_t,
            ebit=ratios_earnings_msft.ebit_t,
            total_assets=ratios_earnings_msft.total_assets_t,
            total_liabilities=ratios_earnings_msft.total_liabilities_t,
            sales=ratios_earnings_msft.sales_t,
            market_value_equity=ratios_earnings_msft.market_cap_t,
            book_value_equity=ratios_earnings_msft.book_equity_t,
        )
        # DSRI calculable pour MSFT → écrase le 99.0 du LLM.
        assert output.m_score.dsri == pytest.approx(m_attendu.dsri)
        assert output.m_score.dsri != 99.0
        # AQI incalculable (current_assets_t1 absent du fixture) → None déterministe.
        assert output.m_score.aqi is None
        assert output.z_score.x1 == pytest.approx(z_attendu.x1)
        assert output.z_score.x1 != 99.0
        assert output.z_score.x4 == pytest.approx(z_attendu.x4)

    @pytest.mark.asyncio
    async def test_financiere_annule_indices_et_termes(
        self,
        ratios_earnings_msft: EarningsQualityRatios,
        earnings_output_msft: EarningsQualityOutput,
    ):
        """is_financial=True → indices du M et termes X1-X5 du Z annulés (modèle inapplicable)."""
        data = earnings_output_msft.model_dump(exclude={"confidence_score"})
        data["is_financial"] = True
        data["m_score"]["dsri"] = 1.5
        data["z_score"]["x1"] = 0.3
        mock_block = MagicMock()
        mock_block.type = "tool_use"
        mock_block.input = data
        mock_response = MagicMock()
        mock_response.content = [mock_block]
        mock_response.stop_reason = "tool_use"
        mock_response.usage = SimpleNamespace(
            input_tokens=800, output_tokens=600,
            cache_read_input_tokens=0, cache_creation_input_tokens=1500,
        )
        mock_client = MagicMock()
        mock_client.messages = AsyncMock()
        mock_client.messages.create.return_value = mock_response

        skill = EarningsQualitySkill(client=mock_client, model="claude-sonnet-4-6")
        inp = EarningsQualityInput(ticker="MSFT", ratios=ratios_earnings_msft)
        output, _ = await skill.execute(inp)

        assert output.m_score.dsri is None
        assert output.m_score.lvgi is None
        assert output.z_score.x1 is None
        assert output.z_score.x5 is None

    @pytest.mark.asyncio
    async def test_signaux_f_et_c_python_priment_sur_bloc_llm(
        self,
        ratios_earnings_msft: EarningsQualityRatios,
        earnings_output_msft: EarningsQualityOutput,
    ):
        """Sprint 142 : les critères F (passe) et signaux C (present) calculés en Python
        écrasent les booléens du bloc LLM ; la somme reste cohérente avec le score agrégé."""
        from app.services.financial_calculations import (
            montier_c_signaux,
            piotroski_f_criteria,
        )

        data = earnings_output_msft.model_dump(exclude={"confidence_score"})
        # Le LLM « hallucine » des booléens et scores incohérents.
        data["f_score"]["criteria"][0]["passe"] = False
        data["f_score"]["f_score"] = 1
        data["c_score"]["signaux"][0]["present"] = True
        data["c_score"]["c_score"] = 5
        mock_block = MagicMock()
        mock_block.type = "tool_use"
        mock_block.input = data
        mock_response = MagicMock()
        mock_response.content = [mock_block]
        mock_response.stop_reason = "tool_use"
        mock_response.usage = SimpleNamespace(
            input_tokens=800, output_tokens=600,
            cache_read_input_tokens=0, cache_creation_input_tokens=1500,
        )
        mock_client = MagicMock()
        mock_client.messages = AsyncMock()
        mock_client.messages.create.return_value = mock_response

        skill = EarningsQualitySkill(client=mock_client, model="claude-sonnet-4-6")
        inp = EarningsQualityInput(ticker="MSFT", ratios=ratios_earnings_msft)
        output, _ = await skill.execute(inp)

        f_attendu = piotroski_f_criteria(
            net_income_t=ratios_earnings_msft.net_income_t,
            total_assets_t=ratios_earnings_msft.total_assets_t,
            total_assets_t1=ratios_earnings_msft.total_assets_t1,
            net_income_t1=ratios_earnings_msft.net_income_t1,
            cfo_t=ratios_earnings_msft.cfo_t,
            ltd_t=ratios_earnings_msft.ltd_t,
            ltd_t1=ratios_earnings_msft.ltd_t1,
            current_assets_t=ratios_earnings_msft.current_assets_t,
            current_liabilities_t=ratios_earnings_msft.current_liabilities_t,
            current_assets_t1=ratios_earnings_msft.current_assets_t1,
            current_liabilities_t1=ratios_earnings_msft.current_liabilities_t1,
            sales_t=ratios_earnings_msft.sales_t,
            sales_t1=ratios_earnings_msft.sales_t1,
            cogs_t=ratios_earnings_msft.cogs_t,
            cogs_t1=ratios_earnings_msft.cogs_t1,
            shares_issued_net=ratios_earnings_msft.shares_issued_net,
        )
        c_attendu = montier_c_signaux(
            net_income_t=ratios_earnings_msft.net_income_t,
            cfo_t=ratios_earnings_msft.cfo_t,
            net_income_t1=ratios_earnings_msft.net_income_t1,
            cfo_t1=ratios_earnings_msft.cfo_t1,
            receivables_t=ratios_earnings_msft.receivables_t,
            receivables_t1=ratios_earnings_msft.receivables_t1,
            sales_t=ratios_earnings_msft.sales_t,
            sales_t1=ratios_earnings_msft.sales_t1,
            inventory_t=ratios_earnings_msft.inventory_t,
            inventory_t1=ratios_earnings_msft.inventory_t1,
            cogs_t=ratios_earnings_msft.cogs_t,
            cogs_t1=ratios_earnings_msft.cogs_t1,
            depreciation_t=ratios_earnings_msft.depreciation_t,
            depreciation_t1=ratios_earnings_msft.depreciation_t1,
            ppe_gross_t=ratios_earnings_msft.ppe_gross_t,
            ppe_gross_t1=ratios_earnings_msft.ppe_gross_t1,
            total_assets_t=ratios_earnings_msft.total_assets_t,
            total_assets_t1=ratios_earnings_msft.total_assets_t1,
        )
        # Critères/signaux Python (booléens) remplacent ceux du LLM.
        assert [c.passe for c in output.f_score.criteria] == [c.passe for c in f_attendu]
        assert [s.present for s in output.c_score.signaux] == [s.present for s in c_attendu]
        # Le poison du LLM est écrasé : ROA positif rétabli (True), divergence rétablie (False).
        assert output.f_score.criteria[0].passe is True
        assert output.c_score.signaux[0].present is False
        # ROA en hausse non accordé (NI T-1 absent du fixture) → critère 3 conservé False.
        assert output.f_score.criteria[2].nom == "ROA en hausse"
        assert output.f_score.criteria[2].passe is False
        # Invariant de cohérence après substitution : sum(passe) == f_score, idem C.
        assert sum(c.passe for c in output.f_score.criteria) == output.f_score.f_score
        assert sum(s.present for s in output.c_score.signaux) == output.c_score.c_score
        # Les scores agrégés poison (1 et 5) sont écrasés par le Python déterministe.
        assert output.c_score.c_score == 0

    @pytest.mark.asyncio
    async def test_financiere_garde_criteria_f_llm_mais_substitue_c(
        self,
        ratios_earnings_msft: EarningsQualityRatios,
        earnings_output_msft: EarningsQualityOutput,
    ):
        """is_financial=True → Piotroski inapplicable : les critères F du LLM sont conservés.
        Montier n'a pas de gate sectoriel → ses signaux restent substitués (parité avec le
        comportement des scores agrégés f_score/c_score)."""
        from app.services.financial_calculations import montier_c_signaux

        data = earnings_output_msft.model_dump(exclude={"confidence_score"})
        data["is_financial"] = True
        # Marqueur reconnaissable sur les critères F du LLM (doivent survivre).
        data["f_score"]["criteria"][0]["nom"] = "MARQUEUR_LLM"
        data["c_score"]["signaux"][0]["present"] = True  # poison C → doit être écrasé
        mock_block = MagicMock()
        mock_block.type = "tool_use"
        mock_block.input = data
        mock_response = MagicMock()
        mock_response.content = [mock_block]
        mock_response.stop_reason = "tool_use"
        mock_response.usage = SimpleNamespace(
            input_tokens=800, output_tokens=600,
            cache_read_input_tokens=0, cache_creation_input_tokens=1500,
        )
        mock_client = MagicMock()
        mock_client.messages = AsyncMock()
        mock_client.messages.create.return_value = mock_response

        skill = EarningsQualitySkill(client=mock_client, model="claude-sonnet-4-6")
        inp = EarningsQualityInput(ticker="MSFT", ratios=ratios_earnings_msft)
        output, _ = await skill.execute(inp)

        # F : critères LLM conservés (Piotroski None pour une financière).
        assert output.f_score.criteria[0].nom == "MARQUEUR_LLM"
        # C : signaux substitués par le Python déterministe (poison écrasé).
        c_attendu = montier_c_signaux(
            net_income_t=ratios_earnings_msft.net_income_t,
            cfo_t=ratios_earnings_msft.cfo_t,
            net_income_t1=ratios_earnings_msft.net_income_t1,
            cfo_t1=ratios_earnings_msft.cfo_t1,
            receivables_t=ratios_earnings_msft.receivables_t,
            receivables_t1=ratios_earnings_msft.receivables_t1,
            sales_t=ratios_earnings_msft.sales_t,
            sales_t1=ratios_earnings_msft.sales_t1,
            inventory_t=ratios_earnings_msft.inventory_t,
            inventory_t1=ratios_earnings_msft.inventory_t1,
            cogs_t=ratios_earnings_msft.cogs_t,
            cogs_t1=ratios_earnings_msft.cogs_t1,
            depreciation_t=ratios_earnings_msft.depreciation_t,
            depreciation_t1=ratios_earnings_msft.depreciation_t1,
            ppe_gross_t=ratios_earnings_msft.ppe_gross_t,
            ppe_gross_t1=ratios_earnings_msft.ppe_gross_t1,
            total_assets_t=ratios_earnings_msft.total_assets_t,
            total_assets_t1=ratios_earnings_msft.total_assets_t1,
        )
        assert [s.present for s in output.c_score.signaux] == [s.present for s in c_attendu]
        assert output.c_score.signaux[0].present is False

    @pytest.mark.asyncio
    async def test_interpretation_f_et_c_python_priment_sur_bloc_llm(
        self,
        ratios_earnings_msft: EarningsQualityRatios,
        earnings_output_msft: EarningsQualityOutput,
    ):
        """Sprint 143 : l'interprétation cadre F/C dérivée du score Python déterministe
        écrase le libellé du bloc LLM (parité avec M/Z, Sprint 131)."""
        from app.skills.tier2.earnings_quality.skill import _scores_depuis_ratios

        data = earnings_output_msft.model_dump(exclude={"confidence_score"})
        # Le LLM « hallucine » des libellés d'interprétation incohérents.
        data["f_score"]["interpretation"] = "POISON_F_LLM"
        data["c_score"]["interpretation"] = "POISON_C_LLM"
        mock_client = MagicMock()
        mock_client.messages = AsyncMock()
        mock_client.messages.create.return_value = _earnings_tool_use_response(data=data)

        skill = EarningsQualitySkill(client=mock_client, model="claude-sonnet-4-6")
        inp = EarningsQualityInput(ticker="MSFT", ratios=ratios_earnings_msft)
        output, _ = await skill.execute(inp)

        attendus = _scores_depuis_ratios(ratios_earnings_msft, is_financial=False)
        # Le poison LLM est écrasé par le libellé dérivé du score agrégé déterministe.
        assert output.f_score.interpretation == attendus.f_interpretation
        assert output.c_score.interpretation == attendus.c_interpretation
        assert output.f_score.interpretation != "POISON_F_LLM"
        assert output.c_score.interpretation != "POISON_C_LLM"
        # Cohérence libellé ↔ score : l'interprétation correspond au seuil du score agrégé.
        from app.services.financial_calculations import (
            _montier_interpretation,
            _piotroski_interpretation,
        )
        assert output.f_score.interpretation == _piotroski_interpretation(output.f_score.f_score)
        assert output.c_score.interpretation == _montier_interpretation(output.c_score.c_score)

    @pytest.mark.asyncio
    async def test_financiere_garde_interpretation_f_llm_mais_substitue_c(
        self,
        ratios_earnings_msft: EarningsQualityRatios,
        earnings_output_msft: EarningsQualityOutput,
    ):
        """is_financial=True → F-Score inapplicable (gate None) : l'interprétation F du LLM
        survit. Montier n'a pas de gate sectoriel → l'interprétation C reste substituée."""
        from app.services.financial_calculations import _montier_interpretation
        from app.skills.tier2.earnings_quality.skill import _scores_depuis_ratios

        data = earnings_output_msft.model_dump(exclude={"confidence_score"})
        data["is_financial"] = True
        data["f_score"]["interpretation"] = "MARQUEUR_F_LLM"  # doit survivre (gate None)
        data["c_score"]["interpretation"] = "POISON_C_LLM"  # doit être écrasé
        mock_client = MagicMock()
        mock_client.messages = AsyncMock()
        mock_client.messages.create.return_value = _earnings_tool_use_response(data=data)

        skill = EarningsQualitySkill(client=mock_client, model="claude-sonnet-4-6")
        inp = EarningsQualityInput(ticker="MSFT", ratios=ratios_earnings_msft)
        output, _ = await skill.execute(inp)

        # F : interprétation LLM conservée (Piotroski None pour une financière).
        assert output.f_score.interpretation == "MARQUEUR_F_LLM"
        # C : interprétation substituée par le libellé déterministe (poison écrasé).
        attendus = _scores_depuis_ratios(ratios_earnings_msft, is_financial=True)
        assert output.c_score.interpretation == attendus.c_interpretation
        assert output.c_score.interpretation == _montier_interpretation(output.c_score.c_score)
        assert output.c_score.interpretation != "POISON_C_LLM"

    @pytest.mark.asyncio
    async def test_interpretation_sloan_python_prime_sur_bloc_llm(
        self,
        ratios_earnings_msft: EarningsQualityRatios,
        earnings_output_msft: EarningsQualityOutput,
    ):
        """Sprint 148 : l'interprétation Sloan dérivée de l'accrual_ratio Python écrase le libellé
        LLM (parité M/Z/F/C). Substitution inconditionnelle — toujours une str."""
        from app.services.financial_calculations import _sloan_interpretation
        from app.skills.tier2.earnings_quality.skill import _scores_depuis_ratios

        data = earnings_output_msft.model_dump(exclude={"confidence_score"})
        data["sloan"]["interpretation"] = "POISON_SLOAN_LLM"
        mock_client = MagicMock()
        mock_client.messages = AsyncMock()
        mock_client.messages.create.return_value = _earnings_tool_use_response(data=data)

        skill = EarningsQualitySkill(client=mock_client, model="claude-sonnet-4-6")
        inp = EarningsQualityInput(ticker="MSFT", ratios=ratios_earnings_msft)
        output, _ = await skill.execute(inp)

        attendus = _scores_depuis_ratios(ratios_earnings_msft, is_financial=False)
        # Le poison LLM est écrasé par le libellé dérivé de l'accrual_ratio déterministe.
        assert output.sloan.interpretation == attendus.sloan_interpretation
        assert output.sloan.interpretation != "POISON_SLOAN_LLM"
        # Cohérence libellé ↔ accrual : l'interprétation correspond au seuil de l'accrual substitué.
        assert output.sloan.interpretation == _sloan_interpretation(output.sloan.accrual_ratio)

    @pytest.mark.asyncio
    async def test_interpretation_sloan_donnees_manquantes_ecrase_aussi(
        self,
        ratios_earnings_msft: EarningsQualityRatios,
        earnings_output_msft: EarningsQualityOutput,
    ):
        """Sprint 148 — branche no-gate : accrual None → 'DONNEES_MANQUANTES' substitué malgré tout
        (écrase le libellé LLM). Verrouille la décision « substitution inconditionnelle »."""
        from app.skills.tier2.earnings_quality.skill import _scores_depuis_ratios

        # cfo_t None → sloan_accrual_ratio renvoie None (donnée manquante).
        ratios = ratios_earnings_msft.model_copy(update={"cfo_t": None})
        assert _scores_depuis_ratios(ratios, is_financial=False).accrual_ratio is None

        data = earnings_output_msft.model_dump(exclude={"confidence_score"})
        data["sloan"]["interpretation"] = "POISON_SLOAN_LLM"
        mock_client = MagicMock()
        mock_client.messages = AsyncMock()
        mock_client.messages.create.return_value = _earnings_tool_use_response(data=data)

        skill = EarningsQualitySkill(client=mock_client, model="claude-sonnet-4-6")
        output, _ = await skill.execute(EarningsQualityInput(ticker="MSFT", ratios=ratios))

        assert output.sloan.accrual_ratio is None
        assert output.sloan.interpretation == "DONNEES_MANQUANTES"

    @pytest.mark.asyncio
    async def test_interpretation_sloan_substituee_meme_pour_financiere(
        self,
        ratios_earnings_msft: EarningsQualityRatios,
        earnings_output_msft: EarningsQualityOutput,
    ):
        """Sprint 148 : Sloan n'a pas de gate sectoriel (contrairement à F) → l'interprétation reste
        substituée même pour une financière (accrual_ratio ignore is_financial)."""
        from app.services.financial_calculations import _sloan_interpretation

        data = earnings_output_msft.model_dump(exclude={"confidence_score"})
        data["is_financial"] = True
        data["sloan"]["interpretation"] = "POISON_SLOAN_LLM"
        mock_client = MagicMock()
        mock_client.messages = AsyncMock()
        mock_client.messages.create.return_value = _earnings_tool_use_response(data=data)

        skill = EarningsQualitySkill(client=mock_client, model="claude-sonnet-4-6")
        output, _ = await skill.execute(
            EarningsQualityInput(ticker="MSFT", ratios=ratios_earnings_msft)
        )

        assert output.sloan.interpretation != "POISON_SLOAN_LLM"
        assert output.sloan.interpretation == _sloan_interpretation(output.sloan.accrual_ratio)

    @pytest.mark.asyncio
    async def test_message_utilisateur_contient_scores_deterministes(
        self,
        ratios_earnings_msft: EarningsQualityRatios,
        earnings_output_msft: EarningsQualityOutput,
    ):
        """Le message envoyé au LLM expose les scores calculés en Python à interpréter."""
        mock_client = MagicMock()
        mock_client.messages = AsyncMock()
        mock_client.messages.create.return_value = _earnings_tool_use_response(earnings_output_msft)

        skill = EarningsQualitySkill(client=mock_client, model="claude-sonnet-4-6")
        inp = EarningsQualityInput(ticker="MSFT", ratios=ratios_earnings_msft)
        await skill.execute(inp)

        user_content = mock_client.messages.create.call_args.kwargs["messages"][0]["content"]
        assert "Scores déterministes" in user_content
        assert "Z-Score" in user_content

    @pytest.mark.asyncio
    async def test_financiere_annule_z_et_m(
        self,
        ratios_earnings_msft: EarningsQualityRatios,
        earnings_output_msft: EarningsQualityOutput,
    ):
        """Si le LLM classe l'entreprise is_financial, M/Z calculés sont None (modèle inapplicable)."""
        data = earnings_output_msft.model_dump(exclude={"confidence_score"})
        data["is_financial"] = True
        data["z_score"]["z_score"] = 3.0
        mock_block = MagicMock()
        mock_block.type = "tool_use"
        mock_block.input = data
        mock_response = MagicMock()
        mock_response.content = [mock_block]
        mock_response.stop_reason = "tool_use"
        mock_response.usage = SimpleNamespace(
            input_tokens=800, output_tokens=600,
            cache_read_input_tokens=0, cache_creation_input_tokens=1500,
        )
        mock_client = MagicMock()
        mock_client.messages = AsyncMock()
        mock_client.messages.create.return_value = mock_response

        skill = EarningsQualitySkill(client=mock_client, model="claude-sonnet-4-6")
        inp = EarningsQualityInput(ticker="MSFT", ratios=ratios_earnings_msft)
        output, _ = await skill.execute(inp)

        assert output.z_score.z_score is None
        assert output.m_score.m_score is None

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


def _mock_tool_use_from_input(payload: dict, **usage_overrides) -> MagicMock:
    """Réponse Anthropic simulée à partir d'un payload tool_use brut (potentiellement malformé)."""
    mock_block = MagicMock()
    mock_block.type = "tool_use"
    mock_block.input = payload
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


class TestStrVersListe:
    def test_liste_json_propre(self):
        assert _str_vers_liste('["a", "b"]') == ["a", "b"]

    def test_chaine_corrompue_garde_premier_fragment(self):
        # cas COIN : la chaîne a absorbé d'autres champs et n'est plus du JSON valide
        brut = '[\n  "Z-Score 0.547 — détresse"\n  ]\n}'
        assert _str_vers_liste(brut) == ["Z-Score 0.547 — détresse"]

    def test_chaine_vide(self):
        assert _str_vers_liste("   ") == []

    def test_scalaire_json(self):
        assert _str_vers_liste('"un seul drapeau"') == ["un seul drapeau"]


class TestCoercePayloadLlm:
    def test_drapeaux_chaine_json_devient_liste(self):
        data = {"drapeaux_rouges": '["Z-Score détresse", "F-Score value_trap"]'}
        _coerce_payload_llm(data)
        assert data["drapeaux_rouges"] == ["Z-Score détresse", "F-Score value_trap"]

    def test_drapeaux_none_devient_liste_vide(self):
        data = {"drapeaux_rouges": None}
        _coerce_payload_llm(data)
        assert data["drapeaux_rouges"] == []

    def test_drapeaux_deja_liste_inchange(self):
        data = {"drapeaux_rouges": ["x"]}
        _coerce_payload_llm(data)
        assert data["drapeaux_rouges"] == ["x"]

    def test_reco_chaine_devient_liste(self):
        data = {"recommandation_prochaine_etape": "analyser le cash-flow"}
        _coerce_payload_llm(data)
        assert data["recommandation_prochaine_etape"] == ["analyser le cash-flow"]


class TestEarningsCoinRobustesse:
    @pytest.mark.asyncio
    async def test_drapeaux_stringifies_recuperes_sans_retry(
        self,
        ratios_earnings_msft: EarningsQualityRatios,
        earnings_output_msft: EarningsQualityOutput,
    ):
        """drapeaux_rouges en chaîne JSON → récupéré par coercion en un seul appel."""
        payload = earnings_output_msft.model_dump(exclude={"confidence_score"})
        payload["drapeaux_rouges"] = '["Z-Score détresse", "accruals dégradés"]'

        mock_client = MagicMock()
        mock_client.messages = AsyncMock()
        mock_client.messages.create.return_value = _mock_tool_use_from_input(payload)

        skill = EarningsQualitySkill(client=mock_client, model="claude-sonnet-4-6")
        inp = EarningsQualityInput(ticker="MSFT", ratios=ratios_earnings_msft)
        output, _ = await skill.execute(inp)

        assert output.drapeaux_rouges == ["Z-Score détresse", "accruals dégradés"]
        assert mock_client.messages.create.await_count == 1

    @pytest.mark.asyncio
    async def test_sortie_tronquee_declenche_un_retry(
        self,
        ratios_earnings_msft: EarningsQualityRatios,
        earnings_output_msft: EarningsQualityOutput,
    ):
        """verdict avalé (champ requis absent) → un retry, succès sur la 2e réponse."""
        bon = earnings_output_msft.model_dump(exclude={"confidence_score"})
        casse = dict(bon)
        casse.pop("verdict")  # tronqué : non récupérable par coercion
        casse["drapeaux_rouges"] = '[\n  "Z-Score 0.547 — détresse"\n  ]\n}'

        mock_client = MagicMock()
        mock_client.messages = AsyncMock()
        mock_client.messages.create.side_effect = [
            _mock_tool_use_from_input(casse),
            _mock_tool_use_from_input(bon),
        ]

        skill = EarningsQualitySkill(client=mock_client, model="claude-sonnet-4-6")
        inp = EarningsQualityInput(ticker="COIN", ratios=ratios_earnings_msft)
        output, _ = await skill.execute(inp)

        assert output.verdict in {"AUCUN_SIGNAL", "ATTENTION", "WATCHLIST", "REJETER"}
        assert mock_client.messages.create.await_count == 2

    @pytest.mark.asyncio
    async def test_deux_sorties_invalides_levent_erreur(
        self,
        ratios_earnings_msft: EarningsQualityRatios,
        earnings_output_msft: EarningsQualityOutput,
    ):
        """Deux réponses malformées d'affilée → ValueError explicite (pas de boucle infinie)."""
        casse = earnings_output_msft.model_dump(exclude={"confidence_score"})
        casse.pop("verdict")

        mock_client = MagicMock()
        mock_client.messages = AsyncMock()
        mock_client.messages.create.side_effect = [
            _mock_tool_use_from_input(casse),
            _mock_tool_use_from_input(casse),
        ]

        skill = EarningsQualitySkill(client=mock_client, model="claude-sonnet-4-6")
        inp = EarningsQualityInput(ticker="COIN", ratios=ratios_earnings_msft)
        with pytest.raises(ValueError, match="invalide après 2 tentatives"):
            await skill.execute(inp)
        assert mock_client.messages.create.await_count == 2
