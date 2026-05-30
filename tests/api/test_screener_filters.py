"""Tests du filtrage post-analyse Sprint 58 — composite_label, min_composite_score, filter_workflow."""
from __future__ import annotations

import uuid
from unittest.mock import AsyncMock

from app.api.endpoints.screen import ScreenEntry, ScreenRequest
from app.orchestrator.core import AnalyzeResponse
from app.services.composite_score import CompositeScore
from app.services.screener import ScreenerService
from app.skills.tier2.graham_analysis.schemas import GrahamRatios

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

RATIOS_MINI = GrahamRatios(
    pe=11.0,
    pb=1.3,
    current_ratio=None,
    debt_equity=0.45,
    eps_growth_total=0.27,
    price=80.0,
    book_value=61.5,
)


def _make_entry(
    ticker: str,
    composite_score: float | None = None,
    composite_label: str | None = None,
    workflow: str = "value_graham",
    erreur: str | None = None,
) -> ScreenEntry:
    return ScreenEntry(
        ticker=ticker,
        defensive_score=5 if erreur is None else None,
        verdict="PASSE" if erreur is None else None,
        composite_score=composite_score,
        composite_label=composite_label,
        workflow_utilise=workflow,
        cost_usd=0.002,
        depuis_cache=False,
        erreur=erreur,
    )


def _make_cs(score: float, label: str) -> CompositeScore:
    return CompositeScore(
        score=score,
        label=label,
        skills_inclus=["graham"],
        skills_exclus=[],
        detail={"graham": 1.0},
    )


def _make_response(
    ticker: str,
    score: int = 5,
    composite_score: float | None = None,
    composite_label: str | None = None,
    workflow: str = "value_graham",
) -> AnalyzeResponse:
    from app.skills.tier2.graham_analysis.schemas import GrahamAnalysisOutput
    from tests.conftest import _make_criteria_defensif, _make_criteria_entreprenant

    graham = GrahamAnalysisOutput(
        ticker=ticker,
        profil_applique="DEFENSIF",
        defensive_score=score,
        enterprising_score=min(score, 5),
        criteria_defensif=_make_criteria_defensif([True] * score + [False] * (8 - score)),
        criteria_entreprenant=_make_criteria_entreprenant([True] * min(score, 5) + [False] * (5 - min(score, 5))),
        valeur_intrinseque_simple=80.0,
        valeur_intrinseque_ajustee=75.0,
        marge_securite=0.06,
        drapeaux_rouges=[],
        verdict="PASSE",
        verdict_detail=f"{ticker}: PASSE",
        recommandation_prochaine_etape=[],
        citations=[],
        cost_usd=0.002,
    )
    cs = _make_cs(composite_score, composite_label) if composite_score is not None else None
    return AnalyzeResponse(
        analysis_id=str(uuid.uuid4()),
        ticker=ticker,
        workflow=workflow,
        skills_applied=["graham_analysis"],
        graham=graham,
        composite_score=cs,
        cost_usd=0.002,
        created_at="2026-05-14T10:00:00+00:00",
    )


def _make_screener(side_effects: list) -> ScreenerService:
    mock_orchestrator = AsyncMock()
    mock_orchestrator.run_company_analysis = AsyncMock(side_effect=side_effects)
    mock_extractor = AsyncMock()
    return ScreenerService(
        orchestrator=mock_orchestrator,
        extractor=mock_extractor,
        cache=None,
    )


# ---------------------------------------------------------------------------
# 1. Nouveaux champs optionnels dans ScreenRequest
# ---------------------------------------------------------------------------

def test_screen_request_nouveaux_champs_optionnels_defaults():
    """ScreenRequest accepte les 3 nouveaux champs, tous None par défaut."""
    req = ScreenRequest(tickers=["BNS"], workflow="value_graham")
    assert req.composite_label is None
    assert req.min_composite_score is None
    assert req.filter_workflow is None


def test_screen_request_nouveaux_champs_acceptes():
    """ScreenRequest accepte les 3 nouveaux champs avec des valeurs explicites."""
    req = ScreenRequest(
        tickers=["BNS"],
        composite_label="FORT",
        min_composite_score=70.0,
        filter_workflow="value_graham",
    )
    assert req.composite_label == "FORT"
    assert req.min_composite_score == 70.0
    assert req.filter_workflow == "value_graham"


# ---------------------------------------------------------------------------
# 2. Compatibilité arrière — sans filtres, comportement inchangé
# ---------------------------------------------------------------------------

async def test_sans_filtres_retourne_tous_les_tickers():
    """Sans filtres, tous les tickers (succès + échecs) sont retournés."""
    screener = _make_screener([
        _make_response("BNS", score=6, composite_score=72.0, composite_label="FORT"),
        _make_response("TD", score=4, composite_score=55.0, composite_label="MODERE"),
        RuntimeError("Erreur TD"),
    ])
    req = ScreenRequest(
        tickers=["BNS", "TD", "FAIL"],
        ratios_map={"BNS": RATIOS_MINI, "TD": RATIOS_MINI, "FAIL": RATIOS_MINI},
    )
    result = await screener.screen(req)
    assert len(result.resultats) == 3


