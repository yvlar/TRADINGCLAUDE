"""Tests CI standard pour run_usage_reporting (E4-S9) — report d'usage métré vers Stripe.

Aucune DB ni SDK réels : asyncpg.create_pool, StripeService et UsageEventService sont patchés.
Couvre l'itération des tenants abonnés, le best-effort, l'idempotence par curseur (fenêtre déjà
rapportée → aucun re-report) et l'enregistrement dans beat_schedule.
"""
from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID

import pytest

from app.db.tenant_context import get_current_tenant
from app.workers.celery_app import celery_app

_TENANT_A = UUID("00000000-0000-0000-0000-000000000001")
_TENANT_B = UUID("00000000-0000-0000-0000-0000000000bb")
_WINDOW_END = datetime(2026, 6, 8, 2, 0, 0, tzinfo=timezone.utc)


def _sub_row(tenant_id: UUID, *, customer: str = "cus_x", since: datetime | None = None) -> dict:
    return {
        "tenant_id": tenant_id,
        "stripe_customer_id": customer,
        "usage_reported_through": since,
    }


def _make_pool(sub_rows: list[dict]) -> AsyncMock:
    pool = AsyncMock()
    pool.fetch = AsyncMock(return_value=sub_rows)
    pool.execute = AsyncMock()
    pool.close = AsyncMock()
    return pool


def _patch_create_pool(mock_pool: AsyncMock):
    return patch("app.workers.tasks.asyncpg.create_pool", AsyncMock(return_value=mock_pool))


def _mock_stripe(*, configured: bool = True) -> MagicMock:
    stripe_svc = MagicMock()
    stripe_svc.is_metered_configured = configured
    stripe_svc.report_usage = AsyncMock()
    return stripe_svc


def _mock_usage(count_fn) -> MagicMock:
    usage_svc = MagicMock()
    usage_svc.count_events_in_window = AsyncMock(side_effect=count_fn)
    return usage_svc


class TestImport:
    def test_run_usage_reporting_importable(self):
        from app.workers.tasks import run_usage_reporting

        assert callable(run_usage_reporting)

    def test_execute_usage_reporting_importable(self):
        from app.workers.tasks import _execute_usage_reporting

        assert callable(_execute_usage_reporting)


class TestReportPremierRun:
    @pytest.mark.asyncio
    async def test_tenant_abonne_consommant_n_produit_un_record_de_quantite_n(self):
        """Preuve d'acceptation : un tenant abonné consommant N produit UN metered record de quantité N."""
        from app.workers.tasks import _execute_usage_reporting

        mock_pool = _make_pool([_sub_row(_TENANT_A, customer="cus_a", since=None)])
        stripe_svc = _mock_stripe()

        async def _count(since, until):
            return 7  # N = 7 unités consommées sur la fenêtre

        usage_svc = _mock_usage(_count)

        with _patch_create_pool(mock_pool):
            with patch("app.workers.tasks.StripeService", return_value=stripe_svc):
                with patch("app.workers.tasks.UsageEventService", return_value=usage_svc):
                    result = await _execute_usage_reporting()

        stripe_svc.report_usage.assert_awaited_once()
        args, kwargs = stripe_svc.report_usage.call_args
        assert args[0] == "cus_a"  # customer cible
        assert args[1] == 7  # quantité = N
        assert result["tenants_reported"] == 1
        assert result["total_quantity"] == 7
        assert result["by_tenant"][str(_TENANT_A)] == 7
        # Curseur avancé : UPDATE subscriptions ... usage_reported_through
        update_call = mock_pool.execute.call_args
        assert "usage_reported_through" in update_call.args[0]

    @pytest.mark.asyncio
    async def test_count_scope_sous_le_contexte_du_tenant(self):
        """Le COUNT de usage_events tourne sous le contexte RLS du tenant (tenant_scope posé avant)."""
        from app.workers.tasks import _execute_usage_reporting

        mock_pool = _make_pool([_sub_row(_TENANT_A), _sub_row(_TENANT_B)])
        stripe_svc = _mock_stripe()
        seen: list[UUID] = []

        async def _count(since, until):
            seen.append(get_current_tenant())
            return 1

        usage_svc = _mock_usage(_count)

        with _patch_create_pool(mock_pool):
            with patch("app.workers.tasks.StripeService", return_value=stripe_svc):
                with patch("app.workers.tasks.UsageEventService", return_value=usage_svc):
                    await _execute_usage_reporting()

        assert seen == [_TENANT_A, _TENANT_B]


class TestIdempotence:
    @pytest.mark.asyncio
    async def test_fenetre_deja_rapportee_ne_re_rapporte_pas(self):
        """2ᵉ exécution sur la même fenêtre (curseur posé) → COUNT 0 → aucun report ni avance."""
        from app.workers.tasks import _execute_usage_reporting

        # Curseur déjà à window_end → la fenêtre (since, until] est vide.
        mock_pool = _make_pool([_sub_row(_TENANT_A, since=_WINDOW_END)])
        stripe_svc = _mock_stripe()

        async def _count(since, until):
            # since == until → fenêtre vide → 0 (le service réel renverrait 0 pour (t, t]).
            return 0 if since is not None else 5

        usage_svc = _mock_usage(_count)

        with _patch_create_pool(mock_pool):
            with patch("app.workers.tasks.StripeService", return_value=stripe_svc):
                with patch("app.workers.tasks.UsageEventService", return_value=usage_svc):
                    result = await _execute_usage_reporting()

        stripe_svc.report_usage.assert_not_awaited()
        assert result["tenants_reported"] == 0
        assert result["total_quantity"] == 0

    @pytest.mark.asyncio
    async def test_deux_runs_consecutifs_le_curseur_du_run1_supprime_le_re_report(self):
        """Bout-en-bout : run 1 rapporte N et avance le curseur ; run 2 voit la fenêtre vide → 0 report.

        Le curseur écrit par l'UPDATE du run 1 alimente le `since` du run 2 (holder mutable) ; le COUNT
        honore réellement la fenêtre `(since, until]` contre une frise d'événements figée — l'idempotence
        est démontrée, pas inférée de deux moitiés mockées indépendamment.
        """
        from app.workers.tasks import _execute_usage_reporting

        # 3 événements, tous dans le passé (avant le window_end réel de chaque run).
        events = [datetime(2020, 1, 1, tzinfo=timezone.utc)] * 3
        holder: dict[str, datetime | None] = {"cursor": None}

        async def _fetch(_query: str) -> list[dict]:
            return [_sub_row(_TENANT_A, customer="cus_a", since=holder["cursor"])]

        async def _execute(query: str, *args) -> None:
            if "usage_reported_through" in query:
                holder["cursor"] = args[1]  # (query, str(tenant_id), window_end)

        async def _count(since, until):
            return sum(1 for e in events if (since is None or e > since) and e <= until)

        mock_pool = AsyncMock()
        mock_pool.fetch = AsyncMock(side_effect=_fetch)
        mock_pool.execute = AsyncMock(side_effect=_execute)
        mock_pool.close = AsyncMock()
        stripe_svc = _mock_stripe()
        usage_svc = _mock_usage(_count)

        with _patch_create_pool(mock_pool):
            with patch("app.workers.tasks.StripeService", return_value=stripe_svc):
                with patch("app.workers.tasks.UsageEventService", return_value=usage_svc):
                    result1 = await _execute_usage_reporting()
                    assert holder["cursor"] is not None  # run 1 a avancé le curseur
                    result2 = await _execute_usage_reporting()

        # Run 1 : N=3 rapporté ; run 2 : fenêtre (curseur, now] vide → aucun re-report.
        assert result1["total_quantity"] == 3
        assert result2["total_quantity"] == 0
        stripe_svc.report_usage.assert_awaited_once()
        assert stripe_svc.report_usage.call_args.args[1] == 3

    @pytest.mark.asyncio
    async def test_identifier_stable_si_avance_curseur_echoue_evite_double_facturation(self):
        """Report réussi puis échec d'avance du curseur → le re-report porte le MÊME identifier.

        Garde contre le double-spend « report OK, commit du curseur KO » : l'identifier est keyé sur
        la borne basse (`since`), inchangée tant que le curseur n'a pas avancé → Stripe dédupe le 2ᵉ
        report de la même fenêtre (facturation at-most-once).
        """
        from app.workers.tasks import _execute_usage_reporting

        since0 = datetime(2026, 6, 7, tzinfo=timezone.utc)
        mock_pool = _make_pool([_sub_row(_TENANT_A, customer="cus_a", since=since0)])
        # L'UPDATE du curseur échoue systématiquement → la fenêtre n'avance jamais.
        mock_pool.execute = AsyncMock(side_effect=RuntimeError("commit du curseur KO"))
        stripe_svc = _mock_stripe()
        usage_svc = _mock_usage(lambda since, until: 2)

        with _patch_create_pool(mock_pool):
            with patch("app.workers.tasks.StripeService", return_value=stripe_svc):
                with patch("app.workers.tasks.UsageEventService", return_value=usage_svc):
                    await _execute_usage_reporting()  # run 1
                    await _execute_usage_reporting()  # run 2 (curseur non avancé)

        ids = [c.kwargs["identifier"] for c in stripe_svc.report_usage.call_args_list]
        assert len(ids) == 2
        assert ids[0] == ids[1] == f"{_TENANT_A}:{since0.isoformat()}"


class TestNonConfigure:
    @pytest.mark.asyncio
    async def test_meter_non_configure_noop(self):
        """Sans meter configuré → aucune itération, aucun report (no-op loggé)."""
        from app.workers.tasks import _execute_usage_reporting

        mock_pool = _make_pool([_sub_row(_TENANT_A)])
        stripe_svc = _mock_stripe(configured=False)
        usage_svc = _mock_usage(lambda since, until: 9)

        with _patch_create_pool(mock_pool):
            with patch("app.workers.tasks.StripeService", return_value=stripe_svc):
                with patch("app.workers.tasks.UsageEventService", return_value=usage_svc):
                    result = await _execute_usage_reporting()

        stripe_svc.report_usage.assert_not_awaited()
        mock_pool.fetch.assert_not_awaited()  # même pas la liste des abonnés
        assert result == {"tenants_reported": 0, "total_quantity": 0, "by_tenant": {}}


class TestBestEffort:
    @pytest.mark.asyncio
    async def test_echec_dun_tenant_ninterrompt_pas_les_autres(self):
        """Un report qui lève (tenant A) n'avorte pas le report du tenant B suivant."""
        from app.workers.tasks import _execute_usage_reporting

        mock_pool = _make_pool([_sub_row(_TENANT_A, customer="cus_a"), _sub_row(_TENANT_B, customer="cus_b")])
        stripe_svc = _mock_stripe()

        async def _report(customer_id, quantity, *, timestamp, identifier=None):
            if customer_id == "cus_a":
                raise RuntimeError("panne Stripe tenant A")

        stripe_svc.report_usage = AsyncMock(side_effect=_report)
        usage_svc = _mock_usage(lambda since, until: 4)

        with _patch_create_pool(mock_pool):
            with patch("app.workers.tasks.StripeService", return_value=stripe_svc):
                with patch("app.workers.tasks.UsageEventService", return_value=usage_svc):
                    result = await _execute_usage_reporting()

        # A échoue, B est tout de même rapporté.
        assert stripe_svc.report_usage.await_count == 2
        assert result["tenants_reported"] == 1
        assert str(_TENANT_B) in result["by_tenant"]
        assert str(_TENANT_A) not in result["by_tenant"]

    @pytest.mark.asyncio
    async def test_echec_n_avance_pas_le_curseur_du_tenant(self):
        """Un report qui lève ne doit PAS avancer le curseur (la fenêtre sera retentée)."""
        from app.workers.tasks import _execute_usage_reporting

        mock_pool = _make_pool([_sub_row(_TENANT_A, customer="cus_a")])
        stripe_svc = _mock_stripe()
        stripe_svc.report_usage = AsyncMock(side_effect=RuntimeError("boom"))
        usage_svc = _mock_usage(lambda since, until: 4)

        with _patch_create_pool(mock_pool):
            with patch("app.workers.tasks.StripeService", return_value=stripe_svc):
                with patch("app.workers.tasks.UsageEventService", return_value=usage_svc):
                    await _execute_usage_reporting()

        # Aucun UPDATE du curseur : l'échec saute l'avance (report → avance, dans cet ordre).
        mock_pool.execute.assert_not_awaited()


class TestBeatSchedule:
    def test_run_usage_reporting_dans_beat_schedule(self):
        assert "run-usage-reporting-daily" in celery_app.conf.beat_schedule

    def test_run_usage_reporting_tache_correcte(self):
        entry = celery_app.conf.beat_schedule["run-usage-reporting-daily"]
        assert entry["task"] == "run_usage_reporting"

    def test_run_usage_reporting_planifie_quotidien_heure_creuse(self):
        from celery.schedules import crontab

        entry = celery_app.conf.beat_schedule["run-usage-reporting-daily"]
        assert isinstance(entry["schedule"], crontab)
        assert entry["schedule"].hour == {2}
