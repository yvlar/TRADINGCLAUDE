"""
Tests Tool Use — migration Sprint 43 : 13 skills migrés.

Pour chaque skill :
  1. Le schema Tool Use exclut bien citations et cost_usd
  2. execute() lève ValueError quand aucun bloc tool_use n'est présent
"""
from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.skills.tier2.buffett_quality.schemas import BuffettQualityInput, BuffettRatios
from app.skills.tier2.buffett_quality.skill import (
    _BUFFETT_TOOL_SCHEMA,
    BuffettQualitySkill,
)
from app.skills.tier2.canadian_tax.schemas import CanadianTaxInput
from app.skills.tier2.canadian_tax.skill import (
    _CANADIAN_TAX_TOOL_SCHEMA,
    CanadianTaxSkill,
)
from app.skills.tier2.damodaran_narrative.schemas import DamodararInput, DamodararRatios
from app.skills.tier2.damodaran_narrative.skill import (
    _DAMODARAN_TOOL_SCHEMA,
    DamodararNarrativeSkill,
)
from app.skills.tier2.dorsey_moat.schemas import DorseyMoatInput, DorseyRatios
from app.skills.tier2.dorsey_moat.skill import _DORSEY_TOOL_SCHEMA, DorseyMoatSkill
from app.skills.tier2.fisher_scuttlebutt.schemas import FisherAnswer, FisherInput
from app.skills.tier2.fisher_scuttlebutt.skill import (
    _FISHER_TOOL_SCHEMA,
    FisherScuttlebuttSkill,
)
from app.skills.tier2.greenblatt.schemas import GreenblattInput, GreenblattRatios
from app.skills.tier2.greenblatt.skill import _GREENBLATT_TOOL_SCHEMA, GreenblattSkill
from app.skills.tier2.klarman_margin.schemas import KlarmanInput, KlarmanRatios
from app.skills.tier2.klarman_margin.skill import (
    _KLARMAN_TOOL_SCHEMA,
    KlarmanMarginSkill,
)
from app.skills.tier2.lynch_categories.schemas import LynchInput, LynchRatios
from app.skills.tier2.lynch_categories.skill import (
    _LYNCH_TOOL_SCHEMA,
    LynchCategoriesSkill,
)
from app.skills.tier2.marks_cycles.schemas import MarksInput, MarksRatios
from app.skills.tier2.marks_cycles.skill import _MARKS_TOOL_SCHEMA, MarksCyclesSkill
from app.skills.tier2.munger_mental.schemas import MungerInput, ThesisContext
from app.skills.tier2.munger_mental.skill import _MUNGER_TOOL_SCHEMA, MungerMentalSkill
from app.skills.tier2.pabrai_dhandho.schemas import PabraiInput, PabraiRatios
from app.skills.tier2.pabrai_dhandho.skill import (
    _PABRAI_TOOL_SCHEMA,
    PabraiDhandhoSkill,
)
from app.skills.tier2.stock_valuation.schemas import StockValuationInput, ValuationRatios
from app.skills.tier2.stock_valuation.skill import (
    _VALUATION_TOOL_SCHEMA,
    StockValuationSkill,
)
from app.skills.tier2.thesis_builder.schemas import AllSkillContexts, ThesisBuilderInput
from app.skills.tier2.thesis_builder.skill import (
    _THESIS_TOOL_SCHEMA,
    ThesisBuilderSkill,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _text_only_response() -> MagicMock:
    """Réponse Anthropic sans aucun bloc tool_use — simule un échec Tool Use."""
    mock_block = MagicMock()
    mock_block.type = "text"
    mock_block.text = '{"ticker": "TST"}'
    resp = MagicMock()
    resp.content = [mock_block]
    resp.stop_reason = "end_turn"
    resp.usage = SimpleNamespace(
        input_tokens=100,
        output_tokens=50,
        cache_read_input_tokens=0,
        cache_creation_input_tokens=0,
    )
    return resp


def _make_skill(cls, class_path: str):
    """Instancie un skill en patchant _load_system_prompt pour éviter la lecture disque."""
    with patch(f"{class_path}._load_system_prompt", return_value="prompt-test"):
        return cls(client=MagicMock(), model="claude-sonnet-4-6")


def _thesis_context() -> ThesisContext:
    return ThesisContext(
        ticker="TST",
        verdict_final="ACHETER",
        position_size_pct=3.0,
        scenario_bull_probabilite=0.35,
        scenario_base_probabilite=0.50,
        scenario_bear_probabilite=0.15,
        synthese_narrative="Narrative de test.",
        kill_criteria=["Perte de parts de marché"],
        devils_advocate="Le management pourrait décevoir.",
    )


def _fisher_answers() -> list[FisherAnswer]:
    return [FisherAnswer(point=i, score=1, commentaire="ok") for i in range(1, 16)]


# ---------------------------------------------------------------------------
# 1. Schémas — citations et cost_usd exclus
# ---------------------------------------------------------------------------


def test_dorsey_schema_exclut_champs_post_assignes():
    props = _DORSEY_TOOL_SCHEMA.get("properties", {})
    assert "citations" not in props
    assert "cost_usd" not in props
    assert "confidence_score" not in props
    assert "moat_type" in props


def test_buffett_schema_exclut_champs_post_assignes():
    props = _BUFFETT_TOOL_SCHEMA.get("properties", {})
    assert "citations" not in props
    assert "cost_usd" not in props
    assert "confidence_score" not in props
    assert "filtres" in props


def test_valuation_schema_exclut_champs_post_assignes():
    props = _VALUATION_TOOL_SCHEMA.get("properties", {})
    assert "citations" not in props
    assert "cost_usd" not in props
    assert "fourchette_centrale" in props


def test_thesis_schema_exclut_champs_post_assignes():
    props = _THESIS_TOOL_SCHEMA.get("properties", {})
    assert "citations" not in props
    assert "cost_usd" not in props
    assert "verdict_final" in props


def test_munger_schema_exclut_champs_post_assignes():
    props = _MUNGER_TOOL_SCHEMA.get("properties", {})
    assert "citations" not in props
    assert "cost_usd" not in props
    assert "biais_detectes" in props


def test_canadian_tax_schema_exclut_champs_post_assignes():
    props = _CANADIAN_TAX_TOOL_SCHEMA.get("properties", {})
    assert "citations" not in props
    assert "cost_usd" not in props
    assert "compte_recommande" in props


def test_lynch_schema_exclut_champs_post_assignes():
    props = _LYNCH_TOOL_SCHEMA.get("properties", {})
    assert "citations" not in props
    assert "cost_usd" not in props
    assert "categorie" in props


def test_fisher_schema_exclut_champs_post_assignes():
    props = _FISHER_TOOL_SCHEMA.get("properties", {})
    assert "citations" not in props
    assert "cost_usd" not in props
    assert "fisher_score" in props


def test_klarman_schema_exclut_champs_post_assignes():
    props = _KLARMAN_TOOL_SCHEMA.get("properties", {})
    assert "citations" not in props
    assert "cost_usd" not in props
    assert "marge_securite_score" in props


def test_greenblatt_schema_exclut_champs_post_assignes():
    props = _GREENBLATT_TOOL_SCHEMA.get("properties", {})
    assert "citations" not in props
    assert "cost_usd" not in props
    assert "roc" in props


def test_damodaran_schema_exclut_champs_post_assignes():
    props = _DAMODARAN_TOOL_SCHEMA.get("properties", {})
    assert "citations" not in props
    assert "cost_usd" not in props
    assert "test_coherence" in props


def test_marks_schema_exclut_champs_post_assignes():
    props = _MARKS_TOOL_SCHEMA.get("properties", {})
    assert "citations" not in props
    assert "cost_usd" not in props
    assert "position_cycle" in props


def test_pabrai_schema_exclut_champs_post_assignes():
    props = _PABRAI_TOOL_SCHEMA.get("properties", {})
    assert "citations" not in props
    assert "cost_usd" not in props
    assert "heads_i_win_score" in props


# ---------------------------------------------------------------------------
# 2. execute() — ValueError quand aucun bloc tool_use
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_dorsey_execute_leve_value_error_sans_tool_use():
    skill = _make_skill(
        DorseyMoatSkill,
        "app.skills.tier2.dorsey_moat.skill.DorseyMoatSkill",
    )
    inp = DorseyMoatInput(ticker="TST", ratios=DorseyRatios())
    with patch(
        "app.skills.tier2.dorsey_moat.skill.call_claude_with_retry",
        new_callable=AsyncMock,
        return_value=_text_only_response(),
    ):
        with pytest.raises(ValueError, match="Aucun bloc tool_use"):
            await skill.execute(inp)


@pytest.mark.asyncio
async def test_buffett_execute_leve_value_error_sans_tool_use():
    skill = _make_skill(
        BuffettQualitySkill,
        "app.skills.tier2.buffett_quality.skill.BuffettQualitySkill",
    )
    inp = BuffettQualityInput(ticker="TST", ratios=BuffettRatios())
    with patch(
        "app.skills.tier2.buffett_quality.skill.call_claude_with_retry",
        new_callable=AsyncMock,
        return_value=_text_only_response(),
    ):
        with pytest.raises(ValueError, match="Aucun bloc tool_use"):
            await skill.execute(inp)


@pytest.mark.asyncio
async def test_valuation_execute_leve_value_error_sans_tool_use():
    skill = _make_skill(
        StockValuationSkill,
        "app.skills.tier2.stock_valuation.skill.StockValuationSkill",
    )
    inp = StockValuationInput(ticker="TST", ratios=ValuationRatios())
    with patch(
        "app.skills.tier2.stock_valuation.skill.call_claude_with_retry",
        new_callable=AsyncMock,
        return_value=_text_only_response(),
    ):
        with pytest.raises(ValueError, match="Aucun bloc tool_use"):
            await skill.execute(inp)


@pytest.mark.asyncio
async def test_thesis_execute_leve_value_error_sans_tool_use():
    skill = _make_skill(
        ThesisBuilderSkill,
        "app.skills.tier2.thesis_builder.skill.ThesisBuilderSkill",
    )
    inp = ThesisBuilderInput(ticker="TST", all_contexts=AllSkillContexts())
    with patch(
        "app.skills.tier2.thesis_builder.skill.call_claude_with_retry",
        new_callable=AsyncMock,
        return_value=_text_only_response(),
    ):
        with pytest.raises(ValueError, match="Aucun bloc tool_use"):
            await skill.execute(inp)


@pytest.mark.asyncio
async def test_munger_execute_leve_value_error_sans_tool_use():
    skill = _make_skill(
        MungerMentalSkill,
        "app.skills.tier2.munger_mental.skill.MungerMentalSkill",
    )
    inp = MungerInput(ticker="TST", thesis_context=_thesis_context())
    with patch(
        "app.skills.tier2.munger_mental.skill.call_claude_with_retry",
        new_callable=AsyncMock,
        return_value=_text_only_response(),
    ):
        with pytest.raises(ValueError, match="Aucun bloc tool_use"):
            await skill.execute(inp)


@pytest.mark.asyncio
async def test_canadian_tax_execute_leve_value_error_sans_tool_use():
    skill = _make_skill(
        CanadianTaxSkill,
        "app.skills.tier2.canadian_tax.skill.CanadianTaxSkill",
    )
    inp = CanadianTaxInput(ticker="TST", position_size_pct=3.0, verdict_final="ACHETER")
    with patch(
        "app.skills.tier2.canadian_tax.skill.call_claude_with_retry",
        new_callable=AsyncMock,
        return_value=_text_only_response(),
    ):
        with pytest.raises(ValueError, match="Aucun bloc tool_use"):
            await skill.execute(inp)


@pytest.mark.asyncio
async def test_lynch_execute_leve_value_error_sans_tool_use():
    skill = _make_skill(
        LynchCategoriesSkill,
        "app.skills.tier2.lynch_categories.skill.LynchCategoriesSkill",
    )
    inp = LynchInput(ticker="TST", ratios=LynchRatios(pe=15.0, eps_growth_5y=0.10))
    with patch(
        "app.skills.tier2.lynch_categories.skill.call_claude_with_retry",
        new_callable=AsyncMock,
        return_value=_text_only_response(),
    ):
        with pytest.raises(ValueError, match="Aucun bloc tool_use"):
            await skill.execute(inp)


@pytest.mark.asyncio
async def test_fisher_execute_leve_value_error_sans_tool_use():
    skill = _make_skill(
        FisherScuttlebuttSkill,
        "app.skills.tier2.fisher_scuttlebutt.skill.FisherScuttlebuttSkill",
    )
    inp = FisherInput(ticker="TST", fisher_answers=_fisher_answers())
    with patch(
        "app.skills.tier2.fisher_scuttlebutt.skill.call_claude_with_retry",
        new_callable=AsyncMock,
        return_value=_text_only_response(),
    ):
        with pytest.raises(ValueError, match="Aucun bloc tool_use"):
            await skill.execute(inp)


@pytest.mark.asyncio
async def test_klarman_execute_leve_value_error_sans_tool_use():
    skill = _make_skill(
        KlarmanMarginSkill,
        "app.skills.tier2.klarman_margin.skill.KlarmanMarginSkill",
    )
    inp = KlarmanInput(
        ticker="TST",
        situation_type="NET_NET",
        klarman_ratios=KlarmanRatios(price=50.0),
    )
    with patch(
        "app.skills.tier2.klarman_margin.skill.call_claude_with_retry",
        new_callable=AsyncMock,
        return_value=_text_only_response(),
    ):
        with pytest.raises(ValueError, match="Aucun bloc tool_use"):
            await skill.execute(inp)


@pytest.mark.asyncio
async def test_greenblatt_execute_leve_value_error_sans_tool_use():
    skill = _make_skill(
        GreenblattSkill,
        "app.skills.tier2.greenblatt.skill.GreenblattSkill",
    )
    inp = GreenblattInput(
        ticker="TST",
        greenblatt_ratios=GreenblattRatios(
            ebit=1000.0,
            enterprise_value=5000.0,
            net_working_capital=500.0,
            net_fixed_assets=1500.0,
        ),
    )
    with patch(
        "app.skills.tier2.greenblatt.skill.call_claude_with_retry",
        new_callable=AsyncMock,
        return_value=_text_only_response(),
    ):
        with pytest.raises(ValueError, match="Aucun bloc tool_use"):
            await skill.execute(inp)


@pytest.mark.asyncio
async def test_damodaran_execute_leve_value_error_sans_tool_use():
    skill = _make_skill(
        DamodararNarrativeSkill,
        "app.skills.tier2.damodaran_narrative.skill.DamodararNarrativeSkill",
    )
    inp = DamodararInput(
        ticker="TST",
        narrative_text="Narrative de test.",
        damodaran_ratios=DamodararRatios(
            revenue_bn=1.0,
            revenue_growth_5y=0.10,
            net_margin=0.20,
            roic=0.15,
        ),
    )
    with patch(
        "app.skills.tier2.damodaran_narrative.skill.call_claude_with_retry",
        new_callable=AsyncMock,
        return_value=_text_only_response(),
    ):
        with pytest.raises(ValueError, match="Aucun bloc tool_use"):
            await skill.execute(inp)


@pytest.mark.asyncio
async def test_marks_execute_leve_value_error_sans_tool_use():
    skill = _make_skill(
        MarksCyclesSkill,
        "app.skills.tier2.marks_cycles.skill.MarksCyclesSkill",
    )
    inp = MarksInput(market_context="Contexte macro test.", marks_ratios=MarksRatios())
    with patch(
        "app.skills.tier2.marks_cycles.skill.call_claude_with_retry",
        new_callable=AsyncMock,
        return_value=_text_only_response(),
    ):
        with pytest.raises(ValueError, match="Aucun bloc tool_use"):
            await skill.execute(inp)


@pytest.mark.asyncio
async def test_pabrai_execute_leve_value_error_sans_tool_use():
    skill = _make_skill(
        PabraiDhandhoSkill,
        "app.skills.tier2.pabrai_dhandho.skill.PabraiDhandhoSkill",
    )
    inp = PabraiInput(
        ticker="TST",
        pabrai_ratios=PabraiRatios(
            price=50.0,
            intrinsic_value_low=75.0,
            intrinsic_value_high=100.0,
            downside_pct=-0.30,
            upside_pct=0.50,
            debt_equity=0.40,
            fcf_yield=0.05,
            business_quality_score=7,
        ),
    )
    with patch(
        "app.skills.tier2.pabrai_dhandho.skill.call_claude_with_retry",
        new_callable=AsyncMock,
        return_value=_text_only_response(),
    ):
        with pytest.raises(ValueError, match="Aucun bloc tool_use"):
            await skill.execute(inp)
