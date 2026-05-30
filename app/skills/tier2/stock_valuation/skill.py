from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, ClassVar

import anthropic

from app.rag.service import RagService
from app.services.valuation_calculations import (
    _BETA_DEFAULT,
    _ERP_MATURE,
    _G_HIGH_MAX,
    _G_TERMINAL_DEFAULT,
    _PROJECTION_YEARS,
    _RD_DEFAULT,
    _RF_DEFAULT,
    _TAX_DEFAULT,
    _WACC_DEFAULT,
    capm_cost_of_equity,
    dcf_sensitivity_matrix,
    dcf_value_per_share,
    poids_capital,
    wacc_cmpc,
)
from app.skills.base import Citation, SkillBase, SkillConfig, UsageDetail
from app.utils.costs import calculate_cost
from app.utils.retry import call_claude_with_retry
from app.utils.tool_schema import build_tool_schema

from .schemas import StockValuationInput, StockValuationOutput, ValuationRatios

logger = logging.getLogger(__name__)

# Schéma dérivé de Pydantic — champs post-assignés exclus.
_VALUATION_TOOL_SCHEMA = build_tool_schema(
    StockValuationOutput,
    exclude={"citations", "cost_usd"},
)

# Secteurs où le DCF classique est inapplicable (references/dcf.md) — la méthode sectorielle
# prime ; l'ossature DCF déterministe n'est alors pas injectée (le bloc LLM est conservé).
# Fragments (et non labels exacts) pour couvrir EN + FR, sources de données du projet étant
# franco-centrées : "financ" (financial/financier/financière/services financiers),
# "banq"/"bank" (banque/banques/bank), "assur"/"insur" (assurance/assureur/insurance),
# "immobil"/"real estate"/"reit" (immobilier/immobilière + libellés anglais).
_SECTEURS_NON_DCF = (
    "financ",
    "banq",
    "bank",
    "assur",
    "insur",
    "immobil",
    "real estate",
    "reit",
)


@dataclass(frozen=True)
class _DcfDeterministe:
    """Ossature DCF calculée en Python — autorité sur les valeurs du LLM (Sprint 132).

    `applicable=False` quand le secteur exclut le DCF (financière/REIT) ou que les données
    de base manquent (FCF/actions) ; le bloc LLM est alors conservé tel quel.
    """

    applicable: bool
    wacc: float | None = None
    terminal_growth: float | None = None
    growth_high: float | None = None
    per_share: float | None = None
    wacc_range: list[float] | None = None
    growth_range: list[float] | None = None
    values: list[list[float]] | None = None


def _secteur_exclut_dcf(sector: str | None) -> bool:
    """Vrai si le secteur relève des financières/REIT — DCF classique inapplicable."""
    if sector is None:
        return False
    secteur = sector.strip().lower()
    return any(mot in secteur for mot in _SECTEURS_NON_DCF)


def _net_debt_bn(ratios: ValuationRatios) -> float:
    """
    Dette nette approximée (milliards) : D/E × capitaux propres comptables.
    Proxy comptable faute de dette nette de marché ; le cash excédentaire n'étant pas
    disponible, il est ignoré (approximation conservatrice). 0 si une donnée manque.
    """
    if (
        ratios.debt_equity is not None
        and ratios.debt_equity > 0
        and ratios.book_value is not None
        and ratios.shares_outstanding_m is not None
    ):
        capitaux_propres_bn = ratios.book_value * ratios.shares_outstanding_m / 1_000.0
        return ratios.debt_equity * capitaux_propres_bn
    return 0.0


def _wacc_central(ratios: ValuationRatios) -> float:
    """WACC retenu pour la valeur DCF centrale : ratios.wacc si fourni, sinon CMPC, sinon défaut."""
    if ratios.wacc is not None and ratios.wacc > 0:
        # Tolère un WACC fourni en fraction (0.09) ou en pourcentage (9.0).
        return ratios.wacc if ratios.wacc < 1 else ratios.wacc / 100.0
    equity_weight, debt_weight = poids_capital(ratios.debt_equity)
    cmpc = wacc_cmpc(
        cost_equity=capm_cost_of_equity(_RF_DEFAULT, _BETA_DEFAULT, _ERP_MATURE),
        cost_debt=_RD_DEFAULT,
        tax_rate=_TAX_DEFAULT,
        equity_weight=equity_weight,
        debt_weight=debt_weight,
    )
    return cmpc if cmpc is not None else _WACC_DEFAULT


