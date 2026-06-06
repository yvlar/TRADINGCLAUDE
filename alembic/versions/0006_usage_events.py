"""usage_events : metering append-only par skill (E4-S1)

Revision ID: 0006_usage_events
Revises: 0005_business_rls
Create Date: 2026-06-06

Ouverture de l'épic E4 (facturation/SaaS). Table append-only qui horodate, **par
skill exécuté** (pas seulement par analyse), la consommation facturable d'un tenant —
source de vérité unique de l'agrégation de facturation (E4-S2 quotas, E4-S5 export).
Aucun UPDATE/DELETE applicatif (cf. `UsageEventService`).

Décisions :
- **Pas de FK vers `analysis_history`** : un événement de consommation doit survivre à
  la purge de l'analyse qui l'a produit (rétention facturation ≠ rétention analyse).
  Le lien reste sémantique (`tenant`/`skill`/`workflow`/`created_at`), pas référentiel.
- **`tenant_id NOT NULL REFERENCES tenants(id)`** → la table entre dans le périmètre RLS :
  même policy que les 6 tables métier (Sprint 163) — `ENABLE`+`FORCE ROW LEVEL SECURITY`
  + policy `usage_events_tenant_isolation` (USING + WITH CHECK sur le prédicat tenant
  standard, fail-closed via `NULLIF`). Sans cela, un pool sans GUC verrait 0 ligne et ses
  INSERT échoueraient au `WITH CHECK`.
- **`id` UUID `gen_random_uuid()`** (et non BIGSERIAL) : aligné sur `audit_log`, append-only,
  pas de séquence à GRANT côté rôle d'isolation.
- **`cost_usd NUMERIC(10,6)`** : précision monétaire exacte (pas de float) pour l'agrégation
  de facturation.
"""
from __future__ import annotations

from collections.abc import Sequence

from alembic import op

revision: str = "0006_usage_events"
down_revision: str | None = "0005_business_rls"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# Prédicat partagé USING/WITH CHECK — identique aux 6 tables métier (Sprint 163) : la ligne
# appartient au tenant du contexte ; GUC absent/vide → NULL::uuid → 0 ligne (fail-closed).
_TENANT_PREDICATE = "tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::uuid"

_UPGRADE_DDL = f"""
CREATE TABLE IF NOT EXISTS usage_events (
    id            UUID           PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id     UUID           NOT NULL REFERENCES tenants(id),
    skill         TEXT           NOT NULL,
    workflow      TEXT           NOT NULL,
    cost_usd      NUMERIC(10, 6) NOT NULL DEFAULT 0,
    tokens_input  INTEGER        NOT NULL DEFAULT 0,
    tokens_output INTEGER        NOT NULL DEFAULT 0,
    created_at    TIMESTAMPTZ    NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_usage_events_tenant_created
    ON usage_events (tenant_id, created_at DESC);
ALTER TABLE usage_events ENABLE ROW LEVEL SECURITY;
ALTER TABLE usage_events FORCE ROW LEVEL SECURITY;
CREATE POLICY usage_events_tenant_isolation ON usage_events
    USING ({_TENANT_PREDICATE}) WITH CHECK ({_TENANT_PREDICATE});
"""

_DOWNGRADE_DDL = """
DROP POLICY IF EXISTS usage_events_tenant_isolation ON usage_events;
ALTER TABLE IF EXISTS usage_events NO FORCE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS usage_events DISABLE ROW LEVEL SECURITY;
DROP TABLE IF EXISTS usage_events CASCADE;
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
