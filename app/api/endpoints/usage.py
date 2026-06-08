from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Query, Request

from app.api.endpoints.auth import _get_current_user
from app.db.tenant_context import get_current_tenant
from app.models.usage import UsageReportingResponse, UsageResponse
from app.services.stripe_service import StripeService
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


@router.get(
    "/usage/reporting",
    response_model=UsageReportingResponse,
    summary="État du report d'usage vers Stripe du tenant courant (E5-S2)",
)
async def get_usage_reporting(request: Request) -> UsageReportingResponse:
    """Expose le curseur de report Stripe et les événements en attente (401 si non authentifié).

    Lecture seule de l'état DB : le curseur `usage_reported_through` (table `subscriptions`,
    HORS RLS → scopé applicativement au tenant courant) et le `COUNT` des `usage_events` non
    encore poussés (`(reported_through, now]`, scopé par la RLS). Aucun appel réseau Stripe →
    **pas de 503** : sans abonnement, `reported_through=None` et `pending_events` couvre tout
    l'historique du tenant (réponse neutre plutôt que de coupler la lecture à la config Stripe).
    """
    await _get_current_user(request)
    tenant_id = get_current_tenant()
    stripe_service: StripeService = request.app.state.stripe_service
    usage_service: UsageEventService = request.app.state.usage_event_service
    reported_through = await stripe_service.get_usage_reported_through(tenant_id)
    pending_events = await usage_service.count_events_in_window(
        reported_through, datetime.now(timezone.utc)
    )
    return UsageReportingResponse(
        reported_through=reported_through, pending_events=pending_events
    )
