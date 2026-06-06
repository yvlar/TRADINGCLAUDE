"""Unitaires du câblage du contexte tenant au pool asyncpg (E3-S3)."""
from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from app.db.tenant_context import TENANT_GUC, apply_tenant_context
from app.models.tenant import LEGACY_TENANT_ID


def test_guc_qualifie_par_namespace():
    """Postgres exige un namespace (point) pour un paramètre de session personnalisé."""
    assert TENANT_GUC == "app.tenant_id"
    assert "." in TENANT_GUC


@pytest.mark.asyncio
async def test_apply_pose_le_tenant_legacy_via_set_config():
    """Palier E3-S3 : chaque connexion empruntée opère sous LEGACY_TENANT_ID."""
    conn = AsyncMock()
    await apply_tenant_context(conn)
    # `false` (3ᵉ arg set_config) = portée session, réappliquée par le setup à chaque acquire.
    conn.execute.assert_awaited_once_with(
        "SELECT set_config($1, $2, false)", TENANT_GUC, str(LEGACY_TENANT_ID)
    )
