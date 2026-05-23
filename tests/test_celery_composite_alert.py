"""Tests pour la tache Celery run_composite_alert_check (Sprint 52)."""
from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.composite_alert import CompositeAlertResult, CompositeAlertService
from app.workers.celery_app import celery_app


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

    def test_7_taches_planifiees_au_total(self):
        # Sprint 94 : ajout de run_esg_degradation_check — 7 tâches au total
        schedule = celery_app.conf.beat_schedule
        assert len(schedule) == 7

    def test_price_alert_toujours_planifiee(self):
        assert "run-price-alert-check-daily" in celery_app.conf.beat_schedule

    def test_watchlist_analysis_toujours_planifiee(self):
        assert "run-watchlist-analysis-weekly" in celery_app.conf.beat_schedule


# ---------------------------------------------------------------------------
# Tests : logique execute_composite_alert_check
# ---------------------------------------------------------------------------


class TestExecuteCompositeAlertCheck:

    @pytest.mark.asyncio
    async def test_retourne_liste_tickers_alertes(self):
        """_execute_composite_alert_check retourne les tickers qui ont declenche une alerte."""
        from app.workers.tasks import _execute_composite_alert_check

        resultats = [
            _make_alerte("BNS", alerte=True),
            _make_alerte("TD", alerte=False),
            _make_alerte("RY", alerte=True),
        ]

        mock_alert_service = AsyncMock()
        mock_alert_service.check_composite_alerts = AsyncMock(return_value=resultats)

        with (
            patch("app.workers.tasks.asyncpg.create_pool", new_callable=AsyncMock) as mock_pool,
            patch("app.workers.tasks._build_orchestrator", new_callable=AsyncMock) as mock_orch,
            patch("app.workers.tasks.WatchlistService") as mock_wl,
            patch("app.workers.tasks.CompositeAlertService", return_value=mock_alert_service),
        ):
            mock_pool.return_value.__aenter__ = AsyncMock()
            mock_pool.return_value.__aexit__ = AsyncMock()
            mock_pool.return_value.close = AsyncMock()
            mock_orch.return_value = (MagicMock(), MagicMock())

            alertes = await _execute_composite_alert_check()

        assert "BNS" in alertes
        assert "RY" in alertes
        assert "TD" not in alertes

    @pytest.mark.asyncio
    async def test_retourne_liste_vide_si_aucune_alerte(self):
        from app.workers.tasks import _execute_composite_alert_check

        resultats = [_make_alerte("BNS", alerte=False)]

        mock_alert_service = AsyncMock()
        mock_alert_service.check_composite_alerts = AsyncMock(return_value=resultats)

        with (
            patch("app.workers.tasks.asyncpg.create_pool", new_callable=AsyncMock) as mock_pool,
            patch("app.workers.tasks._build_orchestrator", new_callable=AsyncMock) as mock_orch,
            patch("app.workers.tasks.WatchlistService"),
            patch("app.workers.tasks.CompositeAlertService", return_value=mock_alert_service),
        ):
            mock_pool.return_value.close = AsyncMock()
            mock_orch.return_value = (MagicMock(), MagicMock())

            alertes = await _execute_composite_alert_check()

        assert alertes == []

    @pytest.mark.asyncio
    async def test_email_service_configure_si_env_present(self):
        from app.workers.tasks import _execute_composite_alert_check

        mock_alert_service = AsyncMock()
        mock_alert_service.check_composite_alerts = AsyncMock(return_value=[])

        with (
            patch("app.workers.tasks.asyncpg.create_pool", new_callable=AsyncMock) as mock_pool,
            patch("app.workers.tasks._build_orchestrator", new_callable=AsyncMock) as mock_orch,
            patch("app.workers.tasks.WatchlistService"),
            patch("app.workers.tasks.CompositeAlertService", return_value=mock_alert_service) as mock_cls,
            patch.dict("os.environ", {"REPORT_EMAIL_TO": "test@example.com", "SMTP_HOST": "smtp.test.com"}),
            patch("app.workers.tasks.EmailService"),
        ):
            mock_pool.return_value.close = AsyncMock()
            mock_orch.return_value = (MagicMock(), MagicMock())

            await _execute_composite_alert_check()

        call_kwargs = mock_cls.call_args.kwargs
        assert call_kwargs["email_to"] == "test@example.com"

    @pytest.mark.asyncio
    async def test_email_service_none_si_smtp_absent(self):
        from app.workers.tasks import _execute_composite_alert_check

        mock_alert_service = AsyncMock()
        mock_alert_service.check_composite_alerts = AsyncMock(return_value=[])

        with (
            patch("app.workers.tasks.asyncpg.create_pool", new_callable=AsyncMock) as mock_pool,
            patch("app.workers.tasks._build_orchestrator", new_callable=AsyncMock) as mock_orch,
            patch("app.workers.tasks.WatchlistService"),
            patch("app.workers.tasks.CompositeAlertService", return_value=mock_alert_service) as mock_cls,
            patch.dict("os.environ", {}, clear=True),
        ):
            mock_pool.return_value.close = AsyncMock()
            mock_orch.return_value = (MagicMock(), MagicMock())

            await _execute_composite_alert_check()

        call_kwargs = mock_cls.call_args.kwargs
        assert call_kwargs["email_service"] is None
        assert call_kwargs["email_to"] is None
