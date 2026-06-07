"""Tests d'intégration des quotas sur /analyze, /analyze-stream et /screen (E4-S2).

Le `client` fixture monte un `quota_service` mocké autorisant par défaut ; chaque test de
dépassement surcharge son comportement pour prouver le 429 et la non-consommation au cache hit.
"""
from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from app.api.main import app
from app.orchestrator.core import AnalyzeResponse
from app.services.quota_service import QuotaExceededError

_VALID_BODY = {
    "ticker": "MSFT",
    "ratios": {
        "pe": 34.2,
        "pb": 12.1,
        "current_ratio": 1.34,
        "debt_equity": 0.28,
        "eps_growth_total": 0.85,
        "price": 420.0,
        "book_value": 35.0,
    },
}


def _quota_error(*, retry_after_s: int | None = 3600) -> QuotaExceededError:
    return QuotaExceededError(
        "Quota mensuel atteint (plan free : 50/50 analyses).",
        plan="free",
        used=50,
        limit=50,
        retry_after_s=retry_after_s,
    )


@pytest.mark.asyncio
async def test_analyze_au_dela_du_quota_429(client):
    app.state.quota_service.check = AsyncMock(side_effect=_quota_error())
    resp = await client.post("/analyze", json=_VALID_BODY)
    assert resp.status_code == 429
    assert "Quota mensuel atteint" in resp.json()["detail"]
    assert resp.headers.get("retry-after") == "3600"


@pytest.mark.asyncio
async def test_analyze_sous_quota_200_et_incremente(client):
    app.state.quota_service.check = AsyncMock(return_value=None)
    app.state.quota_service.increment = AsyncMock(return_value=None)
    resp = await client.post("/analyze", json=_VALID_BODY)
    assert resp.status_code == 200
    # Analyse fraîche (cost_usd > 0 dans la réponse mockée) → le quota est consommé.
    app.state.quota_service.increment.assert_awaited_once()


@pytest.mark.asyncio
async def test_analyze_cache_hit_ne_consomme_pas(client, analyze_response_msft: AnalyzeResponse):
    """Une réponse à cost_usd=0 (cache hit) n'incrémente jamais le quota."""
    cached = analyze_response_msft.model_copy(update={"cost_usd": 0.0})
    app.state.orchestrator.run_company_analysis = AsyncMock(return_value=cached)
    app.state.quota_service.check = AsyncMock(return_value=None)
    app.state.quota_service.increment = AsyncMock(return_value=None)
    resp = await client.post("/analyze", json=_VALID_BODY)
    assert resp.status_code == 200
    app.state.quota_service.increment.assert_not_awaited()


@pytest.mark.asyncio
async def test_analyze_stream_au_dela_du_quota_429(client):
    """Le dépassement renvoie un vrai 429 HTTP avant l'ouverture du flux SSE."""
    app.state.quota_service.check = AsyncMock(side_effect=_quota_error())
    resp = await client.post("/analyze-stream", json=_VALID_BODY)
    assert resp.status_code == 429
    assert "Quota mensuel atteint" in resp.json()["detail"]


@pytest.mark.asyncio
async def test_screen_au_dela_de_la_borne_plan_429(client):
    app.state.quota_service.check_screener_size = AsyncMock(
        side_effect=QuotaExceededError(
            "Liste de 10 tickers au-delà de la borne du plan free (max 5).",
            plan="free",
            used=10,
            limit=5,
            retry_after_s=None,
        )
    )
    resp = await client.post("/screen", json={"tickers": ["A", "B", "C"]})
    assert resp.status_code == 429
    assert "borne du plan" in resp.json()["detail"]
    # Borne de taille (pas temporelle) → pas d'en-tête Retry-After.
    assert "retry-after" not in resp.headers


@pytest.mark.asyncio
async def test_screen_sous_la_borne_plan_200(client):
    app.state.quota_service.check_screener_size = AsyncMock(return_value=None)
    resp = await client.post("/screen", json={"tickers": ["MSFT"]})
    assert resp.status_code == 200
