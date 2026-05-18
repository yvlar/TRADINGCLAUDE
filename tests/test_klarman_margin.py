"""Tests du skill klarman_margin — schemas, skill, orchestrateur."""
from __future__ import annotations

import uuid
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest
from pydantic import ValidationError

from app.orchestrator.core import AnalyzeRequest, AnalyzeResponse, Orchestrator
from app.skills.base import UsageDetail
from app.skills.tier2.klarman_margin.schemas import (
    KlarmanInput,
    KlarmanOutput,
    KlarmanRatios,
)
from app.skills.tier2.klarman_margin.skill import KlarmanMarginSkill


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_klarman_output_dict(
    ticker: str = "BNS",
    situation_type_qualifie: str = "VALEUR_CLASSIQUE",
    marge_securite_score: int = 7,
    preservation_capital_score: int = 8,
    discount_to_intrinsic: float | None = 0.30,
    verdict: str = "OPPORTUNITE_FORTE",
) -> dict:
    return {
        "ticker": ticker,
        "situation_type_qualifie": situation_type_qualifie,
        "marge_securite_score": marge_securite_score,
        "preservation_capital_score": preservation_capital_score,
        "discount_to_intrinsic": discount_to_intrinsic,
        "verdict": verdict,
        "verdict_detail": "Décote de 30% sur NAV avec bilan solide — opportunité forte Klarman.",
        "recommandation_prochaine_etape": ["stock_valuation_triangulation", "investment_thesis_builder"],
    }


def _make_usage() -> UsageDetail:
    return UsageDetail(
        tokens_input=500,
        tokens_output=300,
        tokens_cache_read=1200,
        tokens_cache_creation=0,
        cost_usd=0.004,
        model="claude-sonnet-4-6",
    )


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def klarman_ratios_bns() -> KlarmanRatios:
    return KlarmanRatios(
        price=80.0,
        nav_per_share=115.0,
        debt_equity=0.45,
        revenue_bn=38.0,
    )


@pytest.fixture
def klarman_input_bns(klarman_ratios_bns: KlarmanRatios) -> KlarmanInput:
    return KlarmanInput(
        ticker="BNS",
        situation_type="valeur classique, banque canadienne sous-évaluée",
        klarman_ratios=klarman_ratios_bns,
    )


@pytest.fixture
def klarman_output_bns() -> KlarmanOutput:
    return KlarmanOutput.model_validate(_make_klarman_output_dict())


# ---------------------------------------------------------------------------
# Tests schémas KlarmanRatios
# ---------------------------------------------------------------------------


class TestKlarmanRatiosSchema:
    def test_klarman_ratios_validation_ok(self, klarman_ratios_bns: KlarmanRatios):
        """KlarmanRatios valide — pas d'erreur."""
        assert klarman_ratios_bns.price == 80.0
        assert klarman_ratios_bns.nav_per_share == 115.0

    def test_klarman_ratios_champs_optionnels_none(self):
        """Tous les champs optionnels acceptent None."""
        r = KlarmanRatios(price=50.0)
        assert r.nav_per_share is None
        assert r.liquidation_value is None
        assert r.debt_equity is None
        assert r.revenue_bn is None
        assert r.catalyst is None

    def test_klarman_ratios_avec_catalyst(self, klarman_ratios_bns: KlarmanRatios):
        r = KlarmanRatios(price=80.0, catalyst="Vente d'actifs en Amérique latine planifiée")
        assert r.catalyst is not None

    def test_klarman_discount_calcul(self, klarman_ratios_bns: KlarmanRatios):
        """Discount = (NAV - prix) / NAV."""
        discount = (klarman_ratios_bns.nav_per_share - klarman_ratios_bns.price) / klarman_ratios_bns.nav_per_share
        assert discount == pytest.approx((115.0 - 80.0) / 115.0)
        assert discount > 0.25  # marge de sécurité significative


