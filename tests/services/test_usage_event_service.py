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
        """Append-only : seul `record` est exposé (ni update ni delete)."""
        methods = {m for m in dir(UsageEventService) if not m.startswith("_")}
        assert methods == {"record"}


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
