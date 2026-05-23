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

from .schemas import EsgInput, EsgOutput

logger = logging.getLogger(__name__)

_ESG_TOOL_SCHEMA = build_tool_schema(
    EsgOutput,
    exclude={"citations", "cost_usd"},
)


class EsgSimplifiedSkill(SkillBase):
    """
    Skill Tier 2 : notation ESG simplifiée par proxy financier.
    Évalue 15 critères (5E + 5S + 5G) sans fournisseur ESG externe.
    """

    skill_id: ClassVar[str] = "esg_simplified"
    tier: ClassVar[int] = 2
    description: ClassVar[str] = (
        "Évalue 15 critères ESG (Environnement, Social, Gouvernance) "
        "via des proxies financiers disponibles — sans accès à des bases ESG externes."
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
        path = Path(__file__).parent / "prompts" / "system.md"
        return path.read_text(encoding="utf-8")

    def get_system_prompt(self) -> list[dict[str, Any]]:
        return [
            {
                "type": "text",
                "text": self._system_prompt_text,
                "cache_control": {"type": "ephemeral"},
            }
        ]

    async def get_citations(self, query: str, k: int = 5) -> list[Citation]:
        if self._rag is None:
            return []
        return await self._rag.search(query, k=k)

    def _build_user_message(
        self, input_data: EsgInput, citations: list[Citation]
    ) -> str:
        parts: list[str] = []

        if citations:
            parts.append("## Contexte de référence (corpus ESG)\n")
            for i, cit in enumerate(citations, 1):
                parts.append(
                    f"**[{i}] {cit.source}** (score : {cit.score:.2f})\n{cit.extrait}\n"
                )
            parts.append("---\n")

        data_lines = [f"- **Ticker** : {input_data.ticker}"]
        if input_data.sector is not None:
            data_lines.append(f"- **Secteur** : {input_data.sector}")
        else:
            data_lines.append("- **Secteur** : Non fourni")
        if input_data.revenue_bn is not None:
            data_lines.append(f"- **Revenus** : {input_data.revenue_bn:.2f} Md$")
        if input_data.roe is not None:
            data_lines.append(f"- **ROE** : {input_data.roe:.2%}")
        if input_data.debt_equity is not None:
            data_lines.append(f"- **Dette/Fonds propres** : {input_data.debt_equity:.2f}x")
        if input_data.dividend_years is not None:
            data_lines.append(f"- **Années de dividendes consécutifs** : {input_data.dividend_years}")
        if input_data.eps_growth_10y is not None:
            data_lines.append(f"- **Croissance BPA 10 ans** : {input_data.eps_growth_10y:.1%}")

        parts.append(
            f"Évalue les critères ESG de **{input_data.ticker}** à partir de ces données proxy :\n\n"
            + "\n".join(data_lines)
            + "\n\nApplique les 15 critères ESG (5E + 5S + 5G) selon le cadre du system prompt. "
            "Retourne l'analyse structurée via l'outil `esg_output`."
        )

        return "\n".join(parts)

    async def execute(
        self, input_data: EsgInput
    ) -> tuple[EsgOutput, UsageDetail]:
        """
        Appelle l'API Claude avec Tool Use — le modèle évalue les 15 critères ESG
        et retourne un EsgOutput structuré et validé par Pydantic.
        """
        rag_query = (
            f"ESG criteria proxy financial {input_data.ticker} "
            f"sector {input_data.sector or 'unknown'} "
            f"ROE debt governance environment social"
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
            tools=[{"name": "esg_output", "input_schema": _ESG_TOOL_SCHEMA}],
            tool_choice={"type": "tool", "name": "esg_output"},
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

        esg_output = EsgOutput.model_validate(data)
        esg_output.citations = citations

        if self._config.tracer is not None:
            self._config.tracer.record_generation(
                skill_id=self.skill_id,
                ticker=input_data.ticker,
                model=self._model,
                input_data=input_data.model_dump_json(),
                output_data=esg_output.model_dump_json(),
                usage_detail=usage_detail,
                latency_ms=latency_ms,
            )

        return esg_output, usage_detail
