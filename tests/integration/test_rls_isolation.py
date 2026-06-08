"""Isolation RLS runtime cross-tenant — matrice exhaustive sur les 6 tables (E3-S5).

Skippé par défaut : nécessite `RLS_TEST_DATABASE_URL` pointant un PostgreSQL **migré**
(`alembic upgrade head`) et un rôle **NOSUPERUSER** (un superuser contourne la RLS).
Le rôle doit avoir SELECT/INSERT/UPDATE/DELETE sur les 6 tables métier + `tenants`, et
USAGE sur les séquences (les tables BIGSERIAL `esg_score_history`/`alert_history` en dépendent).

La matrice prouve, **table par table** et en **rouge→vert**, que :
- (a) lecture isolée — un tenant A ne voit que ses propres lignes (`USING`) ;
- (b) `WITH CHECK` — A ne peut pas écrire une ligne rattachée à B ;
- (c) fail-closed — sans contexte tenant (GUC vide) → 0 ligne, jamais d'erreur.

Le second test prouve le chemin réel du threading (E3-S4) : `ContextVar` → setup du
pool → GUC → RLS.
"""
from __future__ import annotations

import os
import uuid
from collections.abc import Callable

import asyncpg
import pytest

from tests.integration._rls_fixtures import RLS_TABLES as _TABLES

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

# Inventaire des 7 tables RLS importé de `_rls_fixtures` (source unique) : les 6 tables métier
# (0005_business_rls) + `usage_events` (0006_usage_events, E4-S1) partagent la même policy tenant,
# donc la même matrice d'isolation.

# Colonnes minimales valides par table : la colonne porteuse du marqueur (pour filtrer
# les lignes du test) + les NOT NULL sans défaut + `tenant_id`. Chaque entrée donne la
# colonne-marqueur et une fabrique (tenant, marqueur) → liste de (colonne, valeur, cast).
# `analysis_id` (annotations) est UNIQUE global → un UUID neuf par insertion.
_PayloadBuilder = Callable[[str, str], list[tuple[str, object, str]]]
_PAYLOADS: dict[str, tuple[str, _PayloadBuilder]] = {
    "analysis_history": (
        "ticker",
        lambda tenant, marker: [
            ("ticker", marker, ""),
            ("input_data", "{}", "::jsonb"),
            ("result", "{}", "::jsonb"),
            ("tenant_id", tenant, "::uuid"),
        ],
    ),
    "watchlist": (
        "ticker",
        lambda tenant, marker: [
            ("ticker", marker, ""),
            ("tenant_id", tenant, "::uuid"),
        ],
    ),
    "composite_score_history": (
        "ticker",
        lambda tenant, marker: [
            ("ticker", marker, ""),
            ("score", 0.0, ""),
            ("label", "test", ""),
            ("tenant_id", tenant, "::uuid"),
        ],
    ),
    "esg_score_history": (
        "ticker",
        lambda tenant, marker: [
            ("ticker", marker, ""),
            ("score", 0.0, ""),
            ("verdict", "ESG_FAIBLE", ""),
            ("tenant_id", tenant, "::uuid"),
        ],
    ),
    "alert_history": (
        "ticker",
        lambda tenant, marker: [
            ("ticker", marker, ""),
            ("type", "prix", ""),
            ("tenant_id", tenant, "::uuid"),
        ],
    ),
    "annotations": (
        "note",
        lambda tenant, marker: [
            ("analysis_id", str(uuid.uuid4()), "::uuid"),
            ("note", marker, ""),
            ("tenant_id", tenant, "::uuid"),
        ],
    ),
    "usage_events": (
        "skill",
        lambda tenant, marker: [
            ("skill", marker, ""),
            ("workflow", "value_graham", ""),
            ("tenant_id", tenant, "::uuid"),
        ],
    ),
}


async def _set_tenant(conn: asyncpg.Connection, tenant: str) -> None:
    # is_local=true : portée transaction — annulée par le rollback final, zéro résidu.
    await conn.execute("SELECT set_config('app.tenant_id', $1, true)", tenant)


def _build_insert(table: str, payload: list[tuple[str, object, str]]) -> tuple[str, list[object]]:
    """Construit l'INSERT paramétré (placeholders `$n` + casts) et la liste de valeurs."""
    cols = ", ".join(col for col, _, _ in payload)
    placeholders = ", ".join(f"${i + 1}{cast}" for i, (_, _, cast) in enumerate(payload))
    values = [value for _, value, _ in payload]
    return f"INSERT INTO {table} ({cols}) VALUES ({placeholders})", values


