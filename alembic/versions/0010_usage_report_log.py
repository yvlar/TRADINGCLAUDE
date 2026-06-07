"""usage_report_log : journal d'idempotence du report d'usage métré vers Stripe (E4-S9)

Revision ID: 0010_usage_report_log
Revises: 0009_stripe_billing
Create Date: 2026-06-07

Neuvième marche de l'épic E4 — ferme la boucle de monétisation : la tâche worker
`run_usage_reporting` pousse la consommation agrégée d'`usage_events` vers Stripe en
metered usage records (`stripe.billing.MeterEvent`). Cette table garantit qu'une
**fenêtre de consommation n'est rapportée qu'une seule fois** (sinon double facturation).

- **`usage_report_log`** : une ligne par (tenant, fenêtre rapportée). La **PK composite
  `(tenant_id, period_start)`** est la barrière d'idempotence : le worker réserve la
  fenêtre via `INSERT … ON CONFLICT DO NOTHING RETURNING` AVANT d'appeler Stripe ; un
  2ᵉ passage sur la même fenêtre ne réserve rien → aucun re-report (même patron que le
  journal `stripe_events` du S172). `quantity` mémorise le nombre d'unités rapportées
  (audit/réconciliation), `reported_at` l'horodatage du report.

Décision RLS documentée — **HORS RLS** (n'entre PAS dans la matrice d'isolation, comme
`subscriptions`/`stripe_events` au S172). `run_usage_reporting` tourne sous le **tenant
legacy** (chemin worker), lit `subscriptions` (hors RLS) pour énumérer les tenants abonnés,
puis réserve/écrit `usage_report_log` pour un tenant **arbitraire**. Sous RLS, le worker ne
verrait que les lignes legacy → réservation cassée. La colonne `tenant_id` *résout* le tenant
facturé, elle n'isole pas la table. Aucune `CREATE POLICY`, aucun `ENABLE ROW LEVEL SECURITY`.
"""
from __future__ import annotations

from collections.abc import Sequence

from alembic import op

revision: str = "0010_usage_report_log"
down_revision: str | None = "0009_stripe_billing"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_UPGRADE_DDL = """
CREATE TABLE IF NOT EXISTS usage_report_log (
    tenant_id    UUID        NOT NULL REFERENCES tenants(id),
    period_start TIMESTAMPTZ NOT NULL,
    period_end   TIMESTAMPTZ NOT NULL,
    quantity     BIGINT      NOT NULL,
    reported_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (tenant_id, period_start)
);
"""

_DOWNGRADE_DDL = """
DROP TABLE IF EXISTS usage_report_log;
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
