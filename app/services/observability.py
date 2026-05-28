from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from typing import Any

import redis.asyncio as aioredis
from pydantic import BaseModel

logger = logging.getLogger(__name__)

# Import Langfuse optionnel — ne plante pas si le package est absent ou non configuré
try:
    from langfuse import Langfuse as _LangfuseClass  # type: ignore[import]

    _LANGFUSE_AVAILABLE = True
except ImportError:
    _LangfuseClass = None  # type: ignore[assignment, misc]
    _LANGFUSE_AVAILABLE = False


@dataclass
class SkillTrace:
    skill_id: str
    ticker: str
    cost_usd: float
    latency_ms: int
    cache_hit: bool
    tokens_input: int
    tokens_output: int
    created_at: datetime


class DailyCost(BaseModel):
    date: str  # "YYYY-MM-DD"
    cost_usd: float


class CostSummary(BaseModel):
    cost_total_usd: float
    cost_par_jour: list[DailyCost]  # triés chronologiquement
    analyses_count: int


class CacheStats(BaseModel):
    hits: int
    misses: int
    hit_ratio: float  # 0.0 si hits + misses == 0
    keys_count: int  # KEYS "analysis:*" filtré


class LatencyStats(BaseModel):
    skill_id: str | None  # None = tous les skills agrégés
    p50_ms: float | None
    p95_ms: float | None
    p99_ms: float | None
    sample_count: int


