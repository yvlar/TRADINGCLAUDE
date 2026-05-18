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
from .schemas import ThesisBuilderInput, ThesisBuilderOutput

logger = logging.getLogger(__name__)

# Schéma dérivé de Pydantic — champs post-assignés exclus.
_THESIS_TOOL_SCHEMA = build_tool_schema(
    ThesisBuilderOutput,
    exclude={"citations", "cost_usd"},
)


class ThesisBuilderSkill(SkillBase):
    """
    Skill Tier 2 : synthèse finale de tous les skills précédents en thèse d'investissement formelle.
    Produit scénarios pondérés, kill criteria, devil's advocate, position size et verdict
    ACHETER / ACCUMULER / CONSERVER / VENDRE.
    """

    skill_id: ClassVar[str] = "investment_thesis_builder"
    tier: ClassVar[int] = 2
    description: ClassVar[str] = (
        "Skill de synthèse finale — consolide tous les résultats des skills précédents "
        "en une thèse d'investissement formelle avec scénarios pondérés, kill criteria, "
        "devil's advocate, sizing et verdict ACHETER/ACCUMULER/CONSERVER/VENDRE."
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
        Recherche RAG dans Qdrant pour les passages pertinents sur la construction de thèse.
        Retourne [] si le RAG n'est pas initialisé.
        """
        if self._rag is None:
            return []
        return await self._rag.search(query, k=k)

    def _build_user_message(
        self,
        input_data: ThesisBuilderInput,
        citations: list[Citation],
    ) -> str:
        """
        Construit le message utilisateur en injectant les contextes des skills précédents
        et les citations RAG avant la demande JSON finale.
        """
        parts: list[str] = []
        ctx = input_data.all_contexts

        if ctx.graham is not None:
            g = ctx.graham
            parts.append(
                f"## Contexte graham_analysis\n"
                f"Verdict : {g.verdict}, Score défensif : {g.defensive_score}/8\n"
                f"Marge de sécurité : {g.marge_securite}\n"
                f"Valeur intrinsèque ajustée : {g.valeur_intrinseque_ajustee}\n"
                f"Drapeaux rouges : {g.drapeaux_rouges}\n"
            )

        if ctx.earnings_quality is not None:
            eq = ctx.earnings_quality
            parts.append(
                f"## Contexte earnings_quality\n"
                f"Verdict : {eq.verdict}, Z-Score : {eq.z_score.z_score}, "
                f"F-Score : {eq.f_score.f_score}/9, M-Score : {eq.m_score.m_score}\n"
                f"Drapeaux rouges : {eq.drapeaux_rouges}\n"
            )

        if ctx.dorsey is not None:
            d = ctx.dorsey
            parts.append(
                f"## Contexte dorsey_moat\n"
                f"Moat type : {d.moat_type}, Durabilité ROIC : {d.roic_durability}\n"
                f"Verdict : {d.verdict_detail}\n"
            )

        if ctx.buffett is not None:
            b = ctx.buffett
            parts.append(
                f"## Contexte buffett_quality\n"
                f"Verdict : {b.verdict}, Quality score : {b.quality_score}/4, "
                f"Owner earnings : {b.owner_earnings}\n"
                f"Drapeaux rouges : {b.drapeaux_rouges}\n"
            )

        if ctx.valuation is not None:
            v = ctx.valuation
            parts.append(
                f"## Contexte stock_valuation_triangulation\n"
                f"Verdict : {v.verdict}, Fourchette : [{v.fourchette_basse} – {v.fourchette_haute}], "
                f"Centrale : {v.fourchette_centrale}, "
                f"Marge de sécurité composite : {v.marge_securite_composite}\n"
            )

        if citations:
            parts.append("## Contexte de référence (corpus investment thesis builder)\n")
            for i, cit in enumerate(citations, 1):
                parts.append(
                    f"**[{i}] {cit.source}** (score : {cit.score:.2f})\n{cit.extrait}\n"
                )
            parts.append("---\n")

        all_contexts_json = input_data.all_contexts.model_dump_json(indent=2)
        parts.append(
            f"Construis la thèse d'investissement formelle pour **{input_data.ticker}** "
            f"en synthétisant tous les contextes disponibles ci-dessus.\n\n"
            f"Données complètes des skills précédents :\n"
            f"```json\n{all_contexts_json}\n```\n\n"
            "Retourne l'analyse structurée via l'outil thesis_builder_output."
        )

        return "\n".join(parts)

    async def execute(
        self, input_data: ThesisBuilderInput
    ) -> tuple[ThesisBuilderOutput, UsageDetail]:
        """
        Appelle l'API Claude avec Tool Use — le modèle popule thesis_builder_output directement,
        éliminant les hallucinations de format JSON texte.
        """
        rag_query = (
            f"investment thesis builder {input_data.ticker} "
            f"scenarios bull base bear kill criteria devil's advocate "
            f"position sizing verdict ACHETER ACCUMULER CONSERVER VENDRE "
            f"marge de sécurité synthèse narrative scénarios pondérés"
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
            tools=[{"name": "thesis_builder_output", "input_schema": _THESIS_TOOL_SCHEMA}],
            tool_choice={"type": "tool", "name": "thesis_builder_output"},
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

        output = ThesisBuilderOutput.model_validate(data)
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
