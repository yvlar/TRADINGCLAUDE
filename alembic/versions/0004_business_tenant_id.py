"""tenant_id sur les 6 tables métier (E3-S2)

Revision ID: 0004_business_tenant_id
Revises: 0003_tenants
Create Date: 2026-06-06

Deuxième marche de l'épic E3 : propager la dimension tenant aux données. Chacune
des 6 tables métier (`analysis_history`, `watchlist`, `composite_score_history`,
`esg_score_history`, `alert_history`, `annotations`) reçoit `tenant_id UUID NOT NULL`
(FK → `tenants`) + un index, avec backfill des lignes existantes vers le tenant
« legacy » (UUID figé posé au Sprint 161).

Aucune RLS ni middleware de contexte ici (E3-S3/S4) : le tenant legacy reste le défaut
des écritures tant que le threading tenant n'est pas câblé (E3-S4) — les écritures
actuelles passent `LEGACY_TENANT_ID` au site d'INSERT (cf. services métier).

Politique `ON DELETE` : `NO ACTION` (défaut PostgreSQL, restrict) — comme le FK
`users.tenant_id` du Sprint 161. Supprimer un tenant échoue tant qu'il porte des
données métier ; le hard-delete d'un tenant (purge en cascade contrôlée) relève d'un
sprint dédié, pas d'un effacement silencieux par `ON DELETE CASCADE`.

Le littéral de l'UUID legacy ci-dessous duplique `app.models.tenant.LEGACY_TENANT_ID`
(une migration est un artefact historique figé — elle n'importe pas de code applicatif
susceptible d'évoluer). Un test verrouille l'égalité des deux sources.
"""
from __future__ import annotations

from collections.abc import Sequence

from alembic import op

revision: str = "0004_business_tenant_id"
down_revision: str | None = "0003_tenants"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_LEGACY_TENANT_ID = "00000000-0000-0000-0000-000000000001"

# Les 6 tables métier (audit FinTech §3.2 M1 — vérifié). Ordre sans incidence : aucune
# FK croisée entre ces tables, chacune ne référence que `tenants`.
_TABLES: tuple[str, ...] = (
    "analysis_history",
    "watchlist",
    "composite_score_history",
    "esg_score_history",
    "alert_history",
    "annotations",
)


def _upgrade_table(table: str) -> str:
    """Backfill-avant-NOT-NULL : ADD nullable → UPDATE legacy → SET NOT NULL → INDEX."""
    return (
        f"ALTER TABLE {table} ADD COLUMN IF NOT EXISTS tenant_id UUID REFERENCES tenants(id);\n"
        f"UPDATE {table} SET tenant_id = '{_LEGACY_TENANT_ID}' WHERE tenant_id IS NULL;\n"
        f"ALTER TABLE {table} ALTER COLUMN tenant_id SET NOT NULL;\n"
        f"CREATE INDEX IF NOT EXISTS idx_{table}_tenant ON {table} (tenant_id);\n"
    )


def _downgrade_table(table: str) -> str:
    """Ordre FK inverse : retirer l'index puis la colonne (donc la FK)."""
    return (
        f"DROP INDEX IF EXISTS idx_{table}_tenant;\n"
        f"ALTER TABLE {table} DROP COLUMN IF EXISTS tenant_id;\n"
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
