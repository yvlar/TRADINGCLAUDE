"""Tests unitaires de la migration RLS sur les 6 tables métier (E3-S3) — sans DB.

Validation runtime (RLS active, isolation cross-tenant rouge→vert, fail-closed) faite
par le job CI `migrations` (idempotence upgrade/downgrade) et par le test d'intégration
`tests/integration/test_rls_isolation.py` (rôle NOSUPERUSER). Ici on verrouille la forme
et le chaînage de la révision.
"""
from __future__ import annotations

import importlib.util
from pathlib import Path
from types import ModuleType

import pytest

_TABLES = (
    "analysis_history",
    "watchlist",
    "composite_score_history",
    "esg_score_history",
    "alert_history",
    "annotations",
)


def _load(name: str) -> ModuleType:
    path = Path(__file__).resolve().parents[1] / "alembic" / "versions" / f"{name}.py"
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_revision_chainee_apres_business_tenant_id():
    m = _load("0005_business_rls")
    assert m.revision == "0005_business_rls"
    assert m.down_revision == "0004_business_tenant_id"


def test_couvre_exactement_les_six_tables_metier():
    m = _load("0005_business_rls")
    assert m._TABLES == _TABLES


@pytest.mark.parametrize("table", _TABLES)
def test_active_row_level_security(table: str):
    m = _load("0005_business_rls")
    assert f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY" in m._UPGRADE_DDL


@pytest.mark.parametrize("table", _TABLES)
def test_force_row_level_security(table: str):
    """FORCE RLS : le propriétaire de table est lui aussi soumis à la policy."""
    m = _load("0005_business_rls")
    assert f"ALTER TABLE {table} FORCE ROW LEVEL SECURITY" in m._UPGRADE_DDL


@pytest.mark.parametrize("table", _TABLES)
def test_cree_policy_isolation_par_table(table: str):
    m = _load("0005_business_rls")
    assert (
        f"CREATE POLICY {table}_tenant_isolation ON {table} " in m._UPGRADE_DDL
    )


@pytest.mark.parametrize("table", _TABLES)
def test_policy_porte_using_et_with_check(table: str):
    """USING filtre les lectures ; WITH CHECK empêche d'écrire la ligne d'un autre tenant.

    On verrouille le **même prédicat lié au tenant** dans les deux clauses : un
    `USING (true)` accidentel (qui exposerait tout) ne passerait pas ce test.
    """
    m = _load("0005_business_rls")
    create = next(
        line
        for line in m._UPGRADE_DDL.split(";")
        if f"CREATE POLICY {table}_tenant_isolation" in line
    )
    assert f"USING ({m._TENANT_PREDICATE})" in create
    assert f"WITH CHECK ({m._TENANT_PREDICATE})" in create


def test_predicat_fail_closed_via_nullif_current_setting():
    """GUC absent/vide → NULL::uuid → 0 ligne (jamais d'erreur, jamais tout visible)."""
    m = _load("0005_business_rls")
    assert (
        "NULLIF(current_setting('app.tenant_id', true), '')::uuid"
        in m._TENANT_PREDICATE
    )


@pytest.mark.parametrize("table", _TABLES)
def test_downgrade_retire_policy_puis_desactive(table: str):
    """Ordre : DROP POLICY (idempotent) avant DISABLE ROW LEVEL SECURITY."""
    m = _load("0005_business_rls")
    ddl = m._DOWNGRADE_DDL
    pos_drop = ddl.index(f"DROP POLICY IF EXISTS {table}_tenant_isolation ON {table}")
    pos_disable = ddl.index(f"ALTER TABLE {table} DISABLE ROW LEVEL SECURITY")
    assert pos_drop < pos_disable


def test_upgrade_downgrade_appelables():
    m = _load("0005_business_rls")
    assert callable(m.upgrade)
    assert callable(m.downgrade)
