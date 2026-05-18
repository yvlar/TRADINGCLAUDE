"""
Evals screener sur le golden dataset Sprint 54 — 10 tickers référence.
Marqueur @pytest.mark.evals : exclu de la CI standard.
Les mocks orchestrateur sont configurés depuis le golden dataset (aucun appel Claude réel).
Exécution : pytest tests/evals/test_screener_evals.py -m evals -v
"""
from __future__ import annotations

import uuid
from unittest.mock import AsyncMock

import pytest

from app.api.endpoints.screen import ScreenRequest
from app.orchestrator.core import AnalyzeRequest, AnalyzeResponse
from app.services.composite_score import compute_composite_score
from app.services.screener import ScreenerService
from app.skills.tier2.graham_analysis.schemas import GrahamAnalysisOutput, GrahamRatios

from tests.conftest import _make_criteria_defensif, _make_criteria_entreprenant
from tests.evals.fixtures import load_screener_golden

_VALID_COMPOSITE_LABELS = {"FAIBLE", "MODÉRÉ", "FORT"}


def _build_graham_output(ticker: str, score: int, verdict: str) -> GrahamAnalysisOutput:
    """Construit un GrahamAnalysisOutput avec exactement `score` critères défensifs réussis."""
    ent_score = min(score, 5)
    return GrahamAnalysisOutput(
        ticker=ticker,
        profil_applique="LES_DEUX",
        enterprising_score=ent_score,
        criteria_defensif=_make_criteria_defensif([True] * score + [False] * (8 - score)),
        criteria_entreprenant=_make_criteria_entreprenant(
            [True] * ent_score + [False] * (5 - ent_score)
        ),
        valeur_intrinseque_simple=None,
        valeur_intrinseque_ajustee=None,
        marge_securite=None,
        drapeaux_rouges=[],
        verdict=verdict,
        verdict_detail=f"Eval mock {ticker} — score={score}",
        recommandation_prochaine_etape=[],
        citations=[],
        cost_usd=0.001,
    )


def _build_response(ticker: str, score: int, verdict: str) -> AnalyzeResponse:
    """Construit une AnalyzeResponse complète avec composite_score calculé depuis le verdict Graham."""
    graham = _build_graham_output(ticker, score, verdict)
    composite = compute_composite_score(
        graham_verdict=graham.defensive_verdict,
        graham_confidence=0.5,
    )
    return AnalyzeResponse(
        analysis_id=str(uuid.uuid4()),
        ticker=ticker,
        workflow="value_graham",
        skills_applied=["graham_analysis"],
        graham=graham,
        composite_score=composite,
        cost_usd=0.001,
        created_at="2026-05-14T10:00:00+00:00",
    )


def _make_screener_from_cases(cases: list[dict]) -> ScreenerService:
    """ScreenerService avec orchestrateur mocké qui retourne les verdicts du golden dataset."""
    score_map = {c["ticker"]: c["expected"]["defensive_score_min"] for c in cases}
    verdict_map = {c["ticker"]: c["expected"]["verdict_allowed"][0] for c in cases}

    async def _side_effect(request: AnalyzeRequest) -> AnalyzeResponse:
        t = request.ticker
        return _build_response(t, score_map.get(t, 1), verdict_map.get(t, "WATCHLIST"))

    mock_orchestrator = AsyncMock()
    mock_orchestrator.run_company_analysis.side_effect = _side_effect
    return ScreenerService(
        orchestrator=mock_orchestrator,
        extractor=AsyncMock(),
        cache=None,
    )


def _build_ratios_map(cases: list[dict]) -> dict[str, GrahamRatios]:
    """Construit le ratios_map pour ScreenRequest depuis le golden dataset."""
    return {case["ticker"]: GrahamRatios(**case["ratios"]) for case in cases}


