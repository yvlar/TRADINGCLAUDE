"""Tests unitaires de la migration plan_limits (E4-S2) — sans DB.

Validation runtime (upgrade/downgrade, FK tenants.plan, application des bornes) faite par
le job CI `migrations` et les tests d'intégration. Ici on verrouille la forme et le chaînage.
"""
from __future__ import annotations

import importlib.util
from pathlib import Path
from types import ModuleType

import pytest


def _load(name: str) -> ModuleType:
    path = Path(__file__).resolve().parents[1] / "alembic" / "versions" / f"{name}.py"
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_revision_chainee_apres_usage_events():
    m = _load("0007_plan_limits")
    assert m.revision == "0007_plan_limits"
    assert m.down_revision == "0006_usage_events"


def test_upgrade_cree_la_table():
    m = _load("0007_plan_limits")
    assert "TABLE IF NOT EXISTS plan_limits" in m._UPGRADE_DDL


@pytest.mark.parametrize(
    "colonne",
    ["plan", "max_analyses_per_month", "max_screener_tickers", "retention_days", "created_at"],
)
def test_upgrade_contient_chaque_colonne(colonne: str):
    m = _load("0007_plan_limits")
    assert colonne in m._UPGRADE_DDL


def test_plan_est_cle_primaire():
    """Clé naturelle = nom du plan (table de référence globale, pas de tenant_id)."""
    m = _load("0007_plan_limits")
    assert "plan                   TEXT        PRIMARY KEY" in m._UPGRADE_DDL


def test_table_globale_sans_tenant_ni_rls():
    """Décision documentée : plan_limits est une table de référence GLOBALE — pas de RLS."""
    m = _load("0007_plan_limits")
    assert "tenant_id" not in m._UPGRADE_DDL
    assert "ROW LEVEL SECURITY" not in m._UPGRADE_DDL
    assert "CREATE POLICY" not in m._UPGRADE_DDL


@pytest.mark.parametrize("plan", ["free", "pro"])
def test_seed_des_plans_de_base(plan: str):
    m = _load("0007_plan_limits")
    assert f"('{plan}'," in m._UPGRADE_DDL
    assert "ON CONFLICT (plan) DO NOTHING" in m._UPGRADE_DDL


def test_rattachement_tenant_plan_avec_fk_et_defaut_free():
    """tenants.plan NOT NULL DEFAULT 'free' REFERENCES plan_limits(plan) (option a)."""
    m = _load("0007_plan_limits")
    assert "ALTER TABLE tenants ADD COLUMN IF NOT EXISTS plan TEXT NOT NULL DEFAULT 'free'" in m._UPGRADE_DDL
    assert "REFERENCES plan_limits(plan)" in m._UPGRADE_DDL


def test_downgrade_retire_colonne_puis_table():
    """Ordre inverse des FK : DROP COLUMN tenants.plan (et sa FK) → DROP TABLE plan_limits."""
    m = _load("0007_plan_limits")
    ddl = m._DOWNGRADE_DDL
    pos_col = ddl.index("DROP COLUMN IF EXISTS plan")
    pos_table = ddl.index("DROP TABLE IF EXISTS plan_limits")
    assert pos_col < pos_table


def test_upgrade_downgrade_appelables():
    m = _load("0007_plan_limits")
    assert callable(m.upgrade)
    assert callable(m.downgrade)
