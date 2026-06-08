"""Tests CI standard pour le threading tenant à travers la frontière Celery (E5-S7).

Aucune DB réelle ni appel Claude : `_build_orchestrator`, `asyncpg.create_pool`, le broker Celery
(`run_full_analysis.delay`) et `PriceAlertService` sont patchés. L'attribution RLS bout-en-bout du
`usage_event` au tenant propriétaire est prouvée en intégration sous PG migré
(`tests/integration/test_price_alert_metering_rls.py`).
"""
from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.db.tenant_context import LEGACY_TENANT_ID, get_current_tenant
from app.workers import tasks

# Aucun des deux n'est le tenant legacy (défaut du ContextVar) : une capture de scope == _TENANT_A
# prouve donc que le scope a bien été posé, et ne peut pas se confondre avec le défaut non posé.
_TENANT_A = uuid.UUID("00000000-0000-0000-0000-0000000000aa")
_TENANT_B = uuid.UUID("00000000-0000-0000-0000-0000000000bb")


class TestExecuteAnalysisTenant:
    @pytest.mark.asyncio
    async def test_execute_analysis_tourne_sous_le_tenant_passe(self):
        """`_execute_analysis(tenant_id)` exécute l'orchestrateur sous `tenant_scope(tenant_id)`."""
        captured: list = []

        fake_orch = MagicMock()

        async def _run(request):
            captured.append(get_current_tenant())
            resp = MagicMock()
            resp.model_dump.return_value = {"ticker": request.ticker}
            return resp

        fake_orch.run_company_analysis = AsyncMock(side_effect=_run)
        fake_pool = AsyncMock()

        with patch.object(
            tasks, "_build_orchestrator", new_callable=AsyncMock,
            return_value=(fake_orch, fake_pool),
        ) as mock_build:
            result = await tasks._execute_analysis({"ticker": "BNS"}, str(_TENANT_A))

        assert captured == [_TENANT_A]  # non-vacuous : _TENANT_A != LEGACY
        assert result == {"ticker": "BNS"}
        mock_build.assert_awaited_once_with(with_metering=True)  # orchestrateur métré
        fake_pool.close.assert_awaited_once()
        assert get_current_tenant() == LEGACY_TENANT_ID  # ContextVar restauré

    @pytest.mark.asyncio
    async def test_execute_analysis_sans_tenant_replie_legacy(self):
        """Sans `tenant_id` (appelant legacy / non authentifié), l'analyse tourne sous legacy."""
        captured: list = []

        fake_orch = MagicMock()

        async def _run(request):
            captured.append(get_current_tenant())
            resp = MagicMock()
            resp.model_dump.return_value = {}
            return resp

        fake_orch.run_company_analysis = AsyncMock(side_effect=_run)

        with patch.object(
            tasks, "_build_orchestrator", new_callable=AsyncMock,
            return_value=(fake_orch, AsyncMock()),
        ):
            await tasks._execute_analysis({"ticker": "BNS"})

        assert captured == [LEGACY_TENANT_ID]


class TestRunFullAnalysisPropagation:
    def test_run_full_analysis_propage_tenant_a_execute_analysis(self):
        """La tâche Celery transmet le `tenant_id` reçu à `_execute_analysis` (restauration du contexte)."""
        mock_redis = MagicMock()
        with (
            patch("app.workers.tasks._get_redis", return_value=mock_redis),
            patch(
                "app.workers.tasks._execute_analysis",
                new_callable=AsyncMock, return_value={"ok": 1},
            ) as mock_exec,
        ):
            from app.workers.tasks import run_full_analysis
            run_full_analysis.apply(args=["job-x", {"ticker": "BNS"}, str(_TENANT_A)])

        mock_exec.assert_awaited_once_with({"ticker": "BNS"}, str(_TENANT_A))

    def test_run_full_analysis_sans_tenant_passe_none(self):
        """Appel rétrocompatible à 2 arguments → `tenant_id=None` (repli legacy)."""
        mock_redis = MagicMock()
        with (
            patch("app.workers.tasks._get_redis", return_value=mock_redis),
            patch(
                "app.workers.tasks._execute_analysis",
                new_callable=AsyncMock, return_value={"ok": 1},
            ) as mock_exec,
        ):
            from app.workers.tasks import run_full_analysis
            run_full_analysis.apply(args=["job-y", {"ticker": "BNS"}])

        mock_exec.assert_awaited_once_with({"ticker": "BNS"}, None)


