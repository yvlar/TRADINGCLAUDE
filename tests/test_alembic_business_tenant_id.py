"""Tests unitaires de la migration tenant_id sur les 6 tables métier (E3-S2) — sans DB.

Validation runtime (upgrade/downgrade idempotents + backfill réel) faite par le job
CI `migrations` contre un vrai PostgreSQL ; ici on verrouille la forme et le chaînage
de la révision, ainsi que la cohérence de l'UUID legacy avec le code applicatif.
"""
from __future__ import annotations

import importlib.util
from pathlib import Path
from types import ModuleType

import pytest

from app.models.tenant import LEGACY_TENANT_ID

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


def test_revision_chainee_apres_tenants():
    m = _load("0004_business_tenant_id")
    assert m.revision == "0004_business_tenant_id"
    assert m.down_revision == "0003_tenants"


def test_couvre_exactement_les_six_tables_metier():
    m = _load("0004_business_tenant_id")
    assert m._TABLES == _TABLES


@pytest.mark.parametrize("table", _TABLES)
def test_ajoute_colonne_tenant_id_avec_fk(table: str):
    m = _load("0004_business_tenant_id")
    assert (
        f"ALTER TABLE {table} ADD COLUMN IF NOT EXISTS tenant_id UUID REFERENCES tenants(id)"
        in m._UPGRADE_DDL
    )


@pytest.mark.parametrize("table", _TABLES)
def test_backfill_legacy_par_table(table: str):
    m = _load("0004_business_tenant_id")
    assert (
        f"UPDATE {table} SET tenant_id = '{m._LEGACY_TENANT_ID}' WHERE tenant_id IS NULL"
        in m._UPGRADE_DDL
    )


@pytest.mark.parametrize("table", _TABLES)
def test_set_not_null_par_table(table: str):
    m = _load("0004_business_tenant_id")
    assert f"ALTER TABLE {table} ALTER COLUMN tenant_id SET NOT NULL" in m._UPGRADE_DDL


@pytest.mark.parametrize("table", _TABLES)
def test_cree_index_tenant_par_table(table: str):
    m = _load("0004_business_tenant_id")
    assert (
        f"CREATE INDEX IF NOT EXISTS idx_{table}_tenant ON {table} (tenant_id)"
        in m._UPGRADE_DDL
    )


@pytest.mark.parametrize("table", _TABLES)
def test_backfill_avant_not_null_par_table(table: str):
    """Le backfill UPDATE précède le SET NOT NULL (sinon échec sur lignes existantes)."""
    m = _load("0004_business_tenant_id")
    ddl = m._UPGRADE_DDL
    pos_backfill = ddl.index(f"UPDATE {table} SET tenant_id")
    pos_not_null = ddl.index(f"ALTER TABLE {table} ALTER COLUMN tenant_id SET NOT NULL")
    assert pos_backfill < pos_not_null


def test_valeur_legacy_coherente_avec_le_code():
    """Le littéral figé dans la migration doit égaler la constante app.models.tenant."""
    m = _load("0004_business_tenant_id")
    assert m._LEGACY_TENANT_ID == str(LEGACY_TENANT_ID)


@pytest.mark.parametrize("table", _TABLES)
def test_downgrade_retire_index_puis_colonne(table: str):
    """Ordre FK inverse : index retiré avant la colonne (donc la FK)."""
    m = _load("0004_business_tenant_id")
    ddl = m._DOWNGRADE_DDL
    pos_index = ddl.index(f"DROP INDEX IF EXISTS idx_{table}_tenant")
    pos_colonne = ddl.index(f"ALTER TABLE {table} DROP COLUMN IF EXISTS tenant_id")
    assert pos_index < pos_colonne


def test_upgrade_downgrade_appelables():
    m = _load("0004_business_tenant_id")
    assert callable(m.upgrade)
    assert callable(m.downgrade)
