"""Tests du screener multi-tickers — ScreenerService + POST /screen."""
from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.api.endpoints.screen import ScreenEntry, ScreenRequest, ScreenResult
from app.orchestrator.core import AnalyzeResponse
from app.services.screener import ScreenerService
from app.skills.tier2.graham_analysis.schemas import GrahamRatios


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_graham_output(ticker: str, score: int, verdict: str):
    from tests.conftest import _make_criteria_defensif, _make_criteria_entreprenant
    from app.skills.tier2.graham_analysis.schemas import GrahamAnalysisOutput

    ent_score = min(score, 5)
    return GrahamAnalysisOutput(
        ticker=ticker,
        profil_applique="DEFENSIF",
        defensive_score=score,
        enterprising_score=ent_score,
        criteria_defensif=_make_criteria_defensif([True] * score + [False] * (8 - score)),
        criteria_entreprenant=_make_criteria_entreprenant([True] * ent_score + [False] * (5 - ent_score)),
        valeur_intrinseque_simple=80.0,
        valeur_intrinseque_ajustee=75.0,
        marge_securite=0.06,
        drapeaux_rouges=[],
        verdict=verdict,
        verdict_detail=f"{ticker}: {verdict}",
        recommandation_prochaine_etape=[],
        citations=[],
        cost_usd=0.002,
    )


def _make_response(ticker: str, score: int, verdict: str, cost: float = 0.002) -> AnalyzeResponse:
    return AnalyzeResponse(
        analysis_id=str(uuid.uuid4()),
        ticker=ticker,
        workflow="value_graham",
        skills_applied=["graham_analysis"],
        graham=_make_graham_output(ticker, score, verdict),
        cost_usd=cost,
        created_at="2026-05-08T10:00:00+00:00",
    )


RATIOS_MINI = GrahamRatios(
    pe=11.0,
    pb=1.3,
    current_ratio=None,
    debt_equity=0.45,
    eps_growth_10y=0.27,
    price=80.0,
    book_value=61.5,
)


# ---------------------------------------------------------------------------
# Tests de validation du schéma ScreenRequest
# ---------------------------------------------------------------------------

def test_screen_request_validation_ok():
    """ScreenRequest valide avec champs obligatoires."""
    req = ScreenRequest(tickers=["BNS", "TD"], workflow="value_graham")
    assert req.tickers == ["BNS", "TD"]
    assert req.workflow == "value_graham"
    assert req.max_parallel == 5


def test_screen_tickers_vide_422():
    """Liste vide → ValidationError."""
    from pydantic import ValidationError
    with pytest.raises(ValidationError, match="Au moins un ticker"):
        ScreenRequest(tickers=[])


def test_screen_tickers_max_depasse_422():
    """21 tickers → ValidationError."""
    from pydantic import ValidationError
    with pytest.raises(ValidationError, match="Maximum 20 tickers"):
        ScreenRequest(tickers=[f"T{i}" for i in range(21)])


def test_screen_ticker_invalide_leve_422():
    """Ticker avec caractères invalides → HTTPException 422."""
    from fastapi import HTTPException
    with pytest.raises(HTTPException) as exc_info:
        ScreenRequest(tickers=["BNS", "DROP TABLE", "TD"])
    assert exc_info.value.status_code == 422


async def test_screen_endpoint_ticker_invalide_422(client):
    """POST /screen avec un ticker invalide → 422."""
    payload = {"tickers": ["BNS; rm -rf /"], "workflow": "value_graham"}
    resp = await client.post("/screen", json=payload)
    assert resp.status_code == 422


