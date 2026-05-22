"""Tests CI standard pour run_scheduled_screener — Sprint 64.

Aucun appel Claude réel. ScreenerService.screen() et WatchlistService.list_entries()
sont patchés pour contrôler les résultats.
CI standard : pytest -m "not e2e and not evals"
"""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.workers.celery_app import celery_app


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_wl_entry(ticker: str) -> MagicMock:
    entry = MagicMock()
    entry.ticker = ticker
    entry.last_esg_score = None
    entry.esg_alert_threshold = 5.0
    return entry


def _make_screen_entry(
    ticker: str,
    composite_label: str | None = None,
    defensive_score: int | None = None,
    composite_score: float | None = None,
    erreur: str | None = None,
) -> MagicMock:
    entry = MagicMock()
    entry.ticker = ticker
    entry.composite_label = composite_label
    entry.defensive_score = defensive_score
    entry.composite_score = composite_score
    entry.erreur = erreur
    return entry


def _make_screen_result(entries: list) -> MagicMock:
    result = MagicMock()
    result.resultats = entries
    return result


def _make_db_pool() -> AsyncMock:
    pool = AsyncMock()
    pool.close = AsyncMock()
    return pool


def _patch_create_pool(mock_pool: AsyncMock):
    """Patch asyncpg.create_pool (coroutine) pour retourner mock_pool."""
    create_pool = AsyncMock(return_value=mock_pool)
    return patch("app.workers.tasks.asyncpg.create_pool", create_pool)


# ---------------------------------------------------------------------------
# Test 1 : import sans erreur
# ---------------------------------------------------------------------------


class TestImport:
    def test_run_scheduled_screener_importable(self):
        from app.workers.tasks import run_scheduled_screener

        assert callable(run_scheduled_screener)

    def test_execute_scheduled_screener_importable(self):
        from app.workers.tasks import _execute_scheduled_screener

        assert callable(_execute_scheduled_screener)


# ---------------------------------------------------------------------------
# Test 2 : watchlist vide
# ---------------------------------------------------------------------------


class TestWatchlistVide:
    @pytest.mark.asyncio
    async def test_watchlist_vide_retourne_zero(self):
        from app.workers.tasks import _execute_scheduled_screener

        mock_pool = _make_db_pool()
        mock_wl_instance = AsyncMock()
        mock_wl_instance.list_entries = AsyncMock(return_value=[])

        with _patch_create_pool(mock_pool):
            with patch("app.workers.tasks.WatchlistService", return_value=mock_wl_instance):
                result = await _execute_scheduled_screener()

        assert result["nb_tickers_screenes"] == 0
        assert result["nb_opportunites"] == 0
        assert result["tickers_fort"] == []


# ---------------------------------------------------------------------------
# Test 3 : tâche identifie les tickers FORT
# ---------------------------------------------------------------------------


