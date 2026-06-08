"""Service de gestion des clés API multi-utilisateurs — Sprint 62."""
from __future__ import annotations

import hashlib
import logging
import uuid
from datetime import datetime, timezone
from uuid import UUID

import asyncpg
from pydantic import BaseModel

from app.db.tenant_context import resolve_tenant
from app.services.audit_log_service import AuditLogService, record_audit_safe

logger = logging.getLogger(__name__)


class ApiKeyRecord(BaseModel):
    id: UUID
    name: str
    role: str  # 'admin' | 'reader'
    active: bool
    created_at: datetime
    last_used_at: datetime | None
    expires_at: datetime | None
    tenant_id: UUID  # tenant propriétaire — sert à résoudre le contexte sur le chemin Bearer (E4-S3)


class ApiKeyService:
    def __init__(
        self, db_pool: asyncpg.Pool, audit_log: AuditLogService | None = None
    ) -> None:
        self._pool = db_pool
        self._audit = audit_log

    @staticmethod
    def _hash(token: str) -> str:
        return hashlib.sha256(token.encode()).hexdigest()

    @staticmethod
    def _row_to_record(row: asyncpg.Record) -> ApiKeyRecord:
        return ApiKeyRecord(
            id=row["id"],
            name=row["name"],
            role=row["role"],
            active=row["active"],
            created_at=row["created_at"],
            last_used_at=row["last_used_at"],
            expires_at=row["expires_at"],
            tenant_id=row["tenant_id"],
        )

    async def validate_key(self, token: str) -> ApiKeyRecord | None:
        key_hash = self._hash(token)
        try:
            row = await self._pool.fetchrow(
                "SELECT id, name, role, active, created_at, last_used_at, expires_at, tenant_id "
                "FROM api_keys WHERE key_hash = $1",
                key_hash,
            )
        except Exception:
            logger.exception("Erreur lors de la validation de la clé API")
            return None
        if row is None:
            return None
        record = self._row_to_record(row)
        if not record.active:
            return None
        now = datetime.now(timezone.utc)
        if record.expires_at and record.expires_at < now:
            return None
        return record

    async def create_key(
        self,
        name: str,
        role: str = "reader",
        expires_at: datetime | None = None,
        tenant_id: UUID | None = None,
    ) -> tuple[str, ApiKeyRecord]:
        # Rattache la clé au tenant courant (résolu depuis le ContextVar) si non précisé —
        # une clé créée par un admin appartient à son tenant ; défaut legacy hors contexte.
        tenant = resolve_tenant(tenant_id)
        token = str(uuid.uuid4())
        key_hash = self._hash(token)
        row = await self._pool.fetchrow(
            "INSERT INTO api_keys (name, key_hash, role, expires_at, tenant_id) "
            "VALUES ($1, $2, $3, $4, $5::uuid) "
            "RETURNING id, name, role, active, created_at, last_used_at, expires_at, tenant_id",
            name,
            key_hash,
            role,
            expires_at,
            str(tenant),
        )
        record = self._row_to_record(row)
        await record_audit_safe(
            self._audit,
            "api_key.create",
            "api_key",
            str(record.id),
            metadata={
                "name": record.name,
                "role": record.role,
                "tenant_id": str(record.tenant_id),
            },
        )
        return token, record

    async def tenant_exists(self, tenant_id: UUID) -> bool:
        """Vrai si le tenant cible existe — garde anti-violation FK avant create_key (E4-S10)."""
        row = await self._pool.fetchrow(
            "SELECT 1 FROM tenants WHERE id = $1::uuid", str(tenant_id)
        )
        return row is not None

    async def list_keys(self) -> list[ApiKeyRecord]:
        rows = await self._pool.fetch(
            "SELECT id, name, role, active, created_at, last_used_at, expires_at, tenant_id "
            "FROM api_keys ORDER BY created_at DESC"
        )
        return [self._row_to_record(r) for r in rows]

    async def revoke_key(self, key_id: UUID) -> bool:
        result = await self._pool.execute(
            "UPDATE api_keys SET active = FALSE WHERE id = $1",
            key_id,
        )
        revoked = result == "UPDATE 1"
        if revoked:
            await record_audit_safe(
                self._audit, "api_key.revoke", "api_key", str(key_id)
            )
        return revoked

    async def record_usage(self, key_id: UUID) -> None:
        await self._pool.execute(
            "UPDATE api_keys SET last_used_at = NOW() WHERE id = $1",
            key_id,
        )
