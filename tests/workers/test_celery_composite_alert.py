"""Tests pour la tache Celery run_composite_alert_check (Sprint 52 ; threading tenant E5-S4)."""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID

import pytest

from app.db.tenant_context import LEGACY_TENANT_ID, get_current_tenant
from app.services.composite_alert import CompositeAlertResult
from app.workers.celery_app import celery_app

# Aucun des deux n'est le tenant legacy (défaut du ContextVar) : une capture de scope == _TENANT_A
# prouve donc que le scope a bien été posé, et ne peut pas se confondre avec le défaut non posé.
_TENANT_A = UUID("00000000-0000-0000-0000-0000000000aa")
_TENANT_B = UUID("00000000-0000-0000-0000-0000000000bb")

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_alerte(ticker: str, alerte: bool = True) -> CompositeAlertResult:
    return CompositeAlertResult(
        ticker=ticker,
        baseline=80.0,
        new_score=60.0 if alerte else 75.0,
        chute=20.0 if alerte else 5.0,
        threshold=15.0,
        alerte_declenchee=alerte,
    )


def _make_pool(tenant_ids: list[UUID]) -> AsyncMock:
    """Pool dont `fetch` renvoie la liste des tenants pour la requête d'énumération (hors RLS)."""
    pool = AsyncMock()

    async def _fetch(query: str, *args):
        if "FROM tenants" in query:
            return [{"id": tid} for tid in tenant_ids]
        return []

    pool.fetch = AsyncMock(side_effect=_fetch)
    pool.execute = AsyncMock()
    pool.close = AsyncMock()
    return pool


def _patch_build():
    """Patch `_build_orchestrator` → (orchestrateur mock, pool fermable async)."""
    orch_pool = AsyncMock()
    orch_pool.close = AsyncMock()
    return patch(
        "app.workers.tasks._build_orchestrator",
        new_callable=AsyncMock,
        return_value=(MagicMock(), orch_pool),
    )


# ---------------------------------------------------------------------------
# Tests : beat schedule
# ---------------------------------------------------------------------------


class TestBeatSchedule:

    def test_composite_alert_dans_beat_schedule(self):
        schedule = celery_app.conf.beat_schedule
        assert "run-composite-alert-check-daily" in schedule

    def test_composite_alert_task_name_correcte(self):
        entry = celery_app.conf.beat_schedule["run-composite-alert-check-daily"]
        assert entry["task"] == "run_composite_alert_check"

    def test_composite_alert_schedule_10h_utc(self):
        from celery.schedules import crontab
        entry = celery_app.conf.beat_schedule["run-composite-alert-check-daily"]
        schedule = entry["schedule"]
        assert isinstance(schedule, crontab)
        assert schedule.hour == frozenset({10})
        assert schedule.minute == frozenset({0})

    def test_9_taches_planifiees_au_total(self):
        # Sprint 94 : run_esg_degradation_check (7) ; Sprint 171 : run_retention_purge (8) ;
        # Sprint 174 : run_usage_reporting (9)
        schedule = celery_app.conf.beat_schedule
        assert len(schedule) == 9

    def test_price_alert_toujours_planifiee(self):
        assert "run-price-alert-check-daily" in celery_app.conf.beat_schedule

    def test_watchlist_analysis_toujours_planifiee(self):
        assert "run-watchlist-analysis-weekly" in celery_app.conf.beat_schedule


# ---------------------------------------------------------------------------
# Tests : logique execute_composite_alert_check
# ---------------------------------------------------------------------------


