from __future__ import annotations

import logging
from collections.abc import Awaitable, Callable
from typing import TypeVar
from uuid import UUID

import asyncpg

from app.db.tenant_context import tenant_scope

logger = logging.getLogger(__name__)

T = TypeVar("T")

# `tenants` est la table parente HORS RLS : son énumération ne dépend d'aucun contexte.
_ENUMERATE_TENANTS = "SELECT id FROM tenants ORDER BY created_at"


async def for_each_tenant(
    db_pool: asyncpg.Pool,
    body: Callable[[UUID], Awaitable[T]],
    *,
    error_message: str,
) -> list[T]:
    """Énumère tous les tenants et exécute `body(tenant_id)` sous le contexte RLS de chacun.

    Centralise l'invariant load-bearing que les chemins planifiés (`app/workers/tasks.py`) copiaient :
    énumérer-puis-scoper est **indissociable** (un corps hors `tenant_scope` lirait les tables sous le
    tenant courant, sans filtrage RLS par tenant) et la tolérance aux pannes est **par tenant** —
    l'échec d'un tenant est loggé (`error_message`, un format à un seul `%s` recevant l'UUID) et la
    boucle continue, jamais un avortement global. Retourne les résultats des tenants traités **sans
    erreur** (un tenant qui lève ne contribue aucun élément) ; l'agrégation (union de tickers, dict de
    compteurs, simple effet de bord…) reste à l'appelant.
    """
    tenant_rows = await db_pool.fetch(_ENUMERATE_TENANTS)
    logger.info("Itération multi-tenant — %d tenant(s)", len(tenant_rows))
    results: list[T] = []
    for row in tenant_rows:
        tenant_id = row["id"]
        try:
            with tenant_scope(tenant_id):
                results.append(await body(tenant_id))
        except Exception:
            logger.exception(error_message, tenant_id)
    return results
