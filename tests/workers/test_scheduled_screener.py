"""Tests CI standard pour run_scheduled_screener — Sprint 64 (threading tenant E5-S4).

Aucun appel Claude réel. ScreenerService.screen() et WatchlistService.list_entries()
sont patchés (par tenant via `get_current_tenant()`) pour contrôler les résultats.
CI standard : pytest -m "not e2e and not evals"
"""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID

import pytest

from app.db.tenant_context import LEGACY_TENANT_ID, get_current_tenant
from app.workers.celery_app import celery_app

# Aucun des deux n'est le tenant legacy (défaut du ContextVar) : une capture de scope == _TENANT_A
# prouve donc que le scope a bien été posé, et ne peut pas se confondre avec le défaut non posé.
_TENANT_A = UUID("00000000-0000-0000-0000-0000000000aa")
_TENANT_B = UUID("00000000-0000-0000-0000-0000000000bb")

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


def _patch_create_pool(mock_pool: AsyncMock):
    """Patch asyncpg.create_pool (coroutine) pour retourner mock_pool."""
    create_pool = AsyncMock(return_value=mock_pool)
    return patch("app.workers.tasks.asyncpg.create_pool", create_pool)


def _patch_watchlist(entries_by_tenant: dict[UUID, list]):
    """Patch WatchlistService — `list_entries()` discrimine par `get_current_tenant()` (preuve RLS-scope)."""

    def _factory(*_args, **_kwargs):
        inst = AsyncMock()

        async def _list():
            return entries_by_tenant.get(get_current_tenant(), [])

        inst.list_entries = AsyncMock(side_effect=_list)
        return inst

    return patch("app.workers.tasks.WatchlistService", side_effect=_factory)


def _patch_screener(screen_by_tenant: dict[UUID, list], seen: list[UUID] | None = None):
    """Patch ScreenerService — `screen()` renvoie les entrées du tenant courant et capture le scope."""
    inst = AsyncMock()

    async def _screen(_req):
        tenant = get_current_tenant()
        if seen is not None:
            seen.append(tenant)
        return _make_screen_result(screen_by_tenant.get(tenant, []))

    inst.screen = AsyncMock(side_effect=_screen)
    return patch("app.workers.tasks.ScreenerService", return_value=inst)


def _patch_build():
    """Patch `_build_orchestrator` → (orchestrateur mock, pool fermable async)."""
    orch_pool = AsyncMock()
    orch_pool.close = AsyncMock()
    return patch(
        "app.workers.tasks._build_orchestrator",
        new_callable=AsyncMock,
        return_value=(MagicMock(), orch_pool),
    )


def _patch_webhook() -> AsyncMock:
    """Mock WebhookService avec toutes les méthodes async utilisées par le screener planifié."""
    webhook = AsyncMock()
    webhook.send_screener_report = AsyncMock(return_value=True)
    webhook.send_screener_pdf_report = AsyncMock(return_value=False)
    webhook.send_esg_alert = AsyncMock(return_value=True)
    return webhook


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

    def test_screen_tenant_watchlist_importable(self):
        from app.workers.tasks import _screen_tenant_watchlist

        assert callable(_screen_tenant_watchlist)


# ---------------------------------------------------------------------------
# Test : metering — orchestrateur métré
# ---------------------------------------------------------------------------


class TestMetering:
    @pytest.mark.asyncio
    async def test_orchestrateur_metre(self):
        """`_execute_scheduled_screener` réclame un orchestrateur métré (with_metering=True)."""
        from app.workers.tasks import _execute_scheduled_screener

        with (
            _patch_create_pool(_make_pool([_TENANT_A])),
            _patch_build() as mock_build,
            _patch_watchlist({_TENANT_A: []}),
            patch("app.workers.tasks.YahooFinanceExtractor"),
            _patch_screener({}),
            patch("app.workers.tasks.WebhookService", return_value=_patch_webhook()),
        ):
            await _execute_scheduled_screener()

        mock_build.assert_awaited_once_with(with_metering=True)


# ---------------------------------------------------------------------------
# Test : watchlist vide (aucun tenant n'a d'entrées)
# ---------------------------------------------------------------------------


class TestWatchlistVide:
    @pytest.mark.asyncio
    async def test_aucune_entree_tous_tenants_retourne_zero(self):
        from app.workers.tasks import _execute_scheduled_screener

        webhook = _patch_webhook()
        with (
            _patch_create_pool(_make_pool([_TENANT_A, _TENANT_B])),
            _patch_build(),
            _patch_watchlist({_TENANT_A: [], _TENANT_B: []}),
            patch("app.workers.tasks.YahooFinanceExtractor"),
            _patch_screener({}),
            patch("app.workers.tasks.WebhookService", return_value=webhook),
        ):
            result = await _execute_scheduled_screener()

        assert result == {"nb_tickers_screenes": 0, "nb_opportunites": 0, "tickers_fort": []}
        webhook.send_screener_report.assert_not_awaited()
        webhook.send_screener_pdf_report.assert_not_awaited()


# ---------------------------------------------------------------------------
# Test : threading tenant — chaque tenant screené sous son scope
# ---------------------------------------------------------------------------


class TestThreadingTenant:
    @pytest.mark.asyncio
    async def test_chaque_tenant_screene_sous_son_scope(self):
        from app.workers.tasks import _execute_scheduled_screener

        seen: list[UUID] = []
        with (
            _patch_create_pool(_make_pool([_TENANT_A, _TENANT_B])),
            _patch_build(),
            _patch_watchlist({_TENANT_A: [_make_wl_entry("BNS")], _TENANT_B: [_make_wl_entry("RY")]}),
            patch("app.workers.tasks.YahooFinanceExtractor"),
            _patch_screener(
                {
                    _TENANT_A: [_make_screen_entry("BNS", composite_label="FORT", defensive_score=6)],
                    _TENANT_B: [_make_screen_entry("RY", composite_label="FORT", defensive_score=6)],
                },
                seen=seen,
            ),
            patch("app.workers.tasks.WebhookService", return_value=_patch_webhook()),
        ):
            await _execute_scheduled_screener()

        # Capture au site screen() : A puis B, tous deux distincts du legacy (non-vacuous).
        assert seen == [_TENANT_A, _TENANT_B]

    @pytest.mark.asyncio
    async def test_lecture_watchlist_scopee_au_tenant_courant(self):
        """B sans entrée → seul A est screené (pas de fuite cross-tenant ; RLS rejouée)."""
        from app.workers.tasks import _execute_scheduled_screener

        seen: list[UUID] = []
        with (
            _patch_create_pool(_make_pool([_TENANT_A, _TENANT_B])),
            _patch_build(),
            _patch_watchlist({_TENANT_A: [_make_wl_entry("BNS")], _TENANT_B: []}),
            patch("app.workers.tasks.YahooFinanceExtractor"),
            _patch_screener(
                {_TENANT_A: [_make_screen_entry("BNS", composite_label="FORT", defensive_score=6)]},
                seen=seen,
            ),
            patch("app.workers.tasks.WebhookService", return_value=_patch_webhook()),
        ):
            await _execute_scheduled_screener()

        assert seen == [_TENANT_A]


# ---------------------------------------------------------------------------
# Test : agrégation union — webhook FORT et compteurs reflètent l'union des tenants
# ---------------------------------------------------------------------------


