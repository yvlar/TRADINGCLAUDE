"""Tests du skill damodaran_narrative — schemas, skill, orchestrateur."""
from __future__ import annotations

import uuid
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest
from pydantic import ValidationError

from app.orchestrator.core import AnalyzeRequest, AnalyzeResponse, Orchestrator
from app.skills.base import UsageDetail
from app.skills.tier2.damodaran_narrative.schemas import (
    DamodararInput,
    DamodararOutput,
    DamodararRatios,
)
from app.skills.tier2.damodaran_narrative.skill import DamodararNarrativeSkill


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_ratios(
    revenue_bn: float = 38.0,
    revenue_growth_5y: float = 0.06,
    net_margin: float = 0.28,
    roic: float = 0.14,
    tam_bn: float | None = None,
    market_share_pct: float | None = None,
    sector: str | None = "Banque",
) -> DamodararRatios:
    return DamodararRatios(
        revenue_bn=revenue_bn,
        revenue_growth_5y=revenue_growth_5y,
        net_margin=net_margin,
        roic=roic,
        tam_bn=tam_bn,
        market_share_pct=market_share_pct,
        sector=sector,
    )


def _make_output_dict(
    ticker: str = "BNS",
    test_coherence: str = "PLAUSIBLE",
    erp_implied: float | None = 4.2,
    narrative_strength: int = 7,
    divergences_detectees: list | None = None,
    verdict: str = "NARRATIVE_ACCEPTABLE",
) -> dict:
    return {
        "ticker": ticker,
        "test_coherence": test_coherence,
        "erp_implied": erp_implied,
        "narrative_strength": narrative_strength,
        "divergences_detectees": divergences_detectees or [],
        "verdict": verdict,
        "verdict_detail": "La narrative BNS est plausible — banque solide dans un marché oligopolistique.",
        "recommandation_prochaine_etape": ["stock_valuation_triangulation"],
    }


