"""Tests du skill greenblatt_magic_formula — schemas, skill, orchestrateur."""
from __future__ import annotations

import uuid
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest
from pydantic import ValidationError

from app.orchestrator.core import AnalyzeRequest, AnalyzeResponse, Orchestrator
from app.skills.base import UsageDetail
from app.skills.tier2.greenblatt.schemas import (
    GreenblattInput,
    GreenblattOutput,
    GreenblattRatios,
)
from app.skills.tier2.greenblatt.skill import GreenblattSkill


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_ratios(
    ebit: float = 12.5,
    enterprise_value: float = 90.0,
    net_working_capital: float = 8.0,
    net_fixed_assets: float = 15.0,
    sector: str | None = None,
) -> GreenblattRatios:
    return GreenblattRatios(
        ebit=ebit,
        enterprise_value=enterprise_value,
        net_working_capital=net_working_capital,
        net_fixed_assets=net_fixed_assets,
        sector=sector,
    )


def _make_output_dict(
    ticker: str = "BNS",
    roc: float = 0.4950,
    earnings_yield: float = 0.1389,
    verdict: str = "TOP_DECILE",
    situations_speciales: list | None = None,
) -> dict:
    return {
        "ticker": ticker,
        "roc": roc,
        "earnings_yield": earnings_yield,
        "verdict": verdict,
        "situations_speciales": situations_speciales or [],
        "verdict_detail": "BNS en top-décile selon la Magic Formula.",
        "recommandation_prochaine_etape": ["graham_analysis", "buffett_quality"],
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
def ratios_top_decile() -> GreenblattRatios:
    """Ratios permettant un verdict TOP_DECILE (ROC > 25 %, EY > 10 %)."""
    return _make_ratios()


@pytest.fixture
def greenblatt_output_top() -> GreenblattOutput:
    return GreenblattOutput.model_validate(_make_output_dict())


# ---------------------------------------------------------------------------
# Tests schémas GreenblattRatios
# ---------------------------------------------------------------------------


class TestGreenblattRatiosSchema:
    def test_greenblatt_ratios_validation_ok(self, ratios_top_decile: GreenblattRatios):
        """GreenblattRatios valide — pas d'erreur."""
        assert ratios_top_decile.ebit == 12.5
        assert ratios_top_decile.enterprise_value == 90.0

    def test_greenblatt_roc_calcul(self, ratios_top_decile: GreenblattRatios):
        """ROC = EBIT / (NWC + NFA)."""
        r = ratios_top_decile
        roc = r.ebit / (r.net_working_capital + r.net_fixed_assets)
        assert roc == pytest.approx(12.5 / 23.0)
        assert roc == pytest.approx(0.5435, rel=1e-3)

    def test_greenblatt_earnings_yield_calcul(self, ratios_top_decile: GreenblattRatios):
        """Earnings Yield = EBIT / EV."""
        r = ratios_top_decile
        ey = r.ebit / r.enterprise_value
        assert ey == pytest.approx(12.5 / 90.0)
        assert ey == pytest.approx(0.1389, rel=1e-2)

    def test_greenblatt_enterprise_value_zero_erreur(self):
        """enterprise_value = 0 → ValidationError."""
        with pytest.raises(ValidationError, match="enterprise_value"):
            GreenblattRatios(
                ebit=10.0,
                enterprise_value=0.0,
                net_working_capital=5.0,
                net_fixed_assets=5.0,
            )

    def test_greenblatt_enterprise_value_negatif_erreur(self):
        """enterprise_value < 0 → ValidationError."""
        with pytest.raises(ValidationError, match="enterprise_value"):
            GreenblattRatios(
                ebit=10.0,
                enterprise_value=-1.0,
                net_working_capital=5.0,
                net_fixed_assets=5.0,
            )

    def test_greenblatt_capital_investi_zero_erreur(self):
        """NWC + NFA = 0 → ValidationError."""
        with pytest.raises(ValidationError, match="net_working_capital"):
            GreenblattRatios(
                ebit=10.0,
                enterprise_value=100.0,
                net_working_capital=0.0,
                net_fixed_assets=0.0,
            )

    def test_greenblatt_sector_optionnel(self):
        """sector est optionnel — None accepté."""
        r = GreenblattRatios(
            ebit=10.0, enterprise_value=50.0, net_working_capital=5.0, net_fixed_assets=5.0
        )
        assert r.sector is None


# ---------------------------------------------------------------------------
# Tests schémas GreenblattOutput
# ---------------------------------------------------------------------------


class TestGreenblattOutputSchema:
    def test_greenblatt_output_verdict_valide(self, greenblatt_output_top: GreenblattOutput):
        """verdict = TOP_DECILE → valide."""
        assert greenblatt_output_top.verdict == "TOP_DECILE"

    def test_greenblatt_output_all_verdicts_valides(self):
        """Les 4 verdicts Greenblatt sont acceptés."""
        for v in ("TOP_DECILE", "BON", "MOYEN", "EVITER"):
            data = _make_output_dict(verdict=v)
            out = GreenblattOutput.model_validate(data)
            assert out.verdict == v

    def test_greenblatt_output_verdict_invalide_erreur(self):
        """verdict = 'NEUTRE' → ValidationError."""
        data = _make_output_dict(verdict="NEUTRE")
        with pytest.raises(ValidationError, match="verdict invalide"):
            GreenblattOutput.model_validate(data)

    def test_greenblatt_output_situations_speciales_liste(self, greenblatt_output_top: GreenblattOutput):
        """situations_speciales est une liste."""
        assert isinstance(greenblatt_output_top.situations_speciales, list)

    def test_greenblatt_output_situations_speciales_avec_valeurs(self):
        """situations_speciales peut contenir des valeurs."""
        data = _make_output_dict(situations_speciales=["spinoff", "restructuration"])
        out = GreenblattOutput.model_validate(data)
        assert len(out.situations_speciales) == 2
        assert "spinoff" in out.situations_speciales

    def test_greenblatt_output_citations_defaut_vide(self, greenblatt_output_top: GreenblattOutput):
        assert greenblatt_output_top.citations == []

    def test_greenblatt_output_cost_usd_defaut_zero(self, greenblatt_output_top: GreenblattOutput):
        assert greenblatt_output_top.cost_usd == pytest.approx(0.0)


# ---------------------------------------------------------------------------
# Tests skill
# ---------------------------------------------------------------------------


class TestGreenblattSkill:
    @pytest.fixture
    def skill(self) -> GreenblattSkill:
        return GreenblattSkill(client=MagicMock(), model="claude-sonnet-4-6")

    def test_skill_id(self, skill: GreenblattSkill):
        assert skill.skill_id == "greenblatt_magic_formula"

    def test_tier(self, skill: GreenblattSkill):
        assert skill.tier == 2

    def test_system_prompt_charge_et_cache(self, skill: GreenblattSkill):
        blocks = skill.get_system_prompt()
        assert blocks[0]["cache_control"]["type"] == "ephemeral"
        assert len(blocks[0]["text"]) > 1024

    def test_system_prompt_contient_roc(self, skill: GreenblattSkill):
        text = skill.get_system_prompt()[0]["text"]
        assert "ROC" in text

    def test_system_prompt_contient_verdicts(self, skill: GreenblattSkill):
        text = skill.get_system_prompt()[0]["text"]
        for v in ("TOP_DECILE", "BON", "MOYEN", "EVITER"):
            assert v in text

    def test_build_user_message_contient_ticker(
        self, skill: GreenblattSkill, ratios_top_decile: GreenblattRatios
    ):
        inp = GreenblattInput(ticker="BNS", greenblatt_ratios=ratios_top_decile)
        msg = skill._build_user_message(inp, citations=[])
        assert "BNS" in msg

    def test_build_user_message_contient_roc(
        self, skill: GreenblattSkill, ratios_top_decile: GreenblattRatios
    ):
        inp = GreenblattInput(ticker="BNS", greenblatt_ratios=ratios_top_decile)
        msg = skill._build_user_message(inp, citations=[])
        assert "ROC" in msg

    @pytest.mark.asyncio
    async def test_get_citations_rag_absent(self):
        """GreenblattSkill avec rag_service=None → get_citations() retourne []."""
        skill = GreenblattSkill(client=MagicMock(), model="claude-sonnet-4-6", rag_service=None)
        citations = await skill.get_citations("test query")
        assert citations == []

    @pytest.mark.asyncio
    async def test_execute_mock_claude(
        self,
        greenblatt_output_top: GreenblattOutput,
        ratios_top_decile: GreenblattRatios,
    ):
        """execute() retourne (GreenblattOutput, UsageDetail) avec cost_usd > 0."""
        mock_response = MagicMock()
        mock_block = MagicMock()
        mock_block.type = "tool_use"
        mock_block.input = greenblatt_output_top.model_dump(exclude={"citations", "cost_usd"})
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

        skill = GreenblattSkill(client=mock_client, model="claude-sonnet-4-6")
        inp = GreenblattInput(ticker="BNS", greenblatt_ratios=ratios_top_decile)
        output, usage = await skill.execute(inp)

        assert isinstance(output, GreenblattOutput)
        assert isinstance(usage, UsageDetail)
        assert usage.cost_usd > 0
        assert output.cost_usd == usage.cost_usd


# ---------------------------------------------------------------------------
# Tests intégration orchestrateur
# ---------------------------------------------------------------------------


class TestOrchestratorGreenblatt:
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
    def mock_greenblatt_skill(self, greenblatt_output_top: GreenblattOutput):
        skill = AsyncMock(spec=GreenblattSkill)
        skill.execute.return_value = (greenblatt_output_top, _make_usage())
        return skill

    @pytest.mark.asyncio
    async def test_orchestrator_avec_greenblatt(
        self,
        mock_db_pool,
        mock_graham_skill,
        mock_earnings_skill,
        mock_greenblatt_skill,
        ratios_msft,
        ratios_top_decile,
    ):
        """greenblatt_input fourni → greenblatt présent dans response."""
        orchestrator = Orchestrator(
            db_pool=mock_db_pool,
            graham_skill=mock_graham_skill,
            earnings_skill=mock_earnings_skill,
            greenblatt_skill=mock_greenblatt_skill,
        )
        req = AnalyzeRequest(
            ticker="BNS",
            ratios=ratios_msft,
            workflow="special_situation",
            greenblatt_input=GreenblattInput(
                ticker="BNS", greenblatt_ratios=ratios_top_decile
            ),
        )
        response = await orchestrator.run_company_analysis(req)

        assert response.greenblatt is not None
        assert "greenblatt_magic_formula" in response.skills_applied
        mock_greenblatt_skill.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_orchestrator_sans_greenblatt(
        self,
        mock_db_pool,
        mock_graham_skill,
        mock_earnings_skill,
        mock_greenblatt_skill,
        ratios_msft,
    ):
        """Sans greenblatt_input → greenblatt = None."""
        orchestrator = Orchestrator(
            db_pool=mock_db_pool,
            graham_skill=mock_graham_skill,
            earnings_skill=mock_earnings_skill,
            greenblatt_skill=mock_greenblatt_skill,
        )
        req = AnalyzeRequest(ticker="BNS", ratios=ratios_msft, workflow="special_situation")
        response = await orchestrator.run_company_analysis(req)

        assert response.greenblatt is None
        assert "greenblatt_magic_formula" not in response.skills_applied
        mock_greenblatt_skill.execute.assert_not_called()
