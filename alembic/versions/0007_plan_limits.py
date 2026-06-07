"""plan_limits : bornes de consommation par plan tarifaire (E4-S2)

Revision ID: 0007_plan_limits
Revises: 0006_usage_events
Create Date: 2026-06-06

Deuxième marche de l'épic E4 (facturation/SaaS). Pose le socle des quotas : une table
de **référence globale** `plan_limits` qui définit, **par plan** (`free`/`pro`/…), les
bornes de consommation d'un tenant (analyses/mois, taille screener, rétention), et le
rattachement `tenants.plan` (un tenant → un plan).

Décisions :
- **`plan_limits` = table de référence GLOBALE → PAS de `tenant_id`, PAS de RLS.** Un plan
  porte la **même** borne pour tous les tenants ; la clé naturelle est le nom du plan, pas
  le tenant. Elle n'entre donc PAS dans la matrice d'isolation RLS (Sprint 165, 7 tables) :
  rien à isoler par tenant (au contraire de `usage_events` qui horodate la conso d'UN tenant).
  C'est l'attribution `tenants.plan` — pas la table de bornes — qui rattache un tenant à un plan.
- **Rattachement par colonne `tenants.plan` (option a), pas table d'association.** Un tenant
  n'a qu'UN plan actif à la fois et l'historique de plan n'est pas requis ce sprint : une
  colonne FK est plus simple et suffisante (une table d'association ne se justifierait que
  pour un historique de souscription, déféré à l'intégration Stripe E4-S6). FK
  `tenants.plan → plan_limits(plan)` : intégrité référentielle (un tenant ne peut pointer un
  plan inexistant) ; `DEFAULT 'free'` → le tenant legacy et tout nouveau tenant démarrent au
  plan gratuit sans backfill explicite.
- **`retention_days`** est posé dès maintenant (borne de rétention par plan) mais n'est pas
  encore appliqué ce sprint — colonne de socle pour la purge par plan (M4).
"""
from __future__ import annotations

from collections.abc import Sequence

from alembic import op

revision: str = "0007_plan_limits"
down_revision: str | None = "0006_usage_events"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# Bornes initiales par plan. `free` = palier d'évaluation borné ; `pro` = palier payant aligné
# sur le plafond technique du screener (max 20 tickers, cf. ScreenRequest). Modifiables par une
# migration ultérieure ou un back-office — la table est la source de vérité des bornes.
_SEED_PLANS = (
    # (plan, max_analyses_per_month, max_screener_tickers, retention_days)
    ("free", 50, 5, 30),
    ("pro", 1000, 20, 365),
)

_SEED_VALUES = ",\n    ".join(
    f"('{plan}', {analyses}, {tickers}, {retention})"
    for plan, analyses, tickers, retention in _SEED_PLANS
)

_UPGRADE_DDL = f"""
CREATE TABLE IF NOT EXISTS plan_limits (
    plan                   TEXT        PRIMARY KEY,
    max_analyses_per_month INTEGER     NOT NULL,
    max_screener_tickers   INTEGER     NOT NULL,
    retention_days         INTEGER     NOT NULL,
    created_at             TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
INSERT INTO plan_limits (plan, max_analyses_per_month, max_screener_tickers, retention_days)
VALUES
    {_SEED_VALUES}
ON CONFLICT (plan) DO NOTHING;
ALTER TABLE tenants ADD COLUMN IF NOT EXISTS plan TEXT NOT NULL DEFAULT 'free'
    REFERENCES plan_limits(plan);
"""

# Ordre inverse des dépendances FK (tenants.plan → plan_limits) : retirer d'abord la colonne
# (donc la FK), puis la table de référence.
_DOWNGRADE_DDL = """
ALTER TABLE IF EXISTS tenants DROP COLUMN IF EXISTS plan;
DROP TABLE IF EXISTS plan_limits CASCADE;
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
