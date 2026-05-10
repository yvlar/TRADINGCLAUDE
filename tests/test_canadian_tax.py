"""Tests du skill canadian_tax_considerations — schemas, skill, orchestrateur."""
from __future__ import annotations

import uuid
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest
from pydantic import ValidationError

from app.orchestrator.core import AnalyzeRequest, AnalyzeResponse, Orchestrator
from app.skills.base import UsageDetail
from app.skills.tier2.canadian_tax.schemas import (
    CanadianTaxInput,
    CanadianTaxOutput,
)
from app.skills.tier2.canadian_tax.skill import CanadianTaxSkill


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_tax_input(
    ticker: str = "BNS",
    province: str = "QC",
    dividende_canadien: bool = True,
    dividende_us: bool = False,
    est_action_croissance: bool = False,
) -> CanadianTaxInput:
    return CanadianTaxInput(
        ticker=ticker,
        position_size_pct=5.0,
        verdict_final="ACCUMULER",
        province=province,
        dividende_canadien=dividende_canadien,
        dividende_us=dividende_us,
        est_reit=False,
        est_action_croissance=est_action_croissance,
    )


def _make_tax_output_dict(
    ticker: str = "BNS",
    compte: str = "CELI",
    impact_retenue_us: str | None = None,
    smith: bool = True,
) -> dict:
    return {
        "ticker": ticker,
        "compte_recommande": compte,
        "justification_fiscale": (
            "BNS est une action canadienne éligible aux dividendes. "
            "Le CELI protège la croissance libre d'impôt. "
            "Les dividendes éligibles bénéficient du crédit d'impôt en compte non enregistré, "
            "mais le CELI reste optimal pour la croissance du capital."
        ),
        "impact_retenue_us": impact_retenue_us,
        "strategie_smith_manoeuvre": smith,
        "taux_inclusion_gain_capital": 0.50,
        "recommandation_prochaine_etape": ["Vérifier les droits CELI disponibles", "Exécuter le placement"],
    }


def _make_usage() -> UsageDetail:
    return UsageDetail(
        tokens_input=500,
        tokens_output=350,
        tokens_cache_read=1400,
        tokens_cache_creation=0,
        cost_usd=0.0045,
        model="claude-sonnet-4-6",
    )


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def tax_output_bns() -> CanadianTaxOutput:
    """CanadianTaxOutput valide pour BNS — CELI recommandé."""
    data = _make_tax_output_dict()
    return CanadianTaxOutput.model_validate(data)


@pytest.fixture
def tax_input_bns() -> CanadianTaxInput:
    return _make_tax_input()


# ---------------------------------------------------------------------------
# Tests schémas CanadianTaxInput
# ---------------------------------------------------------------------------


class TestCanadianTaxInputSchemas:
    def test_tax_province_qc_defaut(self):
        """CanadianTaxInput sans province → province = 'QC' par défaut."""
        inp = CanadianTaxInput(
            ticker="BNS",
            position_size_pct=5.0,
            verdict_final="ACCUMULER",
        )
        assert inp.province == "QC"

    def test_tax_province_validation_invalide(self):
        """province='ZZ' → ValidationError sur CanadianTaxInput."""
        with pytest.raises(ValidationError, match="province invalide"):
            CanadianTaxInput(
                ticker="BNS",
                position_size_pct=5.0,
                verdict_final="ACCUMULER",
                province="ZZ",
            )

    def test_tax_province_on_valide(self):
        inp = CanadianTaxInput(
            ticker="RY",
            position_size_pct=3.0,
            verdict_final="CONSERVER",
            province="ON",
        )
        assert inp.province == "ON"

    def test_tax_province_toutes_valides(self):
        """Les 10 provinces canadiennes sont toutes acceptées."""
        provinces = ["QC", "ON", "BC", "AB", "SK", "MB", "NB", "NS", "PE", "NL"]
        for p in provinces:
            inp = CanadianTaxInput(
                ticker="T", position_size_pct=1.0, verdict_final="ACHETER", province=p
            )
            assert inp.province == p

    def test_tax_position_size_ge_zero(self):
        """position_size_pct = 0.0 → OK (borne inférieure)."""
        inp = CanadianTaxInput(
            ticker="BNS", position_size_pct=0.0, verdict_final="CONSERVER"
        )
        assert inp.position_size_pct == pytest.approx(0.0)

    def test_tax_position_size_le_dix(self):
        """position_size_pct = 10.0 → OK (borne supérieure)."""
        inp = CanadianTaxInput(
            ticker="BNS", position_size_pct=10.0, verdict_final="ACHETER"
        )
        assert inp.position_size_pct == pytest.approx(10.0)

    def test_tax_position_size_depasse_max_erreur(self):
        """position_size_pct = 10.1 → ValidationError."""
        with pytest.raises(ValidationError):
            CanadianTaxInput(
                ticker="BNS", position_size_pct=10.1, verdict_final="ACHETER"
            )

    def test_tax_dividende_canadien_defaut_false(self):
        inp = CanadianTaxInput(
            ticker="BNS", position_size_pct=5.0, verdict_final="ACCUMULER"
        )
        assert inp.dividende_canadien is False

    def test_tax_est_action_croissance_defaut_true(self):
        inp = CanadianTaxInput(
            ticker="SHOP", position_size_pct=2.0, verdict_final="ACCUMULER"
        )
        assert inp.est_action_croissance is True