def _make_price_pool(tenant_ids: list[uuid.UUID]) -> AsyncMock:
    """Pool discriminant la requête `tenants` (hors RLS) de la lecture watchlist (RLS-scopée)."""
    pool = AsyncMock()

    async def _fetch(query: str, *args):
        if "FROM tenants" in query:
            return [{"id": tid} for tid in tenant_ids]
        if "FROM watchlist" in query:  # _trigger : SELECT id, workflow, ratios WHERE ticker = $1
            return [
                {"id": uuid.uuid4(), "workflow": "value_graham", "ratios": None}
            ]
        return []

    pool.fetch = AsyncMock(side_effect=_fetch)
    pool.fetchrow = AsyncMock(return_value=None)  # pas de webhook prix à envoyer
    pool.execute = AsyncMock()
    pool.close = AsyncMock()
    return pool


class TestPriceAlertThreadingTenant:
    @pytest.mark.asyncio
    async def test_check_par_tenant_et_capture_proprietaire_au_delay(self):
        """Chaque tenant est vérifié sous son scope ; le `.delay()` porte le tenant propriétaire."""
        pool = _make_price_pool([_TENANT_A, _TENANT_B])

        seen_check: list = []
        fake_service = MagicMock()

        async def _check(db_pool, extractor):
            tenant = get_current_tenant()
            seen_check.append(tenant)
            # Alerte seulement pour B → une seule re-analyse déclenchée.
            return ["BBB"] if tenant == _TENANT_B else []

        fake_service.check_price_alerts = AsyncMock(side_effect=_check)

        delay_calls: list = []
        fake_task = MagicMock()
        fake_task.delay = MagicMock(side_effect=lambda *a: delay_calls.append(a))

        with (
            patch("app.workers.tasks.asyncpg.create_pool", AsyncMock(return_value=pool)),
            patch.object(tasks, "PriceAlertService", return_value=fake_service),
            patch.object(tasks, "YahooFinanceExtractor"),
            patch.object(tasks, "WebhookService", return_value=AsyncMock()),
            patch.object(tasks, "run_full_analysis", fake_task),
            patch.object(tasks, "_get_redis", return_value=MagicMock()),
        ):
            alerted = await tasks._execute_price_alert_check()

        assert seen_check == [_TENANT_A, _TENANT_B]  # vérif sous chaque tenant
        assert alerted == ["BBB"]  # union des tickers en alerte
        assert len(delay_calls) == 1
        _job_id, _payload, tenant_arg = delay_calls[0]
        assert tenant_arg == str(_TENANT_B)  # tenant propriétaire propagé au worker
        assert get_current_tenant() == LEGACY_TENANT_ID  # ContextVar restauré

    @pytest.mark.asyncio
    async def test_echec_dun_tenant_ninterrompt_pas_les_autres(self):
        """L'échec de la vérif d'un tenant (loggé) n'avorte pas les suivants ; contexte restauré."""
        pool = _make_price_pool([_TENANT_A, _TENANT_B])

        seen_check: list = []
        fake_service = MagicMock()

        async def _check(db_pool, extractor):
            tenant = get_current_tenant()
            seen_check.append(tenant)
            if tenant == _TENANT_A:
                raise RuntimeError("panne extraction prix tenant A")
            return []

        fake_service.check_price_alerts = AsyncMock(side_effect=_check)

        with (
            patch("app.workers.tasks.asyncpg.create_pool", AsyncMock(return_value=pool)),
            patch.object(tasks, "PriceAlertService", return_value=fake_service),
            patch.object(tasks, "YahooFinanceExtractor"),
            patch.object(tasks, "WebhookService", return_value=AsyncMock()),
            patch.object(tasks, "run_full_analysis", MagicMock()),
            patch.object(tasks, "_get_redis", return_value=MagicMock()),
        ):
            alerted = await tasks._execute_price_alert_check()

        assert seen_check == [_TENANT_A, _TENANT_B]  # B traité malgré l'échec de A
        assert alerted == []
        assert get_current_tenant() == LEGACY_TENANT_ID
