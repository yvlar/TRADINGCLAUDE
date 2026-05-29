from __future__ import annotations

import json
import logging

import asyncpg

logger = logging.getLogger(__name__)


async def get_preference(db_pool: asyncpg.Pool, user_id: str, key: str) -> dict | None:
    """Retourne la valeur JSON d'une préférence utilisateur ou None si absente."""
    row = await db_pool.fetchrow(
        "SELECT value FROM user_preferences WHERE user_id = $1::uuid AND key = $2",
        user_id,
        key,
    )
    if row is None:
        return None
    return _decode_jsonb(row["value"])


async def upsert_preference(
    db_pool: asyncpg.Pool, user_id: str, key: str, value: dict
) -> dict:
    """Insère ou met à jour une préférence (idempotent) et renvoie la valeur persistée."""
    row = await db_pool.fetchrow(
        """
        INSERT INTO user_preferences (user_id, key, value)
        VALUES ($1::uuid, $2, $3::jsonb)
        ON CONFLICT (user_id, key) DO UPDATE
            SET value = EXCLUDED.value,
                updated_at = NOW()
        RETURNING value
        """,
        user_id,
        key,
        json.dumps(value),
    )
    return _decode_jsonb(row["value"])


def _decode_jsonb(value: str | dict) -> dict:
    # asyncpg renvoie un JSONB comme str tant qu'aucun codec JSON n'est enregistré
    return json.loads(value) if isinstance(value, str) else value
