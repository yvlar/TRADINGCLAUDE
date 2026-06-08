"""Tests unitaires de la migration du rôle runtime `app_runtime` (Ops S182) — sans DB.

Validation runtime (upgrade/downgrade idempotent + preuve d'isolation sous le rôle) faite par le
job CI `migrations`. Ici on verrouille la forme, le chaînage après 0010, l'absence de mot de passe
(hygiène secrets) et la couverture des GRANTs.
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


def test_revision_chainee_apres_usage_report_cursor():
    m = _load("0011_app_runtime_role")
    assert m.revision == "0011_app_runtime_role"
    assert m.down_revision == "0010_usage_report_cursor"


def test_role_cree_nosuperuser_nobypassrls():
    ddl = _load("0011_app_runtime_role")._CREATE_ROLE
    assert "CREATE ROLE app_runtime LOGIN NOSUPERUSER NOBYPASSRLS" in ddl
    # Idempotent : garde sur pg_roles + ALTER si déjà présent.
    assert "IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'app_runtime')" in ddl
    assert "ALTER ROLE app_runtime LOGIN NOSUPERUSER NOBYPASSRLS" in ddl


def test_aucun_mot_de_passe_dans_la_migration():
    """Hygiène secrets : le rôle est créé sans mot de passe (posé hors-bande au boot)."""
    m = _load("0011_app_runtime_role")
    assert "PASSWORD" not in m._CREATE_ROLE


def test_grants_couvrent_les_tables_rls_et_facturation():
    m = _load("0011_app_runtime_role")
    grants = "\n".join(m._GRANTS)
    # 7 tables RLS + parent + facturation en lecture/écriture.
    for table in (
        "analysis_history", "watchlist", "composite_score_history", "esg_score_history",
        "alert_history", "annotations", "usage_events", "tenants", "api_keys",
        "subscriptions", "stripe_events",
    ):
        assert table in grants
    assert "GRANT SELECT, INSERT, UPDATE, DELETE ON" in grants
    assert "GRANT SELECT ON plan_limits TO app_runtime" in grants
    assert "GRANT USAGE ON SCHEMA public TO app_runtime" in grants
    assert "GRANT USAGE ON ALL SEQUENCES IN SCHEMA public TO app_runtime" in grants


def test_downgrade_revoque_puis_drop_le_role():
    m = _load("0011_app_runtime_role")
    revokes = m._REVOKES
    assert any("REVOKE" in stmt for stmt in revokes)
    assert revokes[-1] == "DROP ROLE IF EXISTS app_runtime"


def test_statements_sans_point_virgule_terminal():
    """asyncpg via SQLAlchemy = une instruction par exécution → pas de `;` terminal sur GRANT/REVOKE."""
    m = _load("0011_app_runtime_role")
    for stmt in (*m._GRANTS, *m._REVOKES):
        assert not stmt.rstrip().endswith(";")


def test_upgrade_downgrade_appelables():
    m = _load("0011_app_runtime_role")
    assert callable(m.upgrade)
    assert callable(m.downgrade)
