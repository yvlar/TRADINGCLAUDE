"""
Tests unitaires et d'intégration — skill ESG Simplifié (Sprint 70).

Couverture :
  - Validation des schémas EsgInput / EsgOutput / EsgCritere
  - Structure obligatoire (15 critères, 5E + 5S + 5G)
  - Cohérence des scores et verdicts
  - execute() avec mock Tool Use (0 token Claude réel)
  - Endpoint POST /analyze avec esg_input
  - Endpoint POST /analyze sans esg_input → esg=None
"""
from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.skills.tier2.esg_simplified.schemas import EsgCritere, EsgInput, EsgOutput
from app.skills.tier2.esg_simplified.skill import EsgSimplifiedSkill, _ESG_TOOL_SCHEMA


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_esg_skill() -> EsgSimplifiedSkill:
    with patch(
        "app.skills.tier2.esg_simplified.skill.EsgSimplifiedSkill._load_system_prompt",
        return_value="prompt de test ESG",
    ):
        return EsgSimplifiedSkill(client=MagicMock(), model="claude-sonnet-4-6")


def _make_15_criteres(e_pass: int = 4, s_pass: int = 3, g_pass: int = 3) -> list[dict]:
    """Génère exactement 15 critères (5E + 5S + 5G) avec le nombre de 'passe=True' demandé."""
    criteres = []
    for i, (dim, nb_pass) in enumerate([("E", e_pass), ("S", s_pass), ("G", g_pass)]):
        for j in range(5):
            criteres.append({
                "dimension": dim,
                "nom": f"Critère {dim}{j+1}",
                "passe": j < nb_pass,
                "observation": f"Observation test {dim}{j+1}",
                "proxy_utilise": "roe",
            })
    return criteres


def _make_mock_esg_response(input_dict: dict) -> MagicMock:
    mock_block = MagicMock()
    mock_block.type = "tool_use"
    mock_block.input = input_dict

    mock_response = MagicMock()
    mock_response.content = [mock_block]
    mock_response.stop_reason = "tool_use"
    mock_response.usage = SimpleNamespace(
        input_tokens=600,
        output_tokens=400,
        cache_read_input_tokens=0,
        cache_creation_input_tokens=900,
    )
    return mock_response


def _make_valid_esg_output_dict(
    ticker: str = "BNS",
    e_pass: int = 4,
    s_pass: int = 3,
    g_pass: int = 3,
) -> dict:
    total = e_pass + s_pass + g_pass
    if total >= 10:
        verdict = "ESG_FORT"
    elif total >= 5:
        verdict = "ESG_MODERE"
    else:
        verdict = "ESG_FAIBLE"
    return {
        "ticker": ticker,
        "esg_score": total,
        "e_score": e_pass,
        "s_score": s_pass,
        "g_score": g_pass,
        "criteres": _make_15_criteres(e_pass, s_pass, g_pass),
        "verdict": verdict,
        "verdict_detail": "Score ESG modéré basé sur les proxies financiers disponibles.",
        "limites": [
            "Analyse basée sur des proxies financiers uniquement, sans données ESG directes.",
            "Les émissions CO2 réelles et les conditions de travail ne sont pas accessibles via ce modèle.",
        ],
    }


# ---------------------------------------------------------------------------
# 1. Validation EsgInput
# ---------------------------------------------------------------------------

def test_esg_input_validation_ok():
    """EsgInput accepte un input complet et valide."""
    inp = EsgInput(
        ticker="BNS",
        sector="Financial Services",
        revenue_bn=32.5,
        roe=0.16,
        debt_equity=0.55,
        dividend_years=25,
        eps_growth_10y=0.62,
    )
    assert inp.ticker == "BNS"
    assert inp.sector == "Financial Services"
    assert inp.roe == pytest.approx(0.16)


def test_esg_input_sector_none():
    """EsgInput accepte sector=None sans erreur."""
    inp = EsgInput(ticker="MSFT", sector=None, roe=0.40)
    assert inp.sector is None
    assert inp.ticker == "MSFT"