# ---------------------------------------------------------------------------
# Tests schémas CanadianTaxOutput
# ---------------------------------------------------------------------------


class TestCanadianTaxOutputSchemas:
    def test_tax_compte_celi_valide(self):
        data = _make_tax_output_dict(compte="CELI")
        out = CanadianTaxOutput.model_validate(data)
        assert out.compte_recommande == "CELI"

    def test_tax_compte_reer_valide(self):
        data = _make_tax_output_dict(compte="REER")
        out = CanadianTaxOutput.model_validate(data)
        assert out.compte_recommande == "REER"

    def test_tax_compte_celiapp_valide(self):
        data = _make_tax_output_dict(compte="CELIAPP")
        out = CanadianTaxOutput.model_validate(data)
        assert out.compte_recommande == "CELIAPP"

    def test_tax_compte_non_enregistre_valide(self):
        data = _make_tax_output_dict(compte="NON_ENREGISTRE")
        out = CanadianTaxOutput.model_validate(data)
        assert out.compte_recommande == "NON_ENREGISTRE"

    def test_tax_verdict_invalide_erreur(self):
        """compte_recommande = 'MARGIN' → ValidationError dans CanadianTaxOutput."""
        data = _make_tax_output_dict(compte="MARGIN")
        with pytest.raises(ValidationError, match="compte_recommande invalide"):
            CanadianTaxOutput.model_validate(data)

    def test_tax_smith_manoeuvre_bool_true(self):
        """strategie_smith_manoeuvre = True → accepté."""
        data = _make_tax_output_dict(smith=True)
        out = CanadianTaxOutput.model_validate(data)
        assert out.strategie_smith_manoeuvre is True

    def test_tax_smith_manoeuvre_bool_false(self):
        """strategie_smith_manoeuvre = False → accepté."""
        data = _make_tax_output_dict(smith=False)
        out = CanadianTaxOutput.model_validate(data)
        assert out.strategie_smith_manoeuvre is False

    def test_tax_taux_inclusion_capital_0_50(self, tax_output_bns: CanadianTaxOutput):
        """taux_inclusion_gain_capital = 0.50 pour particulier canadien."""
        assert tax_output_bns.taux_inclusion_gain_capital == pytest.approx(0.50)

    def test_tax_impact_retenue_us_null_si_canadien(self):
        """dividende canadien → impact_retenue_us = None."""
        data = _make_tax_output_dict(impact_retenue_us=None)
        out = CanadianTaxOutput.model_validate(data)
        assert out.impact_retenue_us is None

    def test_tax_impact_retenue_us_non_null_si_us(self):
        """impact_retenue_us peut être une string non vide."""
        data = _make_tax_output_dict(
            impact_retenue_us="Retenue IRS 15% dans le CELI non récupérable. Préférer le REER."
        )
        out = CanadianTaxOutput.model_validate(data)
        assert out.impact_retenue_us is not None
        assert len(out.impact_retenue_us) > 10

    def test_tax_citations_defaut_vide(self, tax_output_bns: CanadianTaxOutput):
        assert tax_output_bns.citations == []

    def test_tax_cost_usd_defaut_zero(self, tax_output_bns: CanadianTaxOutput):
        assert tax_output_bns.cost_usd == pytest.approx(0.0)


