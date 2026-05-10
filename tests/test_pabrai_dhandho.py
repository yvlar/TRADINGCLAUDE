"""Tests du skill pabrai_dhandho — schemas, skill, orchestrateur."""
from __future__ import annotations

import uuid
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest
from pydantic import ValidationError

from app.orchestrator.core import AnalyzeRequest, AnalyzeResponse, Orchestrator
from app.skills.base import UsageDetail
from app.skills.tier2.pabrai_dhandho.schemas import (
    DhandhoPrincipe,
    PabraiInput,
    PabraiOutput,
    PabraiRatios,
)
from app.skills.tier2.pabrai_dhandho.skill import PabraiDhandhoSkill


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_9_principes(satisfaits: int = 7) -> list[dict]:
    """Génère exactement 9 DhandhoPrincipe, les `satisfaits` premiers sont True."""
    noms = [
        "Business existant",
        "Business simple et prévisible",
        "Détresse business, industrie saine",
        "Fossé concurrentiel durable",
        "Pari concentré justifié",
        "Faible risque, haute incertitude",
        "Arbitrage valeur/prix",
        "Management aligné",
        "Cloning ou documentation solide",
    ]
    return [
        {
            "nom": noms[i],
            "satisfait": i < satisfaits,
            "commentaire": f"Commentaire pour le principe {i + 1}.",
        }
        for i in range(9)
    ]


def _make_ratios(
    price: float = 80.0,
    intrinsic_value_low: float = 92.0,
    intrinsic_value_high: float = 110.0,
    downside_pct: float = -0.30,
    upside_pct: float = 1.0,
    debt_equity: float = 0.45,
    fcf_yield: float = 0.08,
    business_quality_score: int = 7,
) -> PabraiRatios:
    return PabraiRatios(
        price=price,
        intrinsic_value_low=intrinsic_value_low,
        intrinsic_value_high=intrinsic_value_high,
        downside_pct=downside_pct,
        upside_pct=upside_pct,
        debt_equity=debt_equity,
        fcf_yield=fcf_yield,
        business_quality_score=business_quality_score,
    )


