"""Preuve que le durcissement S186 tient sous le rôle réel `app_runtime` : zéro privilège `PUBLIC`,
non-propriété des tables, accès conservé via le GRANT explicite.

Skippé hors PG migré : nécessite `APP_DATABASE_URL` pointant un PostgreSQL **migré**
(`alembic upgrade head` → migrations `0011`+`0012` appliquées) et un mot de passe posé hors-bande sur
`app_runtime`. Exécuté en CI via le gate NOSUPERUSER.

Complète `test_app_runtime_rls.py` (qui prouve que le rôle SUBIT la RLS) : ici on prouve l'autre
moitié de §2.3 de `docs/revue-owasp-rls-2026-06.md` — (a) `app_runtime` n'est propriétaire d'aucune
table RLS (sinon il pourrait `DISABLE`/`NO FORCE` sa propre RLS), et (b) plus aucun privilège ne
provient du pseudo-rôle `PUBLIC` (schéma + tables), tout en gardant ses accès via le GRANT explicite.
"""
from __future__ import annotations

import os

import asyncpg
import pytest

_APP_DB_URL = os.environ.get("APP_DATABASE_URL")

pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(
        not _APP_DB_URL,
        reason="APP_DATABASE_URL non défini (PG migré + rôle app_runtime requis)",
    ),
]

# 7 tables RLS (sous-ensemble de `0011._RW_TABLES` portant ENABLE+FORCE RLS).
_RLS_TABLES = (
    "analysis_history",
    "watchlist",
    "composite_score_history",
    "esg_score_history",
    "alert_history",
    "annotations",
    "usage_events",
)


@pytest.mark.asyncio
async def test_app_runtime_n_est_proprietaire_d_aucune_table_rls():
    """Non-propriété : un propriétaire pourrait DISABLE/NO FORCE sa propre RLS (OWASP §2.3)."""
    conn = await asyncpg.connect(_APP_DB_URL)
    try:
        rows = await conn.fetch(
            "SELECT relname, pg_get_userbyid(relowner) AS owner "
            "FROM pg_class WHERE relname = ANY($1::text[])",
            list(_RLS_TABLES),
        )
        assert {r["relname"] for r in rows} == set(_RLS_TABLES), "tables RLS introuvables (PG migré ?)"
        for row in rows:
            assert row["owner"] != "app_runtime", (
                f"{row['relname']} appartient à app_runtime → il pourrait désactiver sa RLS"
            )
    finally:
        await conn.close()


@pytest.mark.asyncio
async def test_aucun_privilege_via_public_sur_le_schema():
    """Le schéma `public` n'accorde plus rien à PUBLIC (grantee vide dans l'aclitem = `=…/…`)."""
    conn = await asyncpg.connect(_APP_DB_URL)
    try:
        nspacl = await conn.fetchval(
            "SELECT nspacl FROM pg_namespace WHERE nspname = 'public'"
        )
        # nspacl peut être NULL (aucun privilège explicite = défaut owner-only) — pas de PUBLIC.
        public_entries = [str(a) for a in (nspacl or []) if str(a).startswith("=")]
        assert public_entries == [], f"PUBLIC conserve un privilège sur le schéma : {public_entries}"
    finally:
        await conn.close()


@pytest.mark.asyncio
async def test_aucun_privilege_via_public_sur_les_tables_rls():
    """Aucune table RLS n'accorde de privilège à PUBLIC (aclitem à grantee vide)."""
    conn = await asyncpg.connect(_APP_DB_URL)
    try:
        rows = await conn.fetch(
            "SELECT relname, relacl FROM pg_class WHERE relname = ANY($1::text[])",
            list(_RLS_TABLES),
        )
        # Anti-faux-vert : sans cette garde, 0 ligne (mauvaise DB) passerait avec offenders vide.
        assert {r["relname"] for r in rows} == set(_RLS_TABLES), "tables RLS introuvables (PG migré ?)"
        offenders: dict[str, list[str]] = {}
        for row in rows:
            public_entries = [str(a) for a in (row["relacl"] or []) if str(a).startswith("=")]
            if public_entries:
                offenders[row["relname"]] = public_entries
        assert offenders == {}, f"PUBLIC conserve des privilèges sur des tables RLS : {offenders}"
    finally:
        await conn.close()


@pytest.mark.asyncio
async def test_app_runtime_conserve_son_acces_via_grant_explicite():
    """Le durcissement ne casse pas le runtime : accès SELECT/INSERT conservé via le GRANT direct."""
    conn = await asyncpg.connect(_APP_DB_URL)
    try:
        for table in _RLS_TABLES:
            for priv in ("SELECT", "INSERT"):
                granted = await conn.fetchval(
                    "SELECT has_table_privilege('app_runtime', $1, $2)", table, priv
                )
                assert granted is True, f"app_runtime a perdu {priv} sur {table} après le revoke PUBLIC"
        # Et l'accès au schéma lui-même (USAGE) tient via le re-GRANT explicite.
        assert await conn.fetchval(
            "SELECT has_schema_privilege('app_runtime', 'public', 'USAGE')"
        ) is True
    finally:
        await conn.close()
