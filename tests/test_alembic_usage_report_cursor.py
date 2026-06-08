"""Tests unitaires de la migration curseur de report d'usage (E4-S9) — sans DB.

Validation runtime (upgrade/downgrade idempotent) faite par le job CI `migrations`. Ici on
verrouille la forme et le chaînage après 0009.
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
    m = _load("0010_usage_report_cursor")
    assert m.revision == "0010_usage_report_cursor"
    assert m.down_revision == "0009_stripe_billing"


def test_upgrade_ajoute_colonne_curseur_nullable():
    ddl = _load("0010_usage_report_cursor")._UPGRADE_DDL
    assert "ALTER TABLE subscriptions ADD COLUMN IF NOT EXISTS usage_reported_through TIMESTAMPTZ" in ddl
    # Nullable (pas de NOT NULL) : NULL = jamais rapporté, première fenêtre couvre tout l'historique.
    assert "NOT NULL" not in ddl


def test_colonne_reste_hors_rls():
    """Curseur additif sur subscriptions (déjà HORS RLS) — aucune policy introduite."""
    ddl = _load("0010_usage_report_cursor")._UPGRADE_DDL
    assert "ROW LEVEL SECURITY" not in ddl
    assert "CREATE POLICY" not in ddl


def test_downgrade_retire_la_colonne():
    ddl = _load("0010_usage_report_cursor")._DOWNGRADE_DDL
    assert "DROP COLUMN IF EXISTS usage_reported_through" in ddl


def test_upgrade_downgrade_appelables():
    m = _load("0010_usage_report_cursor")
    assert callable(m.upgrade)
    assert callable(m.downgrade)
