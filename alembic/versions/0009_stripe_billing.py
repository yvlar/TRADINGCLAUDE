"""subscriptions + stripe_events : socle de facturation Stripe (E4-S7)

Revision ID: 0009_stripe_billing
Revises: 0008_api_keys_tenant_id
Create Date: 2026-06-07

Septième marche de l'épic E4 — convertit le socle metering+quotas (S166-S171) en
revenu réel. Pose deux tables :

- **`subscriptions`** : rattache un tenant à son abonnement Stripe
  (`stripe_customer_id`/`stripe_subscription_id`/`status`) et au `plan` courant.
  Clé primaire `tenant_id` → **un abonnement actif par tenant** (l'historique de
  souscription n'est pas requis ce sprint, cohérent avec la décision « option a »
  du S167 pour `tenants.plan`). FK `plan → plan_limits(plan)` : intégrité avec les
  bornes de quota. Index sur les identifiants Stripe → résolution du tenant par le
  webhook (qui reçoit un `customer`/`subscription`, pas un `tenant_id` natif).
- **`stripe_events`** : journal des `event.id` Stripe déjà traités → **idempotence**
  du webhook (une même livraison ne déclenche qu'un traitement).

Décision RLS documentée — **les DEUX tables restent HORS RLS** (n'entrent PAS dans
la matrice d'isolation, comme `api_keys` au S168). Le webhook `POST /billing/webhook`
est **auth-exempté** et tourne donc sous le tenant legacy (GUC par défaut) : il lit/écrit
`subscriptions`/`stripe_events` AVANT toute résolution de tenant et pour un tenant
**arbitraire** (celui de l'événement Stripe). Sous RLS, il ne verrait que les lignes du
tenant legacy → synchronisation cassée. La colonne `subscriptions.tenant_id` sert à
*résoudre* le tenant à mettre à jour (`tenants.plan`, lui-même hors RLS), pas à isoler la
table par tenant. Aucune `CREATE POLICY`, aucun `ENABLE ROW LEVEL SECURITY`.
"""
from __future__ import annotations

from collections.abc import Sequence

from alembic import op

revision: str = "0009_stripe_billing"
down_revision: str | None = "0008_api_keys_tenant_id"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_UPGRADE_DDL = """
CREATE TABLE IF NOT EXISTS subscriptions (
    tenant_id              UUID        PRIMARY KEY REFERENCES tenants(id),
    stripe_customer_id     TEXT,
    stripe_subscription_id TEXT,
    status                 TEXT        NOT NULL DEFAULT 'incomplete',
    plan                   TEXT        NOT NULL DEFAULT 'free' REFERENCES plan_limits(plan),
    created_at             TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at             TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_subscriptions_customer
    ON subscriptions (stripe_customer_id);
CREATE INDEX IF NOT EXISTS idx_subscriptions_subscription
    ON subscriptions (stripe_subscription_id);
CREATE TABLE IF NOT EXISTS stripe_events (
    event_id    TEXT        PRIMARY KEY,
    received_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
"""

# Ordre inverse : tables enfants d'abord. DROP TABLE retire aussi les index associés.
_DOWNGRADE_DDL = """
DROP TABLE IF EXISTS stripe_events;
DROP TABLE IF EXISTS subscriptions;
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
