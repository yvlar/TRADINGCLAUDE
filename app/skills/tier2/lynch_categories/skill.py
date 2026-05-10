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
from .schemas import LynchInput, LynchOutput

logger = logging.getLogger(__name__)


def _parse_claude_json(text: str) -> dict[str, Any]:
    """Parse le JSON depuis la rÃ©ponse Claude, gÃ¨re les blocs markdown optionnels."""
    text = text.strip()
    match = re.search(r"```(?:json)?\s*\n?(.*?)\n?```", text, re.DOTALL)
    if match:
        text = match.group(1).strip()
    return json.loads(text)


class LynchCategoriesSkill(SkillBase):
    """
    Skill Tier 2 : classification Lynch en 6 catÃ©gories + PEG + tenbagger.
    Applique One Up on Wall Street (Lynch, 1989) â€” slow grower, stalwart, fast grower,
    cyclical, turnaround, asset play. Verdict EXCELLENT / BON / MOYEN / EVITER.
    """

    skill_id: ClassVar[str] = "lynch_categories"
    tier: ClassVar[int] = 2
    description: ClassVar[str] = (
        "Applique le cadre de Peter Lynch (One Up on Wall Street) â€” classification en 6 catÃ©gories, "
        "calcul du PEG ratio, identification des tenbaggers potentiels. "
        "Verdict EXCELLENT / BON / MOYEN / EVITER selon la catÃ©gorie et la valorisation."
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
        input_data: LynchInput,
        citations: list[Citation],
    ) -> str:
        """Construit le message utilisateur avec les ratios Lynch et les citations RAG."""
        parts: list[str] = []
        r = input_data.ratios

        parts.append(
            f"## Action Ã  analyser : {input_data.ticker}\n\n"
            f"### Ratios financiers\n"
            f"- P/E : {r.pe}\n"
            f"- Croissance BPA 5 ans (eps_growth_5y) : {r.eps_growth_5y} "
            f"({'= ' + str(round(r.eps_growth_5y * 100, 1)) + '%/an' if r.eps_growth_5y is not None else 'N/A'})\n"
            f"- Croissance revenus 5 ans : {r.revenue_growth_5y}\n"
            f"- Marge nette : {r.net_margin}\n"
            f"- Dette/Capitaux propres : {r.debt_equity}\n"
            f"- FCF yield : {r.fcf_yield}\n"
            f"- Rendement dividende : {r.dividend_yield}\n"
            f"- IntensitÃ© capex : {r.capex_intensity}\n"
        )

        if r.eps_growth_5y is not None and r.eps_growth_5y > 0:
            peg = r.pe / (r.eps_growth_5y * 100)
            parts.append(f"\n**PEG calculÃ©** : {r.pe} / ({r.eps_growth_5y} Ã— 100) = {peg:.2f}\n")
        else:
            parts.append("\n**PEG** : null (eps_growth_5y â‰¤ 0)\n")

        if citations:
            parts.append("\n## Contexte de rÃ©fÃ©rence (corpus Lynch)\n")
            for i, cit in enumerate(citations, 1):
                parts.append(f"**[{i}] {cit.source}** (score : {cit.score:.2f})\n{cit.extrait}\n")
            parts.append("---\n")

        ratios_json = input_data.ratios.model_dump_json(indent=2)
        parts.append(
            f"\nClassifie **{input_data.ticker}** selon les 6 catÃ©gories Lynch, "
            f"calcule le PEG ratio, Ã©value le potentiel tenbagger, et attribue un verdict.\n\n"
            f"DonnÃ©es complÃ¨tes :\n```json\n{ratios_json}\n```\n\n"
            "Retourne uniquement le JSON structurÃ© conforme au format de sortie dÃ©fini."
        )

        return "\n".join(parts)

    async def execute(
        self, input_data: LynchInput
    ) -> tuple[LynchOutput, UsageDetail]:
        """
        Appelle l'API Claude avec prompt caching et retourne (LynchOutput, UsageDetail).
        """
        rag_query = (
            f"Lynch categories {input_data.ticker} "
            f"slow grower stalwart fast grower cyclical turnaround asset play "
            f"PEG ratio tenbagger croissance bÃ©nÃ©fices"
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

        output = LynchOutput.model_validate(data)
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

