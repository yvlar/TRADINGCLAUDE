"""
Tests unitaires — migration Tool Use pour graham_analysis et earnings_quality (Sprint 42).

Ces tests vérifient :
  - Le schéma dérivé de Pydantic exclut bien les computed_fields
  - execute() extrait correctement le bloc tool_use de la réponse
  - execute() lève ValueError si aucun bloc tool_use n'est présent
  - call_claude_with_retry est appelé avec tools et tool_choice
  - La migration ne consomme aucun token Claude réel (call_claude_with_retry patché)
"""
from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.skills.tier2.earnings_quality.schemas import (
    EarningsQualityInput,
    EarningsQualityOutput,
    EarningsQualityRatios,
)
from app.skills.tier2.earnings_quality.skill import (
    _EARNINGS_TOOL_SCHEMA,
    EarningsQualitySkill,
)
from app.skills.tier2.graham_analysis.schemas import (
    GrahamAnalysisInput,
    GrahamAnalysisOutput,
    GrahamRatios,
)
from app.skills.tier2.graham_analysis.skill import (
    _GRAHAM_TOOL_SCHEMA,
    GrahamAnalysisSkill,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_graham_skill() -> GrahamAnalysisSkill:
    """GrahamAnalysisSkill sans lecture de fichier système."""
    with patch(
        "app.skills.tier2.graham_analysis.skill.GrahamAnalysisSkill._load_system_prompt",
        return_value="prompt de test",
    ):
        return GrahamAnalysisSkill(client=MagicMock(), model="claude-sonnet-4-6")


def _make_earnings_skill() -> EarningsQualitySkill:
    """EarningsQualitySkill sans lecture de fichier système."""
    with patch(
        "app.skills.tier2.earnings_quality.skill.EarningsQualitySkill._load_system_prompt",
        return_value="prompt de test",
    ):
        return EarningsQualitySkill(client=MagicMock(), model="claude-sonnet-4-6")


def _make_mock_response(input_dict: dict, stop_reason: str = "tool_use") -> MagicMock:
    """Construit un objet réponse Anthropic simulé avec un bloc tool_use."""
    mock_block = MagicMock()
    mock_block.type = "tool_use"
    mock_block.input = input_dict

    mock_response = MagicMock()
    mock_response.content = [mock_block]
    mock_response.stop_reason = stop_reason
    mock_response.usage = SimpleNamespace(
        input_tokens=500,
        output_tokens=300,
        cache_read_input_tokens=0,
        cache_creation_input_tokens=800,
    )
    return mock_response


def _make_text_only_response() -> MagicMock:
    """Réponse sans aucun bloc tool_use — simule un échec de Tool Use."""
    mock_block = MagicMock()
    mock_block.type = "text"
    mock_block.text = '{"ticker": "TST"}'

    mock_response = MagicMock()
    mock_response.content = [mock_block]
    mock_response.stop_reason = "end_turn"
    mock_response.usage = SimpleNamespace(
        input_tokens=100,
        output_tokens=50,
        cache_read_input_tokens=0,
        cache_creation_input_tokens=0,
    )
    return mock_response


# ---------------------------------------------------------------------------
# 1. Vérification des schémas dérivés de Pydantic
# ---------------------------------------------------------------------------

def test_graham_tool_schema_exclut_computed_fields():
    """Les trois computed_fields ne doivent pas figurer dans le schéma Tool Use."""
    props = _GRAHAM_TOOL_SCHEMA.get("properties", {})
    assert "defensive_score" not in props, "defensive_score est un computed_field — ne doit pas être dans le schéma"
    assert "defensive_verdict" not in props, "defensive_verdict est un computed_field — ne doit pas être dans le schéma"
    assert "confidence_score" not in props, "confidence_score est un computed_field — ne doit pas être dans le schéma"


def test_graham_tool_schema_contient_champs_requis():
    """Les champs structurels obligatoires doivent rester dans le schéma."""
    props = _GRAHAM_TOOL_SCHEMA.get("properties", {})
    for champ in ("ticker", "profil_applique", "criteria_defensif", "criteria_entreprenant",
                  "drapeaux_rouges", "verdict", "verdict_detail"):
        assert champ in props, f"Champ requis absent du schéma Tool Use : {champ}"


def test_earnings_tool_schema_exclut_confidence_score():
    """confidence_score est un computed_field — il ne doit pas figurer dans le schéma earnings."""
    props = _EARNINGS_TOOL_SCHEMA.get("properties", {})
    assert "confidence_score" not in props, "confidence_score est un computed_field — ne doit pas être dans le schéma"


def test_earnings_tool_schema_contient_champs_requis():
    """Les champs structurels d'EarningsQualityOutput doivent rester dans le schéma."""
    props = _EARNINGS_TOOL_SCHEMA.get("properties", {})
    for champ in ("ticker", "m_score", "z_score", "f_score", "c_score", "sloan",
                  "drapeaux_rouges", "verdict", "verdict_detail"):
        assert champ in props, f"Champ requis absent du schéma Tool Use earnings : {champ}"


# ---------------------------------------------------------------------------
# 2. execute() — extraction correcte du bloc tool_use
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_graham_execute_extrait_tool_use_block(graham_output_msft: GrahamAnalysisOutput):
    """execute() doit retourner un GrahamAnalysisOutput valide depuis le bloc tool_use."""
    skill = _make_graham_skill()

    tool_input = graham_output_msft.model_dump(
        exclude={"defensive_score", "defensive_verdict", "confidence_score"}
    )
    mock_response = _make_mock_response(tool_input)

    input_data = GrahamAnalysisInput(
        ticker="MSFT",
        ratios=GrahamRatios(pe=34.2, pb=12.1, current_ratio=1.34, debt_equity=0.28,
                            eps_growth_10y=0.85, price=420.0, book_value=35.0),
    )

    with patch("app.skills.tier2.graham_analysis.skill.call_claude_with_retry",
               new_callable=AsyncMock, return_value=mock_response):
        output, usage = await skill.execute(input_data)

    assert isinstance(output, GrahamAnalysisOutput)
    assert output.ticker == "MSFT"
    assert output.defensive_score == graham_output_msft.defensive_score
    assert output.defensive_verdict == graham_output_msft.defensive_verdict
    assert isinstance(usage.cost_usd, float)


@pytest.mark.asyncio
async def test_graham_execute_leve_value_error_sans_tool_use_block():
    """execute() doit lever ValueError si la réponse ne contient aucun bloc tool_use."""
    skill = _make_graham_skill()

    input_data = GrahamAnalysisInput(
        ticker="TST",
        ratios=GrahamRatios(pe=10.0, pb=1.0, current_ratio=2.0, debt_equity=0.3,
                            eps_growth_10y=0.5, price=100.0, book_value=50.0),
    )

    with patch("app.skills.tier2.graham_analysis.skill.call_claude_with_retry",
               new_callable=AsyncMock, return_value=_make_text_only_response()):
        with pytest.raises(ValueError, match="Aucun bloc tool_use"):
            await skill.execute(input_data)


@pytest.mark.asyncio
async def test_graham_execute_passe_tools_et_tool_choice(graham_output_msft: GrahamAnalysisOutput):
    """call_claude_with_retry doit recevoir tools et tool_choice pour forcer le Tool Use."""
    skill = _make_graham_skill()

    tool_input = graham_output_msft.model_dump(
        exclude={"defensive_score", "defensive_verdict", "confidence_score"}
    )
    mock_response = _make_mock_response(tool_input)

    input_data = GrahamAnalysisInput(
        ticker="MSFT",
        ratios=GrahamRatios(pe=34.2, pb=12.1, current_ratio=1.34, debt_equity=0.28,
                            eps_growth_10y=0.85, price=420.0, book_value=35.0),
    )

    with patch("app.skills.tier2.graham_analysis.skill.call_claude_with_retry",
               new_callable=AsyncMock, return_value=mock_response) as mock_call:
        await skill.execute(input_data)

    call_kwargs = mock_call.call_args.kwargs
    assert "tools" in call_kwargs, "tools doit être passé à call_claude_with_retry"
    assert "tool_choice" in call_kwargs, "tool_choice doit être passé à call_claude_with_retry"

    tool_names = [t["name"] for t in call_kwargs["tools"]]
    assert "graham_output" in tool_names

    assert call_kwargs["tool_choice"]["type"] == "tool"
    assert call_kwargs["tool_choice"]["name"] == "graham_output"


# ---------------------------------------------------------------------------
# 3. execute() earnings_quality
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_earnings_execute_leve_value_error_sans_tool_use_block():
    """EarningsQualitySkill.execute() doit lever ValueError si pas de bloc tool_use."""
    skill = _make_earnings_skill()

    input_data = EarningsQualityInput(
        ticker="TST",
        ratios=EarningsQualityRatios(
            sales_t=1_000_000,
            sales_t1=900_000,
            cogs_t=600_000,
            cogs_t1=540_000,
            net_income_t=100_000,
            cfo_t=120_000,
            receivables_t=200_000,
            receivables_t1=180_000,
            current_assets_t=400_000,
            current_liabilities_t=200_000,
            total_assets_t=800_000,
            total_assets_t1=750_000,
        ),
    )

    with patch("app.skills.tier2.earnings_quality.skill.call_claude_with_retry",
               new_callable=AsyncMock, return_value=_make_text_only_response()):
        with pytest.raises(ValueError, match="Aucun bloc tool_use"):
            await skill.execute(input_data)


@pytest.mark.asyncio
async def test_earnings_execute_passe_tools_et_tool_choice(earnings_output_msft: EarningsQualityOutput):
    """EarningsQualitySkill doit passer tools et tool_choice avec le bon nom d'outil."""
    skill = _make_earnings_skill()

    tool_input = earnings_output_msft.model_dump(exclude={"confidence_score"})
    mock_response = _make_mock_response(tool_input)

    input_data = EarningsQualityInput(
        ticker="MSFT",
        ratios=EarningsQualityRatios(
            sales_t=211_915_000_000,
            sales_t1=198_270_000_000,
            cogs_t=74_114_000_000,
            cogs_t1=65_863_000_000,
            net_income_t=72_361_000_000,
            cfo_t=87_582_000_000,
            receivables_t=48_688_000_000,
            receivables_t1=44_261_000_000,
            current_assets_t=184_257_000_000,
            current_liabilities_t=95_082_000_000,
            total_assets_t=512_163_000_000,
            total_assets_t1=484_275_000_000,
        ),
    )

    with patch("app.skills.tier2.earnings_quality.skill.call_claude_with_retry",
               new_callable=AsyncMock, return_value=mock_response) as mock_call:
        await skill.execute(input_data)

    call_kwargs = mock_call.call_args.kwargs
    tool_names = [t["name"] for t in call_kwargs.get("tools", [])]
    assert "earnings_quality_output" in tool_names

    assert call_kwargs["tool_choice"]["type"] == "tool"
    assert call_kwargs["tool_choice"]["name"] == "earnings_quality_output"
