from __future__ import annotations

import asyncpg

from app.db.tenant_context import apply_tenant_context
from app.utils.security_config import resolve_app_database_url


async def create_runtime_pool(*, min_size: int, max_size: int) -> asyncpg.Pool:
    """Crée un pool asyncpg runtime — DSN `app_runtime` + hook tenant indissociables.

    Invariant de sécurité RLS : résoudre la DSN runtime (`resolve_app_database_url` → rôle
    `app_runtime`, NOSUPERUSER/NOBYPASSRLS) ET câbler `setup=apply_tenant_context` (pose le GUC
    `app.tenant_id` à chaque acquisition de connexion) sont deux décisions inséparables —
    oublier l'une OU l'autre rend l'isolation multi-tenant silencieusement inerte. Centraliser
    ces deux décisions ici interdit qu'un futur pool runtime diverge ; l'appelant ne fournit que
    les tailles du pool.
    """
    return await asyncpg.create_pool(
        resolve_app_database_url(),
        min_size=min_size,
        max_size=max_size,
        setup=apply_tenant_context,
    )