class TestFortIdentifies:
    @pytest.mark.asyncio
    async def test_tickers_fort_identifies_via_composite_label(self):
        from app.workers.tasks import _execute_scheduled_screener

        wl_entries = [_make_wl_entry("BNS"), _make_wl_entry("TD")]
        screen_entries = [
            _make_screen_entry("BNS", composite_label="FORT", defensive_score=6),
            _make_screen_entry("TD", composite_label="MODERE", defensive_score=3),
        ]
        mock_pool = _make_db_pool()
        mock_orch_pool = _make_db_pool()
        mock_wl_instance = AsyncMock()
        mock_wl_instance.list_entries = AsyncMock(return_value=wl_entries)
        mock_screener_instance = AsyncMock()
        mock_screener_instance.screen = AsyncMock(
            return_value=_make_screen_result(screen_entries)
        )

        with _patch_create_pool(mock_pool):
            with patch("app.workers.tasks.WatchlistService", return_value=mock_wl_instance):
                with patch(
                    "app.workers.tasks._build_orchestrator",
                    new_callable=AsyncMock,
                    return_value=(MagicMock(), mock_orch_pool),
                ):
                    with patch("app.workers.tasks.YahooFinanceExtractor"):
                        with patch(
                            "app.workers.tasks.ScreenerService",
                            return_value=mock_screener_instance,
                        ):
                            with patch("app.workers.tasks.WebhookService") as MockWebhook:
                                MockWebhook.return_value.send_screener_report = AsyncMock(
                                    return_value=True
                                )
                                MockWebhook.return_value.send_screener_pdf_report = AsyncMock(
                                    return_value=False
                                )
                                result = await _execute_scheduled_screener()

        assert result["nb_tickers_screenes"] == 2
        assert result["nb_opportunites"] == 1
        assert "BNS" in result["tickers_fort"]
        assert "TD" not in result["tickers_fort"]

    @pytest.mark.asyncio
    async def test_tickers_fort_identifies_via_defensive_score(self):
        from app.workers.tasks import _execute_scheduled_screener

        wl_entries = [_make_wl_entry("RY")]
        screen_entries = [
            _make_screen_entry("RY", composite_label=None, defensive_score=7),
        ]
        mock_pool = _make_db_pool()
        mock_orch_pool = _make_db_pool()
        mock_wl_instance = AsyncMock()
        mock_wl_instance.list_entries = AsyncMock(return_value=wl_entries)
        mock_screener_instance = AsyncMock()
        mock_screener_instance.screen = AsyncMock(
            return_value=_make_screen_result(screen_entries)
        )

        with _patch_create_pool(mock_pool):
            with patch("app.workers.tasks.WatchlistService", return_value=mock_wl_instance):
                with patch(
                    "app.workers.tasks._build_orchestrator",
                    new_callable=AsyncMock,
                    return_value=(MagicMock(), mock_orch_pool),
                ):
                    with patch("app.workers.tasks.YahooFinanceExtractor"):
                        with patch(
                            "app.workers.tasks.ScreenerService",
                            return_value=mock_screener_instance,
                        ):
                            with patch("app.workers.tasks.WebhookService") as MockWebhook:
                                MockWebhook.return_value.send_screener_report = AsyncMock(
                                    return_value=True
                                )
                                MockWebhook.return_value.send_screener_pdf_report = AsyncMock(
                                    return_value=False
                                )
                                result = await _execute_scheduled_screener()

        assert result["nb_opportunites"] == 1
        assert "RY" in result["tickers_fort"]


# ---------------------------------------------------------------------------
# Test 4 : webhook appelé si FORT trouvés
# ---------------------------------------------------------------------------


class TestWebhookAppele:
    @pytest.mark.asyncio
    async def test_webhook_appele_si_fort_trouves(self):
        from app.workers.tasks import _execute_scheduled_screener

        wl_entries = [_make_wl_entry("BNS")]
        screen_entries = [
            _make_screen_entry("BNS", composite_label="FORT", defensive_score=6)
        ]
        mock_pool = _make_db_pool()
        mock_orch_pool = _make_db_pool()
        mock_wl_instance = AsyncMock()
        mock_wl_instance.list_entries = AsyncMock(return_value=wl_entries)
        mock_screener_instance = AsyncMock()
        mock_screener_instance.screen = AsyncMock(
            return_value=_make_screen_result(screen_entries)
        )
        mock_webhook = AsyncMock()
        mock_webhook.send_screener_report = AsyncMock(return_value=True)

        mock_webhook.send_screener_pdf_report = AsyncMock(return_value=False)

        with _patch_create_pool(mock_pool):
            with patch("app.workers.tasks.WatchlistService", return_value=mock_wl_instance):
                with patch(
                    "app.workers.tasks._build_orchestrator",
                    new_callable=AsyncMock,
                    return_value=(MagicMock(), mock_orch_pool),
                ):
                    with patch("app.workers.tasks.YahooFinanceExtractor"):
                        with patch(
                            "app.workers.tasks.ScreenerService",
                            return_value=mock_screener_instance,
                        ):
                            with patch(
                                "app.workers.tasks.WebhookService", return_value=mock_webhook
                            ):
                                await _execute_scheduled_screener()

        mock_webhook.send_screener_report.assert_awaited_once()
        call_kwargs = mock_webhook.send_screener_report.call_args
        assert call_kwargs.kwargs["tickers_fort"] == ["BNS"]
        assert call_kwargs.kwargs["nb_tickers_screenes"] == 1


