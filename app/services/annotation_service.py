from __future__ import annotations

import logging

import asyncpg

from app.models.annotation import Annotation

logger = logging.getLogger(__name__)


class AnnotationService:
    """CRUD sur la table annotations PostgreSQL — une note par analysis_id."""

    def __init__(self, db_pool: asyncpg.Pool) -> None:
        self._db = db_pool

    async def upsert(self, analysis_id: str, note: str) -> Annotation:
        """Crée ou remplace l'annotation pour un analysis_id donné."""
        row = await self._db.fetchrow(
            """
            INSERT INTO annotations (analysis_id, note)
            VALUES ($1::uuid, $2)
            ON CONFLICT (analysis_id) DO UPDATE
                SET note = EXCLUDED.note,
                    updated_at = NOW()
            RETURNING
                annotation_id::text,
                analysis_id::text,
                note,
                created_at,
                updated_at
            """,
            analysis_id,
            note,
        )
        return _row_to_annotation(row)

    async def get(self, analysis_id: str) -> Annotation | None:
        """Retourne l'annotation d'une analyse ou None si absente."""
        try:
            row = await self._db.fetchrow(
                """
                SELECT
                    annotation_id::text,
                    analysis_id::text,
                    note,
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
                   a.note, a.created_at, a.updated_at
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
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )
