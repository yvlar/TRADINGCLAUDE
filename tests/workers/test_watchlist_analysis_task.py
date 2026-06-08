"""Tests CI standard pour run_watchlist_analysis (E5-S1) — threading tenant + metering.

Aucune DB réelle ni appel Claude : `_build_orchestrator`, `asyncpg.create_pool` et l'orchestrateur
sont patchés. L'attribution RLS bout-en-bout du `usage_event` au tenant propriétaire est prouvée en
intégration sous PG migré (`tests/integration/test_watchlist_metering_rls.py`).
"""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID

import pytest

from app.db.tenant_context import LEGACY_TENANT_ID, get_current_tenant

# Aucun des deux n'est le tenant legacy (défaut du ContextVar) : une capture de scope == _TENANT_A
# prouve donc que le scope a bien été posé, et ne peut pas se confondre avec le défaut non posé.
_TENANT_A = UUID("00000000-0000-0000-0000-0000000000aa")
_TENANT_B = UUID("00000000-0000-0000-0000-0000000000bb")


def _wl_row(ticker: str) -> dict:
    return {
        "id": UUID("11111111-1111-1111-1111-111111111111"),
        "ticker": ticker,
        "workflow": "value_graham",
        "ratios": None,
        "score_alerte_min": None,
    }


def _make_pool(
    tenant_ids: list[UUID],
    watchlist_by_tenant: dict[UUID, list[dict]],
    raise_for: set[UUID] | None = None,
) -> AsyncMock:
    """Pool dont `fetch` discrimine la requête tenants (hors RLS) de la requête watchlist (RLS-scopée).

    La requête watchlist résout ses lignes depuis `get_current_tenant()` → prouve que la tâche a posé
    le `tenant_scope` AVANT de lire la watchlist (sinon elle verrait les lignes d'un autre tenant). Un
    tenant listé dans `raise_for` lève à la lecture de sa watchlist (simulation d'échec best-effort).
    """
    raise_for = raise_for or set()
    pool = AsyncMock()

    async def _fetch(query: str, *args):
        if "FROM tenants" in query:
            return [{"id": tid} for tid in tenant_ids]
        if "FROM watchlist" in query:
            tenant = get_current_tenant()
            if tenant in raise_for:
                raise RuntimeError(f"panne lecture watchlist tenant {tenant}")
            return watchlist_by_tenant.get(tenant, [])
        return []

    pool.fetch = AsyncMock(side_effect=_fetch)
    pool.execute = AsyncMock()
    pool.close = AsyncMock()
    return pool


def _make_orchestrator(on_run=None) -> AsyncMock:
    orch = AsyncMock()

    async def _run(_request):
        if on_run is not None:
            on_run()
        resp = MagicMock()
        resp.graham = None  # last_score/verdict/intrinsic → None (chemin sans alerte)
        return resp

    orch.run_company_analysis = AsyncMock(side_effect=_run)
    return orch


def _patch_build(orch: AsyncMock, pool: AsyncMock):
    return patch(
        "app.workers.tasks._build_orchestrator",
        new_callable=AsyncMock,
        return_value=(orch, pool),
    )


class TestImport:
    def test_taches_importables(self):
        from app.workers.tasks import (
            _analyze_watchlist_entries,
            _execute_watchlist_analysis,
            run_watchlist_analysis,
        )

        assert callable(run_watchlist_analysis)
        assert callable(_execute_watchlist_analysis)
        assert callable(_analyze_watchlist_entries)


