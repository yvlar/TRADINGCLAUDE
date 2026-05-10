"""Tests du skill lynch_categories — schemas, skill, orchestrateur."""
from __future__ import annotations

import uuid
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest
from pydantic import ValidationError

from app.orchestrator.core import AnalyzeRequest, AnalyzeResponse, Orchestrator
from app.skills.base import UsageDetail
from app.skills.tier2.lynch_categories.schemas import (
    LynchInput,
    LynchOutput,
    LynchRatios,
)
from app.skills.tier2.lynch_categories.skill import LynchCategoriesSkill


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_lynch_output_dict(
    ticker: str = "BNS",
    categorie: str = "STALWART",
    peg_ratio: float | None = 2.2,
    tenbagger_potential: bool = False,
    score_croissance: int = 3,
    verdict: str = "BON",
) -> dict:
    return {
        "ticker": ticker,
        "categorie": categorie,
        "peg_ratio": peg_ratio,
        "tenbagger_potential": tenbagger_potential,
        "score_croissance": score_croissance,
        "verdict": verdict,
        "verdict_detail": "BNS est un stalwart bancaire canadien avec PEG de 2.2.",
        "recommandation_prochaine_etape": ["buffett_quality", "stock_valuation_triangulation"],
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
def ratios_stalwart() -> LynchRatios:
    """Ratios typiques d'un stalwart — BNS."""
    return LynchRatios(
        pe=11.0,
        eps_growth_5y=0.05,
        revenue_growth_5y=0.06,
        net_margin=0.28,
        debt_equity=0.45,
        dividend_yield=0.065,
    )


@pytest.fixture
def ratios_fast_grower() -> LynchRatios:
    """Ratios typiques d'un fast grower — tenbagger potentiel (PEG < 1)."""
    return LynchRatios(
        pe=22.0,
        eps_growth_5y=0.30,
        revenue_growth_5y=0.35,
        net_margin=0.18,
    )


@pytest.fixture
def lynch_output_stalwart() -> LynchOutput:
    return LynchOutput.model_validate(_make_lynch_output_dict())


@pytest.fixture
def lynch_output_fast_grower() -> LynchOutput:
    return LynchOutput.model_validate(
        _make_lynch_output_dict(
            categorie="FAST_GROWER",
            peg_ratio=0.73,
            tenbagger_potential=True,
            score_croissance=5,
            verdict="EXCELLENT",
        )
    )


# ---------------------------------------------------------------------------
# Tests schémas LynchRatios
# ---------------------------------------------------------------------------


class TestLynchRatiosSchema:
    def test_lynch_ratios_validation_ok(self, ratios_stalwart: LynchRatios):
        """LynchRatios valide — pas d'erreur."""
        assert ratios_stalwart.pe == 11.0
        assert ratios_stalwart.eps_growth_5y == 0.05

    def test_lynch_ratios_champs_optionnels_none(self):
        """Champs optionnels acceptent None."""
        r = LynchRatios(pe=20.0, eps_growth_5y=0.10)
        assert r.revenue_growth_5y is None
        assert r.net_margin is None
        assert r.dividend_yield is None
        assert r.capex_intensity is None

    def test_lynch_peg_ratio_calcul(self, ratios_stalwart: LynchRatios):
        """PEG = pe / (eps_growth_5y * 100)."""
        peg = ratios_stalwart.pe / (ratios_stalwart.eps_growth_5y * 100)
        assert peg == pytest.approx(11.0 / 5.0)
        assert peg == pytest.approx(2.2)

    def test_lynch_peg_ratio_fast_grower(self, ratios_fast_grower: LynchRatios):
        """Fast grower avec forte croissance — PEG < 1."""
        peg = ratios_fast_grower.pe / (ratios_fast_grower.eps_growth_5y * 100)
        assert peg == pytest.approx(22.0 / 30.0)
        assert peg < 1.0

    def test_lynch_peg_ratio_null_si_croissance_nulle(self):
        """eps_growth_5y = 0 → on ne divise pas (PEG serait infini)."""
        r = LynchRatios(pe=15.0, eps_growth_5y=0.0)
        assert r.eps_growth_5y <= 0  # confirme la règle nullité

    def test_lynch_peg_ratio_null_si_croissance_negative(self):
        """eps_growth_5y < 0 → PEG = null selon la règle Lynch."""
        r = LynchRatios(pe=15.0, eps_growth_5y=-0.05)
        assert r.eps_growth_5y <= 0


# ---------------------------------------------------------------------------
# Tests schémas LynchOutput
# ---------------------------------------------------------------------------


class TestLynchOutputSchema:
    def test_lynch_output_categorie_valide(self, lynch_output_stalwart: LynchOutput):
        """categorie = STALWART → valide."""
        assert lynch_output_stalwart.categorie == "STALWART"

    def test_lynch_output_all_categories_valides(self):
        """Toutes les 6 catégories Lynch sont acceptées."""
        for cat in ("SLOW_GROWER", "STALWART", "FAST_GROWER", "CYCLICAL", "TURNAROUND", "ASSET_PLAY"):
            data = _make_lynch_output_dict(categorie=cat, tenbagger_potential=False)
            if cat == "FAST_GROWER":
                data["peg_ratio"] = 1.5  # PEG >= 1 → pas de tenbagger
            out = LynchOutput.model_validate(data)
            assert out.categorie == cat

    def test_lynch_output_score_croissance_plage(self, lynch_output_stalwart: LynchOutput):
        """score_croissance dans [0, 5]."""
        assert 0 <= lynch_output_stalwart.score_croissance <= 5

    def test_lynch_output_verdict_valide(self, lynch_output_stalwart: LynchOutput):
        """verdict = BON → valide."""
        assert lynch_output_stalwart.verdict == "BON"

    def test_lynch_output_all_verdicts_valides(self):
        """Les 4 verdicts Lynch sont acceptés."""
        for v in ("EXCELLENT", "BON", "MOYEN", "EVITER"):
            data = _make_lynch_output_dict(verdict=v)
            out = LynchOutput.model_validate(data)
            assert out.verdict == v

    def test_lynch_output_categorie_invalide_erreur(self):
        """categorie = 'GROWTH_STOCK' → ValidationError."""
        data = _make_lynch_output_dict(categorie="GROWTH_STOCK")
        with pytest.raises(ValidationError, match="categorie invalide"):
            LynchOutput.model_validate(data)

    def test_lynch_output_verdict_invalide_erreur(self):
        """verdict = 'NEUTRE' → ValidationError."""
        data = _make_lynch_output_dict(verdict="NEUTRE")
        with pytest.raises(ValidationError, match="verdict invalide"):
            LynchOutput.model_validate(data)

    def test_lynch_output_score_croissance_trop_grand_erreur(self):
        """score_croissance = 6 → ValidationError."""
        data = _make_lynch_output_dict(score_croissance=6)
        with pytest.raises(ValidationError, match="score_croissance hors plage"):
            LynchOutput.model_validate(data)

    def test_lynch_output_score_croissance_negatif_erreur(self):
        """score_croissance = -1 → ValidationError."""
        data = _make_lynch_output_dict(score_croissance=-1)
        with pytest.raises(ValidationError, match="score_croissance hors plage"):
            LynchOutput.model_validate(data)

    def test_lynch_tenbagger_fast_grower_peg_inferieur_1(self, lynch_output_fast_grower: LynchOutput):
        """FAST_GROWER + PEG < 1 → tenbagger_potential = True."""
        assert lynch_output_fast_grower.tenbagger_potential is True
        assert lynch_output_fast_grower.categorie == "FAST_GROWER"
        assert lynch_output_fast_grower.peg_ratio < 1.0

    def test_lynch_tenbagger_false_si_pas_fast_grower(self, lynch_output_stalwart: LynchOutput):
        """STALWART → tenbagger_potential = False."""
        assert lynch_output_stalwart.tenbagger_potential is False

    def test_lynch_tenbagger_true_exige_fast_grower(self):
        """tenbagger_potential=True + categorie STALWART → ValidationError."""
        data = _make_lynch_output_dict(
            categorie="STALWART",
            peg_ratio=0.5,
            tenbagger_potential=True,
        )
        with pytest.raises(ValidationError, match="nécessite categorie=FAST_GROWER"):
            LynchOutput.model_validate(data)

    def test_lynch_tenbagger_true_exige_peg_inferieur_1(self):
        """tenbagger_potential=True + PEG = 1.5 → ValidationError."""
        data = _make_lynch_output_dict(
            categorie="FAST_GROWER",
            peg_ratio=1.5,
            tenbagger_potential=True,
        )
        with pytest.raises(ValidationError, match="nécessite peg_ratio < 1.0"):
            LynchOutput.model_validate(data)

    def test_lynch_tenbagger_true_exige_peg_not_null(self):
        """tenbagger_potential=True + peg_ratio=None → ValidationError."""
        data = _make_lynch_output_dict(
            categorie="FAST_GROWER",
            peg_ratio=None,
            tenbagger_potential=True,
        )
        with pytest.raises(ValidationError, match="nécessite peg_ratio < 1.0"):
            LynchOutput.model_validate(data)

    def test_lynch_citations_defaut_vide(self, lynch_output_stalwart: LynchOutput):
        assert lynch_output_stalwart.citations == []

    def test_lynch_cost_usd_defaut_zero(self, lynch_output_stalwart: LynchOutput):
        assert lynch_output_stalwart.cost_usd == pytest.approx(0.0)


# ---------------------------------------------------------------------------
# Tests skill
# ---------------------------------------------------------------------------


class TestLynchCategoriesSkill:
    @pytest.fixture
    def skill(self) -> LynchCategoriesSkill:
        return LynchCategoriesSkill(client=MagicMock(), model="claude-sonnet-4-6")

    def test_skill_id(self, skill: LynchCategoriesSkill):
        assert skill.skill_id == "lynch_categories"

    def test_tier(self, skill: LynchCategoriesSkill):
        assert skill.tier == 2

    def test_system_prompt_charge_et_cache(self, skill: LynchCategoriesSkill):
        blocks = skill.get_system_prompt()
        assert blocks[0]["cache_control"]["type"] == "ephemeral"
        assert len(blocks[0]["text"]) > 1024

    def test_system_prompt_contient_categories(self, skill: LynchCategoriesSkill):
        text = skill.get_system_prompt()[0]["text"]
        for cat in ("SLOW_GROWER", "STALWART", "FAST_GROWER", "CYCLICAL", "TURNAROUND", "ASSET_PLAY"):
            assert cat in text

    def test_system_prompt_contient_verdicts(self, skill: LynchCategoriesSkill):
        text = skill.get_system_prompt()[0]["text"]
        for v in ("EXCELLENT", "BON", "MOYEN", "EVITER"):
            assert v in text

    def test_system_prompt_contient_peg(self, skill: LynchCategoriesSkill):
        text = skill.get_system_prompt()[0]["text"]
        assert "PEG" in text or "peg" in text.lower()

    def test_build_user_message_contient_ticker(
        self, skill: LynchCategoriesSkill, ratios_stalwart: LynchRatios
    ):
        inp = LynchInput(ticker="BNS", ratios=ratios_stalwart)
        msg = skill._build_user_message(inp, citations=[])
        assert "BNS" in msg

    def test_build_user_message_contient_ratios(
        self, skill: LynchCategoriesSkill, ratios_stalwart: LynchRatios
    ):
        inp = LynchInput(ticker="BNS", ratios=ratios_stalwart)
        msg = skill._build_user_message(inp, citations=[])
        assert str(ratios_stalwart.pe) in msg

    @pytest.mark.asyncio
    async def test_get_citations_rag_absent(self):
        """LynchCategoriesSkill avec rag_service=None → get_citations() retourne []."""
        skill = LynchCategoriesSkill(
            client=MagicMock(), model="claude-sonnet-4-6", rag_service=None
        )
        citations = await skill.get_citations("test query")
        assert citations == []

    @pytest.mark.asyncio
    async def test_execute_mock_claude(
        self,
        lynch_output_stalwart: LynchOutput,
        ratios_stalwart: LynchRatios,
    ):
        """execute() retourne (LynchOutput, UsageDetail) avec cost_usd > 0."""
        mock_response = MagicMock()
        mock_response.content = [MagicMock(text=lynch_output_stalwart.model_dump_json())]
        mock_response.usage = SimpleNamespace(
            input_tokens=600,
            output_tokens=300,
            cache_read_input_tokens=1200,
            cache_creation_input_tokens=0,
        )
        mock_client = MagicMock()
        mock_client.messages = AsyncMock()
        mock_client.messages.create.return_value = mock_response

        skill = LynchCategoriesSkill(client=mock_client, model="claude-sonnet-4-6")
        inp = LynchInput(ticker="BNS", ratios=ratios_stalwart)
        output, usage = await skill.execute(inp)

        assert isinstance(output, LynchOutput)
        assert isinstance(usage, UsageDetail)
        assert usage.cost_usd > 0
        assert output.cost_usd == usage.cost_usd


# ---------------------------------------------------------------------------
# Tests intégration orchestrateur
# ---------------------------------------------------------------------------


class TestOrchestratorLynch:
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
    def mock_lynch_skill(self, lynch_output_stalwart: LynchOutput):
        skill = AsyncMock(spec=LynchCategoriesSkill)
        skill.execute.return_value = (lynch_output_stalwart, _make_usage())
        return skill

    @pytest.mark.asyncio
    async def test_orchestrator_avec_lynch(
        self,
        mock_db_pool,
        mock_graham_skill,
        mock_earnings_skill,
        mock_lynch_skill,
        ratios_msft,
        ratios_stalwart,
    ):
        """lynch_ratios fournis → lynch présent dans response."""
        orchestrator = Orchestrator(
            db_pool=mock_db_pool,
            graham_skill=mock_graham_skill,
            earnings_skill=mock_earnings_skill,
            lynch_skill=mock_lynch_skill,
        )
        req = AnalyzeRequest(
            ticker="BNS",
            ratios=ratios_msft,
            lynch_ratios=ratios_stalwart,
        )
        response = await orchestrator.run_company_analysis(req)

        assert response.lynch is not None
        assert "lynch_categories" in response.skills_applied
        mock_lynch_skill.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_orchestrator_sans_lynch(
        self,
        mock_db_pool,
        mock_graham_skill,
        mock_earnings_skill,
        mock_lynch_skill,
        ratios_msft,
    ):
        """Sans lynch_ratios → lynch = None."""
        orchestrator = Orchestrator(
            db_pool=mock_db_pool,
            graham_skill=mock_graham_skill,
            earnings_skill=mock_earnings_skill,
            lynch_skill=mock_lynch_skill,
        )
        req = AnalyzeRequest(ticker="BNS", ratios=ratios_msft)
        response = await orchestrator.run_company_analysis(req)

        assert response.lynch is None
        assert "lynch_categories" not in response.skills_applied
        mock_lynch_skill.execute.assert_not_called()

    @pytest.mark.asyncio
    async def test_lynch_ratios_defaut_none(self, ratios_msft):
        """lynch_ratios est None par défaut dans AnalyzeRequest."""
        req = AnalyzeRequest(ticker="BNS", ratios=ratios_msft)
        assert req.lynch_ratios is None

    @pytest.mark.asyncio
    async def test_lynch_response_defaut_none(self, graham_output_msft):
        """lynch est None par défaut dans AnalyzeResponse."""
        resp = AnalyzeResponse(
            analysis_id="123",
            ticker="BNS",
            workflow="company_analysis",
            skills_applied=["graham_analysis"],
            graham=graham_output_msft,
            cost_usd=0.003,
            created_at="2026-05-08T10:00:00+00:00",
        )
        assert resp.lynch is None
