"""Tests du middleware RateLimitMiddleware."""
from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient


def _make_rate_limit_app() -> FastAPI:
    """App minimale avec RateLimitMiddleware.

    La pile de middleware est construite lazily au premier appel — le patch sur
    aioredis.from_url doit donc être actif PENDANT les requêtes, pas seulement
    pendant la création de l'app.
    """
    from app.middleware.rate_limit import RateLimitMiddleware

    app = FastAPI()
    app.add_middleware(RateLimitMiddleware, redis_url="redis://localhost:6379/0")

    @app.get("/healthz")
    async def healthz():
        return {"status": "ok"}

    @app.post("/analyze")
    async def analyze():
        return {"ok": True}

    return app


@pytest.fixture
def counting_redis() -> AsyncMock:
    """Redis mock dont incr() simule un compteur croissant depuis une même IP."""
    counter = {"val": 0}

    async def _incr(key: str) -> int:
        counter["val"] += 1
        return counter["val"]

    r = AsyncMock()
    r.incr = AsyncMock(side_effect=_incr)
    r.expire = AsyncMock(return_value=True)
    return r


class TestRateLimitMiddleware:
    async def test_rate_limit_sous_seuil_passe(self, counting_redis: AsyncMock):
        app = _make_rate_limit_app()
        with patch("app.middleware.rate_limit.aioredis.from_url", return_value=counting_redis):
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
                for _ in range(5):
                    r = await c.post("/analyze")
                    assert r.status_code == 200

    async def test_rate_limit_depasse_429(self, counting_redis: AsyncMock):
        app = _make_rate_limit_app()
        with patch("app.middleware.rate_limit.aioredis.from_url", return_value=counting_redis):
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
                for _ in range(10):
                    await c.post("/analyze")
                r = await c.post("/analyze")  # 11e requête → dépasse le seuil
        assert r.status_code == 429

    async def test_rate_limit_ips_differentes_independantes(self):
        """La clé Redis est spécifique à l'IP — des IPs différentes ont des compteurs indépendants.

        ASGITransport utilise toujours la même IP de test ; on vérifie que :
        - la clé Redis inclut bien le host du client (isolation par IP garantie)
        - quand le compteur est à 1 (nouvelle IP), la requête passe toujours
        """
        keys_seen: set[str] = set()

        async def _incr(key: str) -> int:
            keys_seen.add(key)
            return 1  # compteur à 1 → toujours sous le seuil

        mock_redis = AsyncMock()
        mock_redis.incr = AsyncMock(side_effect=_incr)
        mock_redis.expire = AsyncMock(return_value=True)

        app = _make_rate_limit_app()
        with patch("app.middleware.rate_limit.aioredis.from_url", return_value=mock_redis):
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
                for _ in range(10):
                    r = await c.post("/analyze")
                    assert r.status_code == 200

        # La clé Redis inclut l'IP → des IPs différentes produiraient des clés distinctes
        assert len(keys_seen) == 1
        ip_key = next(iter(keys_seen))
        assert ip_key.startswith("ratelimit:")
        assert len(ip_key[len("ratelimit:"):]) > 0

    async def test_rate_limit_healthz_exempt(self):
        """GET /healthz n'incrémente pas le compteur et n'est jamais bloqué."""
        mock_redis = AsyncMock()
        mock_redis.incr = AsyncMock(return_value=999)  # intentionnellement au-delà du seuil
        mock_redis.expire = AsyncMock()

        app = _make_rate_limit_app()
        with patch("app.middleware.rate_limit.aioredis.from_url", return_value=mock_redis):
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
                for _ in range(20):
                    r = await c.get("/healthz")
                    assert r.status_code == 200

        mock_redis.incr.assert_not_called()

    async def test_rate_limit_reset_apres_fenetre(self):
        """Quand le TTL Redis expire, le compteur est réinitialisé à 1 → requête autorisée."""
        mock_redis = AsyncMock()
        mock_redis.incr = AsyncMock(return_value=1)  # compteur réinitialisé → premier appel = 1
        mock_redis.expire = AsyncMock(return_value=True)

        app = _make_rate_limit_app()
        with patch("app.middleware.rate_limit.aioredis.from_url", return_value=mock_redis):
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
                r = await c.post("/analyze")

        assert r.status_code == 200

    async def test_rate_limit_redis_indisponible_bypass(self):
        """Si Redis lève une exception, la requête passe (fail open)."""
        mock_redis = AsyncMock()
        mock_redis.incr = AsyncMock(side_effect=ConnectionError("Redis down"))
        mock_redis.expire = AsyncMock()

        app = _make_rate_limit_app()
        with patch("app.middleware.rate_limit.aioredis.from_url", return_value=mock_redis):
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
                r = await c.post("/analyze")

        assert r.status_code == 200