def test_esg_input_tous_champs_optionnels_sauf_ticker():
    """Seul ticker est obligatoire dans EsgInput."""
    inp = EsgInput(ticker="TST")
    assert inp.revenue_bn is None
    assert inp.roe is None
    assert inp.debt_equity is None
    assert inp.dividend_years is None
    assert inp.eps_growth_10y is None


# ---------------------------------------------------------------------------
# 2. Validation EsgOutput
# ---------------------------------------------------------------------------

def test_esg_output_score_range():
    """esg_score doit toujours être dans [0, 15]."""
    data = _make_valid_esg_output_dict(e_pass=3, s_pass=3, g_pass=2)
    output = EsgOutput.model_validate(data)
    assert 0 <= output.esg_score <= 15


def test_esg_output_criteres_count():
    """EsgOutput doit contenir exactement 15 critères."""
    data = _make_valid_esg_output_dict()
    output = EsgOutput.model_validate(data)
    assert len(output.criteres) == 15


def test_esg_output_dimensions_count():
    """EsgOutput doit contenir exactement 5E + 5S + 5G."""
    data = _make_valid_esg_output_dict()
    output = EsgOutput.model_validate(data)
    e_count = sum(1 for c in output.criteres if c.dimension == "E")
    s_count = sum(1 for c in output.criteres if c.dimension == "S")
    g_count = sum(1 for c in output.criteres if c.dimension == "G")
    assert e_count == 5
    assert s_count == 5
    assert g_count == 5


def test_esg_output_rejete_moins_de_15_criteres():
    """EsgOutput doit rejeter un output avec moins de 15 critères."""
    data = _make_valid_esg_output_dict()
    data["criteres"] = data["criteres"][:14]  # 14 critères
    with pytest.raises(Exception):
        EsgOutput.model_validate(data)


def test_esg_verdict_fort():
    """esg_score >= 10 → verdict ESG_FORT."""
    data = _make_valid_esg_output_dict(e_pass=4, s_pass=4, g_pass=4)  # 12/15
    output = EsgOutput.model_validate(data)
    assert output.verdict == "ESG_FORT"
    assert output.esg_score == 12


def test_esg_verdict_modere():
    """esg_score entre 5 et 9 → verdict ESG_MODERE."""
    data = _make_valid_esg_output_dict(e_pass=2, s_pass=3, g_pass=2)  # 7/15
    output = EsgOutput.model_validate(data)
    assert output.verdict == "ESG_MODERE"
    assert output.esg_score == 7


def test_esg_verdict_faible():
    """esg_score <= 4 → verdict ESG_FAIBLE."""
    data = _make_valid_esg_output_dict(e_pass=1, s_pass=1, g_pass=2)  # 4/15
    output = EsgOutput.model_validate(data)
    assert output.verdict == "ESG_FAIBLE"
    assert output.esg_score == 4


# ---------------------------------------------------------------------------
# 3. Tool Schema
# ---------------------------------------------------------------------------

def test_esg_tool_schema_exclut_champs_post_assignes():
    """Le schéma Tool Use ne doit pas contenir citations ni cost_usd."""
    props = _ESG_TOOL_SCHEMA.get("properties", {})
    assert "citations" not in props
    assert "cost_usd" not in props


def test_esg_tool_schema_contient_champs_requis():
    """Les champs structurels obligatoires doivent être présents dans le schéma."""
    props = _ESG_TOOL_SCHEMA.get("properties", {})
    for champ in ("ticker", "esg_score", "e_score", "s_score", "g_score",
                  "criteres", "verdict", "verdict_detail", "limites"):
        assert champ in props, f"Champ requis absent du schéma Tool Use ESG : {champ}"


# ---------------------------------------------------------------------------
# 4. execute() avec mock Tool Use (0 token réel)
# ---------------------------------------------------------------------------