# ---------------------------------------------------------------------------
# Tests schémas KlarmanOutput
# ---------------------------------------------------------------------------


class TestKlarmanOutputSchema:
    def test_klarman_output_valide(self, klarman_output_bns: KlarmanOutput):
        assert klarman_output_bns.ticker == "BNS"
        assert klarman_output_bns.situation_type_qualifie == "VALEUR_CLASSIQUE"

    def test_klarman_output_situation_type_valide(self, klarman_output_bns: KlarmanOutput):
        assert klarman_output_bns.situation_type_qualifie in {
            "NET_NET", "ACTIFS_CACHES", "DISTRESSED", "SPECIAL_SITUATION", "VALEUR_CLASSIQUE"
        }

    def test_klarman_output_all_situation_types(self):
        for st in ("NET_NET", "ACTIFS_CACHES", "DISTRESSED", "SPECIAL_SITUATION", "VALEUR_CLASSIQUE"):
            data = _make_klarman_output_dict(situation_type_qualifie=st)
            out = KlarmanOutput.model_validate(data)
            assert out.situation_type_qualifie == st

    def test_klarman_output_situation_type_invalide_erreur(self):
        data = _make_klarman_output_dict(situation_type_qualifie="DEEP_VALUE")
        with pytest.raises(ValidationError, match="situation_type_qualifie invalide"):
            KlarmanOutput.model_validate(data)

    def test_klarman_output_marge_score_plage(self, klarman_output_bns: KlarmanOutput):
        """0 <= marge_securite_score <= 10."""
        assert 0 <= klarman_output_bns.marge_securite_score <= 10

    def test_klarman_output_marge_score_zero_ok(self):
        data = _make_klarman_output_dict(
            marge_securite_score=0,
            preservation_capital_score=0,
            verdict="PASSER",
        )
        out = KlarmanOutput.model_validate(data)
        assert out.marge_securite_score == 0

    def test_klarman_output_marge_score_10_ok(self):
        data = _make_klarman_output_dict(marge_securite_score=10)
        out = KlarmanOutput.model_validate(data)
        assert out.marge_securite_score == 10

    def test_klarman_output_marge_score_invalide_erreur(self):
        data = _make_klarman_output_dict(marge_securite_score=11)
        with pytest.raises(ValidationError):
            KlarmanOutput.model_validate(data)

    def test_klarman_output_preservation_score_plage(self, klarman_output_bns: KlarmanOutput):
        """0 <= preservation_capital_score <= 10."""
        assert 0 <= klarman_output_bns.preservation_capital_score <= 10

    def test_klarman_output_preservation_score_invalide_erreur(self):
        data = _make_klarman_output_dict(preservation_capital_score=-1)
        with pytest.raises(ValidationError):
            KlarmanOutput.model_validate(data)

    def test_klarman_output_verdict_valide(self, klarman_output_bns: KlarmanOutput):
        assert klarman_output_bns.verdict == "OPPORTUNITE_FORTE"

    def test_klarman_output_all_verdicts(self):
        for v in ("OPPORTUNITE_FORTE", "OPPORTUNITE_MODEREE", "ATTENDRE", "PASSER"):
            marge = 7 if v in ("OPPORTUNITE_FORTE", "OPPORTUNITE_MODEREE") else 3
            pres = 7 if v in ("OPPORTUNITE_FORTE", "OPPORTUNITE_MODEREE") else 3
            if v == "PASSER":
                marge, pres = 1, 1
            data = _make_klarman_output_dict(
                verdict=v,
                marge_securite_score=marge,
                preservation_capital_score=pres,
            )
            out = KlarmanOutput.model_validate(data)
            assert out.verdict == v

    def test_klarman_output_verdict_invalide_erreur(self):
        data = _make_klarman_output_dict(verdict="BON")
        with pytest.raises(ValidationError, match="verdict invalide"):
            KlarmanOutput.model_validate(data)

    def test_klarman_output_discount_to_intrinsic_none(self):
        data = _make_klarman_output_dict(discount_to_intrinsic=None)
        out = KlarmanOutput.model_validate(data)
        assert out.discount_to_intrinsic is None

    def test_klarman_output_discount_to_intrinsic_negatif_ok(self):
        """Prime vs intrinsic → discount négatif accepté."""
        data = _make_klarman_output_dict(
            discount_to_intrinsic=-0.15,
            marge_securite_score=1,
            verdict="PASSER",
        )
        out = KlarmanOutput.model_validate(data)
        assert out.discount_to_intrinsic == pytest.approx(-0.15)

    def test_klarman_output_citations_defaut_vide(self, klarman_output_bns: KlarmanOutput):
        assert klarman_output_bns.citations == []

    def test_klarman_output_cost_usd_defaut_zero(self, klarman_output_bns: KlarmanOutput):
        assert klarman_output_bns.cost_usd == pytest.approx(0.0)


