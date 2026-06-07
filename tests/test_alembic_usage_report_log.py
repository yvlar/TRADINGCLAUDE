"""Tests unitaires de la migration usage_report_log (E4-S9) — sans DB.

Validation runtime (upgrade/downgrade idempotent, PK, FK) faite par le job CI `migrations`.
Ici on verrouille la forme, le chaînage et la décision HORS RLS.
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


def test_revision_chainee_apres_stripe_billing():
    m = _load("0010_usage_report_log")
    assert m.revision == "0010_usage_report_log"
    assert m.down_revision == "0009_stripe_billing"


def test_upgrade_cree_table_avec_pk_composite_idempotence():
    """La PK (tenant_id, period_start) est la barrière anti-double-report d'une fenêtre."""
    ddl = _load("0010_usage_report_log")._UPGRADE_DDL
    assert "CREATE TABLE IF NOT EXISTS usage_report_log" in ddl
    assert "PRIMARY KEY (tenant_id, period_start)" in ddl


def test_upgrade_porte_quantite_et_horodatage_report():
    ddl = _load("0010_usage_report_log")._UPGRADE_DDL
    assert "quantity     BIGINT      NOT NULL" in ddl
    assert "reported_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()" in ddl


def test_tenant_id_reference_tenants():
    ddl = _load("0010_usage_report_log")._UPGRADE_DDL
    assert "tenant_id    UUID        NOT NULL REFERENCES tenants(id)" in ddl


def test_table_reste_hors_rls():
    """Décision documentée : worker legacy énumère tous les tenants → pas de RLS (comme subscriptions)."""
    ddl = _load("0010_usage_report_log")._UPGRADE_DDL
    assert "ROW LEVEL SECURITY" not in ddl
    assert "CREATE POLICY" not in ddl


def test_downgrade_retire_la_table():
    ddl = _load("0010_usage_report_log")._DOWNGRADE_DDL
    assert "DROP TABLE IF EXISTS usage_report_log" in ddl


def test_upgrade_downgrade_appelables():
    m = _load("0010_usage_report_log")
    assert callable(m.upgrade)
    assert callable(m.downgrade)