async def test_screen_ticker_normalise_majuscules(client):
    """POST /screen avec ticker en minuscules → normalisé en majuscules."""
    payload = {
        "tickers": ["msft"],
        "workflow": "value_graham",
        "ratios_map": {
            "msft": {
                "pe": 34.2, "pb": 12.1, "current_ratio": 1.34,
                "debt_equity": 0.28, "eps_growth_10y": 0.85,
                "price": 420.0, "book_value": 35.0,
            }
        },
    }
    resp = await client.post("/screen", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert data["resultats"][0]["ticker"] == "MSFT"


# ---------------------------------------------------------------------------
# Tests du tri des résultats
# ---------------------------------------------------------------------------

async def test_screen_result_ranking_desc():
    """Les tickers sont triés par defensive_score décroissant."""
    # BNS score=6, TD score=4, RY score=7 → ordre: RY, BNS, TD
    mock_orchestrator = AsyncMock()
    mock_orchestrator.run_company_analysis = AsyncMock(
        side_effect=[
            _make_response("BNS", 6, "ACCEPTABLE"),
            _make_response("TD", 4, "PASSABLE"),
            _make_response("RY", 7, "BON"),
        ]
    )
    mock_extractor = AsyncMock()

    screener = ScreenerService(
        orchestrator=mock_orchestrator,
        extractor=mock_extractor,
        cache=None,
    )

    req = ScreenRequest(
        tickers=["BNS", "TD", "RY"],
        ratios_map={"BNS": RATIOS_MINI, "TD": RATIOS_MINI, "RY": RATIOS_MINI},
    )
    result = await screener.screen(req)

    scores = [e.defensive_score for e in result.resultats if e.erreur is None]
    assert scores == sorted(scores, reverse=True)
    assert result.resultats[0].ticker == "RY"


async def test_screen_echecs_en_bas():
    """Les entrées en erreur apparaissent après les succès."""
    mock_orchestrator = AsyncMock()
    mock_orchestrator.run_company_analysis = AsyncMock(
        side_effect=[
            _make_response("BNS", 6, "ACCEPTABLE"),
            RuntimeError("Timeout"),
        ]
    )
    mock_extractor = AsyncMock()

    screener = ScreenerService(
        orchestrator=mock_orchestrator,
        extractor=mock_extractor,
        cache=None,
    )

    req = ScreenRequest(
        tickers=["BNS", "FAIL"],
        ratios_map={"BNS": RATIOS_MINI, "FAIL": RATIOS_MINI},
    )
    result = await screener.screen(req)

    assert result.resultats[-1].erreur is not None
    assert result.resultats[0].erreur is None


# ---------------------------------------------------------------------------
# Tests de comportement du screener
# ---------------------------------------------------------------------------

async def test_screen_ticker_echec_non_bloquant():
    """1 échec sur 3 → 2 succès + 1 erreur, pas d'exception globale."""
    mock_orchestrator = AsyncMock()
    mock_orchestrator.run_company_analysis = AsyncMock(
        side_effect=[
            _make_response("BNS", 6, "ACCEPTABLE"),
            RuntimeError("API indisponible"),
            _make_response("RY", 5, "ACCEPTABLE"),
        ]
    )
    mock_extractor = AsyncMock()

    screener = ScreenerService(
        orchestrator=mock_orchestrator,
        extractor=mock_extractor,
        cache=None,
    )

    req = ScreenRequest(
        tickers=["BNS", "FAIL", "RY"],
        ratios_map={"BNS": RATIOS_MINI, "FAIL": RATIOS_MINI, "RY": RATIOS_MINI},
    )
    result = await screener.screen(req)

    assert result.tickers_analyses == 2
    assert result.tickers_echec == 1
    assert len(result.resultats) == 3


async def test_screen_deduplication_tickers():
    """['BNS','BNS'] → analysé une seule fois."""
    mock_orchestrator = AsyncMock()
    mock_orchestrator.run_company_analysis = AsyncMock(
        return_value=_make_response("BNS", 6, "ACCEPTABLE")
    )
    mock_extractor = AsyncMock()

    screener = ScreenerService(
        orchestrator=mock_orchestrator,
        extractor=mock_extractor,
        cache=None,
    )

    req = ScreenRequest(
        tickers=["BNS", "BNS", "BNS"],
        ratios_map={"BNS": RATIOS_MINI},
    )
    result = await screener.screen(req)

    # Une seule analyse malgré 3 occurrences
    assert mock_orchestrator.run_company_analysis.call_count == 1
    assert result.tickers_analyses == 1


async def test_screen_cout_total_calcul():
    """cout_total_usd = sum(entry.cost_usd)."""
    mock_orchestrator = AsyncMock()
    mock_orchestrator.run_company_analysis = AsyncMock(
        side_effect=[
            _make_response("BNS", 6, "ACCEPTABLE", cost=0.003),
            _make_response("TD", 4, "PASSABLE", cost=0.004),
        ]
    )
    mock_extractor = AsyncMock()

    screener = ScreenerService(
        orchestrator=mock_orchestrator,
        extractor=mock_extractor,
        cache=None,
    )

    req = ScreenRequest(
        tickers=["BNS", "TD"],
        ratios_map={"BNS": RATIOS_MINI, "TD": RATIOS_MINI},
    )
    result = await screener.screen(req)

    expected = sum(e.cost_usd for e in result.resultats)
    assert abs(result.cout_total_usd - expected) < 1e-9


async def test_screen_workflow_transmis():
    """Le workflow de ScreenRequest est propagé à chaque ScreenEntry."""
    mock_orchestrator = AsyncMock()
    mock_orchestrator.run_company_analysis = AsyncMock(
        return_value=_make_response("BNS", 6, "ACCEPTABLE")
    )
    mock_extractor = AsyncMock()

    screener = ScreenerService(
        orchestrator=mock_orchestrator,
        extractor=mock_extractor,
        cache=None,
    )

    req = ScreenRequest(
        tickers=["BNS"],
        workflow="compounder_buffett",
        ratios_map={"BNS": RATIOS_MINI},
    )
    result = await screener.screen(req)

    assert result.workflow == "compounder_buffett"
    assert result.resultats[0].workflow_utilise == "compounder_buffett"


# ---------------------------------------------------------------------------
# Tests endpoint POST /screen via client HTTP
# ---------------------------------------------------------------------------

async def test_screen_endpoint_avec_ratios_map(client):
    """POST /screen avec ratios_map → 200 + ScreenResult valide."""
    payload = {
        "tickers": ["MSFT"],
        "workflow": "value_graham",
        "ratios_map": {
            "MSFT": {
                "pe": 34.2,
                "pb": 12.1,
                "current_ratio": 1.34,
                "debt_equity": 0.28,
                "eps_growth_10y": 0.85,
                "price": 420.0,
                "book_value": 35.0,
            }
        },
    }
    resp = await client.post("/screen", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert "resultats" in data
    assert "tickers_analyses" in data
    assert "workflow" in data


async def test_screen_endpoint_tickers_vide_422(client):
    """POST /screen avec [] → 422."""
    resp = await client.post("/screen", json={"tickers": []})
    assert resp.status_code == 422


async def test_screen_endpoint_trop_de_tickers_422(client):
    """POST /screen avec 21 tickers → 422."""
    resp = await client.post(
        "/screen",
        json={"tickers": [f"T{i}" for i in range(21)]},
    )
    assert resp.status_code == 422
