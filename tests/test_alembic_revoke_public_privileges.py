"""Tests unitaires de la migration `0012` — revoke `PUBLIC` + re-GRANT `app_runtime` (Ops S186), sans DB.

Validation runtime (upgrade/downgrade + preuve d'absence de privilège `PUBLIC` sous le rôle réel)
faite par le gate CI `migrations` / `tests/integration/test_revoke_public_rls.py`. Ici on verrouille
la forme, le chaînage après `0011`, l'absence de mot de passe (hygiène secrets), et surtout la
**non-divergence** du périmètre re-GRANT vis-à-vis de la migration `0011` (source des GRANTs S182).
"""
from __future__ import annotations

import importlib.util
from pathlib import Path
from types import ModuleType


def _load(name: str) -> ModuleType:
    path = Path(__file__).resolve().parents[1] / "alembic" / "versions" / f"{name}.py"
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_revision_chainee_apres_app_runtime_role():
    m = _load("0012_revoke_public_privileges")
    assert m.revision == "0012_revoke_public_privileges"
    assert m.down_revision == "0011_app_runtime_role"


def test_revoke_des_privileges_public_par_defaut():
    """Le durcissement réel : révoquer USAGE/CREATE que PUBLIC détient par défaut sur le schéma."""
    revokes = "\n".join(_load("0012_revoke_public_privileges")._REVOKE_PUBLIC)
    assert "REVOKE ALL ON SCHEMA public FROM PUBLIC" in revokes
    assert "REVOKE ALL PRIVILEGES ON ALL TABLES IN SCHEMA public FROM PUBLIC" in revokes
    assert "REVOKE ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public FROM PUBLIC" in revokes


def test_regrant_au_seul_app_runtime():
    """Re-GRANT explicite : seul `app_runtime` est re-doté ; aucun re-GRANT vers PUBLIC à l'upgrade."""
    regrant = _load("0012_revoke_public_privileges")._REGRANT
    joined = "\n".join(regrant)
    assert "GRANT USAGE ON SCHEMA public TO app_runtime" in joined
    assert "GRANT SELECT, INSERT, UPDATE, DELETE ON" in joined
    assert "GRANT SELECT ON plan_limits TO app_runtime" in joined
    assert "GRANT USAGE ON ALL SEQUENCES IN SCHEMA public TO app_runtime" in joined
    # Aucun privilège re-accordé à PUBLIC dans le chemin upgrade.
    assert all("TO PUBLIC" not in stmt for stmt in regrant)


def test_perimetre_regrant_ne_diverge_pas_de_0011():
    """Verrou anti-divergence : le périmètre des tables RW de `0012` == celui de `0011` (source S182)."""
    m12 = _load("0012_revoke_public_privileges")
    m11 = _load("0011_app_runtime_role")
    assert m12._RW_TABLES == m11._RW_TABLES
    # Les 4 GRANTs re-accordés par 0012 doivent reproduire mot pour mot les GRANTs de 0011.
    assert set(m12._REGRANT) == set(m11._GRANTS)


def test_aucun_mot_de_passe_dans_la_migration():
    """Hygiène secrets : aucune gestion de mot de passe dans ce durcissement (cohérent S182)."""
    m = _load("0012_revoke_public_privileges")
    src = "\n".join((*m._REVOKE_PUBLIC, *m._REGRANT))
    assert "PASSWORD" not in src


def test_downgrade_restaure_les_privileges_public():
    """downgrade = retour à l'état Postgres par défaut (PUBLIC re-doté sur le schéma)."""
    import inspect

    src = inspect.getsource(_load("0012_revoke_public_privileges").downgrade)
    assert "GRANT ALL ON SCHEMA public TO PUBLIC" in src


def test_statements_sans_point_virgule_terminal():
    """asyncpg via SQLAlchemy = une instruction par exécution → pas de `;` terminal."""
    m = _load("0012_revoke_public_privileges")
    for stmt in (*m._REVOKE_PUBLIC, *m._REGRANT):
        assert not stmt.rstrip().endswith(";")


def test_upgrade_downgrade_appelables():
    m = _load("0012_revoke_public_privileges")
    assert callable(m.upgrade)
    assert callable(m.downgrade)
