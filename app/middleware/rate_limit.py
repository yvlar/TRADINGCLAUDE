from __future__ import annotations

import logging
from collections.abc import Iterable
from typing import ClassVar

import redis.asyncio as aioredis
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from app.utils.client_ip import resolve_client_ip, trusted_proxies_from_env

logger = logging.getLogger(__name__)


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Limite à 10 requêtes par minute par IP via Redis (sliding window approximatif).
    Désactivé silencieusement si Redis est indisponible.
    Clé Redis : ratelimit:{client_ip} — TTL 60s, incrémenté à chaque requête.

    L'IP est résolue via X-Forwarded-For uniquement derrière un proxy de confiance
    (TRUSTED_PROXY_IPS) — sinon l'en-tête est ignoré pour empêcher l'usurpation.
    """

    EXEMPT_PATHS: ClassVar[set[str]] = {"/healthz"}
    MAX_REQUESTS: ClassVar[int] = 10
    WINDOW_S: ClassVar[int] = 60

    def __init__(
        self, app, redis_url: str, trusted_proxies: Iterable[str] | None = None
    ) -> None:
        super().__init__(app)
        self._redis: aioredis.Redis = aioredis.from_url(redis_url, decode_responses=True)
        self._trusted_proxies = (
            frozenset(trusted_proxies)
            if trusted_proxies is not None
            else trusted_proxies_from_env()
        )

    async def dispatch(self, request: Request, call_next) -> Response:
        if request.url.path in self.EXEMPT_PATHS:
            return await call_next(request)

        client_ip = resolve_client_ip(request, self._trusted_proxies)
        key = f"ratelimit:{client_ip}"

        try:
            count = await self._redis.incr(key)
            if count == 1:
                await self._redis.expire(key, self.WINDOW_S)
        except Exception:
            logger.warning("Redis indisponible pour rate limiting — requête autorisée")
            return await call_next(request)

        if count > self.MAX_REQUESTS:
            return JSONResponse(
                {"detail": "Trop de requêtes — réessayez dans 60 secondes"},
                status_code=429,
            )

        return await call_next(request)
