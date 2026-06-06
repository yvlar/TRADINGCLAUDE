from __future__ import annotations

from contextvars import ContextVar, Token
from uuid import UUID

import asyncpg

from app.models.tenant import LEGACY_TENANT_ID

# Nom du GUC PostgreSQL portant le tenant courant — lu par les policies RLS posées
# au Sprint 163 (`NULLIF(current_setting('app.tenant_id', true), '')::uuid`). Le
# préfixe `app.` est obligatoire : Postgres n'accepte un paramètre de session
# personnalisé que s'il est qualifié par un namespace (point).
TENANT_GUC = "app.tenant_id"

# Source unique du tenant courant pour la tâche async en cours (E3-S4). Posé par le
# middleware de requête (`app/middleware/tenant.py`) à partir du JWT authentifié, lu
# ici pour le GUC RLS ET par les sites d'écriture pour la colonne `tenant_id` — d'où
# l'égalité GUC == colonne exigée par le `WITH CHECK` des policies. Défaut legacy :
# requêtes non authentifiées, clés API (hors tenance jusqu'à E4) et workers Celery.
_current_tenant: ContextVar[UUID] = ContextVar("current_tenant", default=LEGACY_TENANT_ID)


def get_current_tenant() -> UUID:
    """Retourne le tenant de la tâche async courante (legacy si aucun n'est posé)."""
    return _current_tenant.get()


def resolve_tenant(tenant_id: UUID | None) -> UUID:
    """Tenant à écrire pour un site d'INSERT : explicite si fourni, sinon celui de la requête.

    Point unique du coalescing param→ContextVar pour les 6 sites d'écriture des tables RLS —
    garantit que la colonne `tenant_id` écrite dérive de la même source que le GUC RLS.
    """
    return tenant_id or get_current_tenant()


def set_current_tenant(tenant_id: UUID | str | None) -> Token[UUID]:
    """Pose le tenant courant ; valeur absente ou invalide → legacy (fail-safe rétrocompat).

    Invariant RLS : un appelant qui passe un `tenant_id` EXPLICITE à un site d'écriture doit
    aussi poser ce même tenant ici (le GUC RLS dérive uniquement de ce ContextVar) — sinon
    colonne ≠ GUC → échec `WITH CHECK`. Un futur worker ciblé sur un tenant fait donc les deux.
    """
    if isinstance(tenant_id, UUID):
        resolved = tenant_id
    elif tenant_id is None:
        resolved = LEGACY_TENANT_ID
    else:
        try:
            resolved = UUID(str(tenant_id))
        except (ValueError, AttributeError, TypeError):
            resolved = LEGACY_TENANT_ID
    return _current_tenant.set(resolved)


def reset_current_tenant(token: Token[UUID]) -> None:
    """Restaure la valeur précédente du ContextVar (appelé en `finally` par le middleware)."""
    _current_tenant.reset(token)


async def apply_tenant_context(conn: asyncpg.Connection) -> None:
    """Pose le tenant courant sur chaque connexion empruntée au pool (E3-S4).

    Branché comme `setup` du pool asyncpg : exécuté à chaque acquisition de connexion,
    il réinitialise le GUC `app.tenant_id` au tenant de la tâche async courante
    (`get_current_tenant`). Comme `setup` rejoue à chaque `fetch`/`execute`, aucune fuite
    du tenant d'une requête précédente n'est possible sur une connexion réutilisée.

    `set_config(…, is_local=false)` = portée session (réappliquée à chaque acquisition),
    par opposition à la portée transaction qui serait perdue hors d'un BEGIN.
    """
    await conn.execute("SELECT set_config($1, $2, false)", TENANT_GUC, str(get_current_tenant()))
