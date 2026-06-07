"""api_keys.tenant_id : rattachement des clés API au tenant (E4-S3)

Revision ID: 0008_api_keys_tenant_id
Revises: 0007_plan_limits
Create Date: 2026-06-07

Troisième marche de l'épic E4 (facturation/SaaS). Ferme le dernier trou de la
multi-tenance : une requête authentifiée par **clé API** (chemin Bearer) doit
s'exécuter sous le tenant **propriétaire de la clé**, pas le tenant legacy. La
colonne `api_keys.tenant_id` permet au `BearerTokenMiddleware` de *résoudre* le
tenant à poser dans le ContextVar (→ GUC RLS, quotas E4-S2, metering E4-S1).

Décision documentée — **`api_keys` reste HORS RLS** (n'entre PAS dans la matrice
d'isolation des 7 tables, Sprints 165/166) : c'est la table d'authentification, lue
par le middleware **avant** que le contexte tenant existe (c'est elle qui le pose).
Si elle était sous RLS, le `validate_key` tournerait sous le GUC legacy par défaut et
ne verrait jamais les clés des autres tenants → authn cassée. Sa colonne `tenant_id`
sert donc à *résoudre* le tenant, pas à isoler la table par tenant.

Backfill-avant-NOT-NULL (pattern Sprint 162/0004) : ADD nullable → UPDATE legacy →
SET NOT NULL → INDEX. Politique `ON DELETE` : `NO ACTION` (défaut, restrict) — comme
les autres FK tenant ; supprimer un tenant échoue tant qu'il porte des clés.

Le littéral de l'UUID legacy duplique `app.models.tenant.LEGACY_TENANT_ID` (une
migration est un artefact historique figé — elle n'importe pas de code applicatif). Un
test verrouille l'égalité des deux sources.
"""
from __future__ import annotations

from collections.abc import Sequence

from alembic import op

revision: str = "0008_api_keys_tenant_id"
down_revision: str | None = "0007_plan_limits"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_LEGACY_TENANT_ID = "00000000-0000-0000-0000-000000000001"

_UPGRADE_DDL = f"""
ALTER TABLE api_keys ADD COLUMN IF NOT EXISTS tenant_id UUID REFERENCES tenants(id);
UPDATE api_keys SET tenant_id = '{_LEGACY_TENANT_ID}' WHERE tenant_id IS NULL;
ALTER TABLE api_keys ALTER COLUMN tenant_id SET NOT NULL;
CREATE INDEX IF NOT EXISTS idx_api_keys_tenant ON api_keys (tenant_id);
"""

# Ordre inverse des dépendances FK : retirer l'index puis la colonne (donc la FK).
_DOWNGRADE_DDL = """
DROP INDEX IF EXISTS idx_api_keys_tenant;
ALTER TABLE api_keys DROP COLUMN IF EXISTS tenant_id;
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
