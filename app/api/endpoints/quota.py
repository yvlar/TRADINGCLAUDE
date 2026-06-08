from __future__ import annotations

from dataclasses import asdict

from fastapi import APIRouter, Request

from app.api.endpoints.auth import _get_current_user
from app.models.quota import QuotaStatusResponse
from app.services.quota_service import QuotaService

router = APIRouter(tags=["quota"])


@router.get(
    "/quota",
    response_model=QuotaStatusResponse,
    summary="État du quota mensuel d'analyses du tenant courant (E5-S6)",
)
async def get_quota(request: Request) -> QuotaStatusResponse:
    """Expose le quota mensuel d'analyses du tenant authentifié (401 sinon) — lecture seule.

    Le tenant vient du contexte serveur (claim JWT → ContextVar) : aucun `tenant_id` accepté en
    query. `QuotaService.read_status` est fail-open (plan non résolu ou Redis indisponible →
    réponse neutre) → le header ne casse jamais ; et n'incrémente jamais le compteur Redis.
    """
    await _get_current_user(request)
    quota_service: QuotaService = request.app.state.quota_service
    status = await quota_service.read_status()
    # QuotaStatus (dataclass) et QuotaStatusResponse partagent les mêmes champs : pas de
    # recopie manuelle à maintenir si un champ s'ajoute au quota.
    return QuotaStatusResponse(**asdict(status))