# ---------------------------------------------------------------------------
# Tests skill
# ---------------------------------------------------------------------------


class TestKlarmanMarginSkill:
    @pytest.fixture
    def skill(self) -> KlarmanMarginSkill:
        return KlarmanMarginSkill(client=MagicMock(), model="claude-sonnet-4-6")

    def test_skill_id(self, skill: KlarmanMarginSkill):
        assert skill.skill_id == "klarman_margin"

    def test_tier(self, skill: KlarmanMarginSkill):
        assert skill.tier == 2

    def test_system_prompt_charge_et_cache(self, skill: KlarmanMarginSkill):
        blocks = skill.get_system_prompt()
        assert blocks[0]["cache_control"]["type"] == "ephemeral"
        assert len(blocks[0]["text"]) > 1024

    def test_system_prompt_contient_situation_types(self, skill: KlarmanMarginSkill):
        text = skill.get_system_prompt()[0]["text"]
        for st in ("NET_NET", "ACTIFS_CACHES", "DISTRESSED", "SPECIAL_SITUATION", "VALEUR_CLASSIQUE"):
            assert st in text

    def test_system_prompt_contient_verdicts(self, skill: KlarmanMarginSkill):
        text = skill.get_system_prompt()[0]["text"]
        for v in ("OPPORTUNITE_FORTE", "OPPORTUNITE_MODEREE", "ATTENDRE", "PASSER"):
            assert v in text

    def test_system_prompt_contient_marge_securite(self, skill: KlarmanMarginSkill):
        text = skill.get_system_prompt()[0]["text"]
        assert "marge" in text.lower() or "margin" in text.lower()

    def test_build_user_message_contient_ticker(
        self, skill: KlarmanMarginSkill, klarman_input_bns: KlarmanInput
    ):
        msg = skill._build_user_message(klarman_input_bns, citations=[])
        assert "BNS" in msg

    def test_build_user_message_contient_prix(
        self, skill: KlarmanMarginSkill, klarman_input_bns: KlarmanInput
    ):
        msg = skill._build_user_message(klarman_input_bns, citations=[])
        assert "80.0" in msg or "80" in msg

    def test_build_user_message_contient_discount(
        self, skill: KlarmanMarginSkill, klarman_input_bns: KlarmanInput
    ):
        """NAV fournie → discount calculé dans le message."""
        msg = skill._build_user_message(klarman_input_bns, citations=[])
        assert "Discount" in msg or "discount" in msg.lower()

    @pytest.mark.asyncio
    async def test_get_citations_rag_absent(self):
        """KlarmanMarginSkill avec rag_service=None → get_citations() retourne []."""
        skill = KlarmanMarginSkill(
            client=MagicMock(), model="claude-sonnet-4-6", rag_service=None
        )
        citations = await skill.get_citations("test query")
        assert citations == []

    @pytest.mark.asyncio
    async def test_execute_mock_claude(
        self,
        klarman_output_bns: KlarmanOutput,
        klarman_input_bns: KlarmanInput,
    ):
        """execute() retourne (KlarmanOutput, UsageDetail) avec cost_usd > 0."""
        mock_response = MagicMock()
        mock_block = MagicMock()
        mock_block.type = "tool_use"
        mock_block.input = klarman_output_bns.model_dump(exclude={"citations", "cost_usd"})
        mock_response.content = [mock_block]
        mock_response.stop_reason = "tool_use"
        mock_response.usage = SimpleNamespace(
            input_tokens=500,
            output_tokens=300,
            cache_read_input_tokens=1200,
            cache_creation_input_tokens=0,
        )
        mock_client = MagicMock()
        mock_client.messages = AsyncMock()
        mock_client.messages.create.return_value = mock_response

        skill = KlarmanMarginSkill(client=mock_client, model="claude-sonnet-4-6")
        output, usage = await skill.execute(klarman_input_bns)

        assert isinstance(output, KlarmanOutput)
        assert isinstance(usage, UsageDetail)
        assert usage.cost_usd > 0
        assert output.cost_usd == usage.cost_usd