# ---------------------------------------------------------------------------
# Tests skill
# ---------------------------------------------------------------------------


class TestCanadianTaxSkill:
    @pytest.fixture
    def skill(self) -> CanadianTaxSkill:
        return CanadianTaxSkill(client=MagicMock(), model="claude-sonnet-4-6")

    def test_skill_id(self, skill: CanadianTaxSkill):
        assert skill.skill_id == "canadian_tax_considerations"

    def test_tier(self, skill: CanadianTaxSkill):
        assert skill.tier == 2

    def test_system_prompt_charge_et_cache(self, skill: CanadianTaxSkill):
        blocks = skill.get_system_prompt()
        assert blocks[0]["cache_control"]["type"] == "ephemeral"
        assert len(blocks[0]["text"]) > 1024

    def test_system_prompt_contient_celi(self, skill: CanadianTaxSkill):
        text = skill.get_system_prompt()[0]["text"]
        assert "CELI" in text

    def test_system_prompt_contient_reer(self, skill: CanadianTaxSkill):
        text = skill.get_system_prompt()[0]["text"]
        assert "REER" in text

    def test_system_prompt_contient_smith(self, skill: CanadianTaxSkill):
        text = skill.get_system_prompt()[0]["text"]
        assert "Smith" in text

    def test_build_user_message_contient_ticker(
        self, skill: CanadianTaxSkill, tax_input_bns: CanadianTaxInput
    ):
        """_build_user_message(input) → message contient le ticker."""
        msg = skill._build_user_message(tax_input_bns, citations=[])
        assert "BNS" in msg

    def test_build_user_message_contient_province(
        self, skill: CanadianTaxSkill, tax_input_bns: CanadianTaxInput
    ):
        msg = skill._build_user_message(tax_input_bns, citations=[])
        assert "QC" in msg

    def test_build_user_message_contient_verdict(
        self, skill: CanadianTaxSkill, tax_input_bns: CanadianTaxInput
    ):
        msg = skill._build_user_message(tax_input_bns, citations=[])
        assert tax_input_bns.verdict_final in msg

    @pytest.mark.asyncio
    async def test_get_citations_rag_absent(self):
        """CanadianTaxSkill avec rag_service=None → get_citations() retourne []."""
        skill = CanadianTaxSkill(
            client=MagicMock(), model="claude-sonnet-4-6", rag_service=None
        )
        citations = await skill.get_citations("CELI REER dividendes")
        assert citations == []

    @pytest.mark.asyncio
    async def test_execute_mock_claude(
        self,
        tax_output_bns: CanadianTaxOutput,
        tax_input_bns: CanadianTaxInput,
    ):
        """execute() retourne (CanadianTaxOutput, UsageDetail) avec cost_usd > 0."""
        mock_response = MagicMock()
        mock_response.content = [MagicMock(text=tax_output_bns.model_dump_json())]
        mock_response.usage = SimpleNamespace(
            input_tokens=500,
            output_tokens=350,
            cache_read_input_tokens=1400,
            cache_creation_input_tokens=0,
        )
        mock_client = MagicMock()
        mock_client.messages = AsyncMock()
        mock_client.messages.create.return_value = mock_response

        skill = CanadianTaxSkill(client=mock_client, model="claude-sonnet-4-6")
        output, usage = await skill.execute(tax_input_bns)

        assert isinstance(output, CanadianTaxOutput)
        assert isinstance(usage, UsageDetail)
        assert usage.cost_usd > 0
        assert output.cost_usd == usage.cost_usd

    @pytest.mark.asyncio
    async def test_execute_retourne_tuple_output_usage(
        self,
        tax_output_bns: CanadianTaxOutput,
        tax_input_bns: CanadianTaxInput,
    ):
        """execute() retourne bien un tuple (CanadianTaxOutput, UsageDetail)."""
        mock_response = MagicMock()
        mock_response.content = [MagicMock(text=tax_output_bns.model_dump_json())]
        mock_response.usage = SimpleNamespace(
            input_tokens=500,
            output_tokens=350,
            cache_read_input_tokens=0,
            cache_creation_input_tokens=1400,
        )
        mock_client = MagicMock()
        mock_client.messages = AsyncMock()
        mock_client.messages.create.return_value = mock_response

        skill = CanadianTaxSkill(client=mock_client, model="claude-sonnet-4-6")
        result = await skill.execute(tax_input_bns)

        assert len(result) == 2
        assert isinstance(result[0], CanadianTaxOutput)
        assert isinstance(result[1], UsageDetail)


