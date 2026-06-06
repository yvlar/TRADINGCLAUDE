"""Service du journal d'audit append-only — E2-S3 (conformité Loi 25)."""
from __future__ import annotations

import json
import logging
from datetime import datetime
from typing import Any
from uuid import UUID

import asyncpg
from pydantic import BaseModel

logger = logging.getLogger(__name__)


class AuditLogEntry(BaseModel):
    id: UUID
    tenant_id: UUID | None
    user_id: UUID | None
    action: str
    cible_type: str
    cible_id: str | None
    metadata: dict[str, Any]
    created_at: datetime


class AuditLogService:
    """Journal d'audit append-only — INSERT pur, aucun UPDATE ni DELETE applicatif."""

    def __init__(self, db_pool: asyncpg.Pool) -> None:
        self._db = db_pool

    async def record(
        self,
        action: str,
        cible_type: str,
        cible_id: str | None,
        user_id: UUID | str | None = None,
        tenant_id: UUID | str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> AuditLogEntry:
        """Insère une entrée d'audit et la retourne (append-only)."""
        row = await self._db.fetchrow(
            """
            INSERT INTO audit_log (tenant_id, user_id, action, cible_type, cible_id, metadata)
            VALUES ($1::uuid, $2::uuid, $3, $4, $5, $6::jsonb)
            RETURNING id, tenant_id, user_id, action, cible_type, cible_id, metadata, created_at
            """,
            str(tenant_id) if tenant_id is not None else None,
            str(user_id) if user_id is not None else None,
            action,
            cible_type,
            cible_id,
            json.dumps(metadata or {}),
        )
        return _row_to_entry(row)

    async def list_recent(self, limit: int = 50) -> list[AuditLogEntry]:
        """Retourne les dernières entrées d'audit, plus récentes d'abord."""
        rows = await self._db.fetch(
            """
            SELECT id, tenant_id, user_id, action, cible_type, cible_id, metadata, created_at
            FROM audit_log
            ORDER BY created_at DESC
            LIMIT $1
            """,
            limit,
        )
        return [_row_to_entry(r) for r in rows]


def _row_to_entry(row: asyncpg.Record) -> AuditLogEntry:
    raw_meta = row["metadata"]
    # asyncpg renvoie le JSONB sous forme de texte sauf codec dédié.
    metadata = json.loads(raw_meta) if isinstance(raw_meta, str) else (raw_meta or {})
    return AuditLogEntry(
        id=row["id"],
        tenant_id=row["tenant_id"],
        user_id=row["user_id"],
        action=row["action"],
        cible_type=row["cible_type"],
        cible_id=row["cible_id"],
        metadata=metadata,
        created_at=row["created_at"],
    )


async def record_audit_safe(
    audit: AuditLogService | None,
    action: str,
    cible_type: str,
    cible_id: str | None,
    **kwargs: Any,
) -> None:
    """Trace best-effort — n'avorte jamais la mutation métier si l'audit échoue."""
    if audit is None:
        return
    try:
        await audit.record(action=action, cible_type=cible_type, cible_id=cible_id, **kwargs)
    except Exception:
        logger.exception("Échec d'écriture du journal d'audit : %s/%s", action, cible_type)
