"""Tests des endpoints /telemetry/* — résumé, coûts, cache, latence."""
from __future__ import annotations

from unittest.mock import AsyncMock

import pytest_asyncio

from app.api.main import app
from app.services.observability import (
    CacheStats,
    CostSummary,
    DailyCost,
    LatencyStats,
    ObservabilityService,
)

# ---------------------------------------------------------------------------
# Fixture — client avec ObservabilityService mocké dans app.state
# ---------------------------------------------------------------------------


@pytest_asyncio.fixture
async def telemetry_client(client):
    """Client HTTP avec ObservabilityService mocké retournant des données de test."""
    mock_obs = AsyncMock(spec=ObservabilityService)
    mock_obs.get_cost_summary.return_value = CostSummary(
        cost_total_usd=0.42,
        cost_par_jour=[
            DailyCost(date="2026-05-01", cost_usd=0.10),
            DailyCost(date="2026-05-08", cost_usd=0.32),
        ],
        analyses_count=18,
    )
    mock_obs.get_cache_stats.return_value = CacheStats(
        hits=54, misses=20, hit_ratio=0.73, keys_count=12
    )
    mock_obs.get_latency_p95.return_value = LatencyStats(
        skill_id=None,
        p50_ms=1800.0,
        p95_ms=3200.0,
        p99_ms=4100.0,
        sample_count=42,
    )
    mock_obs.check_cost_alert.return_value = False

    app.state.observability = mock_obs
    yield client


# ---------------------------------------------------------------------------
# Tests des endpoints /telemetry
# ---------------------------------------------------------------------------


async def test_telemetry_summary_200(telemetry_client) -> None:
    """GET /telemetry/summary → 200 + TelemetrySummary valide."""
    resp = await telemetry_client.get("/telemetry/summary?days=30")
    assert resp.status_code == 200
    data = resp.json()
    assert "cost_total_usd" in data
    assert "analyses_count" in data
    assert "cache_hit_ratio" in data
    assert "alerte_cout_active" in data


async def test_telemetry_costs_200(telemetry_client) -> None:
    """GET /telemetry/costs?days=7 → 200 + list[DailyCost]."""
    resp = await telemetry_client.get("/telemetry/costs?days=7")
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    if data:
        assert "date" in data[0]
        assert "cost_usd" in data[0]


async def test_telemetry_cache_200(telemetry_client) -> None:
    """GET /telemetry/cache → 200 + CacheStats valide."""
    resp = await telemetry_client.get("/telemetry/cache")
    assert resp.status_code == 200
    data = resp.json()
    assert "hits" in data
    assert "misses" in data
    assert "hit_ratio" in data
    assert "keys_count" in data


async def test_telemetry_latency_sans_filtre_200(telemetry_client) -> None:
    """GET /telemetry/latency sans skill_id → 200 + LatencyStats valide."""
    resp = await telemetry_client.get("/telemetry/latency")
    assert resp.status_code == 200
    data = resp.json()
    assert "sample_count" in data
    assert "p95_ms" in data


async def test_telemetry_latency_skill_filtre_200(telemetry_client) -> None:
    """GET /telemetry/latency?skill_id=graham_analysis → 200."""
    app.state.observability.get_latency_p95.return_value = LatencyStats(
        skill_id="graham_analysis",
        p50_ms=1800.0,
        p95_ms=3200.0,
        p99_ms=4100.0,
        sample_count=42,
    )
    resp = await telemetry_client.get("/telemetry/latency?skill_id=graham_analysis")
    assert resp.status_code == 200
    data = resp.json()
    assert data.get("skill_id") == "graham_analysis"


async def test_telemetry_sans_auth_200(client) -> None:
    """/telemetry/* est accessible sans Bearer token (EXEMPT_PREFIXES)."""
    # On s'assure qu'il n'y a pas de header d'auth dans cette requête
    resp = await client.get(
        "/telemetry/summary", headers={"Authorization": ""}
    )
    # L'endpoint ne doit pas retourner 401 (même si les données sont vides)
    assert resp.status_code != 401


async def test_telemetry_hit_ratio_entre_0_et_1(telemetry_client) -> None:
    """0.0 <= hit_ratio <= 1.0."""
    resp = await telemetry_client.get("/telemetry/cache")
    assert resp.status_code == 200
    data = resp.json()
    assert 0.0 <= data["hit_ratio"] <= 1.0


async def test_telemetry_cost_total_non_negatif(telemetry_client) -> None:
    """cost_total_usd >= 0.0."""
    resp = await telemetry_client.get("/telemetry/summary")
    assert resp.status_code == 200
    data = resp.json()
    assert data["cost_total_usd"] >= 0.0
