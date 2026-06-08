"""Endpoints admin pour la gestion des clés API — Sprint 62."""
from __future__ import annotations

import logging
import os
from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel

from app.db.tenant_context import get_current_tenant
from app.services.api_key_service import ApiKeyRecord, ApiKeyService
from app.services.audit_log_service import AuditLogEntry, AuditLogService
from app.utils.env import is_dev_environment

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/admin", tags=["admin"])


class CreateKeyRequest(BaseModel):
    name: str
    role: str = "reader"
    expires_at: datetime | None = None
    # Tenant propriétaire de la clé ; absent → tenant courant (rétrocompatible).
    tenant_id: UUID | None = None


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


def _get_audit_log_service(request: Request) -> AuditLogService:
    service = getattr(request.app.state, "audit_log_service", None)
    if service is None:
        raise HTTPException(status_code=503, detail="AuditLogService non disponible")
    return service


def _is_jwt_user(request: Request) -> bool:
    """Vrai si la requête vient du chemin cookie JWT (qui pose `user_id`), pas d'une clé Bearer/env."""
    return getattr(request.state, "user_id", None) is not None


def _require_admin(request: Request) -> ApiKeyRecord | None:
    """Vérifie que la requête est authentifiée avec un rôle admin ou la clé env."""
    api_key_service = getattr(request.app.state, "api_key_service", None)

    # Dev/test uniquement : aucune clé env ET aucun service DB → bypass admin check.
    # En production, l'absence de configuration ne désarme PAS le contrôle (fail-closed).
    if (
        not os.environ.get("API_KEY", "")
        and api_key_service is None
        and is_dev_environment()
    ):
        return None

    try:
        record = request.state.api_key_record
    except AttributeError:
        raise HTTPException(status_code=401, detail="Token manquant ou invalide")

    if record is None:
        # record None = clé env (admin implicite) OU utilisateur JWT ; pour le JWT on exige le
        # rôle admin, sinon tout utilisateur web (même reader) atteindrait l'admin (fail-open).
        if _is_jwt_user(request) and getattr(request.state, "user_role", "reader") != "admin":
            raise HTTPException(status_code=403, detail="Accès admin requis")
        return None

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
    if body.tenant_id is not None:
        # Verrou cross-tenant : seule la clé env (sans user_id) est exemptée — le chemin JWT pose
        # aussi api_key_record=None, donc un admin web ne provisionne que pour son tenant courant.
        is_env_superadmin = _admin is None and not _is_jwt_user(request)
        if not is_env_superadmin and body.tenant_id != get_current_tenant():
            raise HTTPException(
                status_code=403, detail="Création de clé limitée au tenant courant"
            )
        # Vérifie l'existence du tenant cible AVANT l'INSERT — une FK violée donnerait un 500.
        if not await service.tenant_exists(body.tenant_id):
            raise HTTPException(status_code=404, detail="Tenant introuvable")
    token, record = await service.create_key(
        name=body.name,
        role=body.role,
        expires_at=body.expires_at,
        tenant_id=body.tenant_id,
    )
    logger.info(
        "Clé API créée : name=%s role=%s id=%s tenant=%s",
        record.name,
        record.role,
        record.id,
        record.tenant_id,
    )
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


@router.get(
    "/audit-log",
    response_model=list[AuditLogEntry],
    summary="Lister les dernières entrées du journal d'audit",
)
async def list_audit_log(
    request: Request,
    limit: int = Query(50, ge=1, le=200),
    _admin: ApiKeyRecord | None = Depends(_require_admin),
    service: AuditLogService = Depends(_get_audit_log_service),
) -> list[AuditLogEntry]:
    return await service.list_recent(limit)
