"""Durcissement provisioning DB — revoke privilèges `PUBLIC` + re-GRANT explicite `app_runtime` (Ops S186)

Revision ID: 0012_revoke_public_privileges
Revises: 0011_app_runtime_role
Create Date: 2026-06-08

Ferme le résidu §2.3 de `docs/revue-owasp-rls-2026-06.md` que la migration `0011` (S182) a
explicitement différé. PostgreSQL accorde par défaut `USAGE` + `CREATE` sur le schéma `public` au
pseudo-rôle `PUBLIC` → tout rôle de connexion (présent ou futur) hérite d'un accès au schéma SANS
GRANT explicite. On révoque ces privilèges `PUBLIC` par défaut, puis on re-GRANT explicitement au
seul `app_runtime` (même périmètre que `0011` — verrouillé par `tests/test_alembic_revoke_public_privileges.py`
pour ne pas diverger).

Non-propriété (garantie, jamais transférée) : les tables restent la propriété de `copilote` pour
qu'Alembic puisse migrer ; on ne transfère JAMAIS la propriété à `app_runtime` (un propriétaire peut
`ALTER … NO FORCE / DISABLE ROW LEVEL SECURITY` et contourner sa propre RLS, cf. §2.3). La
non-propriété de `app_runtime` est **assertée** par le test d'intégration
(`tests/integration/test_revoke_public_rls.py`, `pg_class.relowner`), pas par un changement de schéma.

Défense en profondeur — pourquoi le re-GRANT est sûr et non destructeur : les GRANTs de `0011` sont
accordés DIRECTEMENT à `app_runtime`, donc `REVOKE … FROM PUBLIC` ne les touche pas — le runtime
conserve son accès même sans ce re-GRANT. Le re-GRANT rend `0012` auto-portant comme source d'accès
explicite ; le durcissement réel exigé par la revue OWASP §2.3 est le revoke `PUBLIC`.

Idempotence : `REVOKE`/`GRANT` sont idempotents par nature (pas de garde `IF EXISTS` requise).
`downgrade()` : re-`GRANT ALL ON SCHEMA public TO PUBLIC` (retour à l'état Postgres par défaut) ;
les GRANTs directs à `app_runtime` (issus de `0011`) ne sont PAS retirés ici — ils appartiennent à
la révision `0011`.

Hygiène des secrets (`.claude/rules/securite.md`) : aucun mot de passe — cohérent S182.
"""
from __future__ import annotations

from collections.abc import Sequence

from alembic import op

revision: str = "0012_revoke_public_privileges"
down_revision: str | None = "0011_app_runtime_role"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_ROLE = "app_runtime"

# Périmètre identique à `0011._RW_TABLES` — verrouillé par test (non-divergence). 7 tables RLS +
# parent FK `tenants` + facturation HORS RLS (`api_keys`/`subscriptions`/`stripe_events`).
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

# Révocation des privilèges `PUBLIC` par défaut (le durcissement réel). Une instruction par entrée
# (pas de `;` terminal — asyncpg via SQLAlchemy refuse le multi-instructions sur une exécution).
_REVOKE_PUBLIC = (
    "REVOKE ALL ON SCHEMA public FROM PUBLIC",
    "REVOKE ALL PRIVILEGES ON ALL TABLES IN SCHEMA public FROM PUBLIC",
    "REVOKE ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public FROM PUBLIC",
)

# Re-GRANT explicite au SEUL `app_runtime` — miroir de `0011._GRANTS` (verrouillé par test).
_REGRANT = (
    f"GRANT USAGE ON SCHEMA public TO {_ROLE}",
    f"GRANT SELECT, INSERT, UPDATE, DELETE ON {', '.join(_RW_TABLES)} TO {_ROLE}",
    f"GRANT SELECT ON plan_limits TO {_ROLE}",
    f"GRANT USAGE ON ALL SEQUENCES IN SCHEMA public TO {_ROLE}",
)


def upgrade() -> None:
    for statement in (*_REVOKE_PUBLIC, *_REGRANT):
        op.execute(statement)


def downgrade() -> None:
    # Retour à l'état Postgres par défaut : PUBLIC re-doté de USAGE+CREATE sur le schéma. Les tables
    # n'accordent rien à PUBLIC par défaut → seul le schéma est restauré.
    op.execute("GRANT ALL ON SCHEMA public TO PUBLIC")
