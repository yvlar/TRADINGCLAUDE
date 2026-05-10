"""Tests du ObservabilityService — compteurs Redis + calcul de percentiles."""
from __future__ import annotations

from datetime import date, datetime, timezone

import pytest

from app.services.observability import ObservabilityService, SkillTrace


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_trace(
    skill_id: str = "graham_analysis",
    ticker: str = "BNS",
    cost_usd: float = 0.01,
    latency_ms: int = 1000,
    cache_hit: bool = False,
) -> SkillTrace:
    return SkillTrace(
        skill_id=skill_id,
        ticker=ticker,
        cost_usd=cost_usd,
        latency_ms=latency_ms,
        cache_hit=cache_hit,
        tokens_input=100,
        tokens_output=50,
        created_at=datetime.now(timezone.utc),
    )


# ---------------------------------------------------------------------------
# Tests record_skill_execution
# ---------------------------------------------------------------------------


async def test_record_sans_langfuse_ok(obs_service: ObservabilityService) -> None:
    """langfuse=None → pas d'exception levée."""
    await obs_service.record_skill_execution(_make_trace())


async def test_record_incremente_cout_redis(
    obs_service: ObservabilityService, mock_obs_redis
) -> None:
    """INCRBYFLOAT obs:cost:{date} correct après un enregistrement."""
    trace = _make_trace(cost_usd=0.025)
    await obs_service.record_skill_execution(trace)

    date_str = trace.created_at.strftime("%Y-%m-%d")
    val = await mock_obs_redis.get(f"obs:cost:{date_str}")
    assert val is not None
    assert abs(float(val) - 0.025) < 1e-6


async def test_record_cache_hit_incremente_hits(
    obs_service: ObservabilityService, mock_obs_redis
) -> None:
    """cache_hit=True → obs:cache:hits incrémenté de 1."""
    await obs_service.record_skill_execution(_make_trace(cache_hit=True))
    hits = await mock_obs_redis.get("obs:cache:hits")
    assert hits is not None
    assert int(hits) >= 1


async def test_record_cache_miss_incremente_misses(
    obs_service: ObservabilityService, mock_obs_redis
) -> None:
    """cache_hit=False → obs:cache:misses incrémenté de 1."""
    await obs_service.record_skill_execution(_make_trace(cache_hit=False))
    misses = await mock_obs_redis.get("obs:cache:misses")
    assert misses is not None
    assert int(misses) >= 1


# ---------------------------------------------------------------------------
# Tests get_cost_summary
# ---------------------------------------------------------------------------


async def test_get_cost_summary_vide(obs_service: ObservabilityService) -> None:
    """0 enregistrements → cost_total=0.0, cost_par_jour a N entrées."""
    summary = await obs_service.get_cost_summary(days=7)
    assert summary.cost_total_usd == 0.0
    assert len(summary.cost_par_jour) == 7
    assert all(d.cost_usd == 0.0 for d in summary.cost_par_jour)


async def test_get_cost_summary_cumul_correct(obs_service: ObservabilityService) -> None:
    """3 appels à 0.01 USD → total 0.03 USD."""
    for _ in range(3):
        await obs_service.record_skill_execution(_make_trace(cost_usd=0.01))

    summary = await obs_service.get_cost_summary(days=7)
    assert abs(summary.cost_total_usd - 0.03) < 1e-5


# ---------------------------------------------------------------------------
# Tests get_cache_stats
# ---------------------------------------------------------------------------


async def test_get_cache_stats_hit_ratio(obs_service: ObservabilityService) -> None:
    """3 hits + 1 miss → hits=3, misses=1, hit_ratio=0.75."""
    for _ in range(3):
        await obs_service.record_skill_execution(_make_trace(cache_hit=True))
    await obs_service.record_skill_execution(_make_trace(cache_hit=False))

    stats = await obs_service.get_cache_stats()
    assert stats.hits == 3
    assert stats.misses == 1
    assert abs(stats.hit_ratio - 0.75) < 1e-4


async def test_get_cache_stats_vide(obs_service: ObservabilityService) -> None:
    """0 hits, 0 misses → hit_ratio=0.0."""
    stats = await obs_service.get_cache_stats()
    assert stats.hits == 0
    assert stats.misses == 0
    assert stats.hit_ratio == 0.0
    assert 0.0 <= stats.hit_ratio <= 1.0


# ---------------------------------------------------------------------------
# Tests get_latency_p95
# ---------------------------------------------------------------------------


async def test_get_latency_p95_calcul(obs_service: ObservabilityService) -> None:
    """100 valeurs 0, 10, ..., 990ms → p95 dans [940, 960]."""
    for i in range(100):
        await obs_service.record_skill_execution(
            _make_trace(latency_ms=i * 10, skill_id="graham_analysis")
        )

    stats = await obs_service.get_latency_p95(skill_id="graham_analysis")
    assert stats.sample_count == 100
    assert stats.p95_ms is not None
    assert 940 <= stats.p95_ms <= 960


# ---------------------------------------------------------------------------
# Tests check_cost_alert
# ---------------------------------------------------------------------------


async def test_check_cost_alert_depasse(
    obs_service: ObservabilityService, mock_obs_redis
) -> None:
    """obs:alert:{today} présent dans Redis → check_cost_alert() retourne True."""
    today_str = date.today().strftime("%Y-%m-%d")
    await mock_obs_redis.set(f"obs:alert:{today_str}", "1", ex=86400)

    assert await obs_service.check_cost_alert() is True
