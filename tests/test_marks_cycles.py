"""Tests du skill marks_cycles_risk — schemas, skill, orchestrateur."""
from __future__ import annotations

import uuid
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest
from pydantic import ValidationError

from app.orchestrator.core import AnalyzeRequest, Orchestrator
from app.skills.base import UsageDetail
from app.skills.tier2.marks_cycles.schemas import (
    MarksInput,
    MarksOutput,
    MarksRatios,
)
from app.skills.tier2.marks_cycles.skill import MarksCyclesSkill

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_ratios(
    pe_market: float | None = 22.0,
    vix: float | None = 18.0,
    credit_spreads_bps: float | None = 110.0,
    insider_net_buying: float | None = None,
    bullish_sentiment_pct: float | None = 0.45,
) -> MarksRatios:
    return MarksRatios(
        pe_market=pe_market,
        vix=vix,
        credit_spreads_bps=credit_spreads_bps,
        insider_net_buying=insider_net_buying,
        bullish_sentiment_pct=bullish_sentiment_pct,
    )


def _make_output_dict(
    position_cycle: str = "NEUTRE",
    pendule_score: int = -1,
    recommandation_timing: str = "ATTENDRE",
) -> dict:
    return {
        "position_cycle": position_cycle,
        "pendule_score": pendule_score,
        "second_level_insight": "Le consensus voit le marché comme 'normal'. Second-level : les valorisations restent tendues vs taux.",
        "recommandation_timing": recommandation_timing,
        "verdict_detail": "Marché en zone neutre, prudence justifiée.",
        "recommandation_prochaine_etape": ["investment_thesis_builder"],
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
def ratios_neutre() -> MarksRatios:
    return _make_ratios()


@pytest.fixture
def marks_output_neutre() -> MarksOutput:
    return MarksOutput.model_validate(_make_output_dict())


# ---------------------------------------------------------------------------
# Tests schémas MarksRatios
# ---------------------------------------------------------------------------


class TestMarksRatiosSchema:
    def test_marks_ratios_champs_optionnels_none(self):
        """Tous les champs sont optionnels — MarksRatios vide valide."""
        r = MarksRatios()
        assert r.pe_market is None
        assert r.vix is None
        assert r.credit_spreads_bps is None
        assert r.insider_net_buying is None
        assert r.bullish_sentiment_pct is None

    def test_marks_ratios_avec_valeurs(self, ratios_neutre: MarksRatios):
        """MarksRatios avec valeurs — valide."""
        assert ratios_neutre.pe_market == 22.0
        assert ratios_neutre.vix == 18.0


# ---------------------------------------------------------------------------
# Tests schémas MarksOutput
# ---------------------------------------------------------------------------


class TestMarksOutputSchema:
    def test_marks_output_position_cycle_valide(self, marks_output_neutre: MarksOutput):
        """position_cycle = NEUTRE → valide."""
        assert marks_output_neutre.position_cycle == "NEUTRE"

    def test_marks_output_all_positions_valides(self):
        """Toutes les 5 positions de cycle sont acceptées."""
        for pos in ("PESSIMISME_EXCESSIF", "PESSIMISME", "NEUTRE", "OPTIMISME", "EUPHORIE"):
            data = _make_output_dict(position_cycle=pos)
            out = MarksOutput.model_validate(data)
            assert out.position_cycle == pos

    def test_marks_output_position_cycle_invalide_erreur(self):
        """position_cycle = 'NORMAL' → ValidationError."""
        data = _make_output_dict(position_cycle="NORMAL")
        with pytest.raises(ValidationError, match="position_cycle invalide"):
            MarksOutput.model_validate(data)

    def test_marks_output_pendule_score_plage(self, marks_output_neutre: MarksOutput):
        """-5 <= pendule_score <= 5."""
        assert -5 <= marks_output_neutre.pendule_score <= 5

    def test_marks_output_pendule_score_negatif_ok(self):
        """pendule_score = -5 → valide (pessimisme excessif)."""
        data = _make_output_dict(
            position_cycle="PESSIMISME_EXCESSIF",
            pendule_score=-5,
            recommandation_timing="ACHETER_AGRESSIF",
        )
        out = MarksOutput.model_validate(data)
        assert out.pendule_score == -5

    def test_marks_output_pendule_score_positif_ok(self):
        """pendule_score = +5 → valide (euphorie)."""
        data = _make_output_dict(
            position_cycle="EUPHORIE",
            pendule_score=5,
            recommandation_timing="VENDRE",
        )
        out = MarksOutput.model_validate(data)
        assert out.pendule_score == 5

    def test_marks_output_pendule_score_hors_plage_erreur(self):
        """pendule_score = 6 → ValidationError."""
        data = _make_output_dict(pendule_score=6)
        with pytest.raises(ValidationError, match="pendule_score hors plage"):
            MarksOutput.model_validate(data)

    def test_marks_output_pendule_score_trop_negatif_erreur(self):
        """pendule_score = -6 → ValidationError."""
        data = _make_output_dict(pendule_score=-6)
        with pytest.raises(ValidationError, match="pendule_score hors plage"):
            MarksOutput.model_validate(data)

    def test_marks_output_recommandation_timing_valide(self, marks_output_neutre: MarksOutput):
        """recommandation_timing = ATTENDRE → valide."""
        assert marks_output_neutre.recommandation_timing == "ATTENDRE"

    def test_marks_output_all_timings_valides(self):
        """Les 5 timings sont acceptés."""
        for timing in (
            "ACHETER_AGRESSIF",
            "ACHETER_PRUDEMMENT",
            "ATTENDRE",
            "REDUIRE",
            "VENDRE",
        ):
            data = _make_output_dict(recommandation_timing=timing)
            out = MarksOutput.model_validate(data)
            assert out.recommandation_timing == timing

    def test_marks_output_timing_invalide_erreur(self):
        """recommandation_timing = 'CONSERVER' → ValidationError."""
        data = _make_output_dict(recommandation_timing="CONSERVER")
        with pytest.raises(ValidationError, match="recommandation_timing invalide"):
            MarksOutput.model_validate(data)

    def test_marks_output_pas_de_ticker(self, marks_output_neutre: MarksOutput):
        """MarksOutput n'a pas de champ ticker — analyse de marché."""
        assert not hasattr(marks_output_neutre, "ticker")

    def test_marks_output_citations_defaut_vide(self, marks_output_neutre: MarksOutput):
        assert marks_output_neutre.citations == []


# ---------------------------------------------------------------------------
# Tests skill
# ---------------------------------------------------------------------------


class TestMarksCyclesSkill:
    @pytest.fixture
    def skill(self) -> MarksCyclesSkill:
        return MarksCyclesSkill(client=MagicMock(), model="claude-sonnet-4-6")

    def test_skill_id(self, skill: MarksCyclesSkill):
        assert skill.skill_id == "marks_cycles_risk"

    def test_tier(self, skill: MarksCyclesSkill):
        assert skill.tier == 2

    def test_system_prompt_charge_et_cache(self, skill: MarksCyclesSkill):
        blocks = skill.get_system_prompt()
        assert blocks[0]["cache_control"]["type"] == "ephemeral"
        assert len(blocks[0]["text"]) > 1024

    def test_system_prompt_contient_pendule(self, skill: MarksCyclesSkill):
        text = skill.get_system_prompt()[0]["text"]
        assert "pendule" in text.lower() or "PESSIMISME" in text

    def test_system_prompt_contient_positions(self, skill: MarksCyclesSkill):
        text = skill.get_system_prompt()[0]["text"]
        for pos in ("PESSIMISME_EXCESSIF", "PESSIMISME", "NEUTRE", "OPTIMISME", "EUPHORIE"):
            assert pos in text

    @pytest.mark.asyncio
    async def test_get_citations_rag_absent(self):
        skill = MarksCyclesSkill(client=MagicMock(), model="claude-sonnet-4-6", rag_service=None)
        citations = await skill.get_citations("test query")
        assert citations == []

    @pytest.mark.asyncio
    async def test_execute_mock_claude(
        self,
        marks_output_neutre: MarksOutput,
        ratios_neutre: MarksRatios,
    ):
        """execute() retourne (MarksOutput, UsageDetail) avec cost_usd > 0."""
        mock_response = MagicMock()
        mock_block = MagicMock()
        mock_block.type = "tool_use"
        mock_block.input = marks_output_neutre.model_dump(exclude={"citations", "cost_usd"})
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

        skill = MarksCyclesSkill(client=mock_client, model="claude-sonnet-4-6")
        inp = MarksInput(
            market_context="Contexte macro Q1 2026 — inflation maîtrisée, Fed en pause.",
            marks_ratios=ratios_neutre,
        )
        output, usage = await skill.execute(inp)

        assert isinstance(output, MarksOutput)
        assert isinstance(usage, UsageDetail)
        assert usage.cost_usd > 0
        assert output.cost_usd == usage.cost_usd


# ---------------------------------------------------------------------------
# Tests intégration orchestrateur
# ---------------------------------------------------------------------------


class TestOrchestratorMarks:
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
    def mock_marks_skill(self, marks_output_neutre: MarksOutput):
        skill = AsyncMock(spec=MarksCyclesSkill)
        skill.execute.return_value = (marks_output_neutre, _make_usage())
        return skill

    @pytest.mark.asyncio
    async def test_orchestrator_avec_marks(
        self,
        mock_db_pool,
        mock_graham_skill,
        mock_earnings_skill,
        mock_marks_skill,
        ratios_msft,
        ratios_neutre,
    ):
        """marks_input fourni → marks présent dans response."""
        orchestrator = Orchestrator(
            db_pool=mock_db_pool,
            graham_skill=mock_graham_skill,
            earnings_skill=mock_earnings_skill,
            marks_skill=mock_marks_skill,
        )
        req = AnalyzeRequest(
            ticker="BNS",
            ratios=ratios_msft,
            workflow="compounder_buffett",
            marks_input=MarksInput(
                market_context="Contexte macro Q1 2026",
                marks_ratios=ratios_neutre,
            ),
        )
        response = await orchestrator.run_company_analysis(req)

        assert response.marks is not None
        assert "marks_cycles_risk" in response.skills_applied
        mock_marks_skill.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_orchestrator_sans_marks(
        self,
        mock_db_pool,
        mock_graham_skill,
        mock_earnings_skill,
        mock_marks_skill,
        ratios_msft,
    ):
        """Sans marks_input → marks = None."""
        orchestrator = Orchestrator(
            db_pool=mock_db_pool,
            graham_skill=mock_graham_skill,
            earnings_skill=mock_earnings_skill,
            marks_skill=mock_marks_skill,
        )
        req = AnalyzeRequest(ticker="BNS", ratios=ratios_msft, workflow="compounder_buffett")
        response = await orchestrator.run_company_analysis(req)

        assert response.marks is None
        assert "marks_cycles_risk" not in response.skills_applied
        mock_marks_skill.execute.assert_not_called()