class TestMeteringInjection:
    @pytest.mark.asyncio
    async def test_build_orchestrator_injecte_usage_service_si_metering(self, monkeypatch):
        from app.services.usage_event_service import UsageEventService
        from app.workers import tasks

        monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)
        monkeypatch.delenv("LANGFUSE_SECRET_KEY", raising=False)

        mock_pool = AsyncMock()
        mock_rag = MagicMock()
        mock_rag.ensure_collection = AsyncMock()

        with patch("app.workers.tasks.asyncpg.create_pool", AsyncMock(return_value=mock_pool)):
            with patch("app.workers.tasks.anthropic.AsyncAnthropic", MagicMock()):
                with patch("app.workers.tasks.RagClient", MagicMock(return_value=mock_rag)):
                    orchestrator, pool = await tasks._build_orchestrator(with_metering=True)

        assert isinstance(orchestrator._usage_events, UsageEventService)
        assert pool is mock_pool

    @pytest.mark.asyncio
    async def test_build_orchestrator_sans_metering_par_defaut(self, monkeypatch):
        from app.workers import tasks

        monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)
        monkeypatch.delenv("LANGFUSE_SECRET_KEY", raising=False)

        mock_pool = AsyncMock()
        mock_rag = MagicMock()
        mock_rag.ensure_collection = AsyncMock()

        with patch("app.workers.tasks.asyncpg.create_pool", AsyncMock(return_value=mock_pool)):
            with patch("app.workers.tasks.anthropic.AsyncAnthropic", MagicMock()):
                with patch("app.workers.tasks.RagClient", MagicMock(return_value=mock_rag)):
                    orchestrator, _ = await tasks._build_orchestrator()

        assert orchestrator._usage_events is None

    @pytest.mark.asyncio
    async def test_execute_watchlist_construit_orchestrateur_metre(self):
        """`_execute_watchlist_analysis` réclame un orchestrateur métré (with_metering=True)."""
        from app.workers.tasks import _execute_watchlist_analysis

        pool = _make_pool([_TENANT_A], {_TENANT_A: []})
        orch = _make_orchestrator()
        with _patch_build(orch, pool) as mock_build:
            await _execute_watchlist_analysis()

        mock_build.assert_awaited_once_with(with_metering=True)


class TestThreadingTenant:
    @pytest.mark.asyncio
    async def test_chaque_analyse_tourne_sous_le_tenant_proprietaire(self):
        """Chaque entrée watchlist est ré-analysée sous le `tenant_scope` de son propriétaire."""
        from app.workers.tasks import _execute_watchlist_analysis

        pool = _make_pool(
            [_TENANT_A, _TENANT_B],
            {_TENANT_A: [_wl_row("AAA")], _TENANT_B: [_wl_row("BBB")]},
        )
        seen: list[UUID] = []
        orch = _make_orchestrator(on_run=lambda: seen.append(get_current_tenant()))

        with _patch_build(orch, pool):
            await _execute_watchlist_analysis()

        # L'analyse de AAA tourne sous A, celle de BBB sous B (capture au site d'appel orchestrateur).
        assert seen == [_TENANT_A, _TENANT_B]
        assert orch.run_company_analysis.await_count == 2

    @pytest.mark.asyncio
    async def test_lecture_watchlist_scopee_au_tenant_courant(self):
        """La watchlist d'un tenant n'est lue que sous son propre contexte (RLS rejouée par le pool)."""
        from app.workers.tasks import _execute_watchlist_analysis

        # B n'a aucune entrée : seul A doit produire une analyse (pas de fuite cross-tenant).
        pool = _make_pool(
            [_TENANT_A, _TENANT_B],
            {_TENANT_A: [_wl_row("AAA")], _TENANT_B: []},
        )
        seen: list[UUID] = []
        orch = _make_orchestrator(on_run=lambda: seen.append(get_current_tenant()))

        with _patch_build(orch, pool):
            await _execute_watchlist_analysis()

        assert seen == [_TENANT_A]


class TestBestEffort:
    @pytest.mark.asyncio
    async def test_echec_dun_tenant_ninterrompt_pas_les_autres(self):
        """L'échec de la lecture watchlist d'un tenant (loggé) n'avorte pas les suivants."""
        from app.workers.tasks import _execute_watchlist_analysis

        pool = _make_pool(
            [_TENANT_A, _TENANT_B],
            {_TENANT_A: [], _TENANT_B: [_wl_row("BBB")]},
            raise_for={_TENANT_A},
        )
        seen: list[UUID] = []
        orch = _make_orchestrator(on_run=lambda: seen.append(get_current_tenant()))

        with _patch_build(orch, pool):
            await _execute_watchlist_analysis()

        # A échoue à la lecture, B est tout de même ré-analysé.
        assert seen == [_TENANT_B]

    @pytest.mark.asyncio
    async def test_contexte_restaure_apres_echec(self):
        """Le ContextVar tenant est restauré (legacy) même si un tenant échoue — pas de fuite."""
        from app.workers.tasks import _execute_watchlist_analysis

        pool = _make_pool([_TENANT_B], {_TENANT_B: []}, raise_for={_TENANT_B})
        orch = _make_orchestrator()

        with _patch_build(orch, pool):
            await _execute_watchlist_analysis()

        assert get_current_tenant() == LEGACY_TENANT_ID
