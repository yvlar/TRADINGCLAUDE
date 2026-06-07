"""Tests CI standard pour run_usage_reporting (E4-S9) — report métré idempotent + best-effort.

Aucun appel Stripe ni DB réels : `asyncpg.create_pool`, `StripeService` et `UsageEventService`
sont patchés (pas de Docker dans le conteneur web → Stripe mocké). L'idempotence repose sur la
réservation `usage_report_log` (PK composite) ; ici le mock du claim renvoie une ligne au 1ᵉʳ
passage puis `None` au 2ᵉ pour prouver qu'aucun re-report n'a lieu.
"""
from __future__ import annotations

from contextlib import contextmanager
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID

import pytest

from app.db.tenant_context import get_current_tenant
from app.workers.celery_app import celery_app

_TENANT_A = UUID("00000000-0000-0000-0000-000000000001")
_TENANT_B = UUID("00000000-0000-0000-0000-0000000000bb")


def _sub_rows(*tenant_ids: UUID) -> list[dict]:
    return [{"tenant_id": t, "stripe_customer_id": f"cus_{t}"} for t in tenant_ids]


def _make_pool(sub_rows: list[dict], claim_results: list[object]) -> AsyncMock:
    pool = AsyncMock()
    pool.fetch = AsyncMock(return_value=sub_rows)  # tenants abonnés (hors RLS)
    pool.fetchrow = AsyncMock(side_effect=claim_results)  # réservation usage_report_log
    pool.close = AsyncMock()
    return pool


def _make_services(*, metered: bool = True, counts: dict[UUID, int] | None = None):
    stripe_mock = MagicMock()
    stripe_mock.is_metered_configured = metered
    stripe_mock.report_usage = AsyncMock()
    usage_mock = MagicMock()
    if counts is None:
        usage_mock.count_window = AsyncMock(return_value=0)
    else:
        # count_window lit le tenant courant → prouve que la tâche a posé le bon contexte RLS.
        usage_mock.count_window = AsyncMock(side_effect=lambda *a, **k: counts[get_current_tenant()])
    return stripe_mock, usage_mock


@contextmanager
def _patched(pool: AsyncMock, stripe_mock: MagicMock, usage_mock: MagicMock):
    with patch("app.workers.tasks.asyncpg.create_pool", AsyncMock(return_value=pool)), \
         patch("app.workers.tasks.StripeService", return_value=stripe_mock), \
         patch("app.workers.tasks.UsageEventService", return_value=usage_mock):
        yield


class TestImport:
    def test_run_usage_reporting_importable(self):
        from app.workers.tasks import run_usage_reporting

        assert callable(run_usage_reporting)

    def test_execute_usage_reporting_importable(self):
        from app.workers.tasks import _execute_usage_reporting

        assert callable(_execute_usage_reporting)


class TestDisabled:
    @pytest.mark.asyncio
    async def test_noop_si_meter_non_configure(self):
        """Meter absent → tâche désactivée : aucune lecture de tenants, aucun report."""
        from app.workers.tasks import _execute_usage_reporting

        pool = _make_pool(_sub_rows(_TENANT_A), [])
        stripe_mock, usage_mock = _make_services(metered=False)
        with _patched(pool, stripe_mock, usage_mock):
            result = await _execute_usage_reporting()

        assert result["disabled"] is True
        pool.fetch.assert_not_awaited()  # pas d'énumération des tenants
        stripe_mock.report_usage.assert_not_awaited()
        pool.close.assert_awaited_once()


class TestReporting:
    @pytest.mark.asyncio
    async def test_tenant_abonne_consommant_n_produit_un_record_quantite_n(self):
        """Preuve d'acceptation : N unités → un metered record de quantité N."""
        from app.workers.tasks import _execute_usage_reporting

        pool = _make_pool(_sub_rows(_TENANT_A), claim_results=[{"tenant_id": _TENANT_A}])
        stripe_mock, usage_mock = _make_services(counts={_TENANT_A: 5})
        with _patched(pool, stripe_mock, usage_mock):
            result = await _execute_usage_reporting()

        assert result["reported"] == 1
        assert result["total_quantity"] == 5
        stripe_mock.report_usage.assert_awaited_once()
        args, kwargs = stripe_mock.report_usage.call_args
        assert args[0] == f"cus_{_TENANT_A}"
        assert args[1] == 5
        assert isinstance(kwargs["timestamp"], int)
        assert kwargs["identifier"].startswith(f"usage:{_TENANT_A}:")

    @pytest.mark.asyncio
    async def test_deuxieme_run_meme_fenetre_ne_re_rapporte_pas(self):
        """Preuve d'acceptation : 2ᵉ exécution sur la même fenêtre → idempotence (pas de re-report)."""
        from app.workers.tasks import _execute_usage_reporting

        # 1ᵉʳ run réserve (claim → ligne), 2ᵉ run conflit (claim → None).
        pool = _make_pool(_sub_rows(_TENANT_A), claim_results=[{"tenant_id": _TENANT_A}, None])
        pool.fetch = AsyncMock(return_value=_sub_rows(_TENANT_A))  # même fenêtre réinterrogée
        stripe_mock, usage_mock = _make_services(counts={_TENANT_A: 5})
        with _patched(pool, stripe_mock, usage_mock):
            first = await _execute_usage_reporting()
            second = await _execute_usage_reporting()

        assert first["reported"] == 1
        assert second["reported"] == 0
        assert second["skipped"] == 1
        # Un seul metered record au total malgré deux exécutions sur la même fenêtre.
        assert stripe_mock.report_usage.await_count == 1

    @pytest.mark.asyncio
    async def test_fenetre_vide_reserve_sans_appel_stripe(self):
        """Quantité 0 → fenêtre réservée (traitée) mais aucun metered record poussé."""
        from app.workers.tasks import _execute_usage_reporting

        pool = _make_pool(_sub_rows(_TENANT_A), claim_results=[{"tenant_id": _TENANT_A}])
        stripe_mock, usage_mock = _make_services(counts={_TENANT_A: 0})
        with _patched(pool, stripe_mock, usage_mock):
            result = await _execute_usage_reporting()

        assert result["reported"] == 0
        assert result["skipped"] == 1
        pool.fetchrow.assert_awaited_once()  # la fenêtre est tout de même réservée
        stripe_mock.report_usage.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_pose_le_contexte_de_chaque_tenant(self):
        """count_window tourne sous le contexte RLS du tenant ciblé (set via tenant_scope)."""
        from app.workers.tasks import _execute_usage_reporting

        pool = _make_pool(
            _sub_rows(_TENANT_A, _TENANT_B),
            claim_results=[{"tenant_id": _TENANT_A}, {"tenant_id": _TENANT_B}],
        )
        seen: list[UUID] = []
        stripe_mock = MagicMock()
        stripe_mock.is_metered_configured = True
        stripe_mock.report_usage = AsyncMock()
        usage_mock = MagicMock()

        async def _capture(*a, **k):
            seen.append(get_current_tenant())
            return 0

        usage_mock.count_window = AsyncMock(side_effect=_capture)
        with _patched(pool, stripe_mock, usage_mock):
            await _execute_usage_reporting()

        assert seen == [_TENANT_A, _TENANT_B]


class TestBestEffort:
    @pytest.mark.asyncio
    async def test_echec_dun_tenant_ninterrompt_pas_les_autres(self):
        """L'échec du report d'un tenant (loggé) n'avorte pas le report des suivants."""
        from app.workers.tasks import _execute_usage_reporting

        # A échoue dès le comptage ; seule la réservation de B atteint le claim.
        pool = _make_pool(
            _sub_rows(_TENANT_A, _TENANT_B), claim_results=[{"tenant_id": _TENANT_B}]
        )
        stripe_mock = MagicMock()
        stripe_mock.is_metered_configured = True
        stripe_mock.report_usage = AsyncMock()
        usage_mock = MagicMock()

        async def _count(*a, **k):
            tid = get_current_tenant()
            if tid == _TENANT_A:
                raise RuntimeError("panne comptage tenant A")
            return 9

        usage_mock.count_window = AsyncMock(side_effect=_count)
        with _patched(pool, stripe_mock, usage_mock):
            result = await _execute_usage_reporting()

        assert result["reported"] == 1
        assert result["total_quantity"] == 9
        stripe_mock.report_usage.assert_awaited_once()


class TestBeatSchedule:
    def test_run_usage_reporting_dans_beat_schedule(self):
        assert "run-usage-reporting-daily" in celery_app.conf.beat_schedule

    def test_run_usage_reporting_tache_correcte(self):
        entry = celery_app.conf.beat_schedule["run-usage-reporting-daily"]
        assert entry["task"] == "run_usage_reporting"

    def test_run_usage_reporting_planifie_avant_la_purge(self):
        from celery.schedules import crontab

        entry = celery_app.conf.beat_schedule["run-usage-reporting-daily"]
        assert isinstance(entry["schedule"], crontab)
        assert entry["schedule"].hour == {2}  # avant la purge de rétention (03h00)