# ---------------------------------------------------------------------------
# 3. Filtre composite_label
# ---------------------------------------------------------------------------

async def test_filtre_composite_label_fort_exclut_modere_et_faible():
    """composite_label='FORT' n'inclut que les tickers FORT (+ échecs)."""
    screener = _make_screener([
        _make_response("BNS", composite_score=80.0, composite_label="FORT"),
        _make_response("TD", composite_score=55.0, composite_label="MODERE"),
        _make_response("RY", composite_score=35.0, composite_label="FAIBLE"),
    ])
    req = ScreenRequest(
        tickers=["BNS", "TD", "RY"],
        ratios_map={"BNS": RATIOS_MINI, "TD": RATIOS_MINI, "RY": RATIOS_MINI},
        composite_label="FORT",
    )
    result = await screener.screen(req)

    labels = [e.composite_label for e in result.resultats if e.erreur is None]
    assert labels == ["FORT"]
    assert result.tickers_analyses == 1


async def test_filtre_composite_label_modere():
    """composite_label='MODERE' n'inclut que les tickers MODERE."""
    screener = _make_screener([
        _make_response("BNS", composite_score=80.0, composite_label="FORT"),
        _make_response("TD", composite_score=55.0, composite_label="MODERE"),
        _make_response("RY", composite_score=35.0, composite_label="FAIBLE"),
    ])
    req = ScreenRequest(
        tickers=["BNS", "TD", "RY"],
        ratios_map={"BNS": RATIOS_MINI, "TD": RATIOS_MINI, "RY": RATIOS_MINI},
        composite_label="MODERE",
    )
    result = await screener.screen(req)

    tickers_ok = [e.ticker for e in result.resultats if e.erreur is None]
    assert tickers_ok == ["TD"]


# ---------------------------------------------------------------------------
# 4. Filtre min_composite_score
# ---------------------------------------------------------------------------

async def test_filtre_min_composite_score_exclut_score_inferieur():
    """min_composite_score=70.0 exclut les tickers avec score < 70."""
    screener = _make_screener([
        _make_response("BNS", composite_score=80.0, composite_label="FORT"),
        _make_response("TD", composite_score=65.0, composite_label="MODERE"),
        _make_response("RY", composite_score=45.0, composite_label="FAIBLE"),
    ])
    req = ScreenRequest(
        tickers=["BNS", "TD", "RY"],
        ratios_map={"BNS": RATIOS_MINI, "TD": RATIOS_MINI, "RY": RATIOS_MINI},
        min_composite_score=70.0,
    )
    result = await screener.screen(req)

    tickers_ok = [e.ticker for e in result.resultats if e.erreur is None]
    assert tickers_ok == ["BNS"]


async def test_filtre_min_composite_score_exclut_entry_sans_composite():
    """Entry sans composite_score exclue si min_composite_score fourni."""
    screener = _make_screener([
        _make_response("BNS", composite_score=80.0, composite_label="FORT"),
        _make_response("TD"),  # pas de composite_score
    ])
    req = ScreenRequest(
        tickers=["BNS", "TD"],
        ratios_map={"BNS": RATIOS_MINI, "TD": RATIOS_MINI},
        min_composite_score=50.0,
    )
    result = await screener.screen(req)

    tickers_ok = [e.ticker for e in result.resultats if e.erreur is None]
    assert "BNS" in tickers_ok
    assert "TD" not in tickers_ok


# ---------------------------------------------------------------------------
# 5. Filtre filter_workflow
# ---------------------------------------------------------------------------

async def test_filtre_workflow_inclut_quand_match():
    """filter_workflow='value_graham' inclut toutes les entries du workflow demandé."""
    screener = _make_screener([
        _make_response("BNS", composite_score=75.0, composite_label="FORT"),
        _make_response("TD", composite_score=72.0, composite_label="FORT"),
    ])
    req = ScreenRequest(
        tickers=["BNS", "TD"],
        ratios_map={"BNS": RATIOS_MINI, "TD": RATIOS_MINI},
        workflow="value_graham",
        filter_workflow="value_graham",  # correspond au workflow utilisé → tout passe
    )
    result = await screener.screen(req)

    tickers_ok = [e.ticker for e in result.resultats if e.erreur is None]
    assert "BNS" in tickers_ok
    assert "TD" in tickers_ok


async def test_filtre_workflow_exclut_quand_mismatch():
    """filter_workflow différent du workflow utilisé → toutes les entries exclues (sauf échecs)."""
    screener = _make_screener([
        _make_response("BNS", composite_score=75.0, composite_label="FORT"),
        _make_response("TD", composite_score=72.0, composite_label="FORT"),
    ])
    req = ScreenRequest(
        tickers=["BNS", "TD"],
        ratios_map={"BNS": RATIOS_MINI, "TD": RATIOS_MINI},
        workflow="value_graham",
        filter_workflow="compounder_buffett",  # workflow_utilise sera "value_graham" → exclus
    )
    result = await screener.screen(req)

    tickers_ok = [e.ticker for e in result.resultats if e.erreur is None]
    assert tickers_ok == []