def _make_output_dict(
    ticker: str = "BNS",
    heads_i_win_score: int = 7,
    asymetrie: float = 3.33,
    kelly_fractionnel: float | None = 0.14,
    verdict: str = "DHANDHO_FORT",
    satisfaits: int = 7,
) -> dict:
    return {
        "ticker": ticker,
        "principes_dhandho": _make_9_principes(satisfaits),
        "heads_i_win_score": heads_i_win_score,
        "asymetrie": asymetrie,
        "kelly_fractionnel": kelly_fractionnel,
        "verdict": verdict,
        "verdict_detail": "BNS satisfait 7/9 principes Dhandho avec asymétrie 3.33×.",
        "recommandation_prochaine_etape": ["investment_thesis_builder", "canadian_tax_considerations"],
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
def ratios_bns_pabrai() -> PabraiRatios:
    return _make_ratios()


@pytest.fixture
def pabrai_output_fort() -> PabraiOutput:
    return PabraiOutput.model_validate(_make_output_dict())


# ---------------------------------------------------------------------------
# Tests schémas PabraiRatios
# ---------------------------------------------------------------------------


class TestPabraiRatiosSchema:
    def test_pabrai_ratios_validation_ok(self, ratios_bns_pabrai: PabraiRatios):
        """PabraiRatios valide — pas d'erreur."""
        assert ratios_bns_pabrai.price == 80.0
        assert ratios_bns_pabrai.business_quality_score == 7

    def test_pabrai_ratios_business_quality_hors_plage_erreur(self):
        """business_quality_score = 11 → ValidationError (ge=0, le=10)."""
        with pytest.raises(ValidationError):
            PabraiRatios(
                price=80.0,
                intrinsic_value_low=92.0,
                intrinsic_value_high=110.0,
                downside_pct=-0.30,
                upside_pct=1.0,
                debt_equity=0.45,
                fcf_yield=0.08,
                business_quality_score=11,
            )

    def test_pabrai_ratios_cloning_source_optionnel(self):
        """cloning_source est optionnel dans PabraiInput."""
        inp = PabraiInput(ticker="BNS", pabrai_ratios=_make_ratios())
        assert inp.cloning_source is None


# ---------------------------------------------------------------------------
# Tests schémas PabraiOutput
# ---------------------------------------------------------------------------


class TestPabraiOutputSchema:
    def test_pabrai_output_principes_9_elements(self, pabrai_output_fort: PabraiOutput):
        """principes_dhandho contient exactement 9 éléments."""
        assert len(pabrai_output_fort.principes_dhandho) == 9

    def test_pabrai_output_principes_8_elements_erreur(self):
        """8 principes → ValidationError."""
        data = _make_output_dict()
        data["principes_dhandho"] = _make_9_principes()[:8]
        with pytest.raises(ValidationError, match="exactement 9"):
            PabraiOutput.model_validate(data)

    def test_pabrai_output_principes_10_elements_erreur(self):
        """10 principes → ValidationError."""
        data = _make_output_dict()
        data["principes_dhandho"] = _make_9_principes() + [
            {"nom": "Dixième", "satisfait": True, "commentaire": "Extra"}
        ]
        with pytest.raises(ValidationError, match="exactement 9"):
            PabraiOutput.model_validate(data)

    def test_pabrai_output_heads_i_win_score_plage(self, pabrai_output_fort: PabraiOutput):
        """0 <= heads_i_win_score <= 9."""
        assert 0 <= pabrai_output_fort.heads_i_win_score <= 9

    def test_pabrai_output_heads_i_win_score_zero_ok(self):
        """heads_i_win_score = 0 → valide."""
        data = _make_output_dict(heads_i_win_score=0, verdict="PAS_DHANDHO", satisfaits=0)
        out = PabraiOutput.model_validate(data)
        assert out.heads_i_win_score == 0

    def test_pabrai_output_heads_i_win_score_hors_plage_erreur(self):
        """heads_i_win_score = 10 → ValidationError."""
        data = _make_output_dict(heads_i_win_score=10)
        with pytest.raises(ValidationError, match="heads_i_win_score hors plage"):
            PabraiOutput.model_validate(data)

    def test_pabrai_output_asymetrie_non_negatif(self, pabrai_output_fort: PabraiOutput):
        """asymetrie >= 0."""
        assert pabrai_output_fort.asymetrie >= 0

    def test_pabrai_output_asymetrie_zero_ok(self):
        """asymetrie = 0 → valide."""
        data = _make_output_dict(asymetrie=0.0, verdict="PAS_DHANDHO")
        out = PabraiOutput.model_validate(data)
        assert out.asymetrie == 0.0

    def test_pabrai_output_asymetrie_negative_erreur(self):
        """asymetrie = -1 → ValidationError."""
        data = _make_output_dict(asymetrie=-1.0)
        with pytest.raises(ValidationError, match="asymetrie doit être >= 0"):
            PabraiOutput.model_validate(data)

    def test_pabrai_output_verdict_valide(self, pabrai_output_fort: PabraiOutput):
        """verdict = DHANDHO_FORT → valide."""
        assert pabrai_output_fort.verdict == "DHANDHO_FORT"

    def test_pabrai_output_all_verdicts_valides(self):
        """Les 3 verdicts Pabrai sont acceptés."""
        for v in ("DHANDHO_FORT", "DHANDHO_MOYEN", "PAS_DHANDHO"):
            data = _make_output_dict(verdict=v)
            out = PabraiOutput.model_validate(data)
            assert out.verdict == v

    def test_pabrai_output_verdict_invalide_erreur(self):
        """verdict = 'BON' → ValidationError."""
        data = _make_output_dict(verdict="BON")
        with pytest.raises(ValidationError, match="verdict invalide"):
            PabraiOutput.model_validate(data)

    def test_pabrai_output_kelly_fractionnel_none_ok(self):
        """kelly_fractionnel = None → valide."""
        data = _make_output_dict(kelly_fractionnel=None)
        out = PabraiOutput.model_validate(data)
        assert out.kelly_fractionnel is None

    def test_pabrai_output_citations_defaut_vide(self, pabrai_output_fort: PabraiOutput):
        assert pabrai_output_fort.citations == []


# ---------------------------------------------------------------------------
# Tests skill
# ---------------------------------------------------------------------------


class TestPabraiDhandhoSkill:
    @pytest.fixture
    def skill(self) -> PabraiDhandhoSkill:
        return PabraiDhandhoSkill(client=MagicMock(), model="claude-sonnet-4-6")

    def test_skill_id(self, skill: PabraiDhandhoSkill):
        assert skill.skill_id == "pabrai_dhandho"

    def test_tier(self, skill: PabraiDhandhoSkill):
        assert skill.tier == 2

    def test_system_prompt_charge_et_cache(self, skill: PabraiDhandhoSkill):
        blocks = skill.get_system_prompt()
        assert blocks[0]["cache_control"]["type"] == "ephemeral"
        assert len(blocks[0]["text"]) > 1024

    def test_system_prompt_contient_9_principes(self, skill: PabraiDhandhoSkill):
        text = skill.get_system_prompt()[0]["text"]
        assert "9" in text and "principes" in text.lower()

    def test_system_prompt_contient_verdicts(self, skill: PabraiDhandhoSkill):
        text = skill.get_system_prompt()[0]["text"]
        for v in ("DHANDHO_FORT", "DHANDHO_MOYEN", "PAS_DHANDHO"):
            assert v in text

    def test_build_user_message_contient_ticker(
        self, skill: PabraiDhandhoSkill, ratios_bns_pabrai: PabraiRatios
    ):
        inp = PabraiInput(ticker="BNS", pabrai_ratios=ratios_bns_pabrai)
        msg = skill._build_user_message(inp, citations=[])
        assert "BNS" in msg

    def test_build_user_message_contient_asymetrie(
        self, skill: PabraiDhandhoSkill, ratios_bns_pabrai: PabraiRatios
    ):
        inp = PabraiInput(ticker="BNS", pabrai_ratios=ratios_bns_pabrai)
        msg = skill._build_user_message(inp, citations=[])
        assert "symétrie" in msg.lower() or "Asymétrie" in msg

    @pytest.mark.asyncio
    async def test_get_citations_rag_absent(self):
        skill = PabraiDhandhoSkill(
            client=MagicMock(), model="claude-sonnet-4-6", rag_service=None
        )
        citations = await skill.get_citations("test query")
        assert citations == []

    @pytest.mark.asyncio
    async def test_execute_mock_claude(
        self,
        pabrai_output_fort: PabraiOutput,
        ratios_bns_pabrai: PabraiRatios,
    ):
        """execute() retourne (PabraiOutput, UsageDetail) avec cost_usd > 0."""
        mock_response = MagicMock()
        mock_response.content = [MagicMock(text=pabrai_output_fort.model_dump_json())]
        mock_response.usage = SimpleNamespace(
            input_tokens=600,
            output_tokens=300,
            cache_read_input_tokens=1200,
            cache_creation_input_tokens=0,
        )
        mock_client = MagicMock()
        mock_client.messages = AsyncMock()
        mock_client.messages.create.return_value = mock_response

        skill = PabraiDhandhoSkill(client=mock_client, model="claude-sonnet-4-6")
        inp = PabraiInput(ticker="BNS", pabrai_ratios=ratios_bns_pabrai)
        output, usage = await skill.execute(inp)

        assert isinstance(output, PabraiOutput)
        assert isinstance(usage, UsageDetail)
        assert usage.cost_usd > 0
        assert output.cost_usd == usage.cost_usd


# ---------------------------------------------------------------------------
# Tests intégration orchestrateur
# ---------------------------------------------------------------------------


class TestOrchestratorPabrai:
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
    def mock_pabrai_skill(self, pabrai_output_fort: PabraiOutput):
        skill = AsyncMock(spec=PabraiDhandhoSkill)
        skill.execute.return_value = (pabrai_output_fort, _make_usage())
        return skill

    @pytest.mark.asyncio
    async def test_orchestrator_avec_pabrai(
        self,
        mock_db_pool,
        mock_graham_skill,
        mock_earnings_skill,
        mock_pabrai_skill,
        ratios_msft,
        ratios_bns_pabrai,
    ):
        """pabrai_input fourni → pabrai présent dans response."""
        orchestrator = Orchestrator(
            db_pool=mock_db_pool,
            graham_skill=mock_graham_skill,
            earnings_skill=mock_earnings_skill,
            pabrai_skill=mock_pabrai_skill,
        )
        req = AnalyzeRequest(
            ticker="BNS",
            ratios=ratios_msft,
            pabrai_input=PabraiInput(ticker="BNS", pabrai_ratios=ratios_bns_pabrai),
        )
        response = await orchestrator.run_company_analysis(req)

        assert response.pabrai is not None
        assert "pabrai_dhandho" in response.skills_applied
        mock_pabrai_skill.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_orchestrator_sans_pabrai(
        self,
        mock_db_pool,
        mock_graham_skill,
        mock_earnings_skill,
        mock_pabrai_skill,
        ratios_msft,
    ):
        """Sans pabrai_input → pabrai = None."""
        orchestrator = Orchestrator(
            db_pool=mock_db_pool,
            graham_skill=mock_graham_skill,
            earnings_skill=mock_earnings_skill,
            pabrai_skill=mock_pabrai_skill,
        )
        req = AnalyzeRequest(ticker="BNS", ratios=ratios_msft)
        response = await orchestrator.run_company_analysis(req)

        assert response.pabrai is None
        assert "pabrai_dhandho" not in response.skills_applied
        mock_pabrai_skill.execute.assert_not_called()
