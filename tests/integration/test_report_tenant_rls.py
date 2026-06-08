"""Isolation RLS du rapport `GET /report/{id}` — exécuté sous le tenant du demandeur (E4-S11).

Skippé par défaut : nécessite `RLS_TEST_DATABASE_URL` pointant un PostgreSQL **migré**
(`alembic upgrade head`) et un rôle **NOSUPERUSER** (un superuser contourne la RLS et rendrait
la preuve vacuous).

Prouve, via le chemin réel HTTP → `_get_current_user` (cookie JWT) → `tenant_scope` → GUC → RLS :
- une analyse écrite sous le tenant B, demandée **sous B** → 200 + PDF ;
- la **même** analyse demandée **sous le tenant legacy** → 404 (la RLS la masque).

C'est la fermeture du risque résiduel n°2 de `docs/revue-owasp-rls-2026-06.md` : un rapport ne
reflète jamais une analyse d'un autre tenant.
"""
from __future__ import annotations

import json
import os
import uuid
from unittest.mock import AsyncMock, MagicMock

import asyncpg
import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from app.api.endpoints.report import router as report_router
from app.db.tenant_context import apply_tenant_context
from app.models.tenant import LEGACY_TENANT_ID

_RLS_DB_URL = os.environ.get("RLS_TEST_DATABASE_URL")

pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(
        not _RLS_DB_URL,
        reason="RLS_TEST_DATABASE_URL non défini (PG migré + rôle NOSUPERUSER requis)",
    ),
]

_TENANT_B = "00000000-0000-0000-0000-0000000000bb"


def _auth_service_for(tenant_id: str) -> AsyncMock:
    """auth_token_service mocké décodant le cookie en payload portant `tenant_id`."""
    mock = AsyncMock()
    mock.decode_access_token = MagicMock(
        return_value={
            "sub": str(uuid.uuid4()),
            "email": "x@test.com",
            "role": "reader",
            "tenant_id": tenant_id,
            "jti": str(uuid.uuid4()),
            "exp": 9_999_999_999,
        }
    )
    mock.is_jti_blacklisted.return_value = False
    return mock


@pytest.mark.asyncio
async def test_get_report_isole_par_la_rls(graham_output_msft):
    """Le rapport d'une analyse de B est servi sous B (200) et masqué sous legacy (404)."""
    probe = await asyncpg.connect(_RLS_DB_URL)
    try:
        if await probe.fetchval("SELECT current_setting('is_superuser')") == "on":
            pytest.skip("RLS contournée par un superuser — fournir un rôle NOSUPERUSER")
        await probe.execute(
            "INSERT INTO tenants (id, name, slug) VALUES ($1::uuid, 'E4S11-B', 'e4s11-test-b') "
            "ON CONFLICT (id) DO NOTHING",
            _TENANT_B,
        )
    finally:
        await probe.close()

    result_json = json.dumps({"graham": graham_output_msft.model_dump(mode="json")})
    pool = await asyncpg.create_pool(
        _RLS_DB_URL, min_size=1, max_size=2, setup=apply_tenant_context
    )
    analysis_id: uuid.UUID | None = None
    try:
        # Écriture de l'analyse sous le tenant B (GUC posé manuellement pour le seeding).
        async with pool.acquire() as conn:
            await conn.execute("SELECT set_config('app.tenant_id', $1, false)", _TENANT_B)
            analysis_id = await conn.fetchval(
                """
                INSERT INTO analysis_history
                    (ticker, workflow_name, skills_used, input_data, result, cost_usd, tenant_id)
                VALUES ('MSFT', 'value_graham', $1::jsonb, '{}'::jsonb, $2::jsonb, 0.001, $3::uuid)
                RETURNING id
                """,
                json.dumps(["graham_analysis"]),
                result_json,
                _TENANT_B,
            )

        app = FastAPI()
        app.state.db_pool = pool
        app.include_router(report_router)

        # Demandé sous B (propriétaire) → la RLS rend la ligne visible → 200 + PDF.
        app.state.auth_token_service = _auth_service_for(_TENANT_B)
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as c:
            resp_b = await c.get(
                f"/report/{analysis_id}", cookies={"access_token": "x"}
            )
        assert resp_b.status_code == 200
        assert resp_b.content[:4] == b"%PDF"

        # Demandé sous le tenant legacy → la RLS masque la ligne de B → 404.
        app.state.auth_token_service = _auth_service_for(str(LEGACY_TENANT_ID))
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as c:
            resp_legacy = await c.get(
                f"/report/{analysis_id}", cookies={"access_token": "x"}
            )
        assert resp_legacy.status_code == 404
    finally:
        if analysis_id is not None:
            async with pool.acquire() as conn:
                await conn.execute("SELECT set_config('app.tenant_id', $1, false)", _TENANT_B)
                await conn.execute(
                    "DELETE FROM analysis_history WHERE id = $1::uuid", analysis_id
                )
        await pool.close()
