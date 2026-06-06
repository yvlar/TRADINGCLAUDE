from __future__ import annotations

import hmac
import logging
from typing import ClassVar

from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from app.utils.env import is_dev_environment

logger = logging.getLogger(__name__)


class CSRFMiddleware(BaseHTTPMiddleware):
    """
    Valide le token CSRF pour les mutations des utilisateurs authentifiés par cookie.

    Principe double-submit cookie :
    - Le serveur pose un cookie non-httpOnly `csrf_token`
    - Le client lit ce cookie et l'envoie dans le header `X-CSRF-Token`
    - Ce middleware vérifie l'égalité (même-origine garantie par SOP du navigateur)

    Exempt : méthodes safe (GET/HEAD/OPTIONS), requêtes avec Authorization Bearer,
    endpoints pré-authentification (/auth/login, /auth/register, etc.).
    """

    SAFE_METHODS: ClassVar[frozenset[str]] = frozenset({"GET", "HEAD", "OPTIONS"})

    # Endpoints pré-auth : pas de session → pas de CSRF à vérifier
    CSRF_EXEMPT_PATHS: ClassVar[set[str]] = {
        "/auth/login",
        "/auth/register",
        "/auth/forgot-password",
        "/auth/reset-password",
        "/auth/mfa/setup",
        "/auth/mfa/verify",
    }

    CSRF_EXEMPT_PREFIXES: ClassVar[tuple[str, ...]] = (
        "/healthz",
        "/docs",
        "/openapi.json",
        "/redoc",
        "/telemetry",
        "/report",
        "/ws",
    )

    async def dispatch(self, request: Request, call_next) -> Response:
        if request.method in self.SAFE_METHODS:
            return await call_next(request)

        if request.url.path in self.CSRF_EXEMPT_PATHS:
            return await call_next(request)

        if any(request.url.path.startswith(p) for p in self.CSRF_EXEMPT_PREFIXES):
            return await call_next(request)

        # Requêtes Bearer (API keys programmatiques) : pas de CSRF requis
        if request.headers.get("Authorization", "").startswith("Bearer "):
            return await call_next(request)

        # Dev/test uniquement : bypass CSRF. En production, la protection s'applique
        # même si API_KEY est vide (fail-closed) — une variable oubliée ne désarme rien.
        if is_dev_environment():
            return await call_next(request)

        csrf_cookie = request.cookies.get("csrf_token", "")
        csrf_header = request.headers.get("X-CSRF-Token", "")

        if not csrf_cookie or not csrf_header:
            return JSONResponse(
                {"detail": "Token CSRF manquant"},
                status_code=403,
            )

        # Comparaison à temps constant : évite une oracle de timing sur le token.
        if not hmac.compare_digest(csrf_cookie, csrf_header):
            logger.warning("Tentative CSRF détectée sur %s", request.url.path)
            return JSONResponse(
                {"detail": "Token CSRF invalide"},
                status_code=403,
            )

        return await call_next(request)
