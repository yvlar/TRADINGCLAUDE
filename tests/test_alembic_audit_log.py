"""Tests unitaires de la migration audit_log (E2-S3) — sans DB.

Validation runtime (upgrade/downgrade idempotents) faite par le job CI `migrations`
contre un vrai PostgreSQL ; ici on verrouille la forme et le chaînage de la révision.
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


def test_revision_chainee_apres_baseline():
    m = _load("0002_audit_log")
    assert m.revision == "0002_audit_log"
    assert m.down_revision == "0001_baseline"


def test_upgrade_cree_la_table():
    m = _load("0002_audit_log")
    assert "TABLE IF NOT EXISTS audit_log" in m._UPGRADE_DDL


@pytest.mark.parametrize(
    "colonne",
    ["tenant_id", "user_id", "action", "cible_type", "cible_id", "metadata", "created_at"],
)
def test_upgrade_contient_chaque_colonne(colonne: str):
    m = _load("0002_audit_log")
    assert colonne in m._UPGRADE_DDL


@pytest.mark.parametrize(
    "index", ["idx_audit_log_created_at", "idx_audit_log_cible"]
)
def test_upgrade_cree_chaque_index(index: str):
    m = _load("0002_audit_log")
    assert index in m._UPGRADE_DDL


def test_tenant_id_est_nullable_forward_compat():
    """tenant_id posé sans NOT NULL — peuplé à E3, pas de table tenants ici."""
    m = _load("0002_audit_log")
    assert "tenant_id   UUID,\n" in m._UPGRADE_DDL


def test_downgrade_supprime_la_table():
    m = _load("0002_audit_log")
    assert "DROP TABLE IF EXISTS audit_log" in m._DOWNGRADE_DDL


def test_upgrade_downgrade_appelables():
    m = _load("0002_audit_log")
    assert callable(m.upgrade)
    assert callable(m.downgrade)
