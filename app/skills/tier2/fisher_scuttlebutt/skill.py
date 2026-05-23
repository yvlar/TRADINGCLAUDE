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

from .schemas import FisherInput, FisherOutput

logger = logging.getLogger(__name__)

# Schéma dérivé de Pydantic — champs post-assignés exclus.
_FISHER_TOOL_SCHEMA = build_tool_schema(
    FisherOutput,
    exclude={"citations", "cost_usd"},
)


class FisherScuttlebuttSkill(SkillBase):
    """
    Skill Tier 2 : évaluation des 15 points Fisher + qualité de la direction.
    Applique Common Stocks and Uncommon Profits (Fisher, 1958).
    Verdict ACHAT_FORT / ACHAT / CONSERVER / EVITER selon le score et l'intégrité.
    """

    skill_id: ClassVar[str] = "fisher_scuttlebutt"
    tier: ClassVar[int] = 2
    description: ClassVar[str] = (
        "Applique les 15 points de Phil Fisher (Common Stocks and Uncommon Profits, 1958) "
        "et la méthode scuttlebutt pour évaluer la qualité de la direction et la culture. "
        "Verdict ACHAT_FORT / ACHAT / CONSERVER / EVITER. "
        "Points 14 (transparence) et 15 (intégrité) sont éliminatoires."
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
        input_data: FisherInput,
        citations: list[Citation],
    ) -> str:
        """Construit le message utilisateur avec les 15 réponses Fisher et le contexte qualitatif."""
        parts: list[str] = []

        parts.append(f"## Analyse Fisher — {input_data.ticker}\n")

        parts.append("### Évaluations des 15 points\n")
        for ans in input_data.fisher_answers:
            parts.append(
                f"- **Point {ans.point}** : score {ans.score}/2 — {ans.commentaire}"
            )

        if input_data.contexte_qualitatif:
            parts.append(f"\n### Contexte qualitatif (scuttlebutt)\n{input_data.contexte_qualitatif}\n")

        if citations:
            parts.append("\n### Contexte de référence (corpus Fisher scuttlebutt)\n")
            for i, cit in enumerate(citations, 1):
                parts.append(f"**[{i}] {cit.source}** (score : {cit.score:.2f})\n{cit.extrait}\n")
            parts.append("---\n")

        answers_json = input_data.model_dump_json(indent=2)
        parts.append(
            f"\nÉvalue les 15 points Fisher pour **{input_data.ticker}**, calcule le score total, "
            f"qualifie la direction et émet un verdict.\n\n"
            f"Données complètes :\n```json\n{answers_json}\n```\n\n"
            "Retourne l'analyse structurée via l'outil fisher_output. "
            "IMPÉRATIF : points_evalues doit contenir exactement 15 éléments."
        )

        return "\n".join(parts)

    async def execute(
        self, input_data: FisherInput
    ) -> tuple[FisherOutput, UsageDetail]:
        """
        Appelle l'API Claude avec Tool Use — le modèle popule fisher_output directement,
        éliminant les hallucinations de format JSON texte.
        """
        rag_query = (
            f"Fisher scuttlebutt {input_data.ticker} "
            f"15 points direction management qualité culture intégrité "
            f"Common Stocks Uncommon Profits"
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
            tools=[{"name": "fisher_output", "input_schema": _FISHER_TOOL_SCHEMA}],
            tool_choice={"type": "tool", "name": "fisher_output"},
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

        output = FisherOutput.model_validate(data)
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