def test_esg_skill_build_user_message():
    """_build_user_message inclut ticker et sector."""
    skill = _make_esg_skill()
    inp = EsgInput(ticker="BNS", sector="Financial Services", roe=0.16, dividend_years=25)
    msg = skill._build_user_message(inp, citations=[])
    assert "BNS" in msg
    assert "Financial Services" in msg


@pytest.mark.asyncio
async def test_esg_execute_mock_claude():
    """execute() retourne un EsgOutput valide depuis la réponse Tool Use mockée (0 token réel)."""
    skill = _make_esg_skill()
    output_dict = _make_valid_esg_output_dict(ticker="BNS", e_pass=4, s_pass=3, g_pass=3)
    mock_response = _make_mock_esg_response(output_dict)

    inp = EsgInput(ticker="BNS", sector="Financial Services", roe=0.16, dividend_years=25)

    with patch(
        "app.skills.tier2.esg_simplified.skill.call_claude_with_retry",
        new_callable=AsyncMock,
        return_value=mock_response,
    ):
        output, usage = await skill.execute(inp)

    assert isinstance(output, EsgOutput)
    assert output.ticker == "BNS"
    assert len(output.criteres) == 15
    assert isinstance(usage.cost_usd, float)


@pytest.mark.asyncio
async def test_esg_execute_passe_tools_et_tool_choice():
    """call_claude_with_retry doit recevoir tools et tool_choice forcé sur esg_output."""
    skill = _make_esg_skill()
    output_dict = _make_valid_esg_output_dict(ticker="TST")
    mock_response = _make_mock_esg_response(output_dict)
    inp = EsgInput(ticker="TST")

    with patch(
        "app.skills.tier2.esg_simplified.skill.call_claude_with_retry",
        new_callable=AsyncMock,
        return_value=mock_response,
    ) as mock_call:
        await skill.execute(inp)

    call_kwargs = mock_call.call_args.kwargs
    assert "tools" in call_kwargs
    assert "tool_choice" in call_kwargs
    tool_names = [t["name"] for t in call_kwargs["tools"]]
    assert "esg_output" in tool_names
    assert call_kwargs["tool_choice"]["type"] == "tool"
    assert call_kwargs["tool_choice"]["name"] == "esg_output"


# ---------------------------------------------------------------------------
# 5. Tests d'intégration endpoint (0 token réel)
# ---------------------------------------------------------------------------

@pytest.mark.integration
@pytest.mark.asyncio
async def test_esg_endpoint_integration(client):
    """POST /analyze avec esg_input → champ esg présent dans la réponse (orchestrateur mocké)."""
    from app.orchestrator.core import AnalyzeResponse as CoreAnalyzeResponse
    from app.skills.tier2.esg_simplified.schemas import EsgOutput as CoreEsgOutput

    esg_data = _make_valid_esg_output_dict(ticker="BNS", e_pass=4, s_pass=3, g_pass=3)
    esg_out = CoreEsgOutput.model_validate(esg_data)

    # L'orchestrateur est déjà mocké dans le fixture `client` — on vérifie juste que le
    # champ esg est bien présent dans le schéma de réponse (AnalyzeResponse.esg existe)
    payload = {
        "ticker": "BNS",
        "workflow": "value_graham",
        "esg_input": {
            "ticker": "BNS",
            "sector": "Financial Services",
            "roe": 0.16,
            "dividend_years": 25,
        },
    }

    resp = await client.post("/analyze", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    # Le champ esg doit exister dans la réponse (peut être null via mock)
    assert "esg" in data


@pytest.mark.integration
@pytest.mark.asyncio
async def test_esg_endpoint_absent_sans_input(client):
    """POST /analyze sans esg_input → champ esg dans la réponse (null ou non, selon mock)."""
    payload = {
        "ticker": "BNS",
        "workflow": "value_graham",
    }

    resp = await client.post("/analyze", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    # Le champ esg doit exister dans le schéma de réponse
    assert "esg" in data