def _make_usage() -> UsageDetail:
    return UsageDetail(
        tokens_input=600,
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
def ratios_bns_damodaran() -> DamodararRatios:
    return _make_ratios()


@pytest.fixture
def damodaran_output_acceptable() -> DamodararOutput:
    return DamodararOutput.model_validate(_make_output_dict())


# ---------------------------------------------------------------------------
# Tests schémas DamodararRatios
# ---------------------------------------------------------------------------


class TestDamodararRatiosSchema:
    def test_damodaran_ratios_validation_ok(self, ratios_bns_damodaran: DamodararRatios):
        """DamodararRatios valide — pas d'erreur."""
        assert ratios_bns_damodaran.revenue_bn == 38.0
        assert ratios_bns_damodaran.net_margin == 0.28

    def test_damodaran_ratios_champs_optionnels_none(self):
        """tam_bn, market_share_pct, sector sont optionnels."""
        r = DamodararRatios(
            revenue_bn=10.0,
            revenue_growth_5y=0.10,
            net_margin=0.20,
            roic=0.15,
        )
        assert r.tam_bn is None
        assert r.market_share_pct is None
        assert r.sector is None


# ---------------------------------------------------------------------------
# Tests schémas DamodararOutput
# ---------------------------------------------------------------------------


class TestDamodararOutputSchema:
    def test_damodaran_output_test_coherence_valide(
        self, damodaran_output_acceptable: DamodararOutput
    ):
        """test_coherence = PLAUSIBLE → valide."""
        assert damodaran_output_acceptable.test_coherence == "PLAUSIBLE"

    def test_damodaran_output_all_coherences_valides(self):
        """Tous les niveaux de cohérence sont acceptés."""
        for c in ("POSSIBLE", "PLAUSIBLE", "PROBABLE", "INCOHERENT"):
            data = _make_output_dict(test_coherence=c)
            out = DamodararOutput.model_validate(data)
            assert out.test_coherence == c

    def test_damodaran_output_coherence_invalide_erreur(self):
        """test_coherence = 'INCERTAIN' → ValidationError."""
        data = _make_output_dict(test_coherence="INCERTAIN")
        with pytest.raises(ValidationError, match="test_coherence invalide"):
            DamodararOutput.model_validate(data)

    def test_damodaran_output_narrative_strength_plage(
        self, damodaran_output_acceptable: DamodararOutput
    ):
        """0 <= narrative_strength <= 10."""
        assert 0 <= damodaran_output_acceptable.narrative_strength <= 10

    def test_damodaran_output_narrative_strength_zero_ok(self):
        """narrative_strength = 0 → valide."""
        data = _make_output_dict(narrative_strength=0)
        out = DamodararOutput.model_validate(data)
        assert out.narrative_strength == 0

    def test_damodaran_output_narrative_strength_10_ok(self):
        """narrative_strength = 10 → valide."""
        data = _make_output_dict(narrative_strength=10)
        out = DamodararOutput.model_validate(data)
        assert out.narrative_strength == 10

    def test_damodaran_output_narrative_strength_hors_plage_erreur(self):
        """narrative_strength = 11 → ValidationError."""
        data = _make_output_dict(narrative_strength=11)
        with pytest.raises(ValidationError, match="narrative_strength hors plage"):
            DamodararOutput.model_validate(data)

    def test_damodaran_output_narrative_strength_negatif_erreur(self):
        """narrative_strength = -1 → ValidationError."""
        data = _make_output_dict(narrative_strength=-1)
        with pytest.raises(ValidationError, match="narrative_strength hors plage"):
            DamodararOutput.model_validate(data)

    def test_damodaran_output_verdict_valide(self, damodaran_output_acceptable: DamodararOutput):
        """verdict = NARRATIVE_ACCEPTABLE → valide."""
        assert damodaran_output_acceptable.verdict == "NARRATIVE_ACCEPTABLE"

    def test_damodaran_output_all_verdicts_valides(self):
        """Les 4 verdicts Damodaran sont acceptés."""
        for v in (
            "NARRATIVE_FORTE",
            "NARRATIVE_ACCEPTABLE",
            "NARRATIVE_FAIBLE",
            "NARRATIVE_INCOHERENTE",
        ):
            data = _make_output_dict(verdict=v)
            out = DamodararOutput.model_validate(data)
            assert out.verdict == v

    def test_damodaran_output_verdict_invalide_erreur(self):
        """verdict = 'BON' → ValidationError."""
        data = _make_output_dict(verdict="BON")
        with pytest.raises(ValidationError, match="verdict invalide"):
            DamodararOutput.model_validate(data)

    def test_damodaran_output_divergences_liste(self, damodaran_output_acceptable: DamodararOutput):
        """divergences_detectees est une liste."""
        assert isinstance(damodaran_output_acceptable.divergences_detectees, list)

    def test_damodaran_output_erp_implied_none_ok(self):
        """erp_implied = None → valide."""
        data = _make_output_dict(erp_implied=None)
        out = DamodararOutput.model_validate(data)
        assert out.erp_implied is None


# ---------------------------------------------------------------------------
# Tests skill
# ---------------------------------------------------------------------------


class TestDamodararNarrativeSkill:
    @pytest.fixture
    def skill(self) -> DamodararNarrativeSkill:
        return DamodararNarrativeSkill(client=MagicMock(), model="claude-sonnet-4-6")

    def test_skill_id(self, skill: DamodararNarrativeSkill):
        assert skill.skill_id == "damodaran_narrative"

    def test_tier(self, skill: DamodararNarrativeSkill):
        assert skill.tier == 2

    def test_system_prompt_charge_et_cache(self, skill: DamodararNarrativeSkill):
        blocks = skill.get_system_prompt()
        assert blocks[0]["cache_control"]["type"] == "ephemeral"
        assert len(blocks[0]["text"]) > 1024

    def test_system_prompt_contient_coherence(self, skill: DamodararNarrativeSkill):
        text = skill.get_system_prompt()[0]["text"]
        for niveau in ("POSSIBLE", "PLAUSIBLE", "PROBABLE", "INCOHERENT"):
            assert niveau in text

    def test_build_user_message_contient_ticker(
        self, skill: DamodararNarrativeSkill, ratios_bns_damodaran: DamodararRatios
    ):
        inp = DamodararInput(
            ticker="BNS",
            narrative_text="BNS est une banque solide avec un fossé oligopolistique.",
            damodaran_ratios=ratios_bns_damodaran,
        )
        msg = skill._build_user_message(inp, citations=[])
        assert "BNS" in msg

    @pytest.mark.asyncio
    async def test_get_citations_rag_absent(self):
        skill = DamodararNarrativeSkill(
            client=MagicMock(), model="claude-sonnet-4-6", rag_service=None
        )
        citations = await skill.get_citations("test query")
        assert citations == []

    @pytest.mark.asyncio
    async def test_execute_mock_claude(
        self,
        damodaran_output_acceptable: DamodararOutput,
        ratios_bns_damodaran: DamodararRatios,
    ):
        """execute() retourne (DamodararOutput, UsageDetail) avec cost_usd > 0."""
        mock_response = MagicMock()
        mock_block = MagicMock()
        mock_block.type = "tool_use"
        mock_block.input = damodaran_output_acceptable.model_dump(exclude={"citations", "cost_usd"})
        mock_response.content = [mock_block]
        mock_response.stop_reason = "tool_use"
        mock_response.usage = SimpleNamespace(
            input_tokens=600,
            output_tokens=300,
            cache_read_input_tokens=1200,
            cache_creation_input_tokens=0,
        )
        mock_client = MagicMock()
        mock_client.messages = AsyncMock()
        mock_client.messages.create.return_value = mock_response

        skill = DamodararNarrativeSkill(client=mock_client, model="claude-sonnet-4-6")
        inp = DamodararInput(
            ticker="BNS",
            narrative_text="BNS est leader en Amérique latine.",
            damodaran_ratios=ratios_bns_damodaran,
        )
        output, usage = await skill.execute(inp)

        assert isinstance(output, DamodararOutput)
        assert isinstance(usage, UsageDetail)
        assert usage.cost_usd > 0
        assert output.cost_usd == usage.cost_usd


# ---------------------------------------------------------------------------
# Tests intégration orchestrateur
# ---------------------------------------------------------------------------


class TestOrchestratorDamodaran:
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
    def mock_damodaran_skill(self, damodaran_output_acceptable: DamodararOutput):
        skill = AsyncMock(spec=DamodararNarrativeSkill)
        skill.execute.return_value = (damodaran_output_acceptable, _make_usage())
        return skill

    @pytest.mark.asyncio
    async def test_orchestrator_avec_damodaran(
        self,
        mock_db_pool,
        mock_graham_skill,
        mock_earnings_skill,
        mock_damodaran_skill,
        ratios_msft,
        ratios_bns_damodaran,
    ):
        """damodaran_input fourni → damodaran présent dans response."""
        orchestrator = Orchestrator(
            db_pool=mock_db_pool,
            graham_skill=mock_graham_skill,
            earnings_skill=mock_earnings_skill,
            damodaran_skill=mock_damodaran_skill,
        )
        req = AnalyzeRequest(
            ticker="BNS",
            ratios=ratios_msft,
            workflow="fast_grower_lynch",
            damodaran_input=DamodararInput(
                ticker="BNS",
                narrative_text="BNS est un compoundeur stable.",
                damodaran_ratios=ratios_bns_damodaran,
            ),
        )
        response = await orchestrator.run_company_analysis(req)

        assert response.damodaran is not None
        assert "damodaran_narrative" in response.skills_applied
        mock_damodaran_skill.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_orchestrator_sans_damodaran(
        self,
        mock_db_pool,
        mock_graham_skill,
        mock_earnings_skill,
        mock_damodaran_skill,
        ratios_msft,
    ):
        """Sans damodaran_input → damodaran = None."""
        orchestrator = Orchestrator(
            db_pool=mock_db_pool,
            graham_skill=mock_graham_skill,
            earnings_skill=mock_earnings_skill,
            damodaran_skill=mock_damodaran_skill,
        )
        req = AnalyzeRequest(ticker="BNS", ratios=ratios_msft, workflow="fast_grower_lynch")
        response = await orchestrator.run_company_analysis(req)

        assert response.damodaran is None
        assert "damodaran_narrative" not in response.skills_applied
        mock_damodaran_skill.execute.assert_not_called()
