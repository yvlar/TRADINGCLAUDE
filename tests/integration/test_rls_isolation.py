"""Isolation RLS runtime cross-tenant (E3-S3) — minimal, contre un vrai PostgreSQL.

Skippé par défaut : nécessite `RLS_TEST_DATABASE_URL` pointant un PostgreSQL **migré**
(`alembic upgrade head`) et un rôle **NOSUPERUSER** (un superuser contourne la RLS).
Le rôle doit avoir INSERT/SELECT sur `watchlist` et `tenants`.

La matrice exhaustive sur les 6 tables relève d'E3-S5 ; ici on prouve le mécanisme :
lecture isolée par tenant, écriture cross-tenant refusée (WITH CHECK), et fail-closed
sans contexte (GUC vide → 0 ligne).
"""
from __future__ import annotations

import os

import asyncpg
import pytest

_RLS_DB_URL = os.environ.get("RLS_TEST_DATABASE_URL")

pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(
        not _RLS_DB_URL,
        reason="RLS_TEST_DATABASE_URL non défini (PG migré + rôle NOSUPERUSER requis)",
    ),
]

_TENANT_A = "00000000-0000-0000-0000-000000000001"  # tenant legacy (présent après migration)
_TENANT_B = "00000000-0000-0000-0000-0000000000bb"


async def _set_tenant(conn: asyncpg.Connection, tenant: str) -> None:
    # is_local=true : portée transaction — annulée par le rollback final, zéro résidu.
    await conn.execute("SELECT set_config('app.tenant_id', $1, true)", tenant)


@pytest.mark.asyncio
async def test_rls_isole_les_tenants_et_refuse_l_ecriture_croisee():
    conn = await asyncpg.connect(_RLS_DB_URL)
    try:
        if await conn.fetchval("SELECT current_setting('is_superuser')") == "on":
            pytest.skip("RLS contournée par un superuser — fournir un rôle NOSUPERUSER")

        tr = conn.transaction()
        await tr.start()
        try:
            await conn.execute(
                "INSERT INTO tenants (id, name, slug) VALUES ($1::uuid, 'RLS-B', 'rls-test-b') "
                "ON CONFLICT (id) DO NOTHING",
                _TENANT_B,
            )

            await _set_tenant(conn, _TENANT_A)
            await conn.execute(
                "INSERT INTO watchlist (ticker, tenant_id) VALUES ('RLSTESTA', $1::uuid)",
                _TENANT_A,
            )
            await _set_tenant(conn, _TENANT_B)
            await conn.execute(
                "INSERT INTO watchlist (ticker, tenant_id) VALUES ('RLSTESTB', $1::uuid)",
                _TENANT_B,
            )

            await _set_tenant(conn, _TENANT_A)
            rows_a = await conn.fetch(
                "SELECT ticker FROM watchlist WHERE ticker LIKE 'RLSTEST%'"
            )
            assert {r["ticker"] for r in rows_a} == {"RLSTESTA"}

            await _set_tenant(conn, _TENANT_B)
            rows_b = await conn.fetch(
                "SELECT ticker FROM watchlist WHERE ticker LIKE 'RLSTEST%'"
            )
            assert {r["ticker"] for r in rows_b} == {"RLSTESTB"}

            # Fail-closed : GUC vide → NULLIF → NULL::uuid → aucune ligne (jamais d'erreur).
            await _set_tenant(conn, "")
            rows_none = await conn.fetch(
                "SELECT ticker FROM watchlist WHERE ticker LIKE 'RLSTEST%'"
            )
            assert rows_none == []

            # WITH CHECK : un tenant ne peut pas écrire la ligne d'un autre (abort la txn).
            await _set_tenant(conn, _TENANT_A)
            with pytest.raises(asyncpg.PostgresError):
                await conn.execute(
                    "INSERT INTO watchlist (ticker, tenant_id) VALUES ('RLSTESTX', $1::uuid)",
                    _TENANT_B,
                )
        finally:
            await tr.rollback()
    finally:
        await conn.close()
