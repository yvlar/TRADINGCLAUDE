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

from .schemas import MarksInput, MarksOutput

logger = logging.getLogger(__name__)

# Schéma dérivé de Pydantic — champs post-assignés exclus.
_MARKS_TOOL_SCHEMA = build_tool_schema(
    MarksOutput,
    exclude={"citations", "cost_usd"},
)


class MarksCyclesSkill(SkillBase):
    """
    Skill Tier 2 : cadre Howard Marks — cycles et risque.
    Positionne le pendule du sentiment de marché,
    applique le second-level thinking, et recommande un timing d'allocation.
    Note : MarksOutput n'a pas de ticker — analyse du marché, pas d'un titre spécifique.
    """

    skill_id: ClassVar[str] = "marks_cycles_risk"
    tier: ClassVar[int] = 2
    description: ClassVar[str] = (
        "Applique le cadre de Howard Marks (Oaktree Capital) — pendule du sentiment de marché, "
        "second-level thinking, risque comme perte permanente. "
        "Verdict PESSIMISME_EXCESSIF / PESSIMISME / NEUTRE / OPTIMISME / EUPHORIE."
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
        """Recherche RAG dans Qdrant. Retourne [] si le RAG n'est pas initialisé."""
        if self._rag is None:
            return []
        return await self._rag.search(query, k=k)

    def _build_user_message(
        self,
        input_data: MarksInput,
        citations: list[Citation],
    ) -> str:
        """Construit le message utilisateur avec le contexte marché et les indicateurs."""
        parts: list[str] = []
        r = input_data.marks_ratios

        parts.append(
            f"## Contexte de marché\n{input_data.market_context}\n\n"
            f"### Indicateurs quantitatifs\n"
            f"- P/E marché : {r.pe_market if r.pe_market is not None else 'Non fourni'}\n"
            f"- VIX (indice de volatilité) : {r.vix if r.vix is not None else 'Non fourni'}\n"
        )

        if r.credit_spreads_bps is not None:
            parts.append(f"- Credit spreads : {r.credit_spreads_bps} bps\n")
        else:
            parts.append("- Credit spreads : Non fournis\n")

        if r.insider_net_buying is not None:
            parts.append(f"- Achats nets d'insiders : {r.insider_net_buying}\n")
        else:
            parts.append("- Achats nets d'insiders : Non fournis\n")

        if r.bullish_sentiment_pct is not None:
            parts.append(f"- Sentiment haussier (AAII/surveys) : {r.bullish_sentiment_pct * 100:.1f} %\n")
        else:
            parts.append("- Sentiment haussier : Non fourni\n")

        if citations:
            parts.append("\n## Contexte de référence (corpus Marks)\n")
            for i, cit in enumerate(citations, 1):
                parts.append(f"**[{i}] {cit.source}** (score : {cit.score:.2f})\n{cit.extrait}\n")
            parts.append("---\n")

        ratios_json = input_data.marks_ratios.model_dump_json(indent=2)
        parts.append(
            f"\nApplique le cadre Howard Marks sur ce contexte de marché. "
            f"Positionne le pendule, génère un insight second-level, et recommande un timing d'allocation.\n\n"
            f"Indicateurs complets :\n```json\n{ratios_json}\n```\n\n"
            "Retourne l'analyse structurée via l'outil marks_output."
        )

        return "\n".join(parts)

    async def execute(
        self, input_data: MarksInput
    ) -> tuple[MarksOutput, UsageDetail]:
        """
        Appelle l'API Claude avec Tool Use — le modèle popule marks_output directement,
        éliminant les hallucinations de format JSON texte.
        """
        rag_query = (
            "Marks cycles risk pendule sentiment second-level thinking "
            "euphorie pessimisme contrarian allocation tactique"
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
            tools=[{"name": "marks_output", "input_schema": _MARKS_TOOL_SCHEMA}],
            tool_choice={"type": "tool", "name": "marks_output"},
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

        output = MarksOutput.model_validate(data)
        output.citations = citations
        output.cost_usd = cost_usd

        if self._config.tracer is not None:
            self._config.tracer.record_generation(
                skill_id=self.skill_id,
                ticker="MARKET",
                model=self._model,
                input_data=input_data.model_dump_json(),
                output_data=output.model_dump_json(),
                usage_detail=usage_detail,
                latency_ms=latency_ms,
            )

        return output, usage_detail
