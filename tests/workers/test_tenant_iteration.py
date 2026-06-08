"""Tests unitaires du helper `for_each_tenant` (Sprint 188).

Le squelette « énumère les tenants → exécute un corps sous `tenant_scope` → best-effort log-and-
continue » est centralisé ici. Aucune DB réelle : un faux pool fournit les rangées tenant.
L'isolation RLS effective est prouvée en intégration sous PG migré (tests par chemin planifié).
"""
from __future__ import annotations

import logging
from unittest.mock import AsyncMock
from uuid import UUID

import pytest

from app.db.tenant_context import LEGACY_TENANT_ID, get_current_tenant
from app.workers.tenant_iteration import for_each_tenant

_TENANT_A = UUID("00000000-0000-0000-0000-000000000001")
_TENANT_B = UUID("00000000-0000-0000-0000-0000000000bb")
_TENANT_C = UUID("00000000-0000-0000-0000-0000000000cc")


def _make_pool(tenant_ids: list[UUID]) -> AsyncMock:
    pool = AsyncMock()
    pool.fetch = AsyncMock(return_value=[{"id": tid} for tid in tenant_ids])
    return pool


class TestNominal:
    @pytest.mark.asyncio
    async def test_execute_chaque_tenant_et_retourne_les_resultats(self):
        """N tenants → le corps est appelé N fois, les N résultats sont retournés dans l'ordre."""
        pool = _make_pool([_TENANT_A, _TENANT_B, _TENANT_C])

        async def _body(tenant_id: UUID) -> str:
            return f"ok:{tenant_id}"

        results = await for_each_tenant(pool, _body, error_message="boom %s")

        assert results == [f"ok:{_TENANT_A}", f"ok:{_TENANT_B}", f"ok:{_TENANT_C}"]

    @pytest.mark.asyncio
    async def test_corps_execute_sous_le_contexte_du_tenant(self):
        """Au moment de l'appel, le ContextVar porte bien le tenant ciblé (énumère-puis-scope)."""
        pool = _make_pool([_TENANT_A, _TENANT_B])
        seen: list[UUID] = []

        async def _body(tenant_id: UUID) -> None:
            # Le contexte doit déjà refléter le tenant ciblé, pas l'argument seul.
            assert get_current_tenant() == tenant_id
            seen.append(get_current_tenant())

        await for_each_tenant(pool, _body, error_message="boom %s")

        assert seen == [_TENANT_A, _TENANT_B]

    @pytest.mark.asyncio
    async def test_aucun_tenant_retourne_liste_vide(self):
        pool = _make_pool([])
        body = AsyncMock()

        results = await for_each_tenant(pool, body, error_message="boom %s")

        assert results == []
        body.assert_not_awaited()


class TestBestEffort:
    @pytest.mark.asyncio
    async def test_echec_dun_tenant_ninterrompt_pas_les_autres(self):
        """Un corps qui lève sur 1 tenant n'avorte pas les autres (best-effort prouvé non-vacuous)."""
        pool = _make_pool([_TENANT_A, _TENANT_B, _TENANT_C])

        async def _body(tenant_id: UUID) -> str:
            if tenant_id == _TENANT_B:
                raise RuntimeError("panne tenant B")
            return f"ok:{tenant_id}"

        results = await for_each_tenant(pool, _body, error_message="boom %s")

        # B est sauté (aucun résultat), A et C sont traités.
        assert results == [f"ok:{_TENANT_A}", f"ok:{_TENANT_C}"]

    @pytest.mark.asyncio
    async def test_erreur_loggee_avec_le_message_et_luuid(self, caplog):
        """L'échec d'un tenant est loggé via `error_message` (format à un `%s`) + l'UUID."""
        pool = _make_pool([_TENANT_A])

        async def _body(_tenant_id: UUID) -> None:
            raise RuntimeError("panne")

        with caplog.at_level(logging.ERROR, logger="app.workers.tenant_iteration"):
            await for_each_tenant(
                pool, _body, error_message="Erreur de purge pour le tenant %s"
            )

        assert f"Erreur de purge pour le tenant {_TENANT_A}" in caplog.text

    @pytest.mark.asyncio
    async def test_contexte_restaure_apres_echec(self):
        """Le ContextVar tenant revient à legacy après un échec (pas de fuite de contexte)."""
        pool = _make_pool([_TENANT_A])

        async def _body(_tenant_id: UUID) -> None:
            raise RuntimeError("boom")

        await for_each_tenant(pool, _body, error_message="boom %s")

        assert get_current_tenant() == LEGACY_TENANT_ID
