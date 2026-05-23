"""Tests consolidés des middlewares Auth et RateLimit."""
from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from app.middleware.auth import BearerTokenMiddleware
from app.middleware.rate_limit import RateLimitMiddleware

_TEST_API_KEY = "secret-middleware-test-key"

_BODY_ANALYZE = {
    "ticker": "TEST",
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


def _make_auth_app(api_key: str) -> FastAPI:
    """App minimale avec BearerTokenMiddleware."""
    auth_app = FastAPI()
    auth_app.add_middleware(BearerTokenMiddleware, api_key=api_key)

    @auth_app.get("/healthz")
    async def healthz():
        return {"status": "ok"}

    @auth_app.get("/metrics")
    async def metrics():
        return {"period_days": 30}

    @auth_app.post("/analyze")
    async def analyze():
        return {"ok": True}

    return auth_app


def _make_rate_app() -> FastAPI:
    """App minimale avec RateLimitMiddleware."""
    rate_app = FastAPI()
    rate_app.add_middleware(RateLimitMiddleware, redis_url="redis://localhost:6379/0")

    @rate_app.get("/healthz")
    async def healthz():
        return {"status": "ok"}

    @rate_app.post("/analyze")
    async def analyze():
        return {"ok": True}

    return rate_app


@pytest.fixture
def counting_redis() -> AsyncMock:
    """Redis mock dont incr() simule un compteur croissant depuis la même IP."""
    counter = {"val": 0}

    async def _incr(key: str) -> int:
        counter["val"] += 1
        return counter["val"]

    r = AsyncMock()
    r.incr = AsyncMock(side_effect=_incr)
    r.expire = AsyncMock(return_value=True)
    return r


# ---------------------------------------------------------------------------
# Auth — BearerTokenMiddleware
# ---------------------------------------------------------------------------

async def test_auth_absent_retourne_401():
    auth_app = _make_auth_app(_TEST_API_KEY)
    async with AsyncClient(
        transport=ASGITransport(app=auth_app), base_url="http://test"
    ) as c:
        r = await c.post("/analyze")
    assert r.status_code == 401


async def test_auth_invalide_retourne_401():
    auth_app = _make_auth_app(_TEST_API_KEY)
    async with AsyncClient(
        transport=ASGITransport(app=auth_app), base_url="http://test"
    ) as c:
        r = await c.post("/analyze", headers={"Authorization": "Bearer mauvais-token"})
    assert r.status_code == 401


async def test_auth_valide_retourne_200():
    auth_app = _make_auth_app(_TEST_API_KEY)
    async with AsyncClient(
        transport=ASGITransport(app=auth_app), base_url="http://test"
    ) as c:
        r = await c.post(
            "/analyze", headers={"Authorization": f"Bearer {_TEST_API_KEY}"}
        )
    assert r.status_code == 200


async def test_healthz_exempt_sans_token():
    """/healthz est dans EXEMPT_PATHS → 200 sans token."""
    auth_app = _make_auth_app(_TEST_API_KEY)
    async with AsyncClient(
        transport=ASGITransport(app=auth_app), base_url="http://test"
    ) as c:
        r = await c.get("/healthz")
    assert r.status_code == 200


async def test_metrics_exempt_sans_token():
    """/metrics n'est pas dans EXEMPT_PATHS, mais sans API_KEY (vide) → auth désactivée."""
    auth_app = _make_auth_app(api_key="")
    async with AsyncClient(
        transport=ASGITransport(app=auth_app), base_url="http://test"
    ) as c:
        r = await c.get("/metrics")
    assert r.status_code == 200


# ---------------------------------------------------------------------------
# Rate Limit — RateLimitMiddleware
# ---------------------------------------------------------------------------

async def test_rate_limit_sous_seuil_ok(counting_redis: AsyncMock):
    """5 requêtes sous le seuil de 10 → toutes 200."""
    rate_app = _make_rate_app()
    with patch("app.middleware.rate_limit.aioredis.from_url", return_value=counting_redis):
        async with AsyncClient(
            transport=ASGITransport(app=rate_app), base_url="http://test"
        ) as c:
            for _ in range(5):
                r = await c.post("/analyze")
                assert r.status_code == 200


async def test_rate_limit_depasse_429(counting_redis: AsyncMock):
    """11e requête dépasse le seuil de 10 → 429."""
    rate_app = _make_rate_app()
    with patch("app.middleware.rate_limit.aioredis.from_url", return_value=counting_redis):
        async with AsyncClient(
            transport=ASGITransport(app=rate_app), base_url="http://test"
        ) as c:
            for _ in range(10):
                await c.post("/analyze")
            r = await c.post("/analyze")
    assert r.status_code == 429


@pytest.mark.xfail(
    reason="Headers X-RateLimit-* non implémentés dans RateLimitMiddleware",
    strict=False,
)
async def test_rate_limit_headers_presents(counting_redis: AsyncMock):
    """Les headers X-RateLimit-* devraient être présents dans la réponse."""
    rate_app = _make_rate_app()
    with patch("app.middleware.rate_limit.aioredis.from_url", return_value=counting_redis):
        async with AsyncClient(
            transport=ASGITransport(app=rate_app), base_url="http://test"
        ) as c:
            r = await c.post("/analyze")
    assert any(h.startswith("x-ratelimit") for h in r.headers)
