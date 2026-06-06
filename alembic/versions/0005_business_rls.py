"""Row-Level Security tenant sur les 6 tables métier (E3-S3)

Revision ID: 0005_business_rls
Revises: 0004_business_tenant_id
Create Date: 2026-06-06

Troisième marche de l'épic E3 : poser l'isolation au niveau base. Chacune des 6
tables métier (`analysis_history`, `watchlist`, `composite_score_history`,
`esg_score_history`, `alert_history`, `annotations`) — qui portent déjà
`tenant_id NOT NULL` (Sprint 162) — reçoit la Row-Level Security et une policy qui
restreint lignes lues ET écrites au tenant courant.

Contexte tenant : le GUC `app.tenant_id` est posé par connexion au pool asyncpg
(`app.db.tenant_context.apply_tenant_context`). Tant que le threading tenant
endpoints→services n'est pas câblé (E3-S4), ce GUC vaut `LEGACY_TENANT_ID` —
l'isolation est réelle, mais tout le monde est « legacy ».

Décisions :
- `current_setting('app.tenant_id', true)` — le 2ᵉ argument `missing_ok=true` renvoie
  NULL (au lieu d'une erreur) quand le GUC n'est pas posé. `NULLIF(…, '')` traite aussi
  la chaîne vide comme NULL. GUC absent/vide → `NULL::uuid` → `tenant_id = NULL` est NULL
  (jamais vrai) → 0 ligne visible : comportement fail-closed (une requête sans contexte
  tenant ne voit rien, plutôt que tout). Sans le `NULLIF`, un GUC à '' lèverait
  « invalid input syntax for type uuid » — le `NULLIF` rend la policy robuste.
- `WITH CHECK` (en plus de `USING`) : un tenant ne peut pas INSÉRER/UPDATER une ligne
  rattachée à un autre tenant.
- `FORCE ROW LEVEL SECURITY` : sans lui, le propriétaire de la table contourne la
  policy (les superusers la contournent toujours). En prod le rôle applicatif n'est
  pas propriétaire des tables, mais `FORCE` garantit l'isolation même si le rôle
  applicatif possède les tables (défense en profondeur), et rend l'isolation
  prouvable en local via un rôle NOSUPERUSER non-propriétaire.

Réutilise le pattern template sur tuple `_TABLES` posé au Sprint 162.
"""
from __future__ import annotations

from collections.abc import Sequence

from alembic import op

revision: str = "0005_business_rls"
down_revision: str | None = "0004_business_tenant_id"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# Mêmes 6 tables métier qu'au Sprint 162 — chacune porte déjà `tenant_id NOT NULL`.
_TABLES: tuple[str, ...] = (
    "analysis_history",
    "watchlist",
    "composite_score_history",
    "esg_score_history",
    "alert_history",
    "annotations",
)

# Prédicat partagé USING/WITH CHECK : la ligne appartient au tenant du contexte.
_TENANT_PREDICATE = (
    "tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::uuid"
)


def _upgrade_table(table: str) -> str:
    """ENABLE + FORCE RLS puis CREATE POLICY (USING + WITH CHECK) sur le tenant courant."""
    return (
        f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY;\n"
        f"ALTER TABLE {table} FORCE ROW LEVEL SECURITY;\n"
        f"CREATE POLICY {table}_tenant_isolation ON {table} "
        f"USING ({_TENANT_PREDICATE}) WITH CHECK ({_TENANT_PREDICATE});\n"
    )


def _downgrade_table(table: str) -> str:
    """Retirer la policy puis désactiver la RLS, idempotent."""
    return (
        f"DROP POLICY IF EXISTS {table}_tenant_isolation ON {table};\n"
        f"ALTER TABLE {table} NO FORCE ROW LEVEL SECURITY;\n"
        f"ALTER TABLE {table} DISABLE ROW LEVEL SECURITY;\n"
    )


_UPGRADE_DDL = "".join(_upgrade_table(t) for t in _TABLES)
_DOWNGRADE_DDL = "".join(_downgrade_table(t) for t in _TABLES)


def _execute_each(ddl: str) -> None:
    """Exécute chaque instruction séparément (asyncpg = une instruction par exécution)."""
    for statement in ddl.split(";"):
        stripped = statement.strip()
        if stripped:
            op.execute(stripped)


def upgrade() -> None:
    _execute_each(_UPGRADE_DDL)


def downgrade() -> None:
    _execute_each(_DOWNGRADE_DDL)
