"""Endpoints dashboard evals -- Sprint 51."""
from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException, Query, Request

from app.models.evals import EvalRunRecord, EvalsSummary
from app.services.evals_dashboard import EvalsDashboardService, _SKILL_CATALOGUE

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/evals", tags=["evals"])

_VALID_SKILL_IDS = {e["skill_id"] for e in _SKILL_CATALOGUE}


@router.get(
    "/summary",
    response_model=EvalsSummary,
    summary="Resume des golden datasets evals disponibles",
)
async def evals_summary(request: Request) -> EvalsSummary:
    """Retourne les metadonnees de chaque dataset eval + derniere execution si disponible."""
    svc = EvalsDashboardService(redis_client=request.app.state.redis_pool)
    return await svc.get_summary()


@router.post(
    "/record",
    status_code=201,
    summary="Enregistre le resultat d'une execution eval dans l'historique Redis",
)
async def record_eval_run(request: Request, record: EvalRunRecord) -> dict:
    """Persiste le resultat d'une execution eval (TTL 30 jours, max 30 entrees par skill)."""
    if record.skill_id not in _VALID_SKILL_IDS:
        raise HTTPException(
            status_code=400,
            detail=f"skill_id invalide. Valeurs acceptees : {sorted(_VALID_SKILL_IDS)}",
        )

    svc = EvalsDashboardService(redis_client=request.app.state.redis_pool)
    await svc.record_run(record)
    return {"status": "recorded", "skill_id": record.skill_id}


@router.get(
    "/history",
    response_model=list[EvalRunRecord],
    summary="Historique des executions evals pour un skill (plus recent en premier)",
)
async def evals_history(
    request: Request,
    skill_id: str = Query(description=f"ID du skill. Valeurs : {sorted(_VALID_SKILL_IDS)}"),
) -> list[EvalRunRecord]:
    """Retourne les 30 dernieres executions evals pour le skill specifie."""
    if skill_id not in _VALID_SKILL_IDS:
        raise HTTPException(
            status_code=400,
            detail=f"skill_id invalide. Valeurs acceptees : {sorted(_VALID_SKILL_IDS)}",
        )

    svc = EvalsDashboardService(redis_client=request.app.state.redis_pool)
    return await svc.get_history(skill_id)
