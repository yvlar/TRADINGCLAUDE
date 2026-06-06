"""audit_log : journal d'audit append-only (E2-S3)

Revision ID: 0002_audit_log
Revises: 0001_baseline
Create Date: 2026-06-06

Prérequis conformité Loi 25 (traçabilité des mutations métier). Table append-only :
aucun UPDATE/DELETE applicatif. `tenant_id` posé nullable en forward-compat — le
concept de tenant n'arrive qu'à E3 (pas de table `tenants` ici). `user_id` sans
clé étrangère : l'audit doit survivre à la suppression d'un compte et certaines
mutations (clé API) n'ont pas d'utilisateur authentifié.
"""
from __future__ import annotations

from collections.abc import Sequence

from alembic import op

revision: str = "0002_audit_log"
down_revision: str | None = "0001_baseline"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


_UPGRADE_DDL = """
CREATE TABLE IF NOT EXISTS audit_log (
    id          UUID         PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id   UUID,
    user_id     UUID,
    action      TEXT         NOT NULL,
    cible_type  TEXT         NOT NULL,
    cible_id    TEXT,
    metadata    JSONB        NOT NULL DEFAULT '{}',
    created_at  TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_audit_log_created_at ON audit_log (created_at DESC);
CREATE INDEX IF NOT EXISTS idx_audit_log_cible ON audit_log (cible_type, cible_id);
"""

_DOWNGRADE_DDL = """
DROP TABLE IF EXISTS audit_log CASCADE;
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
