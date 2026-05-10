from __future__ import annotations

from fastapi import APIRouter, Depends, Query, Request
from pydantic import BaseModel

from app.services.observability import (
    CacheStats,
    CostSummary,
    DailyCost,
    LatencyStats,
    ObservabilityService,
)

router = APIRouter(prefix="/telemetry", tags=["telemetry"])


def get_observability(request: Request) -> ObservabilityService:
    return request.app.state.observability


class TelemetrySummary(BaseModel):
    cost_total_usd: float
    analyses_count: int
    cache_hit_ratio: float  # 0.0–1.0
    latency_p95_ms: float | None
    alerte_cout_active: bool  # True si seuil journalier dépassé


@router.get(
    "/summary",
    summary="Résumé des métriques d'observabilité",
)
async def get_summary(
    days: int = Query(default=30, ge=1, le=365),
    obs: ObservabilityService = Depends(get_observability),
) -> TelemetrySummary:
    """Coût total, cache hit ratio, latence p95 et alerte coût sur la période."""
    cost_summary = await obs.get_cost_summary(days=days)
    cache_stats = await obs.get_cache_stats()
    latency_stats = await obs.get_latency_p95(skill_id=None)
    alerte = await obs.check_cost_alert()

    return TelemetrySummary(
        cost_total_usd=cost_summary.cost_total_usd,
        analyses_count=cost_summary.analyses_count,
        cache_hit_ratio=cache_stats.hit_ratio,
        latency_p95_ms=latency_stats.p95_ms,
        alerte_cout_active=alerte,
    )


@router.get(
    "/costs",
    summary="Coûts journaliers sur la période",
)
async def get_costs(
    days: int = Query(default=30, ge=1, le=365),
    obs: ObservabilityService = Depends(get_observability),
) -> list[DailyCost]:
    """Liste des coûts journaliers triés chronologiquement."""
    summary = await obs.get_cost_summary(days=days)
    return summary.cost_par_jour


@router.get(
    "/cache",
    summary="Statistiques du cache Redis d'analyses",
)
async def get_cache(
    obs: ObservabilityService = Depends(get_observability),
) -> CacheStats:
    """Hits, misses, hit_ratio et nombre de clés analysis:* en cache."""
    return await obs.get_cache_stats()


@router.get(
    "/latency",
    summary="Statistiques de latence par skill (ou tous les skills agrégés)",
)
async def get_latency(
    skill_id: str | None = Query(default=None),
    obs: ObservabilityService = Depends(get_observability),
) -> LatencyStats:
    """P50/P95/P99 depuis les sorted sets Redis skill_traces:{skill_id}."""
    return await obs.get_latency_p95(skill_id=skill_id)