def _croissance_terminale(ratios: ValuationRatios) -> float:
    """Croissance terminale Gordon : ratios.terminal_growth_rate si fourni, sinon défaut."""
    tg = ratios.terminal_growth_rate
    if tg is None:
        return _G_TERMINAL_DEFAULT
    return tg if tg < 1 else tg / 100.0


def _croissance_phase1(ratios: ValuationRatios, terminal_growth: float) -> float:
    """Croissance d'exploitation phase 1 : EPS 5a → revenus 5a → EPS 10a, plafonnée ; sinon terminale."""
    for source in (ratios.eps_growth_5y, ratios.revenue_growth_5y, ratios.eps_growth_10y):
        if source is not None and source > 0:
            return min(source, _G_HIGH_MAX)
    return terminal_growth


def _dcf_depuis_ratios(ratios: ValuationRatios) -> _DcfDeterministe:
    """Calcule l'ossature DCF (WACC, valeur par action, matrice) depuis les ratios disponibles."""
    if _secteur_exclut_dcf(ratios.sector):
        return _DcfDeterministe(applicable=False)

    wacc = _wacc_central(ratios)
    terminal_growth = _croissance_terminale(ratios)
    growth_high = _croissance_phase1(ratios, terminal_growth)
    net_debt = _net_debt_bn(ratios)

    per_share = dcf_value_per_share(
        fcf_initial_bn=ratios.free_cash_flow_bn,
        growth_high=growth_high,
        years=_PROJECTION_YEARS,
        wacc=wacc,
        terminal_growth=terminal_growth,
        shares_outstanding_m=ratios.shares_outstanding_m,
        net_debt_bn=net_debt,
    )
    matrice = dcf_sensitivity_matrix(
        fcf_initial_bn=ratios.free_cash_flow_bn,
        growth_high=growth_high,
        years=_PROJECTION_YEARS,
        shares_outstanding_m=ratios.shares_outstanding_m,
        net_debt_bn=net_debt,
    )
    if per_share is None or matrice is None:
        return _DcfDeterministe(applicable=False)

    wacc_range, growth_range, values = matrice
    return _DcfDeterministe(
        applicable=True,
        wacc=wacc,
        terminal_growth=terminal_growth,
        growth_high=growth_high,
        per_share=round(per_share, 2),
        wacc_range=wacc_range,
        growth_range=growth_range,
        values=values,
    )


def _injecter_dcf(data: dict[str, Any], dcf: _DcfDeterministe) -> None:
    """
    Écrase la valeur DCF + la matrice de sensibilité du bloc LLM par l'ossature Python
    (Sprint 132). La narrative (hypothèses, comparables, sectoriel, fourchette, verdict) est
    préservée. Si le DCF est inapplicable (financière/REIT) ou non calculable (FCF/actions
    manquants), le bloc LLM est conservé — la méthode sectorielle prime (references/dcf.md).
    """
    if not dcf.applicable:
        return
    for methode in data.get("methodes", []):
        if isinstance(methode, dict) and methode.get("methode") == "dcf":
            methode["valeur"] = dcf.per_share
    data["matrice_sensibilite"] = {
        "wacc_range": dcf.wacc_range,
        "growth_range": dcf.growth_range,
        "values": dcf.values,
    }


