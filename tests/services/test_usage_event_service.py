"""Tests unitaires UsageEventService — metering append-only (E4-S1).

asyncpg mocké via AsyncMock — aucune DB réelle (validation runtime = job CI migrations +
matrice RLS `tests/integration/test_rls_isolation.py`, usage_events = 7ᵉ table).
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from decimal import Decimal
from unittest.mock import AsyncMock

import pytest

from app.models.tenant import LEGACY_TENANT_ID
from app.services.usage_event_service import (
    UsageEventService,
    record_usage_safe,
)

_NOW = datetime(2026, 6, 6, 12, 0, 0, tzinfo=timezone.utc)


def _make_row(
    *,
    tenant_id: uuid.UUID | None = None,
    skill: str = "graham_analysis",
    workflow: str = "value_graham",
    cost_usd: object = Decimal("0.012345"),
    tokens_input: int = 1500,
    tokens_output: int = 800,
) -> dict:
    return {
        "id": uuid.uuid4(),
        "tenant_id": tenant_id or LEGACY_TENANT_ID,
        "skill": skill,
        "workflow": workflow,
        "cost_usd": cost_usd,
        "tokens_input": tokens_input,
        "tokens_output": tokens_output,
        "created_at": _NOW,
    }


class TestRecord:

    @pytest.mark.asyncio
    async def test_record_insere_et_retourne_evenement(self):
        pool = AsyncMock()
        pool.fetchrow = AsyncMock(return_value=_make_row())
        svc = UsageEventService(db_pool=pool)

        event = await svc.record(
            skill="graham_analysis",
            workflow="value_graham",
            cost_usd=0.012345,
            tokens_input=1500,
            tokens_output=800,
        )

        assert event.skill == "graham_analysis"
        assert event.workflow == "value_graham"
        assert event.cost_usd == pytest.approx(0.012345)
        assert event.tokens_input == 1500
        pool.fetchrow.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_record_defaut_tenant_legacy_via_resolve_tenant(self):
        """tenant_id absent → resolve_tenant → tenant courant (legacy par défaut)."""
        pool = AsyncMock()
        pool.fetchrow = AsyncMock(return_value=_make_row())
        svc = UsageEventService(db_pool=pool)

        await svc.record(
            skill="earnings_quality",
            workflow="value_graham",
            cost_usd=0.5,
            tokens_input=10,
            tokens_output=20,
        )

        # args : query=0, tenant=1, skill=2, workflow=3, cost_usd=4, tokens_input=5, tokens_output=6
        assert pool.fetchrow.call_args.args[1] == str(LEGACY_TENANT_ID)

    @pytest.mark.asyncio
    async def test_record_tenant_explicite_est_utilise(self):
        pool = AsyncMock()
        pool.fetchrow = AsyncMock(return_value=_make_row())
        svc = UsageEventService(db_pool=pool)
        tid = uuid.uuid4()

        await svc.record(
            skill="dorsey_moat",
            workflow="compounder_buffett",
            cost_usd=1.0,
            tokens_input=1,
            tokens_output=2,
            tenant_id=tid,
        )

        assert pool.fetchrow.call_args.args[1] == str(tid)

    @pytest.mark.asyncio
    async def test_record_cost_usd_lie_en_decimal(self):
        """asyncpg exige un Decimal pour NUMERIC — un float lèverait DataError."""
        pool = AsyncMock()
        pool.fetchrow = AsyncMock(return_value=_make_row())
        svc = UsageEventService(db_pool=pool)

        await svc.record(
            skill="graham_analysis",
            workflow="value_graham",
            cost_usd=0.012345,
            tokens_input=1,
            tokens_output=2,
        )

        cost_param = pool.fetchrow.call_args.args[4]
        assert isinstance(cost_param, Decimal)
        assert cost_param == Decimal("0.012345")

    @pytest.mark.asyncio
    async def test_record_insert_pur_pas_de_conflict(self):
        """Append-only : INSERT pur, jamais d'UPDATE ni d'ON CONFLICT."""
        pool = AsyncMock()
        pool.fetchrow = AsyncMock(return_value=_make_row())
        svc = UsageEventService(db_pool=pool)

        await svc.record(
            skill="graham_analysis", workflow="value_graham",
            cost_usd=0.1, tokens_input=1, tokens_output=2,
        )

        query = pool.fetchrow.call_args.args[0]
        assert "INSERT INTO usage_events" in query
        assert "ON CONFLICT" not in query
        assert "UPDATE" not in query


class TestAppendOnly:

    def test_service_n_expose_aucune_mutation(self):
        """Append-only : `record` (write) + `aggregate`/`count_events_in_window` (read), jamais update/delete."""
        methods = {m for m in dir(UsageEventService) if not m.startswith("_")}
        assert methods == {"record", "aggregate", "count_events_in_window"}


class TestCountEventsInWindow:

    @pytest.mark.asyncio
    async def test_compte_fenetre_bornee(self):
        pool = AsyncMock()
        pool.fetchval = AsyncMock(return_value=5)
        svc = UsageEventService(db_pool=pool)
        since = datetime(2026, 6, 1, tzinfo=timezone.utc)
        until = datetime(2026, 6, 8, tzinfo=timezone.utc)

        count = await svc.count_events_in_window(since, until)

        assert count == 5
        query, *args = pool.fetchval.call_args.args
        # Borne basse exclue, haute incluse → fenêtres consécutives sans chevauchement ni trou.
        assert "created_at > $1 AND created_at <= $2" in query
        assert args == [since, until]

    @pytest.mark.asyncio
    async def test_since_none_compte_tout_jusqua_until(self):
        """Curseur jamais posé → toute la consommation jusqu'à `until` (created_at <= until)."""
        pool = AsyncMock()
        pool.fetchval = AsyncMock(return_value=12)
        svc = UsageEventService(db_pool=pool)
        until = datetime(2026, 6, 8, tzinfo=timezone.utc)

        count = await svc.count_events_in_window(None, until)

        assert count == 12
        query, *args = pool.fetchval.call_args.args
        assert "created_at <= $1" in query
        assert "created_at >" not in query
        assert args == [until]

    @pytest.mark.asyncio
    async def test_jeu_vide_renvoie_zero(self):
        """COUNT(*) ne renvoie jamais NULL, mais le COALESCE défensif garantit 0."""
        pool = AsyncMock()
        pool.fetchval = AsyncMock(return_value=0)
        svc = UsageEventService(db_pool=pool)
        count = await svc.count_events_in_window(
            datetime(2026, 6, 1, tzinfo=timezone.utc),
            datetime(2026, 6, 8, tzinfo=timezone.utc),
        )
        assert count == 0

    @pytest.mark.asyncio
    async def test_sans_filtre_tenant_applicatif(self):
        """Isolation par la RLS : aucune des requêtes ne porte de WHERE tenant_id."""
        pool = AsyncMock()
        pool.fetchval = AsyncMock(return_value=0)
        svc = UsageEventService(db_pool=pool)
        until = datetime(2026, 6, 8, tzinfo=timezone.utc)

        await svc.count_events_in_window(None, until)
        await svc.count_events_in_window(datetime(2026, 6, 1, tzinfo=timezone.utc), until)

        for call in pool.fetchval.call_args_list:
            assert "tenant_id" not in call.args[0]


class TestAggregate:

    def _pool_with(self, *, totals: dict, skills: list[dict], daily: list[dict]) -> AsyncMock:
        pool = AsyncMock()
        pool.fetchrow = AsyncMock(return_value=totals)
        # fetch est appelé 2 fois : skills puis daily (ordre des requêtes dans aggregate).
        pool.fetch = AsyncMock(side_effect=[skills, daily])
        return pool

    @pytest.mark.asyncio
    async def test_aggregate_calcule_totaux_par_skill_et_par_jour(self):
        pool = self._pool_with(
            totals={
                "total_cost": Decimal("0.030000"),
                "total_in": 3000,
                "total_out": 1500,
            },
            skills=[
                {"skill": "graham_analysis", "cost": Decimal("0.020000"),
                 "tok_in": 2000, "tok_out": 1000, "nb": 2},
                {"skill": "earnings_quality", "cost": Decimal("0.010000"),
                 "tok_in": 1000, "tok_out": 500, "nb": 1},
            ],
            daily=[
                {"day": "2026-06-05", "cost": Decimal("0.010000")},
                {"day": "2026-06-06", "cost": Decimal("0.020000")},
            ],
        )
        svc = UsageEventService(db_pool=pool)

        result = await svc.aggregate(days=30)

        assert result.period_days == 30
        assert result.total_cost_usd == pytest.approx(0.03)
        assert result.total_tokens_input == 3000
        assert result.total_tokens_output == 1500
        assert [s.skill for s in result.by_skill] == ["graham_analysis", "earnings_quality"]
        assert result.by_skill[0].events == 2
        assert result.by_skill[0].cost_usd == pytest.approx(0.02)
        assert result.daily_cost == {"2026-06-05": 0.01, "2026-06-06": 0.02}

    @pytest.mark.asyncio
    async def test_aggregate_fenetre_days_liee_en_str_dans_chaque_requete(self):
        """La fenêtre `days` est passée en str ($1) aux 3 requêtes (borne `interval`)."""
        pool = self._pool_with(
            totals={"total_cost": 0, "total_in": 0, "total_out": 0},
            skills=[],
            daily=[],
        )
        svc = UsageEventService(db_pool=pool)

        await svc.aggregate(days=7)

        assert pool.fetchrow.call_args.args[1] == "7"
        assert all(call.args[1] == "7" for call in pool.fetch.call_args_list)

    @pytest.mark.asyncio
    async def test_aggregate_jeu_vide_renvoie_zeros(self):
        pool = self._pool_with(
            totals={"total_cost": 0, "total_in": 0, "total_out": 0},
            skills=[],
            daily=[],
        )
        svc = UsageEventService(db_pool=pool)

        result = await svc.aggregate(days=90)

        assert result.period_days == 90
        assert result.total_cost_usd == 0.0
        assert result.by_skill == []
        assert result.daily_cost == {}

    @pytest.mark.asyncio
    async def test_aggregate_sans_filtre_tenant_applicatif(self):
        """L'isolation vient de la RLS : aucune des requêtes ne porte de WHERE tenant_id."""
        pool = self._pool_with(
            totals={"total_cost": 0, "total_in": 0, "total_out": 0},
            skills=[],
            daily=[],
        )
        svc = UsageEventService(db_pool=pool)

        await svc.aggregate(days=30)

        queries = [pool.fetchrow.call_args.args[0]]
        queries += [call.args[0] for call in pool.fetch.call_args_list]
        for query in queries:
            assert "tenant_id" not in query