# ---------------------------------------------------------------------------
# Tests intégration orchestrateur
# ---------------------------------------------------------------------------


class TestOrchestratorKlarman:
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
    def mock_klarman_skill(self, klarman_output_bns: KlarmanOutput):
        skill = AsyncMock(spec=KlarmanMarginSkill)
        skill.execute.return_value = (klarman_output_bns, _make_usage())
        return skill

    @pytest.mark.asyncio
    async def test_orchestrator_avec_klarman(
        self,
        mock_db_pool,
        mock_graham_skill,
        mock_earnings_skill,
        mock_klarman_skill,
        klarman_input_bns: KlarmanInput,
        ratios_msft,
    ):
        """klarman_input fourni → klarman présent dans response."""
        orchestrator = Orchestrator(
            db_pool=mock_db_pool,
            graham_skill=mock_graham_skill,
            earnings_skill=mock_earnings_skill,
            klarman_skill=mock_klarman_skill,
        )
        req = AnalyzeRequest(
            ticker="BNS",
            ratios=ratios_msft,
            workflow="special_situation",
            klarman_input=klarman_input_bns,
        )
        response = await orchestrator.run_company_analysis(req)

        assert response.klarman is not None
        assert "klarman_margin" in response.skills_applied
        mock_klarman_skill.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_orchestrator_sans_klarman(
        self,
        mock_db_pool,
        mock_graham_skill,
        mock_earnings_skill,
        mock_klarman_skill,
        ratios_msft,
    ):
        """Sans klarman_input → klarman = None."""
        orchestrator = Orchestrator(
            db_pool=mock_db_pool,
            graham_skill=mock_graham_skill,
            earnings_skill=mock_earnings_skill,
            klarman_skill=mock_klarman_skill,
        )
        req = AnalyzeRequest(ticker="BNS", ratios=ratios_msft, workflow="special_situation")
        response = await orchestrator.run_company_analysis(req)

        assert response.klarman is None
        assert "klarman_margin" not in response.skills_applied
        mock_klarman_skill.execute.assert_not_called()

    @pytest.mark.asyncio
    async def test_klarman_input_defaut_none(self, ratios_msft):
        req = AnalyzeRequest(ticker="BNS", ratios=ratios_msft, workflow="special_situation")
        assert req.klarman_input is None

    @pytest.mark.asyncio
    async def test_klarman_response_defaut_none(self, graham_output_msft):
        resp = AnalyzeResponse(
            analysis_id="123",
            ticker="BNS",
            workflow="company_analysis",
            skills_applied=["graham_analysis"],
            graham=graham_output_msft,
            cost_usd=0.003,
            created_at="2026-05-08T10:00:00+00:00",
        )
        assert resp.klarman is None