class StockValuationSkill(SkillBase):
    """
    Skill Tier 2 : valorisation par triangulation de trois méthodes (DCF, comparables, sectoriel).
    Produit une fourchette basse/centrale/haute et une matrice de sensibilité WACC × g.
    Verdict SOUS_EVALUE / JUSTE_VALEUR / SUREVALUE.
    """

    skill_id: ClassVar[str] = "stock_valuation_triangulation"
    tier: ClassVar[int] = 2
    description: ClassVar[str] = (
        "Valorise une action par trois méthodes indépendantes (DCF avec WACC explicité, "
        "multiples comparables, méthode sectorielle). Produit une fourchette basse/centrale/haute "
        "et une matrice de sensibilité WACC × taux terminal. "
        "Verdict SOUS_EVALUE / JUSTE_VALEUR / SUREVALUE."
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
        Recherche RAG dans Qdrant pour les passages pertinents sur la valorisation.
        Retourne [] si le RAG n'est pas initialisé.
        """
        if self._rag is None:
            return []
        return await self._rag.search(query, k=k)

    def _build_user_message(
        self,
        input_data: StockValuationInput,
        citations: list[Citation],
        dcf: _DcfDeterministe | None = None,
    ) -> str:
        """
        Construit le message utilisateur.
        Injecte les contextes des skills précédents en tête avant les ratios de valorisation.
        L'ossature DCF déterministe (si calculable) est exposée pour interprétation.
        """
        if dcf is None:
            dcf = _dcf_depuis_ratios(input_data.ratios)
        parts: list[str] = []

        if input_data.graham_context is not None:
            ctx = input_data.graham_context
            parts.append(
                f"## Contexte graham_analysis\n"
                f"Verdict : {ctx.verdict}, Score défensif : {ctx.defensive_score}/8\n"
                f"Marge de sécurité Graham : {ctx.marge_securite}\n"
                f"Valeur intrinsèque simple (Graham) : {ctx.valeur_intrinseque_simple}\n"
            )

        if input_data.earnings_context is not None:
            ctx = input_data.earnings_context
            parts.append(
                f"## Contexte earnings_quality\n"
                f"Verdict : {ctx.verdict}, Z-Score : {ctx.z_score}, F-Score : {ctx.f_score}\n"
            )

        if input_data.dorsey_context is not None:
            ctx = input_data.dorsey_context
            parts.append(
                f"## Contexte dorsey_moat\n"
                f"Moat type : {ctx.moat_type}, Durabilité ROIC : {ctx.roic_durability}\n"
            )

        if input_data.buffett_context is not None:
            ctx = input_data.buffett_context
            parts.append(
                f"## Contexte buffett_quality\n"
                f"Quality score : {ctx.quality_score}/4, Verdict : {ctx.verdict}\n"
                f"Owner earnings : {ctx.owner_earnings}\n"
            )

        if citations:
            parts.append("## Contexte de référence (corpus stock valuation triangulation)\n")
            for i, cit in enumerate(citations, 1):
                parts.append(
                    f"**[{i}] {cit.source}** (score : {cit.score:.2f})\n{cit.extrait}\n"
                )
            parts.append("---\n")

        ratios_json = input_data.ratios.model_dump_json(indent=2)
        parts.append(
            f"Valorise **{input_data.ticker}** par triangulation DCF + comparables + sectoriel "
            f"et produit la fourchette basse/centrale/haute avec matrice de sensibilité WACC × g :\n\n"
            f"```json\n{ratios_json}\n```\n"
        )

        if dcf.applicable:
            # Ossature DCF calculée en amont (déterministe) — le LLM l'interprète, ne la recalcule pas.
            parts.append(
                "## Ossature DCF déterministe (calculée en Python — interprète-la, ne la recalcule pas)\n"
                f"- WACC retenu : {dcf.wacc:.2%}\n"
                f"- Croissance terminale (g) : {dcf.terminal_growth:.2%}\n"
                f"- Croissance d'exploitation phase 1 : {dcf.growth_high:.2%}\n"
                f"- Valeur intrinsèque DCF par action : {dcf.per_share:.2f}\n"
                "Cette valeur DCF et la matrice de sensibilité WACC × g font autorité et "
                "remplaceront les tiennes ; concentre-toi sur les comparables, la méthode "
                "sectorielle, la pondération de la fourchette et le verdict.\n"
            )

        parts.append("Retourne l'analyse structurée via l'outil stock_valuation_output.")

        return "\n".join(parts)

    async def execute(
        self, input_data: StockValuationInput
    ) -> tuple[StockValuationOutput, UsageDetail]:
        """
        Appelle l'API Claude avec Tool Use — le modèle popule stock_valuation_output directement,
        éliminant les hallucinations de format JSON texte.
        """
        rag_query = (
            f"stock valuation {input_data.ticker} DCF WACC comparable multiples "
            f"intrinsic value fair value triangulation sensitivity matrix fourchette"
        )
        citations = await self.get_citations(rag_query, k=self._top_k)

        # Ossature DCF déterministe — calculée une fois, exposée au LLM et substituée post-parse.
        dcf = _dcf_depuis_ratios(input_data.ratios)
        user_message = self._build_user_message(input_data, citations, dcf)

        t0 = time.perf_counter()
        response = await call_claude_with_retry(
            self._client,
            timeout_s=self._config.timeout_s,
            max_retries=self._config.max_retries,
            model=self._model,
            system=self.get_system_prompt(),
            messages=[{"role": "user", "content": user_message}],
            max_tokens=4096,
            tools=[{"name": "stock_valuation_output", "input_schema": _VALUATION_TOOL_SCHEMA}],
            tool_choice={"type": "tool", "name": "stock_valuation_output"},
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
        # Substitution déterministe (Sprint 132) : la valeur DCF + la matrice Python priment
        # sur le bloc LLM. Comparables, sectoriel, fourchette et verdict restent au LLM.
        _injecter_dcf(data, dcf)

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

        output = StockValuationOutput.model_validate(data)
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
