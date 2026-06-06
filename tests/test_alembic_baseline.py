"""Tests unitaires de la migration baseline Alembic (E2-S1) — sans DB.

La validation runtime (upgrade/downgrade idempotents) est faite par le job CI
`migrations` contre un vrai PostgreSQL ; ici on verrouille la forme de la migration.
"""
from __future__ import annotations

import importlib.util
from pathlib import Path
from types import ModuleType

import pytest

_TABLES = [
    "analysis_history",
    "watchlist",
    "composite_score_history",
    "esg_score_history",
    "api_keys",
    "alert_history",
    "annotations",
    "users",
    "refresh_tokens",
    "user_preferences",
]


def _load_baseline() -> ModuleType:
    path = Path(__file__).resolve().parents[1] / "alembic" / "versions" / "0001_baseline_schema.py"
    spec = importlib.util.spec_from_file_location("baseline_mig", path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_revision_est_la_racine():
    m = _load_baseline()
    assert m.revision == "0001_baseline"
    assert m.down_revision is None


@pytest.mark.parametrize("table", _TABLES)
def test_upgrade_cree_chaque_table(table: str):
    m = _load_baseline()
    assert f"TABLE IF NOT EXISTS {table}" in m._BASELINE_DDL


@pytest.mark.parametrize("table", _TABLES)
def test_downgrade_supprime_chaque_table(table: str):
    m = _load_baseline()
    assert f"DROP TABLE IF EXISTS {table}" in m._DROP_DDL


def test_upgrade_downgrade_sont_appelables():
    m = _load_baseline()
    assert callable(m.upgrade)
    assert callable(m.downgrade)
