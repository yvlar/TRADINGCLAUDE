"""Tests du skill fisher_scuttlebutt — schemas, skill, orchestrateur."""
from __future__ import annotations

import uuid
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest
from pydantic import ValidationError

from app.orchestrator.core import AnalyzeRequest, AnalyzeResponse, Orchestrator
from app.skills.base import UsageDetail
from app.skills.tier2.fisher_scuttlebutt.schemas import (
    FisherAnswer,
    FisherInput,
    FisherOutput,
)
from app.skills.tier2.fisher_scuttlebutt.skill import FisherScuttlebuttSkill

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_TITRES_FISHER = [
    "Potentiel de croissance du marché",
    "Détermination direction pour croissance",
    "Efficacité de la R&D",
    "Organisation commerciale",
    "Marges bénéficiaires",
    "Actions pour améliorer les marges",
    "Relations employés-direction",
    "Relations direction-cadres",
    "Profondeur managériale",
    "Contrôle des coûts et comptabilité",
    "Aspects sectoriels distinctifs",
    "Perspective long terme bénéfices",
    "Financement de la croissance",
    "Transparence direction — problèmes (ÉLIMINATOIRE)",
    "Intégrité de la direction (ÉLIMINATOIRE)",
]


def _make_fisher_answers(scores: list[int] | None = None) -> list[dict]:
    """Génère exactement 15 FisherAnswer dicts."""
    if scores is None:
        scores = [2] * 13 + [2, 2]  # intégrité OK par défaut
    return [
        {"point": i + 1, "score": scores[i], "commentaire": f"Commentaire point {i + 1}"}
        for i in range(15)
    ]


def _make_fisher_points_evalues(scores: list[int] | None = None) -> list[dict]:
    """Génère exactement 15 FisherPoint dicts."""
    if scores is None:
        scores = [2] * 15
    return [
        {
            "point": i + 1,
            "titre": _TITRES_FISHER[i],
            "score": scores[i],
            "commentaire": f"Évaluation point {i + 1}",
        }
        for i in range(15)
    ]


def _make_fisher_output_dict(
    ticker: str = "BNS",
    fisher_score: int = 22,
    management_quality: str = "BON",
    verdict: str = "ACHAT",
    scores: list[int] | None = None,
) -> dict:
    return {
        "ticker": ticker,
        "fisher_score": fisher_score,
        "points_evalues": _make_fisher_points_evalues(scores),
        "management_quality": management_quality,
        "verdict": verdict,
        "verdict_detail": f"Score Fisher de {fisher_score}/30 — direction de qualité {management_quality}.",
        "recommandation_prochaine_etape": ["klarman_margin", "stock_valuation_triangulation"],
    }


def _make_usage() -> UsageDetail:
    return UsageDetail(
        tokens_input=800,
        tokens_output=600,
        tokens_cache_read=1500,
        tokens_cache_creation=0,
        cost_usd=0.007,
        model="claude-sonnet-4-6",
    )


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def fisher_answers_bns() -> list[FisherAnswer]:
    """15 FisherAnswers valides pour BNS."""
    return [FisherAnswer(**a) for a in _make_fisher_answers()]


@pytest.fixture
def fisher_input_bns(fisher_answers_bns: list[FisherAnswer]) -> FisherInput:
    return FisherInput(ticker="BNS", fisher_answers=fisher_answers_bns)


@pytest.fixture
def fisher_output_bns() -> FisherOutput:
    return FisherOutput.model_validate(_make_fisher_output_dict())


# ---------------------------------------------------------------------------
# Tests schémas FisherAnswer
# ---------------------------------------------------------------------------


