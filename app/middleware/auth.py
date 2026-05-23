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
    Vérifie Authorization: Bearer <token> ou cookie access_token (JWT) sur toutes les routes.

    Priorité de validation :
    1. Paths exempts → pass-through immédiat.
    2. Mode dev (API_KEY vide) → bypass total.
    3. Authorization: Bearer → validation via ApiKeyService (table api_keys) ou clé env.
    4. Cookie access_token → validation JWT via AuthTokenService (web users).
    5. Aucun des deux → 401.

    Rétrocompatibilité : les clés API programmatiques (Bearer) fonctionnent inchangées.
    """

    EXEMPT_PATHS: ClassVar[set[str]] = {
        "/healthz",
        "/docs",
        "/openapi.json",
        "/redoc",
        "/auth/register",
        "/auth/login",
        "/auth/forgot-password",
        "/auth/reset-password",
        "/auth/mfa/setup",
        "/auth/mfa/verify",
    }
    EXEMPT_PREFIXES: ClassVar[tuple[str, ...]] = ("/telemetry", "/report", "/ws")

    def __init__(self, app, api_key: str) -> None:
        super().__init__(app)
        self._api_key = api_key

    async def dispatch(self, request: Request, call_next) -> Response:
        if request.url.path in self.EXEMPT_PATHS:
            return await call_next(request)
        if any(request.url.path.startswith(p) for p in self.EXEMPT_PREFIXES):
            return await call_next(request)

        # Mode dev : API_KEY vide → bypass total (aucune auth configurée)
        if not self._api_key:
            return await call_next(request)

        auth = request.headers.get("Authorization", "")

        # --- Chemin 1 : Bearer token (API keys programmatiques — inchangé) ---
        if auth.startswith("Bearer "):
            token = auth[7:]
            if not token:
                return JSONResponse({"detail": "Token manquant ou invalide"}, status_code=401)

            api_key_service = getattr(request.app.state, "api_key_service", None)
            if api_key_service is not None:
                record = await api_key_service.validate_key(token)
                if record is not None:
                    request.state.api_key_record = record
                    try:
                        await api_key_service.record_usage(record.id)
                    except Exception:
                        logger.warning("Impossible d'enregistrer l'usage de la clé %s", record.id)
                    return await call_next(request)

                # Fallback : clé env comme admin implicite
                if self._api_key and hmac.compare_digest(
                    token.encode("utf-8"), self._api_key.encode("utf-8")
                ):
                    request.state.api_key_record = None
                    return await call_next(request)

                return JSONResponse({"detail": "Token manquant ou invalide"}, status_code=401)

            # Pas de service DB : fallback env uniquement
            if not hmac.compare_digest(token.encode("utf-8"), self._api_key.encode("utf-8")):
                return JSONResponse({"detail": "Token manquant ou invalide"}, status_code=401)
            request.state.api_key_record = None
            return await call_next(request)

        # --- Chemin 2 : Cookie JWT (web users) ---
        access_token_cookie = request.cookies.get("access_token")
        if access_token_cookie:
            auth_token_service = getattr(request.app.state, "auth_token_service", None)
            if auth_token_service is not None:
                payload = auth_token_service.decode_access_token(access_token_cookie)
                if payload:
                    jti = payload.get("jti", "")
                    if jti and await auth_token_service.is_jti_blacklisted(jti):
                        return JSONResponse({"detail": "Session révoquée"}, status_code=401)
                    # Expose le contexte utilisateur pour les endpoints qui en ont besoin
                    request.state.user_id = payload.get("sub")
                    request.state.user_role = payload.get("role", "reader")
                    request.state.user_email = payload.get("email", "")
                    request.state.api_key_record = None
                    return await call_next(request)

        return JSONResponse({"detail": "Token manquant ou invalide"}, status_code=401)
