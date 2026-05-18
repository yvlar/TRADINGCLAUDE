"""Tests du skill munger_mental_models — schemas, skill, orchestrateur."""
from __future__ import annotations

import json
import uuid
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest
from pydantic import ValidationError

from app.orchestrator.core import AnalyzeRequest, AnalyzeResponse, Orchestrator
from app.skills.base import UsageDetail
from app.skills.tier2.munger_mental.schemas import (
    BiaisCognitif,
    MungerInput,
    MungerOutput,
    ThesisContext,
)
from app.skills.tier2.munger_mental.skill import MungerMentalSkill


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_thesis_context(
    ticker: str = "BNS",
    verdict: str = "ACCUMULER",
    position_size: float = 5.0,
) -> ThesisContext:
    return ThesisContext(
        ticker=ticker,
        verdict_final=verdict,
        position_size_pct=position_size,
        scenario_bull_probabilite=0.25,
        scenario_base_probabilite=0.50,
        scenario_bear_probabilite=0.25,
        synthese_narrative="BNS présente un profil solide selon l'analyse fondamentale.",
        kill_criteria=["ROIC < 12% pendant 2 ans", "Ratio dette nette / EBITDA > 3.0×"],
        devils_advocate="Exposition au marché immobilier canadien surévalué.",
    )


def _make_munger_output_dict(
    ticker: str = "BNS",
    verdict: str = "CONFIANCE_JUSTIFIEE",
    lollapalooza: bool = False,
) -> dict:
    return {
        "ticker": ticker,
        "biais_detectes": [
            {
                "nom": "Commitment and Consistency Bias",
                "description": "L'analyste a travaillé longuement sur la thèse BNS, créant un attachement.",
                "impact_sur_these": "MINEUR",
            }
        ],
        "inversion_analysis": (
            "La thèse échouerait si : (1) le marché immobilier canadien subit un choc majeur "
            "entraînant des pertes de crédit significatives, (2) les taux d'intérêt restent élevés "
            "compressant les marges nettes d'intérêt, (3) la compétition des banques numériques "
            "érode la base de dépôts à faible coût."
        ),
        "lollapalooza_risk": lollapalooza,
        "verdict_comportemental": verdict,
        "verdict_detail": "Un seul biais mineur détecté, thèse rigoureuse avec kill criteria précis.",
        "recommandation_prochaine_etape": ["canadian_tax_considerations", "executer_position"],
    }


def _make_usage() -> UsageDetail:
    return UsageDetail(
        tokens_input=600,
        tokens_output=400,
        tokens_cache_read=1500,
        tokens_cache_creation=0,
        cost_usd=0.0055,
        model="claude-sonnet-4-6",
    )


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def munger_output_bns() -> MungerOutput:
    """MungerOutput valide pour BNS — CONFIANCE_JUSTIFIEE."""
    data = _make_munger_output_dict()
    return MungerOutput.model_validate(data)


@pytest.fixture
def thesis_context_bns() -> ThesisContext:
    return _make_thesis_context()


# ---------------------------------------------------------------------------
# Tests schémas
# ---------------------------------------------------------------------------


