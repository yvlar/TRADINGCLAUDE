"""Clés API rattachées au tenant (E4-S3) contre un PostgreSQL migré — chemin réel bout-en-bout.

Skippé par défaut : nécessite `RLS_TEST_DATABASE_URL` pointant un PostgreSQL **migré**
(`alembic upgrade head`, donc 0008_api_keys_tenant_id appliquée) et un rôle **NOSUPERUSER**
(un superuser contourne la RLS et rendrait la preuve vacuous).

Prouve que le tenant d'une **clé API** est threadé bout-en-bout par le chemin réel — pas
le tenant legacy : requête HTTP `Bearer <token>` → `BearerTokenMiddleware` (résout le tenant
de la clé via `ApiKeyService`, pose `request.state.tenant_id`) → `TenantContextMiddleware`
(ContextVar) → `apply_tenant_context` (setup du pool → GUC) → RLS sur l'écriture. Réplique
l'ordre de montage de production (`app/api/main.py`).
"""
from __future__ import annotations

import hashlib
import os
import uuid

import asyncpg
import pytest
from fastapi import FastAPI, Request
from httpx import ASGITransport, AsyncClient

from app.db.tenant_context import apply_tenant_context, resolve_tenant
from app.middleware.auth import BearerTokenMiddleware
from app.middleware.tenant import TenantContextMiddleware
from app.models.tenant import LEGACY_TENANT_ID
from app.services.api_key_service import ApiKeyService

_RLS_DB_URL = os.environ.get("RLS_TEST_DATABASE_URL")

pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(
        not _RLS_DB_URL,
        reason="RLS_TEST_DATABASE_URL non défini (PG migré 0008 + rôle NOSUPERUSER requis)",
    ),
]

_TENANT_B = "00000000-0000-0000-0000-0000000000bb"


@pytest.mark.asyncio
async def test_requete_par_cle_api_ecrit_sous_le_tenant_de_la_cle():
    """Une analyse lancée via clé API d'un tenant B écrit sous B (RLS), pas legacy."""
    # Garde : un superuser contourne la RLS — la preuve serait faussement verte.
    probe = await asyncpg.connect(_RLS_DB_URL)
    try:
        if await probe.fetchval("SELECT current_setting('is_superuser')") == "on":
            pytest.skip("RLS contournée par un superuser — fournir un rôle NOSUPERUSER")
        await probe.execute(
            "INSERT INTO tenants (id, name, slug) VALUES ($1::uuid, 'E4S3-B', 'e4s3-test-b') "
            "ON CONFLICT (id) DO NOTHING",
            _TENANT_B,
        )
        # api_keys est HORS RLS (table d'authn lue avant le contexte tenant) → insertion
        # directe possible sans GUC. Le hash doit matcher ApiKeyService._hash (sha256 hex).
        token = f"e4s3-token-{uuid.uuid4().hex}"
        key_hash = hashlib.sha256(token.encode()).hexdigest()
        await probe.execute(
            "INSERT INTO api_keys (name, key_hash, role, tenant_id) "
            "VALUES ($1, $2, 'reader', $3::uuid)",
            "cle-tenant-b", key_hash, _TENANT_B,
        )
    finally:
        await probe.close()

    suffixe = uuid.uuid4().hex[:6].upper()
    ticker = f"E4S3{suffixe}"

    pool = await asyncpg.create_pool(
        _RLS_DB_URL, min_size=1, max_size=2, setup=apply_tenant_context
    )
    try:
        app = FastAPI()
        app.state.api_key_service = ApiKeyService(db_pool=pool)

        @app.post("/write")
        async def write(request: Request):
            # Site d'écriture réel : tenant_id non précisé → resolve_tenant lit le ContextVar
            # (posé par le threading depuis la clé). Si le threading échouait, ce serait legacy.
            await pool.execute(
                "INSERT INTO watchlist (ticker, tenant_id) VALUES ($1, $2::uuid)",
                ticker, str(resolve_tenant(None)),
            )
            return {"ok": True}

        # Ordre identique à production : interne (Tenant) ajouté avant externe (Bearer).
        app.add_middleware(TenantContextMiddleware)
        app.add_middleware(BearerTokenMiddleware, api_key="env-admin-key")

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            resp = await c.post("/write", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 200

        # Lecture sous B : la ligne existe et lui appartient (RLS la rend visible).
        async with pool.acquire() as conn:
            await conn.execute("SELECT set_config('app.tenant_id', $1, false)", _TENANT_B)
            row_b = await conn.fetchrow(
                "SELECT tenant_id FROM watchlist WHERE ticker = $1", ticker
            )
        assert row_b is not None
        assert str(row_b["tenant_id"]) == _TENANT_B

        # Lecture sous legacy : la RLS masque la ligne de B → invisible (pas écrit sous legacy).
        async with pool.acquire() as conn:
            await conn.execute(
                "SELECT set_config('app.tenant_id', $1, false)", str(LEGACY_TENANT_ID)
            )
            row_legacy = await conn.fetchrow(
                "SELECT tenant_id FROM watchlist WHERE ticker = $1", ticker
            )
        assert row_legacy is None
    finally:
        # Nettoyage sous le tenant B (NOSUPERUSER soumis à la RLS).
        async with pool.acquire() as conn:
            await conn.execute("SELECT set_config('app.tenant_id', $1, false)", _TENANT_B)
            await conn.execute("DELETE FROM watchlist WHERE ticker = $1", ticker)
            await conn.execute(
                "SELECT set_config('app.tenant_id', $1, false)", str(LEGACY_TENANT_ID)
            )
            await conn.execute("DELETE FROM api_keys WHERE key_hash = $1", key_hash)
        await pool.close()
