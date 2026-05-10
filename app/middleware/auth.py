from __future__ import annotations

import hmac
import logging
from typing import ClassVar

from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

logger = logging.getLogger(__name__)


class BearerTokenMiddleware(BaseHTTPMiddleware):
    """
    Vérifie Authorization: Bearer <token> sur toutes les routes sauf EXEMPT_PATHS.
    Désactivé si api_key est vide (pratique pour les environnements de test).
    Utilise hmac.compare_digest pour prévenir les attaques de timing.
    """

    EXEMPT_PATHS: ClassVar[set[str]] = {"/healthz", "/docs", "/openapi.json", "/redoc"}
    EXEMPT_PREFIXES: ClassVar[tuple[str, ...]] = ("/telemetry", "/report", "/ws")

    def __init__(self, app, api_key: str) -> None:
        super().__init__(app)
        self._api_key = api_key

    async def dispatch(self, request: Request, call_next) -> Response:
        if not self._api_key:
            return await call_next(request)
        if request.url.path in self.EXEMPT_PATHS:
            return await call_next(request)
        if any(request.url.path.startswith(p) for p in self.EXEMPT_PREFIXES):
            return await call_next(request)
        auth = request.headers.get("Authorization", "")
        if not auth.startswith("Bearer "):
            return JSONResponse({"detail": "Token manquant ou invalide"}, status_code=401)
        token = auth[7:]
        if not token or not hmac.compare_digest(
            token.encode("utf-8"), self._api_key.encode("utf-8")
        ):
            return JSONResponse({"detail": "Token manquant ou invalide"}, status_code=401)
        return await call_next(request)
