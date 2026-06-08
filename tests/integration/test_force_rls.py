"""Verrou anti-régression : les 7 tables RLS portent `FORCE ROW LEVEL SECURITY`.

Aujourd'hui (§2.3 `docs/revue-owasp-rls-2026-06.md`) `FORCE` est prouvé **indirectement** —
la matrice d'isolation (`test_rls_isolation.py`) échouerait si une table perdait `FORCE`, mais
aucun test ne l'asserte en propre. Ce test lit `pg_class.relforcerowsecurity` et rend la
régression impossible à introduire silencieusement : une migration ajoutant une table RLS sans
`FORCE` (ou le retirant) échoue immédiatement.

Réutilise `_RLS_TABLES` de `test_revoke_public_rls.py` (S186) plutôt que de ré-énumérer — un seul
inventaire des 7 tables RLS, synchrone avec le durcissement PUBLIC.

Skippé hors PG migré : nécessite `APP_DATABASE_URL` pointant un PostgreSQL **migré**
(`alembic upgrade head`) et un mot de passe posé hors-bande sur `app_runtime`. Exécuté en CI via
le gate NOSUPERUSER sous le rôle réel `app_runtime` (lecture catalogue, accessible à tout rôle).
"""
from __future__ import annotations

import os

import asyncpg
import pytest

from tests.integration.test_revoke_public_rls import _RLS_TABLES

_APP_DB_URL = os.environ.get("APP_DATABASE_URL")

pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(
        not _APP_DB_URL,
        reason="APP_DATABASE_URL non défini (PG migré + rôle app_runtime requis)",
    ),
]


@pytest.mark.asyncio
async def test_les_7_tables_rls_portent_force_row_level_security():
    """relforcerowsecurity == true partout (sinon le propriétaire échapperait à sa propre RLS)."""
    conn = await asyncpg.connect(_APP_DB_URL)
    try:
        rows = await conn.fetch(
            "SELECT relname, relforcerowsecurity FROM pg_class WHERE relname = ANY($1::text[])",
            list(_RLS_TABLES),
        )
        # Anti-faux-vert : sans cette garde, 0 ligne (mauvaise DB / PG non migré) passerait à vide.
        assert {r["relname"] for r in rows} == set(_RLS_TABLES), "tables RLS introuvables (PG migré ?)"
        offenders = [r["relname"] for r in rows if not r["relforcerowsecurity"]]
        assert offenders == [], f"FORCE ROW LEVEL SECURITY manquant sur : {offenders}"
    finally:
        await conn.close()
