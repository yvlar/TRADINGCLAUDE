from __future__ import annotations

import logging
import time
from pathlib import Path
from typing import Any, ClassVar

import anthropic

from app.rag.service import RagService
from app.skills.base import Citation, SkillBase, SkillConfig, UsageDetail
from app.utils.costs import calculate_cost
from app.utils.retry import call_claude_with_retry
from app.utils.tool_schema import build_tool_schema
from .schemas import GrahamAnalysisInput, GrahamAnalysisOutput

logger = logging.getLogger(__name__)

# Schéma dérivé de Pydantic — computed_fields et champs post-assignés exclus.
_GRAHAM_TOOL_SCHEMA = build_tool_schema(
    GrahamAnalysisOutput,
    exclude={"defensive_score", "defensive_verdict", "confidence_score", "citations", "cost_usd"},
)


class GrahamAnalysisSkill(SkillBase):
    """
    Skill Tier 2 : filtrage value Graham — 8 critères défensifs + 5 entrepreneuriaux.
    Correspond au skill claude `graham-stock-screening` vectorisé dans Qdrant en Phase 1.
    """

    skill_id: ClassVar[str] = "graham_analysis"
    tier: ClassVar[int] = 2
    description: ClassVar[str] = (
        "Applique les critères quantitatifs de Graham (chapitres 14-15 de The Intelligent Investor) "
        "et calcule la valeur intrinsèque par les deux formules Graham."
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
        """
        Format liste avec cache_control pour activer le prompt caching Anthropic.
        Section 8.2 de l'architecture.
        """
        return [
            {
                "type": "text",
                "text": self._system_prompt_text,
                "cache_control": {"type": "ephemeral"},
            }
        ]

    async def get_citations(self, query: str, k: int = 5) -> list[Citation]:
        """
        Recherche RAG dans Qdrant pour les passages Graham pertinents.
        Retourne [] si le RAG n'est pas initialisé (Phase 0 / OPENAI_API_KEY absente).
        """
        if self._rag is None:
            return []
        return await self._rag.search(query, k=k)

    def _build_user_message(
        self, input_data: GrahamAnalysisInput, citations: list[Citation]
    ) -> str:
        """Construit le message utilisateur avec citations RAG et ratios."""
        parts: list[str] = []

        if citations:
            parts.append("## Contexte de référence (corpus Graham)\n")
            for i, cit in enumerate(citations, 1):
                parts.append(
                    f"**[{i}] {cit.source}** (score : {cit.score:.2f})\n{cit.extrait}\n"
                )
            parts.append("---\n")

        ratios_json = input_data.ratios.model_dump_json(indent=2)
        parts.append(
            f"Analyse les ratios financiers de **{input_data.ticker}** :\n\n"
            f"```json\n{ratios_json}\n```\n\n"
            "Applique les 8 critères défensifs et les 5 critères entrepreneuriaux de Graham. "
            "Retourne l'analyse structurée via l'outil graham_output."
        )

        return "\n".join(parts)

    async def execute(
        self, input_data: GrahamAnalysisInput
    ) -> tuple[GrahamAnalysisOutput, UsageDetail]:
        """
        Appelle l'API Claude avec Tool Use — le modèle popule graham_output directement,
        éliminant les hallucinations de format JSON texte.
        """
        rag_query = (
            f"Graham screening criteria {input_data.ticker} "
            f"PE {input_data.ratios.pe} PB {input_data.ratios.pb} "
            f"debt equity {input_data.ratios.debt_equity}"
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
            tools=[{"name": "graham_output", "input_schema": _GRAHAM_TOOL_SCHEMA}],
            tool_choice={"type": "tool", "name": "graham_output"},
        )
        latency_ms = int((time.perf_counter() - t0) * 1000)

        tool_use_block = next(
            (b for b in response.content if b.type == "tool_use"),
            None,
        )
        if tool_use_block is None:
            raise ValueError(
                f"Aucun bloc tool_use dans la réponse Claude "
                f"(stop_reason={response.stop_reason}, blocks={len(response.content)})"
            )

        data = dict(tool_use_block.input)
        data["citations"] = []

        cost_usd = calculate_cost(response.usage, self._model)

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

        graham_output = GrahamAnalysisOutput.model_validate(data)
        graham_output.citations = citations

        if self._config.tracer is not None:
            self._config.tracer.record_generation(
                skill_id=self.skill_id,
                ticker=input_data.ticker,
                model=self._model,
                input_data=input_data.model_dump_json(),
                output_data=graham_output.model_dump_json(),
                usage_detail=usage_detail,
                latency_ms=latency_ms,
            )

        return graham_output, usage_detail
