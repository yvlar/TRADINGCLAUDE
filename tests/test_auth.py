"""Tests du middleware BearerTokenMiddleware."""
from __future__ import annotations

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from app.middleware.auth import BearerTokenMiddleware

_TEST_API_KEY = "secret-test-key"
_BODY_BNS = {
    "ticker": "BNS",
    "ratios": {
        "pe": 11.0,
        "pb": 1.3,
        "current_ratio": None,
        "debt_equity": 0.45,
        "eps_growth_10y": 0.27,
        "price": 80.0,
        "book_value": 61.5,
    },
}


def _make_auth_app(api_key: str) -> FastAPI:
    """App minimale avec BearerTokenMiddleware pour tests d'isolation."""
    app = FastAPI()
    app.add_middleware(BearerTokenMiddleware, api_key=api_key)

    @app.get("/healthz")
    async def healthz():
        return {"status": "ok"}

    @app.get("/docs-test")
    async def docs_test():
        return {"ok": True}

    @app.post("/analyze")
    async def analyze():
        return {"ok": True}

    @app.get("/history")
    async def history():
        return {"ok": True}

    return app


@pytest.fixture
def auth_app() -> FastAPI:
    return _make_auth_app(_TEST_API_KEY)


class TestBearerTokenMiddleware:
    async def test_auth_missing_token_401(self, auth_app: FastAPI):
        async with AsyncClient(transport=ASGITransport(app=auth_app), base_url="http://test") as c:
            r = await c.post("/analyze")
        assert r.status_code == 401

    async def test_auth_invalid_token_401(self, auth_app: FastAPI):
        async with AsyncClient(transport=ASGITransport(app=auth_app), base_url="http://test") as c:
            r = await c.post("/analyze", headers={"Authorization": "Bearer mauvais-token"})
        assert r.status_code == 401

    async def test_auth_valid_token_passe(self, auth_app: FastAPI):
        async with AsyncClient(transport=ASGITransport(app=auth_app), base_url="http://test") as c:
            r = await c.post("/analyze", headers={"Authorization": f"Bearer {_TEST_API_KEY}"})
        assert r.status_code != 401

    async def test_auth_healthz_exempt_sans_token(self, auth_app: FastAPI):
        async with AsyncClient(transport=ASGITransport(app=auth_app), base_url="http://test") as c:
            r = await c.get("/healthz")
        assert r.status_code == 200

    async def test_auth_docs_exempt_sans_token(self):
        """Les routes /docs et /openapi.json sont exemptées même sans token."""
        app = _make_auth_app(_TEST_API_KEY)

        @app.get("/openapi.json")
        async def openapi():
            return {}

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            r = await c.get("/openapi.json")
        assert r.status_code != 401

    async def test_auth_token_vide_401(self, auth_app: FastAPI):
        async with AsyncClient(transport=ASGITransport(app=auth_app), base_url="http://test") as c:
            r = await c.post("/analyze", headers={"Authorization": "Bearer "})
        assert r.status_code == 401

    async def test_auth_desactive_si_api_key_vide(self):
        """Si api_key est vide, le middleware laisse passer toutes les requêtes."""
        app = _make_auth_app(api_key="")
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            r = await c.post("/analyze")
        assert r.status_code == 200

    async def test_auth_detail_message_correct(self, auth_app: FastAPI):
        async with AsyncClient(transport=ASGITransport(app=auth_app), base_url="http://test") as c:
            r = await c.post("/analyze")
        assert r.json()["detail"] == "Token manquant ou invalide"