@pytest.mark.evals
async def test_golden_all_tickers_aucune_erreur():
    """Les 10 tickers du golden dataset s'exécutent via le screener sans erreur."""
    cases = load_screener_golden()
    assert cases, "golden_screener_dataset.json vide ou absent"

    screener = _make_screener_from_cases(cases)
    req = ScreenRequest(
        tickers=[c["ticker"] for c in cases],
        ratios_map=_build_ratios_map(cases),
    )
    result = await screener.screen(req)

    failing = [e.ticker for e in result.resultats if e.erreur is not None]
    assert result.tickers_echec == 0, f"Tickers en erreur : {failing}"
    assert result.tickers_analyses == len(cases)


@pytest.mark.evals
async def test_golden_tri_desc_par_composite_score():
    """Les résultats sont triés par composite_score décroissant, sans erreur."""
    cases = load_screener_golden()
    screener = _make_screener_from_cases(cases)
    req = ScreenRequest(
        tickers=[c["ticker"] for c in cases],
        ratios_map=_build_ratios_map(cases),
    )
    result = await screener.screen(req)

    scores = [
        e.composite_score
        for e in result.resultats
        if e.erreur is None and e.composite_score is not None
    ]
    assert scores == sorted(scores, reverse=True), (
        f"Tri composite_score incorrect : {scores}"
    )


@pytest.mark.evals
async def test_golden_composite_labels_dans_ensemble_attendu():
    """Chaque composite_label est dans l'ensemble autorisé par le golden dataset."""
    cases = load_screener_golden()
    allowed_by_ticker = {
        c["ticker"]: set(c["expected"]["composite_label_allowed"]) for c in cases
    }

    screener = _make_screener_from_cases(cases)
    req = ScreenRequest(
        tickers=[c["ticker"] for c in cases],
        ratios_map=_build_ratios_map(cases),
    )
    result = await screener.screen(req)

    for entry in result.resultats:
        if entry.erreur is None and entry.composite_label is not None:
            allowed = allowed_by_ticker.get(entry.ticker, _VALID_COMPOSITE_LABELS)
            assert entry.composite_label in allowed, (
                f"{entry.ticker} : composite_label={entry.composite_label!r} "
                f"hors ensemble autorisé {allowed}"
            )


@pytest.mark.evals
async def test_golden_defensive_score_min_respecte():
    """Chaque ticker retourne un defensive_score >= defensive_score_min du dataset."""
    cases = load_screener_golden()
    score_min_by_ticker = {c["ticker"]: c["expected"]["defensive_score_min"] for c in cases}

    screener = _make_screener_from_cases(cases)
    req = ScreenRequest(
        tickers=[c["ticker"] for c in cases],
        ratios_map=_build_ratios_map(cases),
    )
    result = await screener.screen(req)

    for entry in result.resultats:
        if entry.erreur is None:
            score_min = score_min_by_ticker.get(entry.ticker, 0)
            assert entry.defensive_score is not None, (
                f"{entry.ticker} : defensive_score est None"
            )
            assert entry.defensive_score >= score_min, (
                f"{entry.ticker} : defensive_score={entry.defensive_score} < min={score_min}"
            )


@pytest.mark.evals
async def test_golden_candidats_solides_classement_au_dessus_des_rejets():
    """RY, TD, JNJ (candidats solides) se classent avant MSFT, NVDA, SHOP (rejetés Graham)."""
    cases = load_screener_golden()
    screener = _make_screener_from_cases(cases)
    req = ScreenRequest(
        tickers=[c["ticker"] for c in cases],
        ratios_map=_build_ratios_map(cases),
    )
    result = await screener.screen(req)

    rank_by_ticker = {e.ticker: i for i, e in enumerate(result.resultats)}

    candidats_forts = [t for t in ("RY", "TD", "JNJ") if t in rank_by_ticker]
    candidats_rejetes = [t for t in ("MSFT", "NVDA", "SHOP") if t in rank_by_ticker]

    for fort in candidats_forts:
        for rejete in candidats_rejetes:
            assert rank_by_ticker[fort] < rank_by_ticker[rejete], (
                f"{fort} (rang {rank_by_ticker[fort]}) devrait précéder "
                f"{rejete} (rang {rank_by_ticker[rejete]}) dans le classement screener"
            )
