"""Preuve que le rôle runtime `app_runtime` SUBIT la RLS multi-tenant (Ops S182).

Skippé hors PG migré : nécessite `APP_DATABASE_URL` pointant un PostgreSQL **migré**
(`alembic upgrade head` → migration `0011` a créé le rôle + GRANTs) et un mot de passe posé
hors-bande sur `app_runtime`. Exécuté en CI via le gate NOSUPERUSER.

Différence avec `test_rls_isolation.py` (rôle `rls_tester` provisionné à la main par le workflow) :
ici on se connecte sous le rôle **réel** `app_runtime` provisionné par la **migration** — ce test
prouve donc à la fois (a) que les GRANTs de la migration sont suffisants pour le runtime et (b) que
le rôle a bien les attributs `NOSUPERUSER`/`NOBYPASSRLS` qui le rendent soumis aux policies. Sous le
rôle `copilote` (SUPERUSER+BYPASSRLS) de `DATABASE_URL`, ces mêmes assertions échoueraient — d'où la
séparation runtime/migrations.
"""
from __future__ import annotations

import uuid

import asyncpg
import pytest

from tests.integration._rls_fixtures import APP_DB_URL as _APP_DB_URL
from tests.integration._rls_fixtures import app_runtime_pytestmark

pytestmark = app_runtime_pytestmark

_TENANT_A = "00000000-0000-0000-0000-000000000001"  # tenant legacy (présent après migration)
_TENANT_B = "00000000-0000-0000-0000-0000000000bb"


@pytest.mark.asyncio
async def test_app_runtime_est_nosuperuser_nobypassrls():
    """Le rôle de connexion runtime n'a aucun attribut qui court-circuiterait la RLS."""
    conn = await asyncpg.connect(_APP_DB_URL)
    try:
        row = await conn.fetchrow(
            "SELECT rolsuper, rolbypassrls FROM pg_roles WHERE rolname = current_user"
        )
        assert row is not None
        assert row["rolsuper"] is False, "app_runtime ne doit pas être SUPERUSER"
        assert row["rolbypassrls"] is False, "app_runtime ne doit pas avoir BYPASSRLS"
        assert await conn.fetchval("SELECT current_setting('is_superuser')") == "off"
    finally:
        await conn.close()


@pytest.mark.asyncio
async def test_app_runtime_subit_la_rls_via_pool_setup():
    """Un pool sous `app_runtime` voit la RLS s'appliquer : 0 ligne sans contexte, isolation par tenant.

    Chemin réel du runtime : `tenant_scope` (ContextVar) → `apply_tenant_context` (setup du pool) →
    GUC `app.tenant_id` → policy RLS. Témoin rouge→vert : la ligne de B existe (lue sous B) mais reste
    masquée à A et au contexte vide — c'est la policy qui filtre, pas l'absence de données.
    """
    from app.db.tenant_context import apply_tenant_context
    from tests.conftest import as_tenant

    probe = await asyncpg.connect(_APP_DB_URL)
    try:
        # Garde anti-faux-vert : un superuser contournerait la RLS et rendrait le test vacuous.
        if await probe.fetchval("SELECT current_setting('is_superuser')") == "on":
            pytest.skip("RLS contournée par un superuser — fournir le rôle app_runtime (NOSUPERUSER)")
    finally:
        await probe.close()

    pool = await asyncpg.create_pool(
        _APP_DB_URL, min_size=1, max_size=2, setup=apply_tenant_context
    )
    suffixe = uuid.uuid4().hex[:6].upper()
    ticker_a = f"APPRTA{suffixe}"
    ticker_b = f"APPRTB{suffixe}"
    like = f"APPRT%{suffixe}"
    tickers = {_TENANT_A: ticker_a, _TENANT_B: ticker_b}
    try:
        # Le tenant B doit exister (FK watchlist → tenants) ; créé sous son propre contexte.
        with as_tenant(_TENANT_B):
            await pool.execute(
                "INSERT INTO tenants (id, name, slug) VALUES ($1::uuid, 'app-runtime-B', $2) "
                "ON CONFLICT (id) DO NOTHING",
                _TENANT_B,
                f"app-runtime-b-{suffixe.lower()}",
            )

        for tenant, ticker in tickers.items():
            with as_tenant(tenant):
                await pool.execute(
                    "INSERT INTO watchlist (ticker, tenant_id) VALUES ($1, $2::uuid)",
                    ticker, tenant,
                )

        # Isolation : A ne voit que A, B ne voit que B.
        with as_tenant(_TENANT_A):
            rows_a = await pool.fetch("SELECT ticker FROM watchlist WHERE ticker LIKE $1", like)
        assert {r["ticker"] for r in rows_a} == {ticker_a}

        with as_tenant(_TENANT_B):
            rows_b = await pool.fetch("SELECT ticker FROM watchlist WHERE ticker LIKE $1", like)
        assert {r["ticker"] for r in rows_b} == {ticker_b}

        # Fail-closed : sans contexte tenant (GUC vide → NULL::uuid) → 0 ligne.
        async with pool.acquire() as conn:
            await conn.execute("SELECT set_config('app.tenant_id', '', false)")
            rows_none = await conn.fetch("SELECT ticker FROM watchlist WHERE ticker LIKE $1", like)
        assert rows_none == []
    finally:
        # NOSUPERUSER soumis à la RLS → supprimer chaque ligne sous son propre tenant.
        for tenant, ticker in tickers.items():
            with as_tenant(tenant):
                await pool.execute("DELETE FROM watchlist WHERE ticker = $1", ticker)
        await pool.close()
