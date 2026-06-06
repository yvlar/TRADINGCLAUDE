"""tenants : socle multi-tenance (E3-S1)

Revision ID: 0003_tenants
Revises: 0002_audit_log
Create Date: 2026-06-06

Première marche de l'épic E3 (multi-tenance + RLS). Pose la dimension tenant côté
comptes uniquement : table `tenants`, tenant « legacy » de backfill (UUID fixe), et
`users.tenant_id` (FK) rendu NOT NULL après rattachement des comptes existants.

Aucune isolation RLS ni `tenant_id` sur les 6 tables métier ici (E3-S2/S3). L'auth
reste 100 % rétrocompatible : un nouvel inscrit est rattaché au tenant legacy par
défaut côté service.

Le littéral de l'UUID legacy ci-dessous duplique `app.models.tenant.LEGACY_TENANT_ID`
(une migration est un artefact historique figé — elle ne doit pas importer du code
applicatif susceptible d'évoluer). Un test verrouille l'égalité des deux sources.
"""
from __future__ import annotations

from collections.abc import Sequence

from alembic import op

revision: str = "0003_tenants"
down_revision: str | None = "0002_audit_log"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_LEGACY_TENANT_ID = "00000000-0000-0000-0000-000000000001"

_UPGRADE_DDL = f"""
CREATE TABLE IF NOT EXISTS tenants (
    id          UUID         PRIMARY KEY DEFAULT gen_random_uuid(),
    name        TEXT         NOT NULL,
    slug        TEXT         NOT NULL UNIQUE,
    created_at  TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);
INSERT INTO tenants (id, name, slug)
VALUES ('{_LEGACY_TENANT_ID}', 'Legacy', 'legacy')
ON CONFLICT (slug) DO NOTHING;
ALTER TABLE users ADD COLUMN IF NOT EXISTS tenant_id UUID REFERENCES tenants(id);
UPDATE users SET tenant_id = '{_LEGACY_TENANT_ID}' WHERE tenant_id IS NULL;
ALTER TABLE users ALTER COLUMN tenant_id SET NOT NULL;
CREATE INDEX IF NOT EXISTS idx_users_tenant ON users (tenant_id);
"""

# Ordre inverse des dépendances FK (users.tenant_id → tenants) : retirer d'abord
# la colonne (donc la FK), puis la table.
_DOWNGRADE_DDL = """
DROP INDEX IF EXISTS idx_users_tenant;
ALTER TABLE users DROP COLUMN IF EXISTS tenant_id;
DROP TABLE IF EXISTS tenants CASCADE;
"""


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
