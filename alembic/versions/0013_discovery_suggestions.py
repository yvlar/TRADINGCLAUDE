"""discovery_suggestions : suggestions précalculées de la page Découvrir (design débutant)

Revision ID: 0013_discovery_suggestions
Revises: 0012_revoke_public_privileges
Create Date: 2026-06-11

Couche « précalculée » du design hybride (docs/design-decouverte-debutant.md §5) : le worker
Celery `run_discovery_refresh` remplace périodiquement les lignes d'une catégorie ; le chemin
requête (`GET /discovery/*`) ne fait que lire — instantané et gratuit.

Décisions :
- **Table de référence GLOBALE → PAS de `tenant_id`, PAS de RLS** (même statut que `plan_limits`).
  Les suggestions sont identiques pour tous les tenants : la clé naturelle est (catégorie, ticker).
  Rien à isoler — la table n'entre pas dans la matrice RLS.
- **PK composite (category, ticker)** : un titre n'apparaît qu'une fois par catégorie ; le
  rafraîchissement est un DELETE+INSERT transactionnel par catégorie (jamais de moitié visible).
- **GRANT explicite à `app_runtime`** : depuis 0012, les privilèges PUBLIC sont révoqués — toute
  nouvelle table doit accorder ses droits au rôle runtime, sinon le service ne peut pas la lire.
"""
from __future__ import annotations

from collections.abc import Sequence

from alembic import op

revision: str = "0013_discovery_suggestions"
down_revision: str | None = "0012_revoke_public_privileges"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_ROLE = "app_runtime"


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS discovery_suggestions (
            category        TEXT             NOT NULL,
            ticker          TEXT             NOT NULL,
            name            TEXT             NOT NULL,
            composite_score DOUBLE PRECISION,
            composite_label TEXT,
            risk_badge      TEXT             NOT NULL,
            why             TEXT             NOT NULL,
            dividend_yield  DOUBLE PRECISION,
            dividend_years  INTEGER,
            pe              DOUBLE PRECISION,
            price           DOUBLE PRECISION,
            as_of           TIMESTAMPTZ      NOT NULL DEFAULT NOW(),
            PRIMARY KEY (category, ticker)
        )
        """
    )
    op.execute(
        f"GRANT SELECT, INSERT, UPDATE, DELETE ON discovery_suggestions TO {_ROLE}"
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS discovery_suggestions")
