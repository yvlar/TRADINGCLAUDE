"""Tests unitaires de la migration Stripe Billing (E4-S7) — sans DB.

Validation runtime (upgrade/downgrade idempotent, FK, index) faite par le job CI
`migrations` et le test d'intégration. Ici on verrouille la forme et le chaînage.
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


def test_revision_chainee_apres_api_keys_tenant():
    m = _load("0009_stripe_billing")
    assert m.revision == "0009_stripe_billing"
    assert m.down_revision == "0008_api_keys_tenant_id"


def test_upgrade_cree_table_subscriptions_avec_pk_tenant():
    ddl = _load("0009_stripe_billing")._UPGRADE_DDL
    assert "CREATE TABLE IF NOT EXISTS subscriptions" in ddl
    assert "tenant_id              UUID        PRIMARY KEY REFERENCES tenants(id)" in ddl


def test_subscriptions_plan_fk_plan_limits():
    """Le plan de la souscription référence plan_limits (intégrité avec les bornes de quota)."""
    ddl = _load("0009_stripe_billing")._UPGRADE_DDL
    assert "plan                   TEXT        NOT NULL DEFAULT 'free' REFERENCES plan_limits(plan)" in ddl


def test_upgrade_cree_index_resolution_webhook():
    """Index sur les identifiants Stripe → résolution du tenant depuis un événement webhook."""
    ddl = _load("0009_stripe_billing")._UPGRADE_DDL
    assert "idx_subscriptions_customer" in ddl
    assert "idx_subscriptions_subscription" in ddl


def test_upgrade_cree_table_idempotence_stripe_events():
    ddl = _load("0009_stripe_billing")._UPGRADE_DDL
    assert "CREATE TABLE IF NOT EXISTS stripe_events" in ddl
    assert "event_id    TEXT        PRIMARY KEY" in ddl


def test_tables_billing_restent_hors_rls():
    """Décision documentée : subscriptions/stripe_events lues par le webhook hors contexte tenant → pas de RLS."""
    ddl = _load("0009_stripe_billing")._UPGRADE_DDL
    assert "ROW LEVEL SECURITY" not in ddl
    assert "CREATE POLICY" not in ddl


def test_downgrade_retire_les_deux_tables():
    ddl = _load("0009_stripe_billing")._DOWNGRADE_DDL
    assert "DROP TABLE IF EXISTS stripe_events" in ddl
    assert "DROP TABLE IF EXISTS subscriptions" in ddl


def test_upgrade_downgrade_appelables():
    m = _load("0009_stripe_billing")
    assert callable(m.upgrade)
    assert callable(m.downgrade)
