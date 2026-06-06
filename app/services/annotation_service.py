from __future__ import annotations

import logging
from uuid import UUID

import asyncpg

from app.models.annotation import Annotation
from app.models.tenant import LEGACY_TENANT_ID
from app.services.audit_log_service import AuditLogService, record_audit_safe

logger = logging.getLogger(__name__)


class AnnotationService:
    """CRUD sur la table annotations PostgreSQL — une note par analysis_id."""

    def __init__(
        self, db_pool: asyncpg.Pool, audit_log: AuditLogService | None = None
    ) -> None:
        self._db = db_pool
        self._audit = audit_log

    async def upsert(
        self,
        analysis_id: str,
        note: str,
        tags: list[str] | None = None,
        tenant_id: UUID | None = None,
    ) -> Annotation:
        """Crée ou remplace l'annotation (note + tags) pour un analysis_id donné."""
        # Défaut legacy tant que le tenant n'est pas threadé (E3-S4). Le tenant n'est
        # posé qu'à l'INSERT : ré-annoter ne déplace pas une annotation de tenant.
        tenant = tenant_id or LEGACY_TENANT_ID
        row = await self._db.fetchrow(
            """
            INSERT INTO annotations (analysis_id, note, tags, tenant_id)
            VALUES ($1::uuid, $2, $3::text[], $4)
            ON CONFLICT (analysis_id) DO UPDATE
                SET note = EXCLUDED.note,
                    tags = EXCLUDED.tags,
                    updated_at = NOW()
            RETURNING
                annotation_id::text,
                analysis_id::text,
                note,
                tags,
                created_at,
                updated_at
            """,
            analysis_id,
            note,
            tags or [],
            tenant,
        )
        annotation = _row_to_annotation(row)
        await record_audit_safe(
            self._audit,
            "annotation.upsert",
            "annotation",
            annotation.analysis_id,
            metadata={"tags": annotation.tags},
        )
        return annotation

    async def get(self, analysis_id: str) -> Annotation | None:
        """Retourne l'annotation d'une analyse ou None si absente."""
        try:
            row = await self._db.fetchrow(
                """
                SELECT
                    annotation_id::text,
                    analysis_id::text,
                    note,
                    tags,
                    created_at,
                    updated_at
                FROM annotations
                WHERE analysis_id = $1::uuid
                """,
                analysis_id,
            )
        except Exception:
            logger.exception("Erreur lors de la récupération de l'annotation %s", analysis_id)
            return None
        return _row_to_annotation(row) if row else None

    async def get_all_with_ticker(self) -> list[dict]:
        """Retourne toutes les annotations avec le ticker depuis analysis_history."""
        rows = await self._db.fetch("""
            SELECT a.annotation_id::text, a.analysis_id::text,
                   h.ticker,
                   a.note, a.tags, a.created_at, a.updated_at
            FROM annotations a
            LEFT JOIN analysis_history h USING (analysis_id)
            ORDER BY a.updated_at DESC
        """)
        return [dict(row) for row in rows]


def _row_to_annotation(row) -> Annotation:
    return Annotation(
        annotation_id=str(row["annotation_id"]),
        analysis_id=str(row["analysis_id"]),
        note=row["note"],
        tags=list(row["tags"]) if row["tags"] is not None else [],
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )
