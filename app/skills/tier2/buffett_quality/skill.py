from __future__ import annotations

import json
import logging
import re
import time
from pathlib import Path
from typing import Any, ClassVar

import anthropic

from app.rag.service import RagService
from app.skills.base import Citation, SkillBase, SkillConfig, UsageDetail
from app.utils.costs import calculate_cost
from app.utils.retry import call_claude_with_retry
from .schemas import BuffettQualityInput, BuffettQualityOutput

logger = logging.getLogger(__name__)


def _parse_claude_json(text: str) -> dict[str, Any]:
    """Parse le JSON depuis la réponse Claude, gère les blocs markdown optionnels."""
    text = text.strip()
    match = re.search(r"```(?:json)?\s*\n?(.*?)\n?```", text, re.DOTALL)
    if match:
        text = match.group(1).strip()
    return json.loads(text)


class BuffettQualitySkill(SkillBase):
    """
    Skill Tier 2 : application des 4 filtres Buffett et calcul des owner earnings.
    Filtres : business compréhensible, economics favorables durables, management fiable,
    prix attractif. Verdict COMPOUNDER / QUALITE_CORRECTE / REJETER.
    """

    skill_id: ClassVar[str] = "buffett_quality"
    tier: ClassVar[int] = 2
    description: ClassVar[str] = (
        "Applique les 4 filtres de Warren Buffett — business compréhensible, "
        "economics favorables durables, management honnête et compétent, prix attractif. "
        "Calcule les owner earnings. Verdict COMPOUNDER / QUALITE_CORRECTE / REJETER."
    )

    def __init__(
        self,
        client: anthropic.AsyncAnthropic,
        model: str,
        config: SkillConfig | None = None,
        rag_service: RagService | None = None,
        top_k: int = 5,
    ) -> None:
        self._client = client
        self._model = model
        self._config = config or SkillConfig()
        self._rag = rag_service
        self._top_k = top_k
        self._system_prompt_text = self._load_system_prompt()

    def _load_system_prompt(self) -> str:
        """Charge le contenu de prompts/system.md."""
        path = Path(__file__).parent / "prompts" / "system.md"
        return path.read_text(encoding="utf-8")

    def get_system_prompt(self) -> list[dict[str, Any]]:
        """Format liste avec cache_control pour activer le prompt caching (section 8.2)."""
        return [
            {
                "type": "text",
                "text": self._system_prompt_text,
                "cache_control": {"type": "ephemeral"},
            }
        ]

    async def get_citations(self, query: str, k: int = 5) -> list[Citation]:
        """
        Recherche RAG dans Qdrant pour les passages pertinents sur le quality investing Buffett.
        Retourne [] si le RAG n'est pas initialisé.
        """
        if self._rag is None:
            return []
        return await self._rag.search(query, k=k)

    def _build_user_message(
        self,
        input_data: BuffettQualityInput,
        citations: list[Citation],
    ) -> str:
        """
        Construit le message utilisateur.
        Si dorsey_context fourni, l'inclure en tête avant les ratios.
        """
        parts: list[str] = []

        if input_data.dorsey_context is not None:
            ctx = input_data.dorsey_context
            sources_str = ", ".join(ctx.sources) if ctx.sources else "aucune"
            parts.append(
                f"## Contexte dorsey_moat\n"
                f"Moat type : {ctx.moat_type}, Durabilité ROIC : {ctx.roic_durability}\n"
                f"Sources présentes (FORTE/MODÉRÉE) : {sources_str}\n"
            )

        if citations:
            parts.append("## Contexte de référence (corpus Buffett quality investing)\n")
            for i, cit in enumerate(citations, 1):
                parts.append(
                    f"**[{i}] {cit.source}** (score : {cit.score:.2f})\n{cit.extrait}\n"
                )
            parts.append("---\n")

        ratios_json = input_data.ratios.model_dump_json(indent=2)
        parts.append(
            f"Applique les 4 filtres Buffett à **{input_data.ticker}** "
            f"(business compréhensible, economics favorables, management fiable, prix attractif) "
            f"et calcule les owner earnings :\n\n"
            f"```json\n{ratios_json}\n```\n\n"
            "Retourne uniquement le JSON structuré conforme au format de sortie défini."
        )

        return "\n".join(parts)

    async def execute(
        self, input_data: BuffettQualityInput
    ) -> tuple[BuffettQualityOutput, UsageDetail]:
        """
        Appelle l'API Claude avec le system prompt caché et les données financières.
        Injecte les citations RAG et le contexte dorsey dans le message utilisateur.
        """
        rag_query = (
            f"Buffett quality investing {input_data.ticker} "
            f"owner earnings ROIC wonderful business four filters "
            f"favorable economics management price fair value compounder"
        )
        citations = await self.get_citations(rag_query, k=self._top_k)

        user_message = self._build_user_message(input_data, citations)

        t0 = time.perf_counter()
        response = await call_claude_with_retry(
            self._client,
            timeout_s=self._config.timeout_s,
            max_retries=self._config.max_retries,
            model=self._model,
            system=self.get_system_prompt(),
            messages=[{"role": "user", "content": user_message}],
            max_tokens=4096,
        )
        latency_ms = int((time.perf_counter() - t0) * 1000)

        raw_text = response.content[0].text
        data = _parse_claude_json(raw_text)
        cost_usd = calculate_cost(response.usage, self._model)

        # confidence_score = fraction des champs BuffettRatios non-None (complétude des données)
        _ratios_fields = list(input_data.ratios.model_fields.keys())
        _non_null = sum(1 for f in _ratios_fields if getattr(input_data.ratios, f) is not None)
        data["confidence_score"] = round(_non_null / len(_ratios_fields), 2) if _ratios_fields else 0.0

        tokens_input = response.usage.input_tokens
        tokens_output = response.usage.output_tokens
        tokens_cache_r = getattr(response.usage, "cache_read_input_tokens", 0)
        tokens_cache_c = getattr(response.usage, "cache_creation_input_tokens", 0)
        total_consumed = tokens_input + tokens_cache_r + tokens_cache_c
        cache_hit_ratio = round(tokens_cache_r / total_consumed, 4) if total_consumed else 0.0

        logger.info(
            "execute terminé",
            extra={
                "skill_id": self.skill_id,
                "ticker": input_data.ticker,
                "latency_ms": latency_ms,
                "cost_usd": round(cost_usd, 6),
                "cache_hit_ratio": cache_hit_ratio,
                "tokens_input": tokens_input,
                "tokens_output": tokens_output,
                "tokens_cache_read": tokens_cache_r,
                "tokens_cache_creation": tokens_cache_c,
                "model": self._model,
            },
        )

        usage_detail = UsageDetail(
            tokens_input=tokens_input,
            tokens_output=tokens_output,
            tokens_cache_read=tokens_cache_r,
            tokens_cache_creation=tokens_cache_c,
            cost_usd=cost_usd,
            model=self._model,
        )

        output = BuffettQualityOutput.model_validate(data)
        output.citations = citations
        output.cost_usd = cost_usd

        if self._config.tracer is not None:
            self._config.tracer.record_generation(
                skill_id=self.skill_id,
                ticker=input_data.ticker,
                model=self._model,
                input_data=input_data.model_dump_json(),
                output_data=output.model_dump_json(),
                usage_detail=usage_detail,
                latency_ms=latency_ms,
            )

        return output, usage_detail