class ObservabilityService:
    """
    Enregistre les métriques d'exécution des skills (coût, latence, cache hit/miss).
    Fonctionne en mode Redis-only si Langfuse non configuré.
    """

    def __init__(
        self,
        redis_client: aioredis.Redis,
        langfuse_client: Any | None = None,
        daily_threshold_usd: float = 1.0,
    ) -> None:
        self._redis = redis_client
        self._langfuse = langfuse_client
        self._threshold = daily_threshold_usd

    async def record_skill_execution(self, trace: SkillTrace) -> None:
        """
        Enregistre une trace d'exécution de skill dans Redis (et Langfuse si disponible).
        Doit être appelé via asyncio.create_task() — ne jamais awaiter dans le chemin critique.
        """
        try:
            # 1. Span Langfuse si disponible
            if self._langfuse is not None:
                try:
                    if hasattr(self._langfuse, "trace"):
                        self._langfuse.trace(
                            name=f"skill:{trace.skill_id}",
                            metadata={
                                "ticker": trace.ticker,
                                "cost_usd": trace.cost_usd,
                                "latency_ms": trace.latency_ms,
                                "cache_hit": trace.cache_hit,
                                "tokens_input": trace.tokens_input,
                                "tokens_output": trace.tokens_output,
                            },
                        )
                except Exception:
                    logger.debug(
                        "Erreur Langfuse ignorée pour skill %s", trace.skill_id
                    )

            # 2. Coût journalier INCRBYFLOAT obs:cost:{YYYY-MM-DD}
            date_str = trace.created_at.strftime("%Y-%m-%d")
            await self._redis.incrbyfloat(f"obs:cost:{date_str}", trace.cost_usd)

            # 3. Compteurs cache hits/misses
            if trace.cache_hit:
                await self._redis.incr("obs:cache:hits")
            else:
                await self._redis.incr("obs:cache:misses")

            # 4. Latences sorted set — score=timestamp_unix, member=latency:uuid (unicité garantie)
            timestamp_unix = int(trace.created_at.timestamp())
            member = f"{trace.latency_ms}:{uuid.uuid4().hex[:12]}"
            await self._redis.zadd(
                f"skill_traces:{trace.skill_id}",
                {member: timestamp_unix},
            )
            # Garder 1000 dernières entrées
            await self._redis.zremrangebyrank(
                f"skill_traces:{trace.skill_id}", 0, -1001
            )

            # 5. Compteur global analyses
            await self._redis.incr("obs:analyses:total")

            # 6. Alerte coût journalier si seuil dépassé
            daily_cost_str = await self._redis.get(f"obs:cost:{date_str}")
            daily_cost = float(daily_cost_str) if daily_cost_str else 0.0
            if daily_cost > self._threshold:
                await self._redis.set(f"obs:alert:{date_str}", "1", ex=86400)
                logger.warning(
                    "Seuil coût journalier dépassé : %.4f USD > %.2f USD seuil",
                    daily_cost,
                    self._threshold,
                )

        except Exception:
            logger.exception(
                "Erreur lors de l'enregistrement de la trace pour %s/%s",
                trace.skill_id,
                trace.ticker,
            )

    async def get_cost_summary(self, days: int = 30) -> CostSummary:
        """Lit obs:cost:{date} pour les N derniers jours — somme + liste par jour."""
        today = date.today()
        dates = [today - timedelta(days=i) for i in range(days - 1, -1, -1)]

        cost_par_jour: list[DailyCost] = []
        total = 0.0

        for d in dates:
            date_str = d.strftime("%Y-%m-%d")
            val = await self._redis.get(f"obs:cost:{date_str}")
            cost = round(float(val), 6) if val else 0.0
            cost_par_jour.append(DailyCost(date=date_str, cost_usd=cost))
            total += cost

        analyses_raw = await self._redis.get("obs:analyses:total")
        analyses_count = int(analyses_raw) if analyses_raw else 0

        return CostSummary(
            cost_total_usd=round(total, 6),
            cost_par_jour=cost_par_jour,
            analyses_count=analyses_count,
        )

    async def get_cache_stats(self) -> CacheStats:
        """Retourne hits, misses, hit_ratio et nombre de clés analysis:*."""
        hits_raw = await self._redis.get("obs:cache:hits")
        misses_raw = await self._redis.get("obs:cache:misses")

        hits = int(hits_raw) if hits_raw else 0
        misses = int(misses_raw) if misses_raw else 0
        total = hits + misses
        hit_ratio = hits / total if total > 0 else 0.0

        keys = await self._redis.keys("analysis:*")
        keys_count = len(keys) if keys else 0

        return CacheStats(
            hits=hits,
            misses=misses,
            hit_ratio=round(hit_ratio, 4),
            keys_count=keys_count,
        )

    async def get_latency_p95(self, skill_id: str | None = None) -> LatencyStats:
        """
        Calcule p50/p95/p99 depuis le sorted set Redis.
        Si skill_id=None, agrège tous les skills.
        """
        # zrange (stub redis) renvoie une union de types de listes — annoter évite
        # que mypy infère list[Never] sur la branche else et rejette .extend()
        raw_members: list[Any]
        if skill_id is not None:
            raw_members = await self._redis.zrange(
                f"skill_traces:{skill_id}", 0, -1
            )
        else:
            all_keys = await self._redis.keys("skill_traces:*")
            raw_members = []
            for key in all_keys:
                members = await self._redis.zrange(key, 0, -1)
                raw_members.extend(members)

        if not raw_members:
            return LatencyStats(
                skill_id=skill_id,
                p50_ms=None,
                p95_ms=None,
                p99_ms=None,
                sample_count=0,
            )

        latencies: list[float] = []
        for member in raw_members:
            try:
                lat = float(str(member).split(":")[0])
                latencies.append(lat)
            except (ValueError, AttributeError, IndexError):
                pass

        if not latencies:
            return LatencyStats(
                skill_id=skill_id,
                p50_ms=None,
                p95_ms=None,
                p99_ms=None,
                sample_count=0,
            )

        latencies.sort()
        n = len(latencies)

        def _percentile(p: float) -> float:
            idx = min(int(p / 100.0 * n), n - 1)
            return latencies[idx]

        return LatencyStats(
            skill_id=skill_id,
            p50_ms=round(_percentile(50), 1),
            p95_ms=round(_percentile(95), 1),
            p99_ms=round(_percentile(99), 1),
            sample_count=n,
        )

    async def check_cost_alert(self) -> bool:
        """Retourne True si obs:alert:{today} existe dans Redis."""
        today_str = date.today().strftime("%Y-%m-%d")
        val = await self._redis.get(f"obs:alert:{today_str}")
        return val is not None