class TestFisherAnswerSchema:
    def test_fisher_answer_valide(self):
        a = FisherAnswer(point=1, score=2, commentaire="Excellent")
        assert a.point == 1
        assert a.score == 2

    def test_fisher_answer_score_zero(self):
        a = FisherAnswer(point=14, score=0, commentaire="Manque de transparence")
        assert a.score == 0

    def test_fisher_answer_score_hors_plage_erreur(self):
        with pytest.raises(ValidationError):
            FisherAnswer(point=1, score=3, commentaire="invalide")

    def test_fisher_answer_score_negatif_erreur(self):
        with pytest.raises(ValidationError):
            FisherAnswer(point=1, score=-1, commentaire="invalide")

    def test_fisher_answer_point_hors_plage_erreur(self):
        with pytest.raises(ValidationError):
            FisherAnswer(point=16, score=1, commentaire="invalide")

    def test_fisher_answer_point_zero_erreur(self):
        with pytest.raises(ValidationError):
            FisherAnswer(point=0, score=1, commentaire="invalide")


# ---------------------------------------------------------------------------
# Tests schémas FisherInput
# ---------------------------------------------------------------------------


class TestFisherInputSchema:
    def test_fisher_answers_validation_15_points(self, fisher_input_bns: FisherInput):
        """fisher_answers doit contenir exactement 15 éléments."""
        assert len(fisher_input_bns.fisher_answers) == 15

    def test_fisher_input_14_answers_erreur(self):
        """Moins de 15 réponses → ValidationError."""
        answers = [FisherAnswer(**a) for a in _make_fisher_answers()[:14]]
        with pytest.raises(ValidationError):
            FisherInput(ticker="TST", fisher_answers=answers)

    def test_fisher_input_16_answers_erreur(self):
        """Plus de 15 réponses → ValidationError."""
        answers = [FisherAnswer(**a) for a in _make_fisher_answers()] + [
            FisherAnswer(point=1, score=1, commentaire="extra")
        ]
        with pytest.raises(ValidationError):
            FisherInput(ticker="TST", fisher_answers=answers)

    def test_fisher_input_contexte_optionnel(self, fisher_answers_bns: list[FisherAnswer]):
        inp = FisherInput(ticker="BNS", fisher_answers=fisher_answers_bns)
        assert inp.contexte_qualitatif is None

    def test_fisher_input_avec_contexte(self, fisher_answers_bns: list[FisherAnswer]):
        ctx = "Glassdoor 4.2, ex-employés positifs sur la culture."
        inp = FisherInput(ticker="BNS", fisher_answers=fisher_answers_bns, contexte_qualitatif=ctx)
        assert inp.contexte_qualitatif == ctx


# ---------------------------------------------------------------------------
# Tests schémas FisherOutput
# ---------------------------------------------------------------------------


class TestFisherOutputSchema:
    def test_fisher_output_valide(self, fisher_output_bns: FisherOutput):
        assert fisher_output_bns.ticker == "BNS"
        assert fisher_output_bns.fisher_score == 22

    def test_fisher_output_points_evalues_15(self, fisher_output_bns: FisherOutput):
        """points_evalues doit contenir exactement 15 éléments."""
        assert len(fisher_output_bns.points_evalues) == 15

    def test_fisher_output_14_points_erreur(self):
        """Moins de 15 points → ValidationError."""
        data = _make_fisher_output_dict()
        data["points_evalues"] = data["points_evalues"][:14]
        with pytest.raises(ValidationError, match="exactement 15"):
            FisherOutput.model_validate(data)

    def test_fisher_output_score_plage_0_30(self, fisher_output_bns: FisherOutput):
        """0 <= fisher_score <= 30."""
        assert 0 <= fisher_output_bns.fisher_score <= 30

    def test_fisher_output_score_max_30_ok(self):
        data = _make_fisher_output_dict(fisher_score=30)
        out = FisherOutput.model_validate(data)
        assert out.fisher_score == 30

    def test_fisher_output_score_zero_ok(self):
        data = _make_fisher_output_dict(
            fisher_score=0,
            management_quality="MEDIOCRE",
            verdict="EVITER",
        )
        out = FisherOutput.model_validate(data)
        assert out.fisher_score == 0

    def test_fisher_output_management_quality_valide(self, fisher_output_bns: FisherOutput):
        assert fisher_output_bns.management_quality == "BON"

    def test_fisher_output_all_management_qualities(self):
        for mq, score, verdict in [
            ("EXCEPTIONNEL", 28, "ACHAT_FORT"),
            ("BON", 22, "ACHAT"),
            ("ADEQUAT", 15, "CONSERVER"),
            ("MEDIOCRE", 8, "EVITER"),
        ]:
            data = _make_fisher_output_dict(
                fisher_score=score,
                management_quality=mq,
                verdict=verdict,
            )
            out = FisherOutput.model_validate(data)
            assert out.management_quality == mq

    def test_fisher_output_management_quality_invalide_erreur(self):
        data = _make_fisher_output_dict(management_quality="EXCELLENT")
        with pytest.raises(ValidationError, match="management_quality invalide"):
            FisherOutput.model_validate(data)

    def test_fisher_output_verdict_valide(self, fisher_output_bns: FisherOutput):
        assert fisher_output_bns.verdict == "ACHAT"

    def test_fisher_output_all_verdicts(self):
        for v, score, mq in [
            ("ACHAT_FORT", 28, "EXCEPTIONNEL"),
            ("ACHAT", 22, "BON"),
            ("CONSERVER", 15, "ADEQUAT"),
            ("EVITER", 8, "MEDIOCRE"),
        ]:
            data = _make_fisher_output_dict(
                fisher_score=score,
                management_quality=mq,
                verdict=v,
            )
            out = FisherOutput.model_validate(data)
            assert out.verdict == v

    def test_fisher_output_verdict_invalide_erreur(self):
        data = _make_fisher_output_dict(verdict="BON")
        with pytest.raises(ValidationError, match="verdict invalide"):
            FisherOutput.model_validate(data)

    def test_fisher_output_citations_defaut_vide(self, fisher_output_bns: FisherOutput):
        assert fisher_output_bns.citations == []

    def test_fisher_output_cost_usd_defaut_zero(self, fisher_output_bns: FisherOutput):
        assert fisher_output_bns.cost_usd == pytest.approx(0.0)


