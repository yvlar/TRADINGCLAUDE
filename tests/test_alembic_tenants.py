"""Tests unitaires de la migration tenants (E3-S1) — sans DB.

Validation runtime (upgrade/downgrade idempotents + backfill réel) faite par le job
CI `migrations` contre un vrai PostgreSQL ; ici on verrouille la forme et le chaînage
de la révision, ainsi que la cohérence de l'UUID legacy avec le code applicatif.
"""
from __future__ import annotations

import importlib.util
from pathlib import Path
from types import ModuleType

import pytest

from app.models.tenant import LEGACY_TENANT_ID, LEGACY_TENANT_NAME, LEGACY_TENANT_SLUG


def _load(name: str) -> ModuleType:
    path = Path(__file__).resolve().parents[1] / "alembic" / "versions" / f"{name}.py"
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_revision_chainee_apres_audit_log():
    m = _load("0003_tenants")
    assert m.revision == "0003_tenants"
    assert m.down_revision == "0002_audit_log"


def test_upgrade_cree_la_table_tenants():
    m = _load("0003_tenants")
    assert "TABLE IF NOT EXISTS tenants" in m._UPGRADE_DDL


@pytest.mark.parametrize("colonne", ["id", "name", "slug", "created_at"])
def test_tenants_contient_chaque_colonne(colonne: str):
    m = _load("0003_tenants")
    assert colonne in m._UPGRADE_DDL


def test_slug_est_unique():
    m = _load("0003_tenants")
    assert "slug        TEXT         NOT NULL UNIQUE" in m._UPGRADE_DDL


def test_insere_tenant_legacy():
    m = _load("0003_tenants")
    assert "INSERT INTO tenants" in m._UPGRADE_DDL
    assert "ON CONFLICT (slug) DO NOTHING" in m._UPGRADE_DDL


def test_valeurs_legacy_coherentes_avec_le_code():
    """Les littéraux figés dans la migration doivent égaler les constantes app.models.tenant."""
    m = _load("0003_tenants")
    assert m._LEGACY_TENANT_ID == str(LEGACY_TENANT_ID)
    assert f"'{LEGACY_TENANT_SLUG}'" in m._UPGRADE_DDL
    assert f"'{LEGACY_TENANT_NAME}'" in m._UPGRADE_DDL


def test_ajoute_colonne_tenant_id_aux_users():
    m = _load("0003_tenants")
    assert "ALTER TABLE users ADD COLUMN IF NOT EXISTS tenant_id UUID REFERENCES tenants(id)" in m._UPGRADE_DDL


def test_backfill_avant_not_null():
    """Le backfill UPDATE précède le SET NOT NULL (sinon échec sur lignes existantes)."""
    m = _load("0003_tenants")
    ddl = m._UPGRADE_DDL
    pos_backfill = ddl.index("UPDATE users SET tenant_id")
    pos_not_null = ddl.index("ALTER COLUMN tenant_id SET NOT NULL")
    assert pos_backfill < pos_not_null


def test_cree_index_tenant():
    m = _load("0003_tenants")
    assert "idx_users_tenant" in m._UPGRADE_DDL


def test_downgrade_retire_colonne_index_et_table():
    m = _load("0003_tenants")
    ddl = m._DOWNGRADE_DDL
    assert "DROP INDEX IF EXISTS idx_users_tenant" in ddl
    assert "DROP COLUMN IF EXISTS tenant_id" in ddl
    assert "DROP TABLE IF EXISTS tenants" in ddl
    # Ordre FK inverse : colonne (donc FK) retirée avant la table.
    assert ddl.index("DROP COLUMN IF EXISTS tenant_id") < ddl.index("DROP TABLE IF EXISTS tenants")


def test_upgrade_downgrade_appelables():
    m = _load("0003_tenants")
    assert callable(m.upgrade)
    assert callable(m.downgrade)