class TestExecuteCompositeAlertCheck:

    @pytest.mark.asyncio
    async def test_orchestrateur_metre(self):
        """_execute_composite_alert_check réclame un orchestrateur métré (with_metering=True)."""
        from app.workers.tasks import _execute_composite_alert_check

        mock_alert_service = AsyncMock()
        mock_alert_service.check_composite_alerts = AsyncMock(return_value=[])

        with (
            patch("app.workers.tasks.asyncpg.create_pool", AsyncMock(return_value=_make_pool([_TENANT_A]))),
            _patch_build() as mock_build,
            patch("app.workers.tasks.WatchlistService"),
            patch("app.workers.tasks.CompositeAlertService", return_value=mock_alert_service),
        ):
            await _execute_composite_alert_check()

        mock_build.assert_awaited_once_with(with_metering=True)

    @pytest.mark.asyncio
    async def test_chaque_tenant_sous_son_scope_union_des_alertes(self):
        """Chaque tenant est vérifié sous son `tenant_scope` ; le retour est l'union des tickers en alerte."""
        from app.workers.tasks import _execute_composite_alert_check

        results_by_tenant = {
            _TENANT_A: [_make_alerte("AAA", alerte=True)],
            _TENANT_B: [_make_alerte("BBB", alerte=True), _make_alerte("CCC", alerte=False)],
        }
        seen: list[UUID] = []

        async def _check():
            tenant = get_current_tenant()
            seen.append(tenant)
            return results_by_tenant.get(tenant, [])

        mock_alert_service = AsyncMock()
        mock_alert_service.check_composite_alerts = AsyncMock(side_effect=_check)

        with (
            patch("app.workers.tasks.asyncpg.create_pool", AsyncMock(return_value=_make_pool([_TENANT_A, _TENANT_B]))),
            _patch_build(),
            patch("app.workers.tasks.WatchlistService"),
            patch("app.workers.tasks.CompositeAlertService", return_value=mock_alert_service),
            patch("app.workers.tasks.WebhookService", return_value=AsyncMock()),
        ):
            alertes = await _execute_composite_alert_check()

        # Capture au site d'appel : A puis B, tous deux distincts du legacy (non-vacuous).
        assert seen == [_TENANT_A, _TENANT_B]
        # CCC non déclenché → exclu ; AAA (tenant A) et BBB (tenant B) → union.
        assert alertes == ["AAA", "BBB"]

    @pytest.mark.asyncio
    async def test_best_effort_un_tenant_en_echec_ninterrompt_pas_les_autres(self):
        """L'échec d'un tenant (loggé) n'avorte pas les suivants ; le ContextVar est restauré (legacy)."""
        from app.workers.tasks import _execute_composite_alert_check

        seen: list[UUID] = []

        async def _check():
            tenant = get_current_tenant()
            seen.append(tenant)
            if tenant == _TENANT_A:
                raise RuntimeError("panne tenant A")
            return [_make_alerte("BBB", alerte=True)]

        mock_alert_service = AsyncMock()
        mock_alert_service.check_composite_alerts = AsyncMock(side_effect=_check)

        with (
            patch("app.workers.tasks.asyncpg.create_pool", AsyncMock(return_value=_make_pool([_TENANT_A, _TENANT_B]))),
            _patch_build(),
            patch("app.workers.tasks.WatchlistService"),
            patch("app.workers.tasks.CompositeAlertService", return_value=mock_alert_service),
            patch("app.workers.tasks.WebhookService", return_value=AsyncMock()),
        ):
            alertes = await _execute_composite_alert_check()

        assert seen == [_TENANT_A, _TENANT_B]  # A échoue, B traité tout de même
        assert alertes == ["BBB"]
        assert get_current_tenant() == LEGACY_TENANT_ID  # pas de fuite de contexte

    @pytest.mark.asyncio
    async def test_email_service_configure_si_env_present(self):
        from app.workers.tasks import _execute_composite_alert_check

        mock_alert_service = AsyncMock()
        mock_alert_service.check_composite_alerts = AsyncMock(return_value=[])

        with (
            patch("app.workers.tasks.asyncpg.create_pool", AsyncMock(return_value=_make_pool([]))),
            _patch_build(),
            patch("app.workers.tasks.WatchlistService"),
            patch("app.workers.tasks.CompositeAlertService", return_value=mock_alert_service) as mock_cls,
            patch.dict("os.environ", {"REPORT_EMAIL_TO": "test@example.com", "SMTP_HOST": "smtp.test.com"}),
            patch("app.workers.tasks.EmailService"),
        ):
            await _execute_composite_alert_check()

        call_kwargs = mock_cls.call_args.kwargs
        assert call_kwargs["email_to"] == "test@example.com"

    @pytest.mark.asyncio
    async def test_email_service_none_si_smtp_absent(self):
        from app.workers.tasks import _execute_composite_alert_check

        mock_alert_service = AsyncMock()
        mock_alert_service.check_composite_alerts = AsyncMock(return_value=[])

        with (
            patch("app.workers.tasks.asyncpg.create_pool", AsyncMock(return_value=_make_pool([]))),
            _patch_build(),
            patch("app.workers.tasks.WatchlistService"),
            patch("app.workers.tasks.CompositeAlertService", return_value=mock_alert_service) as mock_cls,
            patch.dict("os.environ", {}, clear=True),
        ):
            await _execute_composite_alert_check()

        call_kwargs = mock_cls.call_args.kwargs
        assert call_kwargs["email_service"] is None
        assert call_kwargs["email_to"] is None
