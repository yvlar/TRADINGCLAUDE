"""Tests d'intégration — les réponses 500 ne fuitent pas str(exc) (Sprint 125)."""
from __future__ import annotations

from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from app.api.main import app, global_exception_handler

_SECRET_LEAK = "duplicate key value violates unique constraint users_email_key"

_BODY = {
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


class TestGlobalExceptionHandler:
    async def test_500_body_generique_sans_str_exc(self):
        boom_app = FastAPI()
        boom_app.add_exception_handler(Exception, global_exception_handler)

        @boom_app.get("/boom")
        async def boom():
            raise RuntimeError(_SECRET_LEAK)

        async with AsyncClient(
            transport=ASGITransport(app=boom_app, raise_app_exceptions=False),
            base_url="http://test",
        ) as c:
            r = await c.get("/boom")

        assert r.status_code == 500
        body = r.json()
        assert _SECRET_LEAK not in r.text
        assert body["error"] == "Erreur interne"
        assert "correlation_id" in body
        assert "RuntimeError" not in r.text


class TestAnalyzeErrorSanitization:
    async def test_analyze_500_ne_fuite_pas_le_detail(self, client: AsyncClient):
        app.state.orchestrator.run_company_analysis.side_effect = RuntimeError(_SECRET_LEAK)
        try:
            r = await client.post("/analyze", json=_BODY)
        finally:
            app.state.orchestrator.run_company_analysis.side_effect = None

        assert r.status_code == 500
        assert _SECRET_LEAK not in r.text
        assert "correlation_id" in r.json()["detail"]


class TestScreenErrorSanitization:
    async def test_screen_500_ne_fuite_pas_le_detail(self, client: AsyncClient):
        app.state.screener.screen.side_effect = RuntimeError(_SECRET_LEAK)
        try:
            r = await client.post("/screen", json={"tickers": ["MSFT", "TD"]})
        finally:
            app.state.screener.screen.side_effect = None

        assert r.status_code == 500
        assert _SECRET_LEAK not in r.text
        assert "correlation_id" in r.json()["detail"]
