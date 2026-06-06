"""Tests unitaires de la migration usage_events (E4-S1) — sans DB.

Validation runtime (upgrade/downgrade idempotents, isolation RLS cross-tenant) faite par
le job CI `migrations` et `tests/integration/test_rls_isolation.py` (usage_events est la
7ᵉ table de la matrice). Ici on verrouille la forme et le chaînage de la révision.
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


def test_revision_chainee_apres_business_rls():
    m = _load("0006_usage_events")
    assert m.revision == "0006_usage_events"
    assert m.down_revision == "0005_business_rls"


def test_upgrade_cree_la_table():
    m = _load("0006_usage_events")
    assert "TABLE IF NOT EXISTS usage_events" in m._UPGRADE_DDL


@pytest.mark.parametrize(
    "colonne",
    ["id", "tenant_id", "skill", "workflow", "cost_usd", "tokens_input", "tokens_output", "created_at"],
)
def test_upgrade_contient_chaque_colonne(colonne: str):
    m = _load("0006_usage_events")
    assert colonne in m._UPGRADE_DDL


def test_tenant_id_not_null_fk_tenants():
    """tenant_id NOT NULL REFERENCES tenants(id) → la table entre dans le périmètre RLS."""
    m = _load("0006_usage_events")
    assert "tenant_id     UUID           NOT NULL REFERENCES tenants(id)" in m._UPGRADE_DDL


def test_cost_usd_numerique_precis():
    """Précision monétaire exacte — NUMERIC, jamais float."""
    m = _load("0006_usage_events")
    assert "cost_usd      NUMERIC(10, 6)" in m._UPGRADE_DDL


def test_upgrade_cree_index_tenant_created():
    m = _load("0006_usage_events")
    assert "idx_usage_events_tenant_created" in m._UPGRADE_DDL
    assert "(tenant_id, created_at DESC)" in m._UPGRADE_DDL


def test_pas_de_fk_vers_analysis_history():
    """Append-only : l'événement survit à la purge de l'analyse (lien sémantique, pas FK)."""
    m = _load("0006_usage_events")
    assert "analysis_history" not in m._UPGRADE_DDL


def test_active_et_force_row_level_security():
    m = _load("0006_usage_events")
    assert "ALTER TABLE usage_events ENABLE ROW LEVEL SECURITY" in m._UPGRADE_DDL
    assert "ALTER TABLE usage_events FORCE ROW LEVEL SECURITY" in m._UPGRADE_DDL


def test_cree_policy_isolation_using_et_with_check():
    """USING filtre les lectures ; WITH CHECK empêche d'écrire la ligne d'un autre tenant."""
    m = _load("0006_usage_events")
    create = next(
        line
        for line in m._UPGRADE_DDL.split(";")
        if "CREATE POLICY usage_events_tenant_isolation" in line
    )
    assert f"USING ({m._TENANT_PREDICATE})" in create
    assert f"WITH CHECK ({m._TENANT_PREDICATE})" in create


def test_predicat_fail_closed_via_nullif_current_setting():
    """GUC absent/vide → NULL::uuid → 0 ligne (jamais d'erreur, jamais tout visible)."""
    m = _load("0006_usage_events")
    assert (
        "NULLIF(current_setting('app.tenant_id', true), '')::uuid" in m._TENANT_PREDICATE
    )


def test_downgrade_retire_policy_puis_table():
    """Ordre : DROP POLICY (idempotent) → DISABLE RLS → DROP TABLE."""
    m = _load("0006_usage_events")
    ddl = m._DOWNGRADE_DDL
    pos_policy = ddl.index("DROP POLICY IF EXISTS usage_events_tenant_isolation")
    pos_disable = ddl.index("DISABLE ROW LEVEL SECURITY")
    pos_table = ddl.index("DROP TABLE IF EXISTS usage_events")
    assert pos_policy < pos_disable < pos_table


def test_upgrade_downgrade_appelables():
    m = _load("0006_usage_events")
    assert callable(m.upgrade)
    assert callable(m.downgrade)
