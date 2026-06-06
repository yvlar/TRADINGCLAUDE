from __future__ import annotations

import asyncpg

from app.models.tenant import LEGACY_TENANT_ID

# Nom du GUC PostgreSQL portant le tenant courant — lu par les policies RLS posées
# au Sprint 163 (`NULLIF(current_setting('app.tenant_id', true), '')::uuid`). Le
# préfixe `app.` est obligatoire : Postgres n'accepte un paramètre de session
# personnalisé que s'il est qualifié par un namespace (point).
TENANT_GUC = "app.tenant_id"


async def apply_tenant_context(conn: asyncpg.Connection) -> None:
    """Pose le tenant legacy sur chaque connexion empruntée au pool (palier E3-S3).

    Branché comme `setup` du pool asyncpg : exécuté à chaque acquisition de connexion,
    il réinitialise le contexte tenant. Tant que le threading tenant endpoints→services
    n'est pas câblé (E3-S4), toute connexion opère sous `LEGACY_TENANT_ID` — la RLS est
    réelle dès maintenant, seul le tenant effectif reste figé au legacy.

    `set_config(…, is_local=false)` = portée session (réappliquée à chaque acquisition),
    par opposition à la portée transaction qui serait perdue hors d'un BEGIN.
    """
    await conn.execute("SELECT set_config($1, $2, false)", TENANT_GUC, str(LEGACY_TENANT_ID))
