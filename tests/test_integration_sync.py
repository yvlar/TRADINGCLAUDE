"""Tests d'intégration synchrones — endpoints /analyze, /history, /metrics, /healthz, /extract."""
from __future__ import annotations

import uuid

from app.api.main import _VERSION, app
from app.orchestrator.core import HistoryEntry, HistoryResponse, MetricsResponse

TICKER_TEST = "TEST"

BODY_TEST = {
    "ticker": TICKER_TEST,
    "ratios": {
        "pe": 15.0,
        "pb": 1.5,
        "current_ratio": 2.0,
        "debt_equity": 0.30,
        "eps_growth_10y": 0.30,
        "price": 100.0,
        "book_value": 66.0,
    },
}

BODY_SANS_PB = {
    # pb manquant — pe est optionnel depuis Sprint 36, pb reste requis
    "ticker": TICKER_TEST,
    "ratios": {
        "pe": 11.0,
        "current_ratio": 2.0,
        "debt_equity": 0.30,
        "eps_growth_10y": 0.30,
        "price": 100.0,
        "book_value": 66.0,
    },
}


async def test_healthz_retourne_ok(client):
    r = await client.get("/healthz")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


async def test_healthz_contient_version(client):
    r = await client.get("/healthz")
    assert r.json()["version"] == _VERSION


async def test_analyze_graham_seulement_retourne_200(client):
    r = await client.post("/analyze", json=BODY_TEST)
    assert r.status_code == 200


async def test_analyze_coute_non_nul(client):
    r = await client.post("/analyze", json=BODY_TEST)
    assert r.status_code == 200
    assert r.json()["cost_usd"] > 0


async def test_analyze_analysis_id_est_uuid(client):
    r = await client.post("/analyze", json=BODY_TEST)
    assert r.status_code == 200
    analysis_id = r.json()["analysis_id"]
    parsed = uuid.UUID(analysis_id)
    assert str(parsed) == analysis_id


async def test_analyze_skills_applied_contient_graham(client):
    r = await client.post("/analyze", json=BODY_TEST)
    assert r.status_code == 200
    assert "graham_analysis" in r.json()["skills_applied"]


async def test_analyze_ratios_manquants_422(client):
    r = await client.post("/analyze", json=BODY_SANS_PB)
    assert r.status_code == 422


async def test_analyze_ticker_vide_422(client):
    body = {**BODY_TEST, "ticker": ""}
    r = await client.post("/analyze", json=body)
    assert r.status_code == 422


async def test_analyze_ticker_invalide_422(client):
    for ticker_invalide in ["DROP TABLE", "BNS; rm -rf", "B.NS.TO", "TOOLONGTICKERX"]:
        r = await client.post("/analyze", json={**BODY_TEST, "ticker": ticker_invalide})
        assert r.status_code == 422, f"Attendu 422 pour ticker {ticker_invalide!r}"


async def test_analyze_ticker_minuscules_accepte(client):
    """Un ticker en minuscules est normalisé automatiquement → 200 (pas 422)."""
    body = {**BODY_TEST, "ticker": "bns"}
    r = await client.post("/analyze", json=body)
    assert r.status_code == 200


async def test_history_apres_analyse(client):
    entry = HistoryEntry(
        analysis_id=str(uuid.uuid4()),
        ticker=TICKER_TEST,
        workflow="company_analysis",
        skills_applied=["graham_analysis"],
        cost_usd=0.001,
        defensive_score=5,
        graham_verdict="CANDIDAT_SOLIDE",
        earnings_verdict=None,
        created_at="2026-05-08T14:00:00+00:00",
    )
    app.state.orchestrator.get_history.return_value = HistoryResponse(
        ticker=TICKER_TEST, entries=[entry], next_before=None
    )
    r = await client.get(f"/history?ticker={TICKER_TEST}")
    assert r.status_code == 200
    assert len(r.json()["entries"]) > 0


async def test_history_pagination_cursor(client):
    app.state.orchestrator.get_history.return_value = HistoryResponse(
        ticker=TICKER_TEST,
        entries=[],
        next_before="2026-05-07T14:00:00+00:00",
    )
    r = await client.get(
        f"/history?ticker={TICKER_TEST}&before=2026-05-08T14%3A00%3A00%2B00%3A00"
    )
    assert r.status_code == 200
    assert "next_before" in r.json()


async def test_metrics_retourne_periode(client):
    app.state.orchestrator.get_metrics.return_value = MetricsResponse(
        period_days=7,
        total_analyses=3,
        total_cost_usd=0.009,
        avg_cost_per_analysis=0.003,
        cache_hit_ratio_avg=0.70,
        top_tickers=[],
        skills_usage={},
    )
    r = await client.get("/metrics?days=7")
    assert r.status_code == 200
    assert r.json()["period_days"] == 7


async def test_metrics_total_non_negatif(client):
    app.state.orchestrator.get_metrics.return_value = MetricsResponse(
        period_days=30,
        total_analyses=0,
        total_cost_usd=0.0,
        avg_cost_per_analysis=0.0,
        cache_hit_ratio_avg=0.0,
        top_tickers=[],
        skills_usage={},
    )
    r = await client.get("/metrics?days=30")
    assert r.status_code == 200
    assert r.json()["total_analyses"] >= 0


async def test_extract_endpoint_existe(client):
    """GET /extract → 404 attendu (mock yahoo retourne 404 pour ticker inconnu)."""
    r = await client.get(f"/extract?ticker={TICKER_TEST}")
    assert r.status_code in {200, 404, 422}
