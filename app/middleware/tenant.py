from __future__ import annotations

from starlette.types import ASGIApp, Receive, Scope, Send

from app.db.tenant_context import reset_current_tenant, set_current_tenant


class TenantContextMiddleware:
    """Résout le tenant de la requête et le pose dans le ContextVar lu par la couche DB.

    Le tenant authentifié est extrait par `BearerTokenMiddleware` (claim JWT →
    `request.state.tenant_id`, donc `scope["state"]["tenant_id"]`) ; ici on le transfère
    au ContextVar `current_tenant`. Requêtes non authentifiées / clés API / chemins
    exemptés → `tenant_id` absent → défaut legacy (géré par `set_current_tenant`).

    ASGI pur (et non `BaseHTTPMiddleware`) délibérément : `set`/`reset` s'exécutent dans
    la MÊME tâche que l'endpoint et ses acquisitions de connexion au pool — la valeur est
    donc visible jusqu'aux écritures DB, et le `reset` en `finally` garantit zéro fuite
    inter-requêtes sous concurrence. Doit être monté en couche interne, après l'auth.
    """

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        tenant_id = scope.get("state", {}).get("tenant_id")
        token = set_current_tenant(tenant_id)
        try:
            await self.app(scope, receive, send)
        finally:
            reset_current_tenant(token)