class TestMungerSchemas:
    def test_munger_biais_non_vide(self):
        """MungerOutput avec biais_detectes non vide → pas d'erreur."""
        data = _make_munger_output_dict()
        out = MungerOutput.model_validate(data)
        assert len(out.biais_detectes) > 0

    def test_munger_inversion_non_vide(self, munger_output_bns: MungerOutput):
        """inversion_analysis est une string non vide dans un output valide."""
        assert munger_output_bns.inversion_analysis != ""
        assert len(munger_output_bns.inversion_analysis) > 10

    def test_munger_verdict_invalide_erreur(self):
        """verdict_comportemental = 'NEUTRE' → ValidationError."""
        data = _make_munger_output_dict(verdict="NEUTRE")
        with pytest.raises(ValidationError, match="verdict_comportemental invalide"):
            MungerOutput.model_validate(data)

    def test_munger_impact_invalide_erreur(self):
        """BiaisCognitif.impact_sur_these = 'ELEVE' → ValidationError."""
        data = _make_munger_output_dict()
        data["biais_detectes"][0]["impact_sur_these"] = "ELEVE"
        with pytest.raises(ValidationError, match="impact_sur_these invalide"):
            MungerOutput.model_validate(data)

    def test_munger_lollapalooza_risk_bool_true(self):
        """lollapalooza_risk = True → accepté."""
        data = _make_munger_output_dict(lollapalooza=True)
        out = MungerOutput.model_validate(data)
        assert out.lollapalooza_risk is True

    def test_munger_lollapalooza_risk_bool_false(self):
        """lollapalooza_risk = False → accepté."""
        data = _make_munger_output_dict(lollapalooza=False)
        out = MungerOutput.model_validate(data)
        assert out.lollapalooza_risk is False

    def test_munger_verdict_confiance_justifiee_valide(self):
        data = _make_munger_output_dict(verdict="CONFIANCE_JUSTIFIEE")
        out = MungerOutput.model_validate(data)
        assert out.verdict_comportemental == "CONFIANCE_JUSTIFIEE"

    def test_munger_verdict_biais_detecte_valide(self):
        data = _make_munger_output_dict(verdict="BIAIS_DETECTE")
        out = MungerOutput.model_validate(data)
        assert out.verdict_comportemental == "BIAIS_DETECTE"

    def test_munger_verdict_alerte_rouge_valide(self):
        data = _make_munger_output_dict(verdict="ALERTE_ROUGE")
        out = MungerOutput.model_validate(data)
        assert out.verdict_comportemental == "ALERTE_ROUGE"

    def test_munger_impact_mineur_valide(self):
        data = _make_munger_output_dict()
        data["biais_detectes"][0]["impact_sur_these"] = "MINEUR"
        out = MungerOutput.model_validate(data)
        assert out.biais_detectes[0].impact_sur_these == "MINEUR"

    def test_munger_impact_modere_valide(self):
        data = _make_munger_output_dict()
        data["biais_detectes"][0]["impact_sur_these"] = "MODERE"
        out = MungerOutput.model_validate(data)
        assert out.biais_detectes[0].impact_sur_these == "MODERE"

    def test_munger_impact_majeur_valide(self):
        data = _make_munger_output_dict()
        data["biais_detectes"][0]["impact_sur_these"] = "MAJEUR"
        out = MungerOutput.model_validate(data)
        assert out.biais_detectes[0].impact_sur_these == "MAJEUR"

    def test_munger_citations_defaut_vide(self, munger_output_bns: MungerOutput):
        assert munger_output_bns.citations == []

    def test_munger_cost_usd_defaut_zero(self, munger_output_bns: MungerOutput):
        assert munger_output_bns.cost_usd == pytest.approx(0.0)

    def test_munger_biais_liste_vide_avec_confiance(self):
        """biais_detectes vide est accepté (CONFIANCE_JUSTIFIEE avec aucun biais)."""
        data = _make_munger_output_dict()
        data["biais_detectes"] = []
        out = MungerOutput.model_validate(data)
        assert out.biais_detectes == []

    def test_thesis_context_valide(self, thesis_context_bns: ThesisContext):
        assert thesis_context_bns.ticker == "BNS"
        assert thesis_context_bns.verdict_final == "ACCUMULER"
        assert len(thesis_context_bns.kill_criteria) == 2

    def test_munger_input_valide(self, thesis_context_bns: ThesisContext):
        inp = MungerInput(ticker="BNS", thesis_context=thesis_context_bns)
        assert inp.ticker == "BNS"


# ---------------------------------------------------------------------------
# Tests skill
# ---------------------------------------------------------------------------


