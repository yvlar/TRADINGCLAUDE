"""subscriptions.usage_reported_through : curseur d'idempotence du report d'usage (E4-S9)

Revision ID: 0010_usage_report_cursor
Revises: 0009_stripe_billing
Create Date: 2026-06-08

Neuvième marche de l'épic E4 — facturation à l'usage métrée vers Stripe. Ferme la boucle
de monétisation : la consommation agrégée (`usage_events`) est poussée vers Stripe en
metered usage records (`stripe.billing.MeterEvent`) pour facturer l'usage réel *en plus* de
l'abonnement forfaitaire.

Ajoute **une seule colonne** à `subscriptions` :
- **`usage_reported_through TIMESTAMPTZ`** (nullable) — curseur de la dernière fenêtre de
  consommation déjà rapportée à Stripe pour ce tenant. La tâche `run_usage_reporting` agrège
  `usage_events` sur la fenêtre `(usage_reported_through, now()]`, pousse le metered record,
  puis avance le curseur à `now()`. **Anti-double-facturation** : une 2ᵉ exécution sur la même
  fenêtre voit `usage_reported_through = now()` → fenêtre vide → aucun re-report. `NULL` (valeur
  initiale, défaut SQL) = jamais rapporté → la première fenêtre couvre tout l'historique du tenant.

Décision RLS documentée — **`subscriptions` reste HORS RLS** (inchangé depuis `0009`, comme
`api_keys`/`stripe_events`) : le report tourne sous le tenant legacy (chemin worker), lit la
liste des abonnés et résout chaque `tenant_id` *arbitrairement* depuis la table parente. Le
curseur isole les fenêtres de report, pas les tenants entre eux ; l'agrégation de `usage_events`,
elle, reste scopée par la RLS (la tâche pose `tenant_scope(tenant_id)` avant le COUNT). Aucune
`CREATE POLICY`, aucun `ENABLE ROW LEVEL SECURITY` (curseur = colonne additive sur table existante).
"""
from __future__ import annotations

from collections.abc import Sequence

from alembic import op

revision: str = "0010_usage_report_cursor"
down_revision: str | None = "0009_stripe_billing"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_UPGRADE_DDL = """
ALTER TABLE subscriptions ADD COLUMN IF NOT EXISTS usage_reported_through TIMESTAMPTZ;
"""

_DOWNGRADE_DDL = """
ALTER TABLE subscriptions DROP COLUMN IF EXISTS usage_reported_through;
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
