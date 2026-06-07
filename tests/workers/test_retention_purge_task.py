"""Tests CI standard pour run_retention_purge (E4-S6) — itération tenant + best-effort.

Aucune DB réelle : asyncpg.create_pool et RetentionService sont patchés. L'isolation RLS de la
purge (chaque tenant ne purge que ses lignes) est prouvée en intégration sous PG migré
(`tests/integration/test_retention_purge_rls.py`).
"""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID

import pytest

from app.db.tenant_context import get_current_tenant
from app.services.retention_service import PurgeResult
from app.workers.celery_app import celery_app

_TENANT_A = UUID("00000000-0000-0000-0000-000000000001")
_TENANT_B = UUID("00000000-0000-0000-0000-0000000000bb")


def _make_db_pool(tenant_ids: list[UUID]) -> AsyncMock:
    pool = AsyncMock()
    pool.fetch = AsyncMock(return_value=[{"id": tid} for tid in tenant_ids])
    pool.close = AsyncMock()
    return pool


def _patch_create_pool(mock_pool: AsyncMock):
    return patch("app.workers.tasks.asyncpg.create_pool", AsyncMock(return_value=mock_pool))


class TestImport:
    def test_run_retention_purge_importable(self):
        from app.workers.tasks import run_retention_purge

        assert callable(run_retention_purge)

    def test_execute_retention_purge_importable(self):
        from app.workers.tasks import _execute_retention_purge

        assert callable(_execute_retention_purge)


class TestIterationTenants:
    @pytest.mark.asyncio
    async def test_itere_tenants_et_agrege_les_comptes(self):
        """La tâche purge chaque tenant et agrège le total de lignes supprimées."""
        from app.workers.tasks import _execute_retention_purge

        mock_pool = _make_db_pool([_TENANT_A, _TENANT_B])
        results = {
            _TENANT_A: PurgeResult(_TENANT_A, "free", 30, {"analysis_history": 2, "alert_history": 1}),
            _TENANT_B: PurgeResult(_TENANT_B, "pro", 365, {"analysis_history": 4}),
        }
        # purge_tenant() lit le tenant courant : le mock résout le résultat depuis le contexte,
        # prouvant que la tâche a posé le bon contexte AVANT d'appeler le service.
        mock_service = MagicMock()
        mock_service.purge_tenant = AsyncMock(side_effect=lambda: results[get_current_tenant()])

        with _patch_create_pool(mock_pool):
            with patch("app.workers.tasks.RetentionService", return_value=mock_service):
                result = await _execute_retention_purge()

        assert result["tenants_purged"] == 2
        assert result["total_deleted"] == 7  # 3 (A) + 4 (B)
        assert result["by_tenant"][str(_TENANT_A)]["total_deleted"] == 3
        assert result["by_tenant"][str(_TENANT_B)]["plan"] == "pro"
        assert mock_service.purge_tenant.await_count == 2

    @pytest.mark.asyncio
    async def test_pose_le_contexte_de_chaque_tenant(self):
        """Chaque purge tourne sous le contexte du tenant courant (set_current_tenant)."""
        from app.workers.tasks import _execute_retention_purge

        mock_pool = _make_db_pool([_TENANT_A, _TENANT_B])
        seen: list[UUID] = []

        async def _capture():
            # Au moment de la purge, le ContextVar doit déjà porter le tenant ciblé.
            tid = get_current_tenant()
            seen.append(tid)
            return PurgeResult(tid, "free", 30, {"analysis_history": 0})

        mock_service = MagicMock()
        mock_service.purge_tenant = AsyncMock(side_effect=_capture)

        with _patch_create_pool(mock_pool):
            with patch("app.workers.tasks.RetentionService", return_value=mock_service):
                await _execute_retention_purge()

        assert seen == [_TENANT_A, _TENANT_B]

    @pytest.mark.asyncio
    async def test_tenant_sans_borne_ignore(self):
        """Un tenant dont purge_tenant retourne None (pas de borne) n'est pas compté."""
        from app.workers.tasks import _execute_retention_purge

        mock_pool = _make_db_pool([_TENANT_A, _TENANT_B])
        results = {
            _TENANT_A: PurgeResult(_TENANT_A, "free", 30, {"analysis_history": 5}),
            _TENANT_B: None,
        }
        mock_service = MagicMock()
        mock_service.purge_tenant = AsyncMock(side_effect=lambda: results[get_current_tenant()])

        with _patch_create_pool(mock_pool):
            with patch("app.workers.tasks.RetentionService", return_value=mock_service):
                result = await _execute_retention_purge()

        assert result["tenants_purged"] == 1
        assert result["total_deleted"] == 5
        assert str(_TENANT_B) not in result["by_tenant"]


class TestBestEffort:
    @pytest.mark.asyncio
    async def test_echec_dun_tenant_ninterrompt_pas_les_autres(self):
        """L'échec de la purge d'un tenant (loggé) n'avorte pas la purge des suivants."""
        from app.workers.tasks import _execute_retention_purge

        mock_pool = _make_db_pool([_TENANT_A, _TENANT_B])

        async def _purge():
            tid = get_current_tenant()
            if tid == _TENANT_A:
                raise RuntimeError("panne purge tenant A")
            return PurgeResult(tid, "pro", 365, {"analysis_history": 9})

        mock_service = MagicMock()
        mock_service.purge_tenant = AsyncMock(side_effect=_purge)

        with _patch_create_pool(mock_pool):
            with patch("app.workers.tasks.RetentionService", return_value=mock_service):
                result = await _execute_retention_purge()

        # A échoue, B est tout de même purgé.
        assert mock_service.purge_tenant.await_count == 2
        assert result["tenants_purged"] == 1
        assert result["total_deleted"] == 9
        assert str(_TENANT_B) in result["by_tenant"]
        assert str(_TENANT_A) not in result["by_tenant"]

    @pytest.mark.asyncio
    async def test_contexte_restaure_apres_echec(self):
        """Le ContextVar tenant est restauré même quand la purge lève (pas de fuite de contexte)."""
        from app.db.tenant_context import LEGACY_TENANT_ID
        from app.workers.tasks import _execute_retention_purge

        mock_pool = _make_db_pool([_TENANT_A])
        mock_service = MagicMock()
        mock_service.purge_tenant = AsyncMock(side_effect=RuntimeError("boom"))

        with _patch_create_pool(mock_pool):
            with patch("app.workers.tasks.RetentionService", return_value=mock_service):
                await _execute_retention_purge()

        # Hors de la boucle, le ContextVar est revenu à sa valeur par défaut (legacy).
        assert get_current_tenant() == LEGACY_TENANT_ID


class TestBeatSchedule:
    def test_run_retention_purge_dans_beat_schedule(self):
        assert "run-retention-purge-daily" in celery_app.conf.beat_schedule

    def test_run_retention_purge_tache_correcte(self):
        entry = celery_app.conf.beat_schedule["run-retention-purge-daily"]
        assert entry["task"] == "run_retention_purge"

    def test_run_retention_purge_planifie_quotidien_heure_creuse(self):
        from celery.schedules import crontab

        entry = celery_app.conf.beat_schedule["run-retention-purge-daily"]
        assert isinstance(entry["schedule"], crontab)
        assert entry["schedule"].hour == {3}
