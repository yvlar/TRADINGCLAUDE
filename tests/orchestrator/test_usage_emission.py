"""Tests de l'émission de metering par skill depuis l'orchestrateur (E4-S1).

`_emit_usage_events` mappe `skills_applied` ↔ `all_usages` (remplies en lockstep) et
émet un `usage_events` best-effort par skill consommé. Pas de DB : un faux service
capture les appels.
"""
from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.orchestrator.core import AnalyzeRequest, Orchestrator
from app.skills.base import UsageDetail
from app.skills.tier2.graham_analysis.skill import GrahamAnalysisSkill


class _FakeUsageEventService:
    """Capture les appels `record` (signature de `UsageEventService.record`)."""

    def __init__(self, *, fail: bool = False) -> None:
        self.calls: list[dict] = []
        self._fail = fail

    async def record(
        self, *, skill, workflow, cost_usd, tokens_input, tokens_output, tenant_id=None
    ):
        if self._fail:
            raise RuntimeError("DB metering indisponible")
        self.calls.append(
            {
                "skill": skill,
                "workflow": workflow,
                "cost_usd": cost_usd,
                "tokens_input": tokens_input,
                "tokens_output": tokens_output,
            }
        )


def _usage(cost: float, *, ti: int = 100, to: int = 50) -> UsageDetail:
    return UsageDetail(
        tokens_input=ti,
        tokens_output=to,
        tokens_cache_read=0,
        tokens_cache_creation=0,
        cost_usd=cost,
        model="claude-sonnet-4-6",
    )


def _orchestrator(usage_service: object | None) -> Orchestrator:
    return Orchestrator(
        db_pool=MagicMock(),
        graham_skill=MagicMock(),
        earnings_skill=MagicMock(),
        usage_event_service=usage_service,
    )


@pytest.mark.asyncio
async def test_emet_une_ligne_par_skill_consomme():
    fake = _FakeUsageEventService()
    orch = _orchestrator(fake)

    await orch._emit_usage_events(
        ["graham_analysis", "earnings_quality"],
        [_usage(0.01, ti=1500, to=800), _usage(0.02, ti=2000, to=900)],
        "value_graham",
    )

    assert [c["skill"] for c in fake.calls] == ["graham_analysis", "earnings_quality"]
    assert all(c["workflow"] == "value_graham" for c in fake.calls)
    # Appariement positionnel skill ↔ usage (tokens portés du bon UsageDetail).
    assert fake.calls[0]["cost_usd"] == 0.01
    assert fake.calls[0]["tokens_input"] == 1500
    assert fake.calls[1]["cost_usd"] == 0.02
    assert fake.calls[1]["tokens_output"] == 900


@pytest.mark.asyncio
async def test_cache_hit_cost_zero_n_emet_rien():
    """Un skill à coût nul (rien consommé) n'émet aucun usage_events."""
    fake = _FakeUsageEventService()
    orch = _orchestrator(fake)

    await orch._emit_usage_events(
        ["graham_analysis", "earnings_quality"],
        [_usage(0.0), _usage(0.03)],
        "value_graham",
    )

    assert [c["skill"] for c in fake.calls] == ["earnings_quality"]


@pytest.mark.asyncio
async def test_sans_service_ne_fait_rien():
    """Rétrocompat : un orchestrateur sans service de metering reste fonctionnel."""
    orch = _orchestrator(None)
    # Ne doit pas lever.
    await orch._emit_usage_events(["graham_analysis"], [_usage(0.01)], "value_graham")


@pytest.mark.asyncio
async def test_echec_metering_n_avorte_pas_l_analyse():
    """Best-effort : une panne du service de metering est avalée (analyse préservée)."""
    fake = _FakeUsageEventService(fail=True)
    orch = _orchestrator(fake)
    # Aucune exception attendue malgré le service qui lève.
    await orch._emit_usage_events(["graham_analysis"], [_usage(0.01)], "value_graham")


@pytest.mark.asyncio
async def test_run_company_analysis_emet_un_evenement_par_skill(
    graham_output_msft, earnings_output_msft, ratios_bns, ratios_earnings_msft
):
    """Bout-en-bout : la VRAIE `run_company_analysis` apparie `skills_applied`↔`all_usages`.

    Prouve que les sites d'append réels (et non des listes fabriquées à la main) sont
    correctement appariés — une régression où un bloc skill n'appenderait qu'à une seule
    liste serait attrapée ici. Claude est mocké via `execute` ; `_persist` est court-circuité.
    """
    fake = _FakeUsageEventService()
    graham = AsyncMock(spec=GrahamAnalysisSkill)
    graham.execute.return_value = (graham_output_msft, _usage(0.01, ti=1500, to=800))
    earnings = AsyncMock()
    earnings.execute.return_value = (earnings_output_msft, _usage(0.02, ti=2000, to=900))

    orch = Orchestrator(
        db_pool=MagicMock(),
        graham_skill=graham,
        earnings_skill=earnings,
        usage_event_service=fake,
    )
    orch._persist = AsyncMock(return_value=uuid.uuid4())

    request = AnalyzeRequest(
        ticker="TEST",
        workflow="value_graham",
        ratios=ratios_bns,
        earnings_ratios=ratios_earnings_msft,
    )
    await orch.run_company_analysis(request)

    # Un événement par skill exécuté, dans l'ordre, avec le coût/les tokens du bon skill.
    assert [c["skill"] for c in fake.calls] == ["graham_analysis", "earnings_quality"]
    assert fake.calls[0]["cost_usd"] == 0.01
    assert fake.calls[0]["tokens_input"] == 1500
    assert fake.calls[1]["cost_usd"] == 0.02
    assert fake.calls[1]["tokens_input"] == 2000
    assert all(c["workflow"] == "value_graham" for c in fake.calls)
