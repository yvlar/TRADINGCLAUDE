from __future__ import annotations

from fastapi import APIRouter, Query, Request

from app.api.endpoints.auth import _get_current_user
from app.models.usage import UsageResponse
from app.services.usage_event_service import UsageEventService

router = APIRouter(tags=["usage"])


@router.get(
    "/usage",
    response_model=UsageResponse,
    summary="Consommation agrégée du tenant courant (E4-S5)",
)
async def get_usage(
    request: Request,
    days: int = Query(default=30, ge=1, le=365),
) -> UsageResponse:
    """Agrège `usage_events` pour le tenant authentifié (401 sinon).

    L'isolation vient de la RLS via le contexte tenant serveur (claim JWT → ContextVar →
    GUC) : aucun `tenant_id` n'est accepté en query.
    - `days` : fenêtre en jours (défaut 30, bornes 1-365 → 422)
    """
    await _get_current_user(request)
    service: UsageEventService = request.app.state.usage_event_service
    return await service.aggregate(days=days)