class TestAgregationUnion:
    @pytest.mark.asyncio
    async def test_webhook_fort_agrege_union_des_tenants(self):
        from app.workers.tasks import _execute_scheduled_screener

        webhook = _patch_webhook()
        with (
            _patch_create_pool(_make_pool([_TENANT_A, _TENANT_B])),
            _patch_build(),
            _patch_watchlist(
                {
                    _TENANT_A: [_make_wl_entry("BNS")],
                    _TENANT_B: [_make_wl_entry("RY"), _make_wl_entry("TD")],
                }
            ),
            patch("app.workers.tasks.YahooFinanceExtractor"),
            _patch_screener(
                {
                    _TENANT_A: [_make_screen_entry("BNS", composite_label="FORT", defensive_score=6)],
                    _TENANT_B: [
                        _make_screen_entry("RY", composite_label=None, defensive_score=7),
                        _make_screen_entry("TD", composite_label="FAIBLE", defensive_score=2),
                    ],
                }
            ),
            patch("app.workers.tasks.WebhookService", return_value=webhook),
        ):
            result = await _execute_scheduled_screener()

        # Union : BNS (label FORT, tenant A) + RY (defensive_score>=5, tenant B) ; TD exclu.
        assert result["nb_tickers_screenes"] == 3
        assert result["nb_opportunites"] == 2
        assert result["tickers_fort"] == ["BNS", "RY"]
        webhook.send_screener_report.assert_awaited_once()
        call = webhook.send_screener_report.call_args
        assert call.kwargs["tickers_fort"] == ["BNS", "RY"]
        assert call.kwargs["nb_tickers_screenes"] == 3

    @pytest.mark.asyncio
    async def test_webhook_fort_non_appele_si_aucun_fort(self):
        from app.workers.tasks import _execute_scheduled_screener

        webhook = _patch_webhook()
        with (
            _patch_create_pool(_make_pool([_TENANT_A])),
            _patch_build(),
            _patch_watchlist({_TENANT_A: [_make_wl_entry("TD")]}),
            patch("app.workers.tasks.YahooFinanceExtractor"),
            _patch_screener(
                {_TENANT_A: [_make_screen_entry("TD", composite_label="FAIBLE", defensive_score=2)]}
            ),
            patch("app.workers.tasks.WebhookService", return_value=webhook),
        ):
            result = await _execute_scheduled_screener()

        webhook.send_screener_report.assert_not_awaited()
        assert result["nb_opportunites"] == 0
        assert result["tickers_fort"] == []


# ---------------------------------------------------------------------------
# Test : best-effort et tolérance aux erreurs
# ---------------------------------------------------------------------------


class TestBestEffortEtErreurs:
    @pytest.mark.asyncio
    async def test_echec_dun_tenant_ninterrompt_pas_les_autres(self):
        """L'échec du screening d'un tenant (loggé) n'avorte pas les suivants ; ContextVar restauré."""
        from app.workers.tasks import _execute_scheduled_screener

        seen: list[UUID] = []

        async def _screen(_req):
            tenant = get_current_tenant()
            seen.append(tenant)
            if tenant == _TENANT_A:
                raise RuntimeError("panne screener tenant A")
            return _make_screen_result(
                [_make_screen_entry("RY", composite_label="FORT", defensive_score=6)]
            )

        screener_inst = AsyncMock()
        screener_inst.screen = AsyncMock(side_effect=_screen)
        webhook = _patch_webhook()

        with (
            _patch_create_pool(_make_pool([_TENANT_A, _TENANT_B])),
            _patch_build(),
            _patch_watchlist({_TENANT_A: [_make_wl_entry("BNS")], _TENANT_B: [_make_wl_entry("RY")]}),
            patch("app.workers.tasks.YahooFinanceExtractor"),
            patch("app.workers.tasks.ScreenerService", return_value=screener_inst),
            patch("app.workers.tasks.WebhookService", return_value=webhook),
        ):
            result = await _execute_scheduled_screener()

        # A lève dans son batch (avalé par le try/except batch → 0 entrée), B produit RY FORT.
        assert seen == [_TENANT_A, _TENANT_B]
        assert result["tickers_fort"] == ["RY"]
        assert get_current_tenant() == LEGACY_TENANT_ID

    @pytest.mark.asyncio
    async def test_ticker_avec_erreur_dans_resultats_ignore(self):
        """Un ScreenEntry avec erreur != None est exclu des FORT même si dans les résultats."""
        from app.workers.tasks import _execute_scheduled_screener

        with (
            _patch_create_pool(_make_pool([_TENANT_A])),
            _patch_build(),
            _patch_watchlist({_TENANT_A: [_make_wl_entry("ERR")]}),
            patch("app.workers.tasks.YahooFinanceExtractor"),
            _patch_screener(
                {
                    _TENANT_A: [
                        _make_screen_entry(
                            "ERR", composite_label="FORT", defensive_score=8, erreur="timeout"
                        )
                    ]
                }
            ),
            patch("app.workers.tasks.WebhookService", return_value=_patch_webhook()),
        ):
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
