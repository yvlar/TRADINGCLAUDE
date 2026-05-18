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
from .schemas import EarningsQualityInput, EarningsQualityOutput

logger = logging.getLogger(__name__)

# Schéma dérivé de Pydantic — computed_field confidence_score et champs post-assignés exclus.
_EARNINGS_TOOL_SCHEMA = build_tool_schema(
    EarningsQualityOutput,
    exclude={"confidence_score", "citations", "cost_usd"},
)


class EarningsQualitySkill(SkillBase):
    """
    Skill Tier 2 : détection de manipulations comptables et risque de faillite.
    Cinq cadres : M-Score (Beneish), Z-Score (Altman), F-Score (Piotroski),
    C-Score (Montier), Accruals (Sloan).
    """

    skill_id: ClassVar[str] = "earnings_quality"
    tier: ClassVar[int] = 2
    description: ClassVar[str] = (
        "Détecte les manipulations comptables et le risque de faillite via "
        "M-Score (Beneish), Z-Score (Altman), F-Score (Piotroski), "
        "C-Score (Montier) et accruals (Sloan)."
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
        Recherche RAG dans Qdrant pour les passages pertinents sur la qualité des bénéfices.
        Retourne [] si le RAG n'est pas initialisé.
        """
        if self._rag is None:
            return []
        return await self._rag.search(query, k=k)

    def _build_user_message(
        self,
        input_data: EarningsQualityInput,
        citations: list[Citation],
    ) -> str:
        """
        Construit le message utilisateur.
        Si graham_context fourni, l'inclure en tête avant les ratios.
        """
        parts: list[str] = []

        if input_data.graham_context is not None:
            ctx = input_data.graham_context
            drapeaux = ", ".join(ctx.drapeaux_rouges) if ctx.drapeaux_rouges else "aucun"
            marge = f"{ctx.marge_securite:.2%}" if ctx.marge_securite is not None else "N/A"
            parts.append(
                f"## Contexte Graham\n"
                f"Verdict : {ctx.verdict}, Score défensif : {ctx.defensive_score}/8, "
                f"Marge de sécurité : {marge}\n"
                f"Drapeaux rouges Graham : {drapeaux}\n"
            )

        if citations:
            parts.append("## Contexte de référence (corpus qualité des bénéfices)\n")
            for i, cit in enumerate(citations, 1):
                parts.append(
                    f"**[{i}] {cit.source}** (score : {cit.score:.2f})\n{cit.extrait}\n"
                )
            parts.append("---\n")

        ratios_json = input_data.ratios.model_dump_json(indent=2)
        parts.append(
            f"Analyse la qualité des bénéfices de **{input_data.ticker}** "
            f"via les cinq cadres (M-Score, Z-Score, F-Score, C-Score, Accruals) :\n\n"
            f"```json\n{ratios_json}\n```\n\n"
            "Retourne l'analyse structurée via l'outil earnings_quality_output."
        )

        return "\n".join(parts)

    async def execute(
        self, input_data: EarningsQualityInput
    ) -> tuple[EarningsQualityOutput, UsageDetail]:
        """
        Appelle l'API Claude avec Tool Use — le modèle popule earnings_quality_output
        directement, éliminant les hallucinations de format JSON texte.
        """
        rag_query = (
            f"earnings quality fraud detection {input_data.ticker} "
            f"accruals M-Score Z-Score F-Score Beneish Piotroski"
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
            tools=[{"name": "earnings_quality_output", "input_schema": _EARNINGS_TOOL_SCHEMA}],
            tool_choice={"type": "tool", "name": "earnings_quality_output"},
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

        output = EarningsQualityOutput.model_validate(data)
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