class TestMungerMentalSkill:
    @pytest.fixture
    def skill(self) -> MungerMentalSkill:
        return MungerMentalSkill(client=MagicMock(), model="claude-sonnet-4-6")

    def test_skill_id(self, skill: MungerMentalSkill):
        assert skill.skill_id == "munger_mental_models"

    def test_tier(self, skill: MungerMentalSkill):
        assert skill.tier == 2

    def test_system_prompt_charge_et_cache(self, skill: MungerMentalSkill):
        blocks = skill.get_system_prompt()
        assert blocks[0]["cache_control"]["type"] == "ephemeral"
        assert len(blocks[0]["text"]) > 1024

    def test_system_prompt_contient_biais(self, skill: MungerMentalSkill):
        text = skill.get_system_prompt()[0]["text"]
        assert "Commitment" in text or "biais" in text.lower()

    def test_system_prompt_contient_verdicts(self, skill: MungerMentalSkill):
        text = skill.get_system_prompt()[0]["text"]
        assert "CONFIANCE_JUSTIFIEE" in text
        assert "BIAIS_DETECTE" in text
        assert "ALERTE_ROUGE" in text

    def test_system_prompt_contient_inversion(self, skill: MungerMentalSkill):
        text = skill.get_system_prompt()[0]["text"]
        assert "inversion" in text.lower() or "Invert" in text

    def test_build_user_message_contient_ticker(
        self, skill: MungerMentalSkill, thesis_context_bns: ThesisContext
    ):
        """_build_user_message(input) → message contient le ticker."""
        inp = MungerInput(ticker="BNS", thesis_context=thesis_context_bns)
        msg = skill._build_user_message(inp, citations=[])
        assert "BNS" in msg

    def test_build_user_message_contient_verdict_thesis(
        self, skill: MungerMentalSkill, thesis_context_bns: ThesisContext
    ):
        """thesis_context.verdict_final présent → message contient le verdict."""
        inp = MungerInput(ticker="BNS", thesis_context=thesis_context_bns)
        msg = skill._build_user_message(inp, citations=[])
        assert thesis_context_bns.verdict_final in msg

    def test_build_user_message_contient_kill_criteria(
        self, skill: MungerMentalSkill, thesis_context_bns: ThesisContext
    ):
        inp = MungerInput(ticker="BNS", thesis_context=thesis_context_bns)
        msg = skill._build_user_message(inp, citations=[])
        assert "kill_criteria" in msg.lower() or thesis_context_bns.kill_criteria[0] in msg

    def test_build_user_message_contient_json(
        self, skill: MungerMentalSkill, thesis_context_bns: ThesisContext
    ):
        inp = MungerInput(ticker="BNS", thesis_context=thesis_context_bns)
        msg = skill._build_user_message(inp, citations=[])
        assert "JSON" in msg or "json" in msg

    @pytest.mark.asyncio
    async def test_get_citations_rag_absent(self):
        """MungerMentalSkill avec rag_service=None → get_citations() retourne []."""
        skill = MungerMentalSkill(
            client=MagicMock(), model="claude-sonnet-4-6", rag_service=None
        )
        citations = await skill.get_citations("test query")
        assert citations == []

    @pytest.mark.asyncio
    async def test_execute_mock_claude(
        self,
        munger_output_bns: MungerOutput,
        thesis_context_bns: ThesisContext,
    ):
        """execute() retourne (MungerOutput, UsageDetail) avec cost_usd > 0."""
        mock_response = MagicMock()
        mock_block = MagicMock()
        mock_block.type = "tool_use"
        mock_block.input = munger_output_bns.model_dump(exclude={"citations", "cost_usd"})
        mock_response.content = [mock_block]
        mock_response.stop_reason = "tool_use"
        mock_response.usage = SimpleNamespace(
            input_tokens=600,
            output_tokens=400,
            cache_read_input_tokens=1500,
            cache_creation_input_tokens=0,
        )
        mock_client = MagicMock()
        mock_client.messages = AsyncMock()
        mock_client.messages.create.return_value = mock_response

        skill = MungerMentalSkill(client=mock_client, model="claude-sonnet-4-6")
        inp = MungerInput(ticker="BNS", thesis_context=thesis_context_bns)
        output, usage = await skill.execute(inp)

        assert isinstance(output, MungerOutput)
        assert isinstance(usage, UsageDetail)
        assert usage.cost_usd > 0
        assert output.cost_usd == usage.cost_usd

    @pytest.mark.asyncio
    async def test_execute_retourne_tuple_output_usage(
        self,
        munger_output_bns: MungerOutput,
        thesis_context_bns: ThesisContext,
    ):
        """execute() retourne bien un tuple (MungerOutput, UsageDetail)."""
        mock_response = MagicMock()
        mock_block = MagicMock()
        mock_block.type = "tool_use"
        mock_block.input = munger_output_bns.model_dump(exclude={"citations", "cost_usd"})
        mock_response.content = [mock_block]
        mock_response.stop_reason = "tool_use"
        mock_response.usage = SimpleNamespace(
            input_tokens=600,
            output_tokens=400,
            cache_read_input_tokens=0,
            cache_creation_input_tokens=1500,
        )
        mock_client = MagicMock()
        mock_client.messages = AsyncMock()
        mock_client.messages.create.return_value = mock_response

        skill = MungerMentalSkill(client=mock_client, model="claude-sonnet-4-6")
        inp = MungerInput(ticker="BNS", thesis_context=thesis_context_bns)
        result = await skill.execute(inp)

        assert len(result) == 2
        assert isinstance(result[0], MungerOutput)
        assert isinstance(result[1], UsageDetail)


# ---------------------------------------------------------------------------
# Tests intégration orchestrateur
# ---------------------------------------------------------------------------