# ---------------------------------------------------------------------------
# 6. Filtres combinés (AND)
# ---------------------------------------------------------------------------

async def test_filtres_combines_and():
    """Filtres combinés : composite_label='FORT' AND min_composite_score=75 — seul BNS passe."""
    screener = _make_screener([
        _make_response("BNS", composite_score=80.0, composite_label="FORT"),
        _make_response("TD", composite_score=70.0, composite_label="FORT"),   # FORT mais < 75
        _make_response("RY", composite_score=85.0, composite_label="MODERE"), # >= 75 mais pas FORT
    ])
    req = ScreenRequest(
        tickers=["BNS", "TD", "RY"],
        ratios_map={"BNS": RATIOS_MINI, "TD": RATIOS_MINI, "RY": RATIOS_MINI},
        composite_label="FORT",
        min_composite_score=75.0,
    )
    result = await screener.screen(req)

    tickers_ok = [e.ticker for e in result.resultats if e.erreur is None]
    assert tickers_ok == ["BNS"]


# ---------------------------------------------------------------------------
# 7. Tickers en échec toujours inclus
# ---------------------------------------------------------------------------

async def test_echecs_toujours_inclus_avec_filtres():
    """Les tickers en échec sont inclus dans les résultats même si filtres actifs."""
    screener = _make_screener([
        _make_response("BNS", composite_score=45.0, composite_label="FAIBLE"),
        RuntimeError("Erreur API"),
    ])
    req = ScreenRequest(
        tickers=["BNS", "FAIL"],
        ratios_map={"BNS": RATIOS_MINI, "FAIL": RATIOS_MINI},
        composite_label="FORT",  # BNS sera exclu (FAIBLE), mais FAIL reste
    )
    result = await screener.screen(req)

    assert result.tickers_echec == 1
    assert any(e.erreur is not None for e in result.resultats)
    echec = next(e for e in result.resultats if e.erreur is not None)
    assert echec.ticker == "FAIL"


async def test_echecs_inclus_avec_tous_filtres_actifs():
    """Tickers en échec inclus même quand les 3 filtres sont actifs."""
    screener = _make_screener([
        RuntimeError("Timeout extraction"),
        _make_response("TD", composite_score=80.0, composite_label="FORT"),
    ])
    req = ScreenRequest(
        tickers=["FAIL", "TD"],
        ratios_map={"FAIL": RATIOS_MINI, "TD": RATIOS_MINI},
        composite_label="FORT",
        min_composite_score=75.0,
        filter_workflow="value_graham",
    )
    result = await screener.screen(req)

    assert result.tickers_echec == 1
    tickers_resultats = [e.ticker for e in result.resultats]
    assert "FAIL" in tickers_resultats
    assert "TD" in tickers_resultats


# ---------------------------------------------------------------------------
# 8. Test d'intégration endpoint POST /screen avec filtres
# ---------------------------------------------------------------------------

async def test_endpoint_screen_avec_filtre_composite_label(client):
    """POST /screen avec composite_label → 200 + ScreenResult JSON valide."""
    payload = {
        "tickers": ["BNS"],
        "workflow": "value_graham",
        "composite_label": "FORT",
        "ratios_map": {
            "BNS": {
                "pe": 11.0,
                "pb": 1.3,
                "current_ratio": None,
                "debt_equity": 0.45,
                "eps_growth_total": 0.27,
                "price": 80.0,
                "book_value": 61.5,
            }
        },
    }
    resp = await client.post("/screen", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert "resultats" in data
    assert "tickers_analyses" in data
    assert "workflow" in data


async def test_endpoint_screen_avec_min_composite_score(client):
    """POST /screen avec min_composite_score → 200 + ScreenResult JSON valide."""
    payload = {
        "tickers": ["TD"],
        "workflow": "value_graham",
        "min_composite_score": 70.0,
        "ratios_map": {
            "TD": {
                "pe": 12.0,
                "pb": 1.4,
                "current_ratio": None,
                "debt_equity": 0.50,
                "eps_growth_total": 0.30,
                "price": 90.0,
                "book_value": 65.0,
            }
        },
    }
    resp = await client.post("/screen", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert "resultats" in data


async def test_endpoint_screen_avec_filter_workflow(client):
    """POST /screen avec filter_workflow → 200 + ScreenResult JSON valide."""
    payload = {
        "tickers": ["RY"],
        "workflow": "value_graham",
        "filter_workflow": "value_graham",
        "ratios_map": {
            "RY": {
                "pe": 10.5,
                "pb": 1.2,
                "current_ratio": None,
                "debt_equity": 0.40,
                "eps_growth_total": 0.35,
                "price": 130.0,
                "book_value": 110.0,
            }
        },
    }
    resp = await client.post("/screen", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert "resultats" in data
