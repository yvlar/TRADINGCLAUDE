from __future__ import annotations

import logging
import time
from pathlib import Path
from typing import Any, ClassVar

import anthropic

from app.rag.service import RagService
from app.services.financial_calculations import OwnerEarningsDetail, owner_earnings_detail
from app.skills.base import Citation, SkillBase, SkillConfig, UsageDetail
from app.utils.costs import calculate_cost
from app.utils.retry import call_claude_with_retry
from app.utils.tool_schema import build_tool_schema

from .schemas import BuffettQualityInput, BuffettQualityOutput

logger = logging.getLogger(__name__)

# Schéma dérivé de Pydantic — confidence_score et champs post-assignés exclus.
# owner_earnings est calculé en Python et injecté post-parse — jamais produit par le LLM.
_BUFFETT_TOOL_SCHEMA = build_tool_schema(
    BuffettQualityOutput,
    exclude={"confidence_score", "citations", "cost_usd", "owner_earnings"},
)

_OE_METHODE_LABELS = {
    "fourni": "maintenance capex fourni",
    "capex_x070": "approximation 70 % du capex total (entreprise mature)",
    "egal_dna": "approximation capex ≈ D&A (entreprise stable) — owner earnings = BPA",
}


def _compute_owner_earnings(input_data: BuffettQualityInput) -> OwnerEarningsDetail:
    """Owner earnings déterministes depuis les ratios — source unique message + output."""
    r = input_data.ratios
    return owner_earnings_detail(
        eps_ttm=r.eps_ttm,
        net_margin=r.net_margin,
        revenue_bn=r.revenue_bn,
        depreciation_bn=r.depreciation_bn,
        capex_bn=r.capex_bn,
        maintenance_capex_bn=r.maintenance_capex_bn,
    )


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
            f"(business compréhensible, economics favorables, management fiable, prix attractif) :\n\n"
            f"```json\n{ratios_json}\n```\n\n"
        )

        oe = _compute_owner_earnings(input_data)
        if oe.owner_earnings is not None:
            methode = _OE_METHODE_LABELS.get(
                oe.methode_maintenance_capex or "", oe.methode_maintenance_capex or ""
            )
            parts.append(
                f"**Owner earnings** (calculés en Python, déterministe) : "
                f"{oe.owner_earnings:.2f} $/action — méthode : {methode}. "
                "Utilise cette valeur pour le filtre prix_attractif "
                "(owner earnings yield = owner earnings / price) ; ne la recalcule pas.\n\n"
            )
        else:
            parts.append(
                "**Owner earnings** : données insuffisantes pour le calcul déterministe "
                "(owner_earnings sera null dans l'output) — évalue le filtre prix_attractif "
                "via le P/E relatif à la croissance.\n\n"
            )

        parts.append("Retourne l'analyse structurée via l'outil buffett_quality_output.")

        return "\n".join(parts)

    async def execute(
        self, input_data: BuffettQualityInput
    ) -> tuple[BuffettQualityOutput, UsageDetail]:
        """
        Appelle l'API Claude avec Tool Use — le modèle popule buffett_quality_output directement,
        éliminant les hallucinations de format JSON texte.
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
            tools=[{"name": "buffett_quality_output", "input_schema": _BUFFETT_TOOL_SCHEMA}],
            tool_choice={"type": "tool", "name": "buffett_quality_output"},
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
        # Valeur déterministe calculée en Python — prime sur toute valeur LLM (parité Sprint 128).
        data["owner_earnings"] = _compute_owner_earnings(input_data).owner_earnings

        cost_usd = calculate_cost(response.usage, self._model)

        # confidence_score = fraction des champs BuffettRatios non-None (complétude des données)
        _ratios_fields = list(type(input_data.ratios).model_fields.keys())
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
