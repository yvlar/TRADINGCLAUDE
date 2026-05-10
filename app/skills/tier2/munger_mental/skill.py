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
from .schemas import MungerInput, MungerOutput

logger = logging.getLogger(__name__)


def _parse_claude_json(text: str) -> dict[str, Any]:
    """Parse le JSON depuis la rÃ©ponse Claude, gÃ¨re les blocs markdown optionnels."""
    text = text.strip()
    match = re.search(r"```(?:json)?\s*\n?(.*?)\n?```", text, re.DOTALL)
    if match:
        text = match.group(1).strip()
    return json.loads(text)


class MungerMentalSkill(SkillBase):
    """
    Skill Tier 2 : dÃ©tection des biais cognitifs (Munger) dans la thÃ¨se d'investissement.
    Applique les 25 biais de Psychology of Human Misjudgment, inversion et lollapalooza.
    Verdict CONFIANCE_JUSTIFIEE / BIAIS_DETECTE / ALERTE_ROUGE.
    """

    skill_id: ClassVar[str] = "munger_mental_models"
    tier: ClassVar[int] = 2
    description: ClassVar[str] = (
        "Applique les 25 biais cognitifs de Charlie Munger (Psychology of Human Misjudgment), "
        "inversion ('invert, always invert'), et lollapalooza effects pour dÃ©tecter les biais "
        "dans la thÃ¨se d'investissement. Verdict CONFIANCE_JUSTIFIEE / BIAIS_DETECTE / ALERTE_ROUGE."
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
        Recherche RAG dans Qdrant pour les passages sur les biais cognitifs Munger.
        Retourne [] si le RAG n'est pas initialisÃ©.
        """
        if self._rag is None:
            return []
        return await self._rag.search(query, k=k)

    def _build_user_message(
        self,
        input_data: MungerInput,
        citations: list[Citation],
    ) -> str:
        """
        Construit le message utilisateur en injectant le contexte de la thÃ¨se
        et les citations RAG avant la demande JSON finale.
        """
        parts: list[str] = []
        ctx = input_data.thesis_context

        parts.append(
            f"## ThÃ¨se d'investissement Ã  auditer : {input_data.ticker}\n"
            f"- Verdict final : {ctx.verdict_final}\n"
            f"- Position size : {ctx.position_size_pct}%\n"
            f"- ProbabilitÃ© bull : {ctx.scenario_bull_probabilite}\n"
            f"- ProbabilitÃ© base : {ctx.scenario_base_probabilite}\n"
            f"- ProbabilitÃ© bear : {ctx.scenario_bear_probabilite}\n"
            f"- Kill criteria : {ctx.kill_criteria}\n"
            f"- Devil's advocate : {ctx.devils_advocate}\n\n"
            f"## SynthÃ¨se narrative\n{ctx.synthese_narrative}\n"
        )

        if citations:
            parts.append("## Contexte de rÃ©fÃ©rence (corpus Munger mental models)\n")
            for i, cit in enumerate(citations, 1):
                parts.append(
                    f"**[{i}] {cit.source}** (score : {cit.score:.2f})\n{cit.extrait}\n"
                )
            parts.append("---\n")

        thesis_context_json = input_data.thesis_context.model_dump_json(indent=2)
        parts.append(
            f"Effectue l'audit comportemental complet de la thÃ¨se d'investissement pour "
            f"**{input_data.ticker}** selon le cadre Munger (25 biais, inversion, lollapalooza).\n\n"
            f"DonnÃ©es complÃ¨tes de la thÃ¨se :\n"
            f"```json\n{thesis_context_json}\n```\n\n"
            "Retourne uniquement le JSON structurÃ© conforme au format de sortie dÃ©fini."
        )

        return "\n".join(parts)

    async def execute(
        self, input_data: MungerInput
    ) -> tuple[MungerOutput, UsageDetail]:
        """
        Appelle l'API Claude avec le system prompt cachÃ© et le contexte de la thÃ¨se.
        Retourne (MungerOutput, UsageDetail).
        """
        rag_query = (
            f"Munger biais cognitifs {input_data.ticker} "
            f"inversion lollapalooza commitment bias overconfidence "
            f"social proof sunk cost anchoring mental models investment"
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

        output = MungerOutput.model_validate(data)
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