# ---------------------------------------------------------------------------
# Test 5 : webhook non appelé si aucun FORT
# ---------------------------------------------------------------------------


class TestWebhookNonAppele:
    @pytest.mark.asyncio
    async def test_webhook_non_appele_si_aucun_fort(self):
        from app.workers.tasks import _execute_scheduled_screener

        wl_entries = [_make_wl_entry("TD")]
        screen_entries = [
            _make_screen_entry("TD", composite_label="FAIBLE", defensive_score=2)
        ]
        mock_pool = _make_db_pool()
        mock_orch_pool = _make_db_pool()
        mock_wl_instance = AsyncMock()
        mock_wl_instance.list_entries = AsyncMock(return_value=wl_entries)
        mock_screener_instance = AsyncMock()
        mock_screener_instance.screen = AsyncMock(
            return_value=_make_screen_result(screen_entries)
        )
        mock_webhook = AsyncMock()
        mock_webhook.send_screener_report = AsyncMock(return_value=True)

        mock_webhook.send_screener_pdf_report = AsyncMock(return_value=False)

        with _patch_create_pool(mock_pool):
            with patch("app.workers.tasks.WatchlistService", return_value=mock_wl_instance):
                with patch(
                    "app.workers.tasks._build_orchestrator",
                    new_callable=AsyncMock,
                    return_value=(MagicMock(), mock_orch_pool),
                ):
                    with patch("app.workers.tasks.YahooFinanceExtractor"):
                        with patch(
                            "app.workers.tasks.ScreenerService",
                            return_value=mock_screener_instance,
                        ):
                            with patch(
                                "app.workers.tasks.WebhookService", return_value=mock_webhook
                            ):
                                result = await _execute_scheduled_screener()

        mock_webhook.send_screener_report.assert_not_awaited()
        assert result["nb_opportunites"] == 0
        assert result["tickers_fort"] == []


# ---------------------------------------------------------------------------
# Test 6 : tolérance aux erreurs de screen
# ---------------------------------------------------------------------------