class TestRecordUsageSafe:

    @pytest.mark.asyncio
    async def test_safe_noop_si_service_none(self):
        # Metering désactivé : ne doit pas lever (best-effort).
        await record_usage_safe(
            None, skill="graham_analysis", workflow="value_graham",
            cost_usd=0.1, tokens_input=1, tokens_output=2,
        )

    @pytest.mark.asyncio
    async def test_safe_delegue_a_record(self):
        svc = AsyncMock(spec=UsageEventService)
        await record_usage_safe(
            svc, skill="graham_analysis", workflow="value_graham",
            cost_usd=0.1, tokens_input=1, tokens_output=2,
        )
        svc.record.assert_awaited_once_with(
            skill="graham_analysis",
            workflow="value_graham",
            cost_usd=0.1,
            tokens_input=1,
            tokens_output=2,
            tenant_id=None,
        )

    @pytest.mark.asyncio
    async def test_safe_avale_exception(self):
        """Une panne de metering ne doit jamais remonter à l'appelant (analyse préservée)."""
        svc = AsyncMock(spec=UsageEventService)
        svc.record.side_effect = Exception("DB metering indisponible")
        # Aucune exception attendue.
        await record_usage_safe(
            svc, skill="graham_analysis", workflow="value_graham",
            cost_usd=0.1, tokens_input=1, tokens_output=2,
        )
