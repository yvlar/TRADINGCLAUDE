from __future__ import annotations

from uuid import UUID

# Tenant « legacy » de backfill : rattache tous les comptes pré-multi-tenance.
# Source unique des valeurs du tenant legacy — référencées par UserService et par
# le backfill des sprints E3 suivants. La migration 0003 en garde une copie littérale
# (artefact historique figé, n'importe pas de code applicatif) ; un test verrouille
# l'égalité migration ↔ constantes (UUID, slug, name).
LEGACY_TENANT_ID: UUID = UUID("00000000-0000-0000-0000-000000000001")
LEGACY_TENANT_SLUG: str = "legacy"
LEGACY_TENANT_NAME: str = "Legacy"
