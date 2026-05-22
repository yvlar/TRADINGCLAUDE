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

    Priorité de validation :
    1. Si ApiKeyService présent dans app.state → valide via table api_keys (DB)
       Fallback : clé env API_KEY acceptée comme admin implicite.
    2. Sinon → compare directement avec API_KEY env (rétrocompatibilité).

    Désactivé en mode dev si API_KEY vide ET aucun ApiKeyService (app.state).
    """

    EXEMPT_PATHS: ClassVar[set[str]] = {"/healthz", "/docs", "/openapi.json", "/redoc"}
    EXEMPT_PREFIXES: ClassVar[tuple[str, ...]] = ("/telemetry", "/report", "/ws")

    def __init__(self, app, api_key: str) -> None:
        super().__init__(app)
        self._api_key = api_key

    async def dispatch(self, request: Request, call_next) -> Response:
        if request.url.path in self.EXEMPT_PATHS:
            return await call_next(request)
        if any(request.url.path.startswith(p) for p in self.EXEMPT_PREFIXES):
            return await call_next(request)

        api_key_service = getattr(request.app.state, "api_key_service", None)

        # Mode dev : API_KEY vide → bypass total (aucune auth configurée)
        # Depuis Sprint 62, api_key_service est toujours présent — on ne teste plus is None
        if not self._api_key:
            return await call_next(request)

        auth = request.headers.get("Authorization", "")
        if not auth.startswith("Bearer "):
            return JSONResponse({"detail": "Token manquant ou invalide"}, status_code=401)
        token = auth[7:]
        if not token:
            return JSONResponse({"detail": "Token manquant ou invalide"}, status_code=401)

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

        # Pas de service DB : fallback env uniquement (comportement original)
        if not hmac.compare_digest(token.encode("utf-8"), self._api_key.encode("utf-8")):
            return JSONResponse({"detail": "Token manquant ou invalide"}, status_code=401)
        request.state.api_key_record = None
        return await call_next(request)
