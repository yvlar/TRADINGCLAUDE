from __future__ import annotations

import hashlib
import json
import logging

import redis.asyncio as aioredis

from app.orchestrator.core import AnalyzeResponse
from app.skills.tier2.graham_analysis.schemas import GrahamRatios

logger = logging.getLogger(__name__)


class AnalysisCacheService:
    """
    Cache Redis des analyses — clé = analysis:{ticker}:{workflow}:{ratios_hash}.
    Évite les re-analyses Claude identiques (même ticker + workflow + ratios).
    """

    def __init__(self, redis_client: aioredis.Redis, ttl_seconds: int = 86400) -> None:
        self._redis = redis_client
        self._ttl = ttl_seconds

    async def get(
        self,
        ticker: str,
        workflow: str,
        ratios: GrahamRatios,
    ) -> AnalyzeResponse | None:
        """Retourne None si absent ou expiré. Supprime les entrées corrompues."""
        key = self._cache_key(ticker, workflow, ratios)
        data = await self._redis.get(key)
        if data is None:
            return None
        try:
            return AnalyzeResponse.model_validate_json(data)
        except Exception:
            logger.warning("Entrée de cache invalide pour %s — supprimée", key)
            await self._redis.delete(key)
            return None

    async def set(
        self,
        ticker: str,
        workflow: str,
        ratios: GrahamRatios,
        response: AnalyzeResponse,
    ) -> None:
        """Sérialise via model_dump_json(), TTL configurable."""
        key = self._cache_key(ticker, workflow, ratios)
        await self._redis.set(key, response.model_dump_json(), ex=self._ttl)
        logger.debug("Analyse %s/%s mise en cache (TTL %ds)", ticker, workflow, self._ttl)

    async def invalidate(self, ticker: str) -> int:
        """Supprime toutes les entrées du ticker (KEYS + DEL). Retourne le nombre supprimé."""
        pattern = f"analysis:{ticker}:*"
        keys = await self._redis.keys(pattern)
        if not keys:
            return 0
        count = await self._redis.delete(*keys)
        logger.info(
            "Cache invalidé pour %s — %d entrée(s) supprimée(s)", ticker, count
        )
        return int(count)

    def _cache_key(self, ticker: str, workflow: str, ratios: GrahamRatios) -> str:
        # mode="json" sérialise les datetime ; exclut la traçabilité (horodatage/source) de la clé :
        # l'identité de cache porte sur les données financières, pas sur le MOMENT de récupération
        # (sinon chaque extraction change la clé et le cache ne hit jamais).
        ratios_json = json.dumps(
            ratios.model_dump(mode="json", exclude={"ratios_fetched_at", "ratios_source"}),
            sort_keys=True,
        )
        ratios_hash = hashlib.sha256(ratios_json.encode()).hexdigest()[:12]
        return f"analysis:{ticker}:{workflow}:{ratios_hash}"
