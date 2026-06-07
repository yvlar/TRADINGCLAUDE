"""Tests unitaires de la migration api_keys.tenant_id (E4-S3) — sans DB.

Validation runtime (upgrade/downgrade, FK, backfill, NOT NULL) faite par le job CI
`migrations` et les tests d'intégration. Ici on verrouille la forme et le chaînage.
"""
from __future__ import annotations

import importlib.util
from pathlib import Path
from types import ModuleType

from app.models.tenant import LEGACY_TENANT_ID


def _load(name: str) -> ModuleType:
    path = Path(__file__).resolve().parents[1] / "alembic" / "versions" / f"{name}.py"
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_revision_chainee_apres_plan_limits():
    m = _load("0008_api_keys_tenant_id")
    assert m.revision == "0008_api_keys_tenant_id"
    assert m.down_revision == "0007_plan_limits"


def test_upgrade_ajoute_colonne_tenant_id_avec_fk():
    m = _load("0008_api_keys_tenant_id")
    ddl = m._UPGRADE_DDL
    assert "ADD COLUMN IF NOT EXISTS tenant_id UUID REFERENCES tenants(id)" in ddl


def test_upgrade_backfill_legacy_puis_set_not_null():
    """Pattern backfill-avant-NOT-NULL : UPDATE legacy doit précéder le SET NOT NULL."""
    m = _load("0008_api_keys_tenant_id")
    ddl = m._UPGRADE_DDL
    pos_update = ddl.index("UPDATE api_keys SET tenant_id")
    pos_not_null = ddl.index("ALTER COLUMN tenant_id SET NOT NULL")
    assert pos_update < pos_not_null


def test_upgrade_cree_index_tenant():
    m = _load("0008_api_keys_tenant_id")
    assert "CREATE INDEX IF NOT EXISTS idx_api_keys_tenant ON api_keys (tenant_id)" in m._UPGRADE_DDL


def test_api_keys_reste_hors_rls():
    """Décision documentée : api_keys est la table d'authn lue avant le contexte tenant — pas de RLS."""
    m = _load("0008_api_keys_tenant_id")
    ddl = m._UPGRADE_DDL
    assert "ROW LEVEL SECURITY" not in ddl
    assert "CREATE POLICY" not in ddl


def test_uuid_legacy_egal_a_la_constante():
    """Le littéral figé de la migration doit égaler la source applicative LEGACY_TENANT_ID."""
    m = _load("0008_api_keys_tenant_id")
    assert m._LEGACY_TENANT_ID == str(LEGACY_TENANT_ID)


def test_downgrade_retire_index_puis_colonne():
    """Ordre inverse des FK : DROP INDEX → DROP COLUMN (et donc la FK)."""
    m = _load("0008_api_keys_tenant_id")
    ddl = m._DOWNGRADE_DDL
    pos_index = ddl.index("DROP INDEX IF EXISTS idx_api_keys_tenant")
    pos_col = ddl.index("DROP COLUMN IF EXISTS tenant_id")
    assert pos_index < pos_col


def test_upgrade_downgrade_appelables():
    m = _load("0008_api_keys_tenant_id")
    assert callable(m.upgrade)
    assert callable(m.downgrade)