# ---------------------------------------------------------------------------
# Tests intégration orchestrateur
# ---------------------------------------------------------------------------


class TestOrchestratorCanadianTax:
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
    def mock_tax_skill(self, tax_output_bns: CanadianTaxOutput):
        skill = AsyncMock(spec=CanadianTaxSkill)
        skill.execute.return_value = (tax_output_bns, _make_usage())
        return skill

    @pytest.mark.asyncio
    async def test_orchestrator_avec_tax(
        self,
        mock_db_pool,
        mock_graham_skill,
        mock_earnings_skill,
        mock_tax_skill,
        ratios_msft,
    ):
        """tax_input fourni dans AnalyzeRequest → canadian_tax présent dans response,
        skills_applied contient 'canadian_tax_considerations'."""
        orchestrator = Orchestrator(
            db_pool=mock_db_pool,
            graham_skill=mock_graham_skill,
            earnings_skill=mock_earnings_skill,
            canadian_tax_skill=mock_tax_skill,
        )
        tax_input = CanadianTaxInput(
            ticker="BNS",
            position_size_pct=5.0,
            verdict_final="ACCUMULER",
            province="QC",
            dividende_canadien=True,
        )
        req = AnalyzeRequest(
            ticker="BNS",
            ratios=ratios_msft,
            tax_input=tax_input,
        )
        response = await orchestrator.run_company_analysis(req)

        assert response.canadian_tax is not None
        assert "canadian_tax_considerations" in response.skills_applied
        mock_tax_skill.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_orchestrator_sans_tax(
        self,
        mock_db_pool,
        mock_graham_skill,
        mock_earnings_skill,
        mock_tax_skill,
        ratios_msft,
    ):
        """tax_input = None → canadian_tax = None dans response, skill non appelé."""
        orchestrator = Orchestrator(
            db_pool=mock_db_pool,
            graham_skill=mock_graham_skill,
            earnings_skill=mock_earnings_skill,
            canadian_tax_skill=mock_tax_skill,
        )
        req = AnalyzeRequest(
            ticker="BNS",
            ratios=ratios_msft,
            tax_input=None,
        )
        response = await orchestrator.run_company_analysis(req)

        assert response.canadian_tax is None
        assert "canadian_tax_considerations" not in response.skills_applied
        mock_tax_skill.execute.assert_not_called()

    @pytest.mark.asyncio
    async def test_tax_skill_absent_pas_erreur(
        self,
        mock_db_pool,
        mock_graham_skill,
        mock_earnings_skill,
        ratios_msft,
    ):
        """tax_input fourni mais canadian_tax_skill=None → canadian_tax = None, pas d'erreur."""
        orchestrator = Orchestrator(
            db_pool=mock_db_pool,
            graham_skill=mock_graham_skill,
            earnings_skill=mock_earnings_skill,
            canadian_tax_skill=None,
        )
        tax_input = CanadianTaxInput(
            ticker="BNS", position_size_pct=5.0, verdict_final="ACCUMULER"
        )
        req = AnalyzeRequest(
            ticker="BNS",
            ratios=ratios_msft,
            tax_input=tax_input,
        )
        response = await orchestrator.run_company_analysis(req)

        assert response.canadian_tax is None
        assert "canadian_tax_considerations" not in response.skills_applied

    @pytest.mark.asyncio
    async def test_tax_input_defaut_none(self, ratios_msft):
        """tax_input est None par défaut dans AnalyzeRequest."""
        req = AnalyzeRequest(ticker="BNS", ratios=ratios_msft)
        assert req.tax_input is None

    @pytest.mark.asyncio
    async def test_canadian_tax_response_defaut_none(self, graham_output_msft):
        """canadian_tax est None par défaut dans AnalyzeResponse."""
        resp = AnalyzeResponse(
            analysis_id="123",
            ticker="BNS",
            workflow="company_analysis",
            skills_applied=["graham_analysis"],
            graham=graham_output_msft,
            cost_usd=0.003,
            created_at="2026-05-08T10:00:00+00:00",
        )
        assert resp.canadian_tax is None
