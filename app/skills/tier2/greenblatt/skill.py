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
from .schemas import GreenblattInput, GreenblattOutput

logger = logging.getLogger(__name__)

# Schéma dérivé de Pydantic — champs post-assignés exclus.
_GREENBLATT_TOOL_SCHEMA = build_tool_schema(
    GreenblattOutput,
    exclude={"citations", "cost_usd"},
)


class GreenblattSkill(SkillBase):
    """
    Skill Tier 2 : Magic Formula de Joel Greenblatt.
    Calcule ROC et Earnings Yield, classe l'action (TOP_DECILE / BON / MOYEN / EVITER),
    et identifie les situations spéciales (spinoffs, arbitrage, restructuring).
    """

    skill_id: ClassVar[str] = "greenblatt_magic_formula"
    tier: ClassVar[int] = 2
    description: ClassVar[str] = (
        "Applique la Magic Formula de Joel Greenblatt — classement combinant ROC (qualité) "
        "et Earnings Yield (bon marché). Identifie également les situations spéciales. "
        "Verdict TOP_DECILE / BON / MOYEN / EVITER."
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
        input_data: GreenblattInput,
        citations: list[Citation],
    ) -> str:
        """Construit le message utilisateur avec les ratios Greenblatt et les citations RAG."""
        parts: list[str] = []
        r = input_data.greenblatt_ratios

        roc = r.ebit / (r.net_working_capital + r.net_fixed_assets)
        earnings_yield = r.ebit / r.enterprise_value

        parts.append(
            f"## Action à analyser : {input_data.ticker}\n\n"
            f"### Ratios Magic Formula\n"
            f"- EBIT : {r.ebit} M$\n"
            f"- Enterprise Value (EV) : {r.enterprise_value} M$\n"
            f"- Net Working Capital (NWC) : {r.net_working_capital} M$\n"
            f"- Net Fixed Assets (NFA) : {r.net_fixed_assets} M$\n"
            f"- Secteur : {r.sector or 'Non spécifié'}\n\n"
            f"### Métriques pré-calculées\n"
            f"- **ROC** = EBIT / (NWC + NFA) = {r.ebit} / ({r.net_working_capital} + {r.net_fixed_assets}) = **{roc:.4f}** ({roc * 100:.2f} %)\n"
            f"- **Earnings Yield** = EBIT / EV = {r.ebit} / {r.enterprise_value} = **{earnings_yield:.4f}** ({earnings_yield * 100:.2f} %)\n"
        )

        if citations:
            parts.append("\n## Contexte de référence (corpus Greenblatt)\n")
            for i, cit in enumerate(citations, 1):
                parts.append(f"**[{i}] {cit.source}** (score : {cit.score:.2f})\n{cit.extrait}\n")
            parts.append("---\n")

        ratios_json = input_data.greenblatt_ratios.model_dump_json(indent=2)
        parts.append(
            f"\nApplique la Magic Formula de Greenblatt sur **{input_data.ticker}**. "
            f"Évalue le ROC et l'Earnings Yield, attribue un verdict et identifie les situations spéciales.\n\n"
            f"Données complètes :\n```json\n{ratios_json}\n```\n\n"
            "Retourne l'analyse structurée via l'outil greenblatt_output."
        )

        return "\n".join(parts)

    async def execute(
        self, input_data: GreenblattInput
    ) -> tuple[GreenblattOutput, UsageDetail]:
        """
        Appelle l'API Claude avec Tool Use — le modèle popule greenblatt_output directement,
        éliminant les hallucinations de format JSON texte.
        """
        rag_query = (
            f"Greenblatt magic formula {input_data.ticker} "
            f"ROC earnings yield EBIT enterprise value situations spéciales spinoffs"
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
            tools=[{"name": "greenblatt_output", "input_schema": _GREENBLATT_TOOL_SCHEMA}],
            tool_choice={"type": "tool", "name": "greenblatt_output"},
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

        output = GreenblattOutput.model_validate(data)
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