class TestOrchestratorMunger:
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
        skill = AsyncMock()
        skill.execute.return_value = (thesis_output_bns, _make_usage())
        return skill

    @pytest.fixture
    def mock_munger_skill(self, munger_output_bns: MungerOutput):
        skill = AsyncMock(spec=MungerMentalSkill)
        skill.execute.return_value = (munger_output_bns, _make_usage())
        return skill

    @pytest.mark.asyncio
    async def test_orchestrator_avec_munger_apres_thesis(
        self,
        mock_db_pool,
        mock_graham_skill,
        mock_earnings_skill,
        mock_thesis_skill,
        mock_munger_skill,
        ratios_msft,
    ):
        """thesis_ratios=True + munger_ratios=True → munger présent dans response,
        skills_applied contient 'munger_mental_models'."""
        orchestrator = Orchestrator(
            db_pool=mock_db_pool,
            graham_skill=mock_graham_skill,
            earnings_skill=mock_earnings_skill,
            thesis_skill=mock_thesis_skill,
            munger_skill=mock_munger_skill,
        )
        req = AnalyzeRequest(
            ticker="BNS",
            ratios=ratios_msft,
            workflow="compounder_buffett",
            thesis_ratios=True,
            munger_ratios=True,
        )
        response = await orchestrator.run_company_analysis(req)

        assert response.munger is not None
        assert "munger_mental_models" in response.skills_applied
        mock_munger_skill.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_orchestrator_munger_sans_thesis_pas_execute(
        self,
        mock_db_pool,
        mock_graham_skill,
        mock_earnings_skill,
        mock_munger_skill,
        ratios_msft,
    ):
        """munger_ratios=True mais thesis absent (thesis_ratios=False) → munger = None."""
        orchestrator = Orchestrator(
            db_pool=mock_db_pool,
            graham_skill=mock_graham_skill,
            earnings_skill=mock_earnings_skill,
            munger_skill=mock_munger_skill,
        )
        req = AnalyzeRequest(
            ticker="BNS",
            ratios=ratios_msft,
            workflow="compounder_buffett",
            thesis_ratios=False,
            munger_ratios=True,
        )
        response = await orchestrator.run_company_analysis(req)

        assert response.munger is None
        assert "munger_mental_models" not in response.skills_applied
        mock_munger_skill.execute.assert_not_called()

    @pytest.mark.asyncio
    async def test_munger_skill_absent_pas_erreur(
        self,
        mock_db_pool,
        mock_graham_skill,
        mock_earnings_skill,
        mock_thesis_skill,
        ratios_msft,
    ):
        """munger_ratios=True mais munger_skill=None → munger = None, pas d'erreur."""
        orchestrator = Orchestrator(
            db_pool=mock_db_pool,
            graham_skill=mock_graham_skill,
            earnings_skill=mock_earnings_skill,
            thesis_skill=mock_thesis_skill,
            munger_skill=None,
        )
        req = AnalyzeRequest(
            ticker="BNS",
            ratios=ratios_msft,
            workflow="compounder_buffett",
            thesis_ratios=True,
            munger_ratios=True,
        )
        response = await orchestrator.run_company_analysis(req)

        assert response.munger is None
        assert "munger_mental_models" not in response.skills_applied

    @pytest.mark.asyncio
    async def test_munger_ratios_defaut_false(self, ratios_msft):
        """munger_ratios est False par défaut dans AnalyzeRequest."""
        req = AnalyzeRequest(ticker="BNS", ratios=ratios_msft)
        assert req.munger_ratios is False

    @pytest.mark.asyncio
    async def test_munger_response_defaut_none(self, graham_output_msft):
        """munger est None par défaut dans AnalyzeResponse."""
        resp = AnalyzeResponse(
            analysis_id="123",
            ticker="BNS",
            workflow="company_analysis",
            skills_applied=["graham_analysis"],
            graham=graham_output_msft,
            cost_usd=0.003,
            created_at="2026-05-08T10:00:00+00:00",
        )
        assert resp.munger is None


# Dépendance de conftest pour thesis_output_bns
from app.skills.tier2.thesis_builder.schemas import ThesisBuilderOutput, ThesisScenario  # noqa: E402


@pytest.fixture
def thesis_output_bns() -> ThesisBuilderOutput:
    """ThesisBuilderOutput valide pour BNS — ACCUMULER."""
    return ThesisBuilderOutput.model_validate({
        "ticker": "BNS",
        "scenario_bull": {"probabilite": 0.25, "rendement_cible": 0.80, "hypotheses": ["Expansion moat"]},
        "scenario_base": {"probabilite": 0.50, "rendement_cible": 0.30, "hypotheses": ["Croissance stable"]},
        "scenario_bear": {"probabilite": 0.25, "rendement_cible": -0.25, "hypotheses": ["Compression marges"]},
        "kill_criteria": ["ROIC < 12%", "Ratio dette > 3.0×"],
        "devils_advocate": "Exposition immobilier canadien.",
        "position_size_pct": 5.0,
        "verdict_final": "ACCUMULER",
        "synthese_narrative": "BNS présente un profil solide.",
    })