@pytest.mark.asyncio
@pytest.mark.parametrize("table", _TABLES)
async def test_matrice_isolation_cross_tenant(table: str):
    """Pour chaque table métier : lecture isolée + WITH CHECK + fail-closed (NOSUPERUSER).

    Témoin rouge→vert : la MÊME requête de lecture renvoie {A} sous GUC=A et {B} sous
    GUC=B — donc les deux lignes existent bel et bien, et c'est la **policy** (pas
    l'absence de données) qui masque celle de l'autre tenant. Sans la RLS, chaque
    lecture verrait {A, B} et l'égalité échouerait : le test est vert *parce que* la
    policy filtre.
    """
    marker_column, builder = _PAYLOADS[table]
    suffixe = uuid.uuid4().hex[:8].upper()
    marker_a = f"RLSA{suffixe}"
    marker_b = f"RLSB{suffixe}"
    like = f"RLS%{suffixe}"

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

            # Insertion légitime sous chaque tenant (GUC == tenant_id → WITH CHECK satisfait).
            await _set_tenant(conn, _TENANT_A)
            sql_a, vals_a = _build_insert(table, builder(_TENANT_A, marker_a))
            await conn.execute(sql_a, *vals_a)

            await _set_tenant(conn, _TENANT_B)
            sql_b, vals_b = _build_insert(table, builder(_TENANT_B, marker_b))
            await conn.execute(sql_b, *vals_b)

            select = f"SELECT {marker_column} AS m FROM {table} WHERE {marker_column} LIKE $1"

            # (a) Lecture isolée — A ne voit que A.
            await _set_tenant(conn, _TENANT_A)
            rows_a = await conn.fetch(select, like)
            assert {r["m"] for r in rows_a} == {marker_a}

            # Témoin rouge→vert — MÊME requête, GUC=B → seulement B (la ligne de B existe,
            # masquée à A par la seule policy).
            await _set_tenant(conn, _TENANT_B)
            rows_b = await conn.fetch(select, like)
            assert {r["m"] for r in rows_b} == {marker_b}

            # (c) Fail-closed — GUC vide → NULLIF → NULL::uuid → 0 ligne (jamais d'erreur).
            await _set_tenant(conn, "")
            rows_none = await conn.fetch(select, like)
            assert rows_none == []

            # (b) WITH CHECK — A ne peut pas écrire une ligne de B (abort la txn → en dernier).
            await _set_tenant(conn, _TENANT_A)
            sql_x, vals_x = _build_insert(table, builder(_TENANT_B, f"RLSX{suffixe}"))
            with pytest.raises(asyncpg.PostgresError):
                await conn.execute(sql_x, *vals_x)
        finally:
            await tr.rollback()
    finally:
        await conn.close()


@pytest.mark.asyncio
async def test_threading_contextvar_isole_deux_tenants_reels_via_pool_setup():
    """E3-S4 : le tenant posé dans le ContextVar (pas le GUC manuel) isole les écritures/lectures.

    Prouve le chemin réel du sprint : `set_current_tenant` → `apply_tenant_context` (setup du
    pool, rejoué à chaque acquire) → GUC → RLS. Deux tenants distincts, rôle NOSUPERUSER.
    """
    from app.db.tenant_context import apply_tenant_context
    from tests.conftest import as_tenant

    # Garde : un superuser contourne la RLS — le test serait faussement vert.
    probe = await asyncpg.connect(_RLS_DB_URL)
    try:
        if await probe.fetchval("SELECT current_setting('is_superuser')") == "on":
            pytest.skip("RLS contournée par un superuser — fournir un rôle NOSUPERUSER")
        await probe.execute(
            "INSERT INTO tenants (id, name, slug) VALUES ($1::uuid, 'RLS-B', 'rls-test-b') "
            "ON CONFLICT (id) DO NOTHING",
            _TENANT_B,
        )
    finally:
        await probe.close()

    pool = await asyncpg.create_pool(_RLS_DB_URL, min_size=1, max_size=2, setup=apply_tenant_context)
    # Tickers distincts par tenant : l'index unique (ticker, workflow) du watchlist est global,
    # pas tenant-scoped — deux tenants ne peuvent donc pas partager un ticker (gotcha hors E3-S4).
    suffixe = uuid.uuid4().hex[:6].upper()
    ticker_a = f"THREADA{suffixe}"
    ticker_b = f"THREADB{suffixe}"
    tickers = {_TENANT_A: ticker_a, _TENANT_B: ticker_b}
    try:
        # Écriture sous tenant A puis B (le setup pose le GUC depuis le ContextVar à l'acquire).
        for tenant, ticker in tickers.items():
            with as_tenant(tenant):
                await pool.execute(
                    "INSERT INTO watchlist (ticker, tenant_id) VALUES ($1, $2::uuid)",
                    ticker, tenant,
                )

        # Lecture isolée : A ne voit que SON ticker, B que le sien (jamais celui de l'autre).
        with as_tenant(_TENANT_A):
            rows_a = await pool.fetch(
                "SELECT ticker FROM watchlist WHERE ticker LIKE $1", f"THREAD%{suffixe}"
            )
        assert {r["ticker"] for r in rows_a} == {ticker_a}

        with as_tenant(_TENANT_B):
            rows_b = await pool.fetch(
                "SELECT ticker FROM watchlist WHERE ticker LIKE $1", f"THREAD%{suffixe}"
            )
        assert {r["ticker"] for r in rows_b} == {ticker_b}
    finally:
        # Nettoyage : NOSUPERUSER soumis à la RLS → supprimer chaque ligne sous son propre tenant.
        for tenant, ticker in tickers.items():
            with as_tenant(tenant):
                await pool.execute("DELETE FROM watchlist WHERE ticker = $1", ticker)
        await pool.close()
