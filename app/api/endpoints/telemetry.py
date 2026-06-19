from __future__ import annotations

import os
from datetime import datetime

from fastapi import APIRouter, Depends, Query, Request
from pydantic import BaseModel

from app.services.eval_drift_service import SUPPORTED_DATASETS, EvalDriftResult, EvalDriftService
from app.services.observability import (
    CacheStats,
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


def get_eval_drift_service(request: Request) -> EvalDriftService | None:
    return getattr(request.app.state, "eval_drift_service", None)


@router.get(
    "/eval-drift",
    summary="Résultats de drift detection par golden dataset",
)
async def get_eval_drift(
    request: Request,
    dataset: str | None = Query(default=None, description="Nom du dataset (graham/earnings/dorsey/buffett/damodaran). Omis = tous."),
) -> EvalDriftResult | list[EvalDriftResult] | None:
    """
    Lecture seule — retourne le dernier résultat de drift detection depuis Redis.
    Ne déclenche pas d'exécution. Pour déclencher, utiliser la tâche Celery run_eval_drift_check.
    """
    svc: EvalDriftService | None = get_eval_drift_service(request)
    if svc is None:
        from fastapi import HTTPException
        raise HTTPException(status_code=503, detail="EvalDriftService non disponible")

    if dataset is not None:
        if dataset not in SUPPORTED_DATASETS:
            from fastapi import HTTPException
            raise HTTPException(
                status_code=400,
                detail=f"Dataset {dataset!r} invalide. Valides: {sorted(SUPPORTED_DATASETS)}",
            )
        return await svc.get_last_result(dataset)

    results: list[EvalDriftResult] = []
    for ds in sorted(SUPPORTED_DATASETS):
        result = await svc.get_last_result(ds)
        if result is not None:
            results.append(result)
    return results


class WebhookStatus(BaseModel):
    url_configuree: bool
    derniere_notification: datetime | None
    nb_erreurs: int


@router.get(
    "/webhook",
    summary="Statut du service webhook",
)
async def get_webhook_status(request: Request) -> WebhookStatus:
    """URL configurée, dernière notification envoyée et nb d'erreurs depuis le démarrage."""
    webhook_service = getattr(request.app.state, "webhook_service", None)
    if webhook_service is None:
        return WebhookStatus(
            url_configuree=bool(os.environ.get("WEBHOOK_URL")),
            derniere_notification=None,
            nb_erreurs=0,
        )
    return WebhookStatus(
        url_configuree=webhook_service.url_configuree,
        derniere_notification=webhook_service.derniere_notification,
        nb_erreurs=webhook_service.nb_erreurs,
    )