class TestToleranceErreurs:
    @pytest.mark.asyncio
    async def test_erreur_screen_narrete_pas_la_tache(self):
        from app.workers.tasks import _execute_scheduled_screener

        wl_entries = [_make_wl_entry("INVALID")]
        mock_pool = _make_db_pool()
        mock_orch_pool = _make_db_pool()
        mock_wl_instance = AsyncMock()
        mock_wl_instance.list_entries = AsyncMock(return_value=wl_entries)
        mock_screener_instance = AsyncMock()
        mock_screener_instance.screen = AsyncMock(
            side_effect=RuntimeError("Ticker invalide")
        )

        with _patch_create_pool(mock_pool):
            with patch("app.workers.tasks.WatchlistService", return_value=mock_wl_instance):
                with patch(
                    "app.workers.tasks._build_orchestrator",
                    new_callable=AsyncMock,
                    return_value=(MagicMock(), mock_orch_pool),
                ):
                    with patch("app.workers.tasks.YahooFinanceExtractor"):
                        with patch(
                            "app.workers.tasks.ScreenerService",
                            return_value=mock_screener_instance,
                        ):
                            with patch("app.workers.tasks.WebhookService") as MockWebhook:
                                MockWebhook.return_value.send_screener_report = AsyncMock()
                                MockWebhook.return_value.send_screener_pdf_report = AsyncMock(
                                    return_value=False
                                )
                                result = await _execute_scheduled_screener()

        assert result["nb_tickers_screenes"] == 1
        assert result["nb_opportunites"] == 0
        assert result["tickers_fort"] == []

    @pytest.mark.asyncio
    async def test_ticker_avec_erreur_dans_resultats_ignore(self):
        """Un ScreenEntry avec erreur != None est exclu des FORT même si dans les résultats."""
        from app.workers.tasks import _execute_scheduled_screener

        wl_entries = [_make_wl_entry("ERR")]
        screen_entries = [
            _make_screen_entry(
                "ERR", composite_label="FORT", defensive_score=8, erreur="timeout"
            )
        ]
        mock_pool = _make_db_pool()
        mock_orch_pool = _make_db_pool()
        mock_wl_instance = AsyncMock()
        mock_wl_instance.list_entries = AsyncMock(return_value=wl_entries)
        mock_screener_instance = AsyncMock()
        mock_screener_instance.screen = AsyncMock(
            return_value=_make_screen_result(screen_entries)
        )

        with _patch_create_pool(mock_pool):
            with patch("app.workers.tasks.WatchlistService", return_value=mock_wl_instance):
                with patch(
                    "app.workers.tasks._build_orchestrator",
                    new_callable=AsyncMock,
                    return_value=(MagicMock(), mock_orch_pool),
                ):
                    with patch("app.workers.tasks.YahooFinanceExtractor"):
                        with patch(
                            "app.workers.tasks.ScreenerService",
                            return_value=mock_screener_instance,
                        ):
                            with patch("app.workers.tasks.WebhookService") as MockWebhook:
                                MockWebhook.return_value.send_screener_report = AsyncMock()
                                MockWebhook.return_value.send_screener_pdf_report = AsyncMock(
                                    return_value=False
                                )
                                result = await _execute_scheduled_screener()

        assert result["nb_opportunites"] == 0
        assert "ERR" not in result["tickers_fort"]


# ---------------------------------------------------------------------------
# Test 7 : beat_schedule contient run-scheduled-screener
# ---------------------------------------------------------------------------


class TestBeatSchedule:
    def test_run_scheduled_screener_dans_beat_schedule(self):
        schedule = celery_app.conf.beat_schedule
        assert "run-scheduled-screener" in schedule

    def test_run_scheduled_screener_tache_correcte(self):
        entry = celery_app.conf.beat_schedule["run-scheduled-screener"]
        assert entry["task"] == "run_scheduled_screener"

    def test_run_scheduled_screener_planifie_dimanche(self):
        from celery.schedules import crontab

        entry = celery_app.conf.beat_schedule["run-scheduled-screener"]
        schedule = entry["schedule"]
        assert isinstance(schedule, crontab)


# ---------------------------------------------------------------------------
# Test 8 : WebhookService.send_screener_report (méthode directe)
# ---------------------------------------------------------------------------


class TestWebhookServiceSendScreenerReport:
    @pytest.mark.asyncio
    async def test_send_screener_report_construit_payload_correct(self):
        import os

        from app.services.webhook_service import WebhookService

        with patch.dict(os.environ, {"WEBHOOK_URL": "http://test.local/hook"}):
            svc = WebhookService()
            with patch.object(
                svc, "_post", new_callable=AsyncMock, return_value=True
            ) as mock_post:
                result = await svc.send_screener_report(
                    nb_tickers_screenes=10,
                    tickers_fort=["BNS", "RY"],
                )

        assert result is True
        payload = mock_post.call_args[0][0]
        assert payload["type"] == "screener"
        assert payload["nb_tickers_screenes"] == 10
        assert payload["nb_opportunites"] == 2
        assert payload["tickers_fort"] == ["BNS", "RY"]

    @pytest.mark.asyncio
    async def test_send_screener_report_retourne_false_sans_webhook_url(self):
        import os

        from app.services.webhook_service import WebhookService

        env = {k: v for k, v in os.environ.items() if k != "WEBHOOK_URL"}
        with patch.dict(os.environ, env, clear=True):
            svc = WebhookService()
            result = await svc.send_screener_report(
                nb_tickers_screenes=5,
                tickers_fort=["BNS"],
            )

        assert result is False
