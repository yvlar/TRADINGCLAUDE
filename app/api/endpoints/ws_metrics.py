from __future__ import annotations

import asyncio
import json
import logging
from datetime import datetime, timezone

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

logger = logging.getLogger(__name__)

router = APIRouter(tags=["websocket"])


@router.websocket("/ws/metrics")
async def ws_metrics(websocket: WebSocket) -> None:
    """
    Push les métriques Redis toutes les 5 secondes.
    Pas d'auth requise — dashboard de monitoring interne (lecture seule).
    Fermeture propre si le client se déconnecte.
    """
    await websocket.accept()
    logger.debug("WebSocket /ws/metrics connecté")
    try:
        while True:
            payload = await _build_metrics_payload(websocket.app.state)
            await websocket.send_text(json.dumps(payload))
            await asyncio.sleep(5)
    except WebSocketDisconnect:
        logger.debug("WebSocket /ws/metrics déconnecté proprement")
    except Exception:
        logger.exception("Erreur inattendue WebSocket /ws/metrics")
        try:
            await websocket.close(code=1011)
        except Exception:
            pass


async def _build_metrics_payload(state) -> dict:
    """Construit le payload depuis Redis — clés job:*, obs:cost:*, obs:cache:*."""
    redis = state.redis_pool

    # Jobs en cours / échoués depuis les clés job:*:status
    job_keys = await redis.keys("job:*:status")
    jobs_en_cours = 0
    jobs_echoues_1h = 0
    for key in job_keys or []:
        status = await redis.get(key)
        if status == "running":
            jobs_en_cours += 1
        elif status == "failed":
            jobs_echoues_1h += 1

    # Coût du jour depuis obs:cost:{YYYY-MM-DD}
    today_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    cost_str = await redis.get(f"obs:cost:{today_str}")
    cout_total_1h_usd = round(float(cost_str), 4) if cost_str else 0.0

    # Cache hit ratio depuis obs:cache:hits / obs:cache:misses
    hits_str = await redis.get("obs:cache:hits")
    misses_str = await redis.get("obs:cache:misses")
    hits = int(hits_str) if hits_str else 0
    misses = int(misses_str) if misses_str else 0
    total = hits + misses
    cache_hit_ratio = round(hits / total, 4) if total > 0 else 0.0

    # Analyses totales depuis obs:analyses:total
    analyses_str = await redis.get("obs:analyses:total")
    analyses_24h = int(analyses_str) if analyses_str else 0

    return {
        "jobs_en_cours": jobs_en_cours,
        "jobs_echoues_1h": jobs_echoues_1h,
        "cout_total_1h_usd": cout_total_1h_usd,
        "cache_hit_ratio": cache_hit_ratio,
        "analyses_24h": analyses_24h,
        "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    }
