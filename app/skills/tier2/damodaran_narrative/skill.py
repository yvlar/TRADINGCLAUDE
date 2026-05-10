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
from .schemas import DamodararInput, DamodararOutput

logger = logging.getLogger(__name__)


def _parse_claude_json(text: str) -> dict[str, Any]:
    """Parse le JSON depuis la rÃ©ponse Claude, gÃ¨re les blocs markdown optionnels."""
    text = text.strip()
    match = re.search(r"```(?:json)?\s*\n?(.*?)\n?```", text, re.DOTALL)
    if match:
        text = match.group(1).strip()
    return json.loads(text)


class DamodararNarrativeSkill(SkillBase):
    """
    Skill Tier 2 : cadre Damodaran Narrative and Numbers.
    Aligne la narrative (story) avec les chiffres financiers,
    teste la cohÃ©rence possible/plausible/probable,
    et dÃ©tecte les divergences entre story et data.
    """

    skill_id: ClassVar[str] = "damodaran_narrative"
    tier: ClassVar[int] = 2
    description: ClassVar[str] = (
        "Applique le cadre d'Aswath Damodaran â€” alignement narrative et chiffres, "
        "test possible/plausible/probable, ERP implicite, dÃ©tection des divergences. "
        "Verdict NARRATIVE_FORTE / NARRATIVE_ACCEPTABLE / NARRATIVE_FAIBLE / NARRATIVE_INCOHERENTE."
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
        """Recherche RAG dans Qdrant. Retourne [] si le RAG n'est pas initialisÃ©."""
        if self._rag is None:
            return []
        return await self._rag.search(query, k=k)

    def _build_user_message(
        self,
        input_data: DamodararInput,
        citations: list[Citation],
    ) -> str:
        """Construit le message utilisateur avec la narrative et les ratios Damodaran."""
        parts: list[str] = []
        r = input_data.damodaran_ratios

        parts.append(
            f"## Action Ã  analyser : {input_data.ticker}\n\n"
            f"### Narrative soumise\n{input_data.narrative_text}\n\n"
            f"### Ratios financiers\n"
            f"- Revenus : {r.revenue_bn} G$\n"
            f"- Croissance revenus 5 ans (revenue_growth_5y) : {r.revenue_growth_5y} "
            f"({r.revenue_growth_5y * 100:.1f} %/an)\n"
            f"- Marge nette : {r.net_margin} ({r.net_margin * 100:.1f} %)\n"
            f"- ROIC : {r.roic} ({r.roic * 100:.1f} %)\n"
            f"- TAM : {r.tam_bn} G$\n" if r.tam_bn else "- TAM : Non fourni\n"
        )

        parts.append(
            f"- Part de marchÃ© actuelle : {r.market_share_pct * 100:.1f} %\n"
            if r.market_share_pct is not None
            else "- Part de marchÃ© actuelle : Non fournie\n"
        )
        parts.append(f"- Secteur : {r.sector or 'Non spÃ©cifiÃ©'}\n")

        if citations:
            parts.append("\n## Contexte de rÃ©fÃ©rence (corpus Damodaran)\n")
            for i, cit in enumerate(citations, 1):
                parts.append(f"**[{i}] {cit.source}** (score : {cit.score:.2f})\n{cit.extrait}\n")
            parts.append("---\n")

        ratios_json = input_data.damodaran_ratios.model_dump_json(indent=2)
        parts.append(
            f"\nApplique le cadre Damodaran sur **{input_data.ticker}**. "
            f"Teste la cohÃ©rence narrative-chiffres, estime l'ERP implicite, "
            f"identifie les divergences et attribue un verdict.\n\n"
            f"DonnÃ©es complÃ¨tes :\n```json\n{ratios_json}\n```\n\n"
            "Retourne uniquement le JSON structurÃ© conforme au format de sortie dÃ©fini."
        )

        return "\n".join(parts)

    async def execute(
        self, input_data: DamodararInput
    ) -> tuple[DamodararOutput, UsageDetail]:
        """
        Appelle l'API Claude avec prompt caching et retourne (DamodararOutput, UsageDetail).
        """
        rag_query = (
            f"Damodaran narrative numbers {input_data.ticker} "
            f"story to numbers possible plausible probable ERP valorisation DCF"
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

        tokens_input = response.usage.input_tokens
        tokens_output = response.usage.output_tokens
        tokens_cache_r = getattr(response.usage, "cache_read_input_tokens", 0)
        tokens_cache_c = getattr(response.usage, "cache_creation_input_tokens", 0)
        total_consumed = tokens_input + tokens_cache_r + tokens_cache_c
        cache_hit_ratio = round(tokens_cache_r / total_consumed, 4) if total_consumed else 0.0

        logger.info(
            "execute terminÃ©",
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

        output = DamodararOutput.model_validate(data)
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

