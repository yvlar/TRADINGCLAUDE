from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class TenantAdminEntry(BaseModel):
    """Ligne tenant exposée à l'admin (super-admin onboarding/support) — Sprint 204."""

    id: UUID
    name: str
    slug: str
    plan: str
    # Présent uniquement si le tenant a un abonnement Stripe (LEFT JOIN subscriptions).
    stripe_customer_id: str | None
    created_at: datetime


# Tenant « legacy » de backfill : rattache tous les comptes pré-multi-tenance.
# Source unique des valeurs du tenant legacy — référencées par UserService et par
# le backfill des sprints E3 suivants. La migration 0003 en garde une copie littérale
# (artefact historique figé, n'importe pas de code applicatif) ; un test verrouille
# l'égalité migration ↔ constantes (UUID, slug, name).
LEGACY_TENANT_ID: UUID = UUID("00000000-0000-0000-0000-000000000001")
LEGACY_TENANT_SLUG: str = "legacy"
LEGACY_TENANT_NAME: str = "Legacy"
