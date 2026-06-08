from __future__ import annotations

import json
import logging
import uuid

import redis.asyncio as aioredis
from fastapi import APIRouter, HTTPException, Request

from app.db.tenant_context import get_current_tenant
from app.orchestrator.core import AnalyzeRequest
from app.workers.tasks import run_full_analysis

logger = logging.getLogger(__name__)

router = APIRouter()

_JOB_TTL = 86400  # 24 heures


@router.post("/analyze-async", summary="Soumet une analyse asynchrone — retourne un job_id immédiatement")
async def analyze_async(body: AnalyzeRequest, request: Request) -> dict:
    """Lance le workflow company_analysis en arrière-plan via Celery."""
    job_id = str(uuid.uuid4())
    r: aioredis.Redis = request.app.state.redis_pool
    request_dict = body.model_dump(mode="json")

    await r.set(f"job:{job_id}:status", "pending", ex=_JOB_TTL)

    # Tenant capturé au site `.delay()` : le ContextVar ne traverse pas le broker Celery (E5-S7).
    run_full_analysis.delay(job_id, request_dict, str(get_current_tenant()))
    logger.info("Job %s soumis pour ticker %s", job_id, body.ticker)

    return {"job_id": job_id}


@router.get("/jobs/{job_id}", summary="Statut et résultat d'un job async")
async def get_job(job_id: str, request: Request) -> dict:
    """Retourne le statut du job : pending | running | done | failed."""
    r: aioredis.Redis = request.app.state.redis_pool

    status = await r.get(f"job:{job_id}:status")
    if status is None:
        raise HTTPException(status_code=404, detail=f"Job {job_id} introuvable")

    result_raw = await r.get(f"job:{job_id}:result")
    error = await r.get(f"job:{job_id}:error")

    return {
        "status": status,
        "result": json.loads(result_raw) if result_raw else None,
        "error": error,
    }