# ---------------------------------------------------------------------------
# Tests skill
# ---------------------------------------------------------------------------


class TestFisherScuttlebuttSkill:
    @pytest.fixture
    def skill(self) -> FisherScuttlebuttSkill:
        return FisherScuttlebuttSkill(client=MagicMock(), model="claude-sonnet-4-6")

    def test_skill_id(self, skill: FisherScuttlebuttSkill):
        assert skill.skill_id == "fisher_scuttlebutt"

    def test_tier(self, skill: FisherScuttlebuttSkill):
        assert skill.tier == 2

    def test_system_prompt_charge_et_cache(self, skill: FisherScuttlebuttSkill):
        blocks = skill.get_system_prompt()
        assert blocks[0]["cache_control"]["type"] == "ephemeral"
        assert len(blocks[0]["text"]) > 1024

    def test_system_prompt_contient_15_points(self, skill: FisherScuttlebuttSkill):
        text = skill.get_system_prompt()[0]["text"]
        assert "Point 15" in text or "point 15" in text.lower()

    def test_system_prompt_contient_verdicts(self, skill: FisherScuttlebuttSkill):
        text = skill.get_system_prompt()[0]["text"]
        for v in ("ACHAT_FORT", "ACHAT", "CONSERVER", "EVITER"):
            assert v in text

    def test_system_prompt_contient_eliminatoires(self, skill: FisherScuttlebuttSkill):
        text = skill.get_system_prompt()[0]["text"]
        assert "ÉLIMINATOIRE" in text or "éliminatoire" in text.lower()

    def test_build_user_message_contient_ticker(
        self, skill: FisherScuttlebuttSkill, fisher_input_bns: FisherInput
    ):
        msg = skill._build_user_message(fisher_input_bns, citations=[])
        assert "BNS" in msg

    def test_build_user_message_contient_15_points(
        self, skill: FisherScuttlebuttSkill, fisher_input_bns: FisherInput
    ):
        msg = skill._build_user_message(fisher_input_bns, citations=[])
        assert "Point 15" in msg or "point 15" in msg.lower()

    @pytest.mark.asyncio
    async def test_get_citations_rag_absent(self):
        """FisherScuttlebuttSkill avec rag_service=None → get_citations() retourne []."""
        skill = FisherScuttlebuttSkill(
            client=MagicMock(), model="claude-sonnet-4-6", rag_service=None
        )
        citations = await skill.get_citations("test query")
        assert citations == []

    @pytest.mark.asyncio
    async def test_execute_mock_claude(
        self,
        fisher_output_bns: FisherOutput,
        fisher_input_bns: FisherInput,
    ):
        """execute() retourne (FisherOutput, UsageDetail) avec cost_usd > 0."""
        mock_response = MagicMock()
        mock_block = MagicMock()
        mock_block.type = "tool_use"
        mock_block.input = fisher_output_bns.model_dump(exclude={"citations", "cost_usd"})
        mock_response.content = [mock_block]
        mock_response.stop_reason = "tool_use"
        mock_response.usage = SimpleNamespace(
            input_tokens=800,
            output_tokens=600,
            cache_read_input_tokens=1500,
            cache_creation_input_tokens=0,
        )
        mock_client = MagicMock()
        mock_client.messages = AsyncMock()
        mock_client.messages.create.return_value = mock_response

        skill = FisherScuttlebuttSkill(client=mock_client, model="claude-sonnet-4-6")
        output, usage = await skill.execute(fisher_input_bns)

        assert isinstance(output, FisherOutput)
        assert isinstance(usage, UsageDetail)
        assert usage.cost_usd > 0
        assert output.cost_usd == usage.cost_usd


