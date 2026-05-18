"""Endpoints admin pour la gestion des clés API — Sprint 62."""
from __future__ import annotations

import logging
import os
from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel

from app.services.api_key_service import ApiKeyRecord, ApiKeyService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/admin", tags=["admin"])


class CreateKeyRequest(BaseModel):
    name: str
    role: str = "reader"
    expires_at: datetime | None = None


class CreateKeyResponse(BaseModel):
    token: str  # Seul moment où le token clair est exposé — ne jamais stocker
    key: ApiKeyRecord


class RevokeKeyResponse(BaseModel):
    revoked: bool


def _get_api_key_service(request: Request) -> ApiKeyService:
    service = getattr(request.app.state, "api_key_service", None)
    if service is None:
        raise HTTPException(status_code=503, detail="ApiKeyService non disponible")
    return service


def _require_admin(request: Request) -> ApiKeyRecord | None:
    """Vérifie que la requête est authentifiée avec un rôle admin ou la clé env."""
    api_key_service = getattr(request.app.state, "api_key_service", None)

    # Mode dev complet : aucune clé env ET aucun service DB → bypass admin check
    if not os.environ.get("API_KEY", "") and api_key_service is None:
        return None

    try:
        record = request.state.api_key_record
    except AttributeError:
        raise HTTPException(status_code=401, detail="Token manquant ou invalide")

    if record is None:
        return None  # clé env → admin implicite

    if record.role != "admin":
        raise HTTPException(status_code=403, detail="Accès admin requis")
    return record


@router.post(
    "/keys",
    response_model=CreateKeyResponse,
    status_code=201,
    summary="Créer une nouvelle clé API",
)
async def create_key(
    body: CreateKeyRequest,
    request: Request,
    _admin: ApiKeyRecord | None = Depends(_require_admin),
    service: ApiKeyService = Depends(_get_api_key_service),
) -> CreateKeyResponse:
    if body.role not in ("admin", "reader"):
        raise HTTPException(status_code=422, detail="role doit être 'admin' ou 'reader'")
    token, record = await service.create_key(
        name=body.name, role=body.role, expires_at=body.expires_at
    )
    logger.info("Clé API créée : name=%s role=%s id=%s", record.name, record.role, record.id)
    return CreateKeyResponse(token=token, key=record)


@router.get(
    "/keys",
    response_model=list[ApiKeyRecord],
    summary="Lister toutes les clés API",
)
async def list_keys(
    _admin: ApiKeyRecord | None = Depends(_require_admin),
    service: ApiKeyService = Depends(_get_api_key_service),
) -> list[ApiKeyRecord]:
    return await service.list_keys()


@router.delete(
    "/keys/{key_id}",
    response_model=RevokeKeyResponse,
    summary="Révoquer une clé API",
)
async def revoke_key(
    key_id: UUID,
    _admin: ApiKeyRecord | None = Depends(_require_admin),
    service: ApiKeyService = Depends(_get_api_key_service),
) -> RevokeKeyResponse:
    revoked = await service.revoke_key(key_id)
    if not revoked:
        raise HTTPException(status_code=404, detail="Clé API introuvable")
    logger.info("Clé API révoquée : id=%s", key_id)
    return RevokeKeyResponse(revoked=True)
