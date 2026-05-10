from __future__ import annotations

import logging

from app.skills.base import UsageDetail

logger = logging.getLogger(__name__)


class LangfuseTracer:
    """
    Wrapper autour du SDK Langfuse pour tracer les appels Claude.
    Instancié uniquement si LANGFUSE_SECRET_KEY est présente.
    Toutes les méthodes sont synchrones — le SDK Langfuse bufferise en arrière-plan.
    """

    def __init__(self, secret_key: str, public_key: str, host: str) -> None:
        from langfuse import Langfuse  # import paresseux — optionnel
        self._lf = Langfuse(
            secret_key=secret_key,
            public_key=public_key,
            host=host,
        )
        logger.info("LangfuseTracer initialisé (host=%s)", host)

    def record_generation(
        self,
        *,
        skill_id: str,
        ticker: str,
        model: str,
        input_data: str,
        output_data: str,
        usage_detail: UsageDetail,
        latency_ms: int,
    ) -> None:
        """Enregistre une génération Claude dans Langfuse."""
        total_consumed = (
            usage_detail.tokens_input
            + usage_detail.tokens_cache_read
            + usage_detail.tokens_cache_creation
        )
        cache_hit_ratio = (
            round(usage_detail.tokens_cache_read / total_consumed, 4)
            if total_consumed > 0
            else 0.0
        )

        try:
            trace = self._lf.trace(
                name=f"{skill_id}/{ticker}",
                metadata={"ticker": ticker, "skill_id": skill_id},
            )
            trace.generation(
                name=skill_id,
                model=model,
                input=input_data,
                output=output_data,
                usage={
                    "input": usage_detail.tokens_input,
                    "output": usage_detail.tokens_output,
                    "total": usage_detail.tokens_input + usage_detail.tokens_output,
                    "unit": "TOKENS",
                },
                metadata={
                    "cost_usd": usage_detail.cost_usd,
                    "tokens_cache_read": usage_detail.tokens_cache_read,
                    "tokens_cache_creation": usage_detail.tokens_cache_creation,
                    "cache_hit_ratio": cache_hit_ratio,
                    "latency_ms": latency_ms,
                },
            )
        except Exception:
            logger.exception("Erreur Langfuse — trace ignorée pour %s/%s", skill_id, ticker)

    def shutdown(self) -> None:
        """Flush les traces en attente avant l'arrêt du service."""
        try:
            self._lf.flush()
        except Exception:
            logger.exception("Erreur lors du flush Langfuse")
