"""Rôle de connexion runtime `app_runtime` (NOSUPERUSER/NOBYPASSRLS) — RLS active en prod (Ops S182)

Revision ID: 0011_app_runtime_role
Revises: 0010_usage_report_cursor
Create Date: 2026-06-08

Risque résiduel n°1 de `docs/revue-owasp-rls-2026-06.md` §2.4 : tant que les pools API + workers
se connectent avec `copilote` (SUPERUSER+BYPASSRLS, défaut `.env.example`), **toute** policy RLS
(Sprints 163-181) est **inerte**. Ce sprint provisionne un rôle de connexion applicatif
`app_runtime` — `NOSUPERUSER`, `NOBYPASSRLS`, **non-propriétaire** des tables — qui **subit** les
policies. Le rôle `copilote` (propriétaire) reste réservé aux migrations Alembic.

Décision tranchée — **provisioning par migration Alembic, pas par `infra/postgres/init.sql`** :
- `init.sql` est un **no-op** qui ne s'exécute que sur un **volume postgres neuf**
  (`/docker-entrypoint-initdb.d/`) → un déploiement existant n'obtiendrait jamais le rôle, et le
  correctif de sécurité ne s'appliquerait pas en prod.
- `alembic upgrade head` tourne sur **tout** déploiement (existant + neuf + CI), sous la DSN
  `copilote` (SUPERUSER → peut `CREATE ROLE`). Les GRANT, eux, sont des objets de schéma : les
  co-localiser avec les migrations (où naissent les tables RLS) garantit qu'une future table RLS
  étendra le GRANT dans la même révision.

Hygiène des secrets (`.claude/rules/securite.md`) — **aucun mot de passe dans la migration** :
le rôle est créé `LOGIN` mais SANS mot de passe (donc inutilisable tant qu'un mot de passe n'est
pas posé hors-bande). Le mot de passe de connexion est provisionné par l'ops via
`ALTER ROLE app_runtime PASSWORD …` (valeur tirée de `APP_DATABASE_URL`, jamais commitée) ; la CI
le pose en clair pour la preuve d'isolation (rôle jetable).

Périmètre des GRANT — modélise le bloc `rls_tester` du gate CI (`.github/workflows/ci.yml`) :
SELECT/INSERT/UPDATE/DELETE sur les 7 tables RLS + `tenants` (parent FK) + `api_keys` +
`subscriptions`/`stripe_events` (facturation HORS RLS), SELECT sur `plan_limits` (référence
globale), USAGE sur le schéma + toutes les séquences (tables BIGSERIAL). La **non-propriété** des
tables (un propriétaire pourrait `ALTER … DISABLE ROW LEVEL SECURITY`) est garantie par
construction (Alembic crée les tables sous `copilote`) ; son durcissement explicite + le revoke
`PUBLIC` sont différés (Sprint 186 suggéré).
"""
from __future__ import annotations

from collections.abc import Sequence

from alembic import op

revision: str = "0011_app_runtime_role"
down_revision: str | None = "0010_usage_report_cursor"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_ROLE = "app_runtime"

# Tables métier accédées en lecture/écriture par le runtime (7 RLS + parent + facturation).
_RW_TABLES = (
    "analysis_history",
    "watchlist",
    "composite_score_history",
    "esg_score_history",
    "alert_history",
    "annotations",
    "usage_events",
    "tenants",
    "api_keys",
    "subscriptions",
    "stripe_events",
)

# Création idempotente du rôle SANS mot de passe (LOGIN mais inutilisable jusqu'au provisioning
# hors-bande du mot de passe). NOSUPERUSER/NOBYPASSRLS = le rôle subit les policies RLS. Le bloc
# `DO $$ … $$` est UNE seule instruction (les `;` internes vivent dans le corps de la fonction)
# — exécuté tel quel, jamais splitté (cf. `_execute` : asyncpg = une instruction par exécution).
_CREATE_ROLE = f"""
DO $$
BEGIN
  IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = '{_ROLE}') THEN
    CREATE ROLE {_ROLE} LOGIN NOSUPERUSER NOBYPASSRLS NOCREATEDB NOCREATEROLE;
  ELSE
    ALTER ROLE {_ROLE} LOGIN NOSUPERUSER NOBYPASSRLS NOCREATEDB NOCREATEROLE;
  END IF;
END $$
"""

# Une instruction GRANT/REVOKE par entrée (pas de `;` terminal — asyncpg via SQLAlchemy refuse
# le multi-instructions sur une exécution).
_GRANTS = (
    f"GRANT USAGE ON SCHEMA public TO {_ROLE}",
    f"GRANT SELECT, INSERT, UPDATE, DELETE ON {', '.join(_RW_TABLES)} TO {_ROLE}",
    f"GRANT SELECT ON plan_limits TO {_ROLE}",
    f"GRANT USAGE ON ALL SEQUENCES IN SCHEMA public TO {_ROLE}",
)

# Downgrade : révoquer les privilèges puis retirer le rôle (idempotent — il ne possède aucun objet).
_REVOKES = (
    f"REVOKE ALL ON ALL SEQUENCES IN SCHEMA public FROM {_ROLE}",
    f"REVOKE ALL ON plan_limits FROM {_ROLE}",
    f"REVOKE ALL ON {', '.join(_RW_TABLES)} FROM {_ROLE}",
    f"REVOKE ALL ON SCHEMA public FROM {_ROLE}",
    f"DROP ROLE IF EXISTS {_ROLE}",
)


def upgrade() -> None:
    op.execute(_CREATE_ROLE.strip())
    for statement in _GRANTS:
        op.execute(statement)


def downgrade() -> None:
    for statement in _REVOKES:
        op.execute(statement)