# ---------------------------------------------------------------------------
# Tests intégration orchestrateur
# ---------------------------------------------------------------------------


class TestOrchestratorFisher:
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
    def mock_fisher_skill(self, fisher_output_bns: FisherOutput):
        skill = AsyncMock(spec=FisherScuttlebuttSkill)
        skill.execute.return_value = (fisher_output_bns, _make_usage())
        return skill

    @pytest.mark.asyncio
    async def test_orchestrator_avec_fisher(
        self,
        mock_db_pool,
        mock_graham_skill,
        mock_earnings_skill,
        mock_fisher_skill,
        fisher_input_bns: FisherInput,
        ratios_msft,
    ):
        """fisher_input fourni → fisher présent dans response."""
        orchestrator = Orchestrator(
            db_pool=mock_db_pool,
            graham_skill=mock_graham_skill,
            earnings_skill=mock_earnings_skill,
            fisher_skill=mock_fisher_skill,
        )
        req = AnalyzeRequest(
            ticker="BNS",
            ratios=ratios_msft,
            workflow="compounder_buffett",
            fisher_input=fisher_input_bns,
        )
        response = await orchestrator.run_company_analysis(req)

        assert response.fisher is not None
        assert "fisher_scuttlebutt" in response.skills_applied
        mock_fisher_skill.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_orchestrator_sans_fisher(
        self,
        mock_db_pool,
        mock_graham_skill,
        mock_earnings_skill,
        mock_fisher_skill,
        ratios_msft,
    ):
        """Sans fisher_input → fisher = None."""
        orchestrator = Orchestrator(
            db_pool=mock_db_pool,
            graham_skill=mock_graham_skill,
            earnings_skill=mock_earnings_skill,
            fisher_skill=mock_fisher_skill,
        )
        req = AnalyzeRequest(ticker="BNS", ratios=ratios_msft, workflow="compounder_buffett")
        response = await orchestrator.run_company_analysis(req)

        assert response.fisher is None
        assert "fisher_scuttlebutt" not in response.skills_applied
        mock_fisher_skill.execute.assert_not_called()

    @pytest.mark.asyncio
    async def test_fisher_input_defaut_none(self, ratios_msft):
        req = AnalyzeRequest(ticker="BNS", ratios=ratios_msft, workflow="compounder_buffett")
        assert req.fisher_input is None

    @pytest.mark.asyncio
    async def test_fisher_response_defaut_none(self, graham_output_msft):
        resp = AnalyzeResponse(
            analysis_id="123",
            ticker="BNS",
            workflow="company_analysis",
            skills_applied=["graham_analysis"],
            graham=graham_output_msft,
            cost_usd=0.003,
            created_at="2026-05-08T10:00:00+00:00",
        )
        assert resp.fisher is None
