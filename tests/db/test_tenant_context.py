"""Unitaires du câblage du contexte tenant au pool asyncpg (E3-S3) + threading (E3-S4)."""
from __future__ import annotations

import asyncio
import uuid
from unittest.mock import AsyncMock

import pytest

from app.db.tenant_context import (
    TENANT_GUC,
    apply_tenant_context,
    get_current_tenant,
    reset_current_tenant,
    set_current_tenant,
)
from app.models.tenant import LEGACY_TENANT_ID


def test_guc_qualifie_par_namespace():
    """Postgres exige un namespace (point) pour un paramètre de session personnalisé."""
    assert TENANT_GUC == "app.tenant_id"
    assert "." in TENANT_GUC


@pytest.mark.asyncio
async def test_apply_pose_le_tenant_legacy_via_set_config():
    """Hors requête (ContextVar non posé) : chaque connexion empruntée opère sous LEGACY_TENANT_ID."""
    conn = AsyncMock()
    await apply_tenant_context(conn)
    # `false` (3ᵉ arg set_config) = portée session, réappliquée par le setup à chaque acquire.
    conn.execute.assert_awaited_once_with(
        "SELECT set_config($1, $2, false)", TENANT_GUC, str(LEGACY_TENANT_ID)
    )


@pytest.mark.asyncio
async def test_apply_pose_le_tenant_courant():
    """E3-S4 : le tenant posé dans le ContextVar est propagé au GUC par `setup`."""
    tenant = uuid.uuid4()
    tok = set_current_tenant(tenant)
    try:
        conn = AsyncMock()
        await apply_tenant_context(conn)
        conn.execute.assert_awaited_once_with(
            "SELECT set_config($1, $2, false)", TENANT_GUC, str(tenant)
        )
    finally:
        reset_current_tenant(tok)


def test_get_defaut_legacy():
    """Sans tenant posé, le ContextVar vaut le tenant legacy."""
    assert get_current_tenant() == LEGACY_TENANT_ID


def test_set_reset_restaure_la_valeur_precedente():
    tenant = uuid.uuid4()
    tok = set_current_tenant(tenant)
    assert get_current_tenant() == tenant
    reset_current_tenant(tok)
    assert get_current_tenant() == LEGACY_TENANT_ID


@pytest.mark.parametrize("invalide", [None, "", "pas-un-uuid", 12345])
def test_set_valeur_invalide_retombe_sur_legacy(invalide):
    """Claim absent/malformé → legacy (fail-safe rétrocompat), jamais une exception."""
    tok = set_current_tenant(invalide)
    try:
        assert get_current_tenant() == LEGACY_TENANT_ID
    finally:
        reset_current_tenant(tok)


def test_set_accepte_uuid_sous_forme_de_chaine():
    tenant = uuid.uuid4()
    tok = set_current_tenant(str(tenant))
    try:
        assert get_current_tenant() == tenant
    finally:
        reset_current_tenant(tok)


@pytest.mark.asyncio
async def test_isolation_concurrente_entre_taches():
    """Deux tâches async simultanées avec tenants différents ne se contaminent pas."""
    tenant_a = uuid.uuid4()
    tenant_b = uuid.uuid4()

    async def _capture(tenant: uuid.UUID, delai: float) -> uuid.UUID:
        tok = set_current_tenant(tenant)
        try:
            await asyncio.sleep(delai)  # laisse l'autre tâche poser SA valeur entre-temps
            return get_current_tenant()
        finally:
            reset_current_tenant(tok)

    vu_a, vu_b = await asyncio.gather(
        _capture(tenant_a, 0.02), _capture(tenant_b, 0.01)
    )
    assert vu_a == tenant_a
    assert vu_b == tenant_b
    # Hors des tâches, le contexte parent reste au défaut legacy.
    assert get_current_tenant() == LEGACY_TENANT_ID
