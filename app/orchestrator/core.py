from __future__ import annotations

import asyncio
import json as _json
import logging
import time
from collections.abc import AsyncGenerator
from datetime import datetime, timezone
from typing import TYPE_CHECKING

import asyncpg
from pydantic import BaseModel, Field, field_validator

from app.services.composite_score import CompositeScore, compute_composite_score
from app.skills.base import UsageDetail
from app.utils.ticker_sanitizer import sanitize_ticker

if TYPE_CHECKING:
    from app.services.analysis_cache import AnalysisCacheService
    from app.services.composite_history_service import CompositeHistoryService
    from app.services.esg_history_service import EsgHistoryService
    from app.services.observability import ObservabilityService

from app.orchestrator.router import WorkflowRouter

_workflow_router = WorkflowRouter()

from app.services.observability import SkillTrace
from app.services.ratios_recon import (
    _earnings_ratios_trace,
    _graham_ratios_trace,
    _valuation_ratios_trace,
)
from app.skills.tier2.buffett_quality.schemas import (
    BuffettQualityInput,
    BuffettQualityOutput,
    BuffettRatios,
)
from app.skills.tier2.buffett_quality.schemas import (
    DorseyContext as BuffettDorseyContext,
)
from app.skills.tier2.buffett_quality.skill import BuffettQualitySkill
from app.skills.tier2.canadian_tax.schemas import (
    CanadianTaxInput,
    CanadianTaxOutput,
)
from app.skills.tier2.canadian_tax.skill import CanadianTaxSkill
from app.skills.tier2.damodaran_narrative.schemas import (
    DamodararInput,
    DamodararOutput,
)
from app.skills.tier2.damodaran_narrative.skill import DamodararNarrativeSkill
from app.skills.tier2.dorsey_moat.schemas import (
    DorseyMoatInput,
    DorseyMoatOutput,
    DorseyRatios,
)
from app.skills.tier2.dorsey_moat.schemas import (
    EarningsContext as DorseyEarningsContext,
)
from app.skills.tier2.dorsey_moat.skill import DorseyMoatSkill
from app.skills.tier2.earnings_quality.schemas import (
    EarningsQualityInput,
    EarningsQualityOutput,
    EarningsQualityRatios,
    GrahamContext,
)
from app.skills.tier2.earnings_quality.skill import EarningsQualitySkill
from app.skills.tier2.esg_simplified.schemas import (
    EsgInput,
    EsgOutput,
)
from app.skills.tier2.esg_simplified.skill import EsgSimplifiedSkill
from app.skills.tier2.fisher_scuttlebutt.schemas import (
    FisherInput,
    FisherOutput,
)
from app.skills.tier2.fisher_scuttlebutt.skill import FisherScuttlebuttSkill
from app.skills.tier2.graham_analysis.schemas import (
    GrahamAnalysisInput,
    GrahamAnalysisOutput,
    GrahamRatios,
)
from app.skills.tier2.graham_analysis.skill import GrahamAnalysisSkill
from app.skills.tier2.greenblatt.schemas import (
    GreenblattInput,
    GreenblattOutput,
)
from app.skills.tier2.greenblatt.skill import GreenblattSkill
from app.skills.tier2.klarman_margin.schemas import (
    KlarmanInput,
    KlarmanOutput,
)
from app.skills.tier2.klarman_margin.skill import KlarmanMarginSkill
from app.skills.tier2.lynch_categories.schemas import (
    LynchInput,
    LynchOutput,
    LynchRatios,
)
from app.skills.tier2.lynch_categories.skill import LynchCategoriesSkill
from app.skills.tier2.marks_cycles.schemas import (
    MarksInput,
    MarksOutput,
)
from app.skills.tier2.marks_cycles.skill import MarksCyclesSkill
from app.skills.tier2.munger_mental.schemas import (
    MungerInput,
    MungerOutput,
    ThesisContext,
)
from app.skills.tier2.munger_mental.skill import MungerMentalSkill
from app.skills.tier2.pabrai_dhandho.schemas import (
    PabraiInput,
    PabraiOutput,
)
from app.skills.tier2.pabrai_dhandho.skill import PabraiDhandhoSkill
from app.skills.tier2.stock_valuation.schemas import (
    BuffettContext as ValuationBuffettContext,
)
from app.skills.tier2.stock_valuation.schemas import (
    DorseyContext as ValuationDorseyContext,
)
from app.skills.tier2.stock_valuation.schemas import (
    EarningsContext as ValuationEarningsContext,
)
from app.skills.tier2.stock_valuation.schemas import (
    GrahamContext as ValuationGrahamContext,
)
from app.skills.tier2.stock_valuation.schemas import (
    StockValuationInput,
    StockValuationOutput,
    ValuationRatios,
)
from app.skills.tier2.stock_valuation.skill import StockValuationSkill
from app.skills.tier2.thesis_builder.schemas import (
    AllSkillContexts,
    ThesisBuilderInput,
    ThesisBuilderOutput,
)
from app.skills.tier2.thesis_builder.skill import ThesisBuilderSkill

logger = logging.getLogger(__name__)


def _detect_inter_skill_conflicts(
    graham: "GrahamAnalysisOutput | None",
    buffett: "BuffettQualityOutput | None",
    earnings: "EarningsQualityOutput | None",
    dorsey: "DorseyMoatOutput | None",
) -> list[str]:
    """Détecte les contradictions flagrantes entre les verdicts de skills."""
    conflicts: list[str] = []

    if graham is not None and buffett is not None:
        if graham.defensive_verdict == "REJETER" and buffett.verdict == "COMPOUNDER":
            conflicts.append(
                "graham=REJETER + buffett=COMPOUNDER : contradiction fondamentale — revue manuelle requise"
            )

    if earnings is not None and buffett is not None:
        if earnings.verdict == "REJETER" and buffett.verdict == "COMPOUNDER":
            conflicts.append(
                "earnings_quality=REJETER + buffett=COMPOUNDER : risque comptable sur supposé compounder"
            )

    if graham is not None and earnings is not None:
        if graham.defensive_verdict == "PASSE" and earnings.verdict == "REJETER":
            conflicts.append(
                "graham=PASSE + earnings_quality=REJETER : scores défensifs positifs mais risque de manipulation comptable"
            )

    return conflicts


def _extract_int(result_json: str, *keys: str) -> int | None:
    """Navigue dans un JSONB imbriqué et retourne un int ou None."""
    try:
        obj = _json.loads(result_json)
        for key in keys:
            obj = obj[key]
        return int(obj)
    except (KeyError, TypeError, ValueError):
        return None


def _extract_str(result_json: str, *keys: str) -> str | None:
    """Navigue dans un JSONB imbriqué et retourne une str ou None."""
    try:
        obj = _json.loads(result_json)
        for key in keys:
            obj = obj[key]
        return str(obj)
    except (KeyError, TypeError, ValueError):
        return None


def _row_to_history_entry(row) -> "HistoryEntry":
    """Construit un HistoryEntry depuis une row jointe analysis_history + annotations."""
    tags = row["tags"]
    return HistoryEntry(
        analysis_id=str(row["id"]),
        ticker=row["ticker"],
        workflow=row["workflow_name"],
        skills_applied=_json.loads(row["skills_used"]),
        cost_usd=float(row["cost_usd"]),
        defensive_score=_extract_int(row["result"], "graham", "defensive_score"),
        graham_verdict=_extract_str(row["result"], "graham", "verdict"),
        earnings_verdict=_extract_str(row["result"], "earnings_quality", "verdict"),
        created_at=row["created_at"].isoformat(),
        tags=list(tags) if tags is not None else [],
    )


class AnalyzeRequest(BaseModel):
    """Corps de la requête POST /analyze — section 5.2 de l'architecture."""

    ticker: str
    ratios: GrahamRatios | None = None

    @field_validator("ticker")
    @classmethod
    def valider_ticker(cls, v: str) -> str:
        return sanitize_ticker(v)
    workflow: str = "value_graham"
    earnings_ratios: EarningsQualityRatios | None = None
    dorsey_ratios: DorseyRatios | None = None
    buffett_ratios: BuffettRatios | None = None
    valuation_ratios: ValuationRatios | None = None
    thesis_ratios: bool = False  # True pour activer thesis_builder en fin de workflow
    munger_ratios: bool = False  # True pour activer munger après thesis_builder
    tax_input: CanadianTaxInput | None = None  # Fourni directement par l'utilisateur
    lynch_ratios: LynchRatios | None = None
    fisher_input: FisherInput | None = None
    klarman_input: KlarmanInput | None = None
    greenblatt_input: GreenblattInput | None = None
    damodaran_input: DamodararInput | None = None
    marks_input: MarksInput | None = None
    pabrai_input: PabraiInput | None = None
    esg_input: EsgInput | None = None


class AnalyzeResponse(BaseModel):
    """Réponse complète du workflow company_analysis."""

    analysis_id: str
    ticker: str
    workflow: str
    skills_applied: list[str]
    graham: GrahamAnalysisOutput | None = None
    earnings_quality: EarningsQualityOutput | None = None
    dorsey: DorseyMoatOutput | None = None
    buffett: BuffettQualityOutput | None = None
    valuation: StockValuationOutput | None = None
    thesis: ThesisBuilderOutput | None = None
    munger: MungerOutput | None = None
    canadian_tax: CanadianTaxOutput | None = None
    lynch: LynchOutput | None = None
    fisher: FisherOutput | None = None
    klarman: KlarmanOutput | None = None
    greenblatt: GreenblattOutput | None = None
    damodaran: DamodararOutput | None = None
    marks: MarksOutput | None = None
    pabrai: PabraiOutput | None = None
    esg: EsgOutput | None = None
    cost_usd: float
    created_at: str
    inter_skill_conflicts: list[str] = Field(
        default_factory=list,
        description="Contradictions détectées entre verdicts de skills — calculé de façon déterministe.",
    )
    composite_score: CompositeScore | None = Field(
        default=None,
        description="Score composite pondéré 0-100 — calculé de façon déterministe depuis les verdicts des skills.",
    )
    depuis_cache_composite: bool = Field(
        default=False,
        description="True si composite_score retourné depuis composite_score_history (< 24h) sans appel Claude.",
    )
    ratios_fetched_at: str | None = Field(
        default=None,
        description="Date ISO de récupération des ratios Graham d'entrée (traçabilité). None si analyse ancienne ou ratios saisis manuellement.",
    )
    ratios_source: str | None = Field(
        default=None,
        description="Source des ratios Graham d'entrée (ex. « Yahoo Finance »). None si inconnue.",
    )
    earnings_ratios_fetched_at: str | None = Field(
        default=None,
        description="Date ISO de récupération des ratios Qualité bénéfices d'entrée (traçabilité). None si analyse ancienne ou ratios saisis manuellement.",
    )
    earnings_ratios_source: str | None = Field(
        default=None,
        description="Source des ratios Qualité bénéfices d'entrée (ex. « Yahoo Finance »). None si inconnue.",
    )
    valuation_ratios_fetched_at: str | None = Field(
        default=None,
        description="Date ISO de récupération des ratios Valorisation d'entrée (traçabilité). None si analyse ancienne ou ratios saisis manuellement.",
    )
    valuation_ratios_source: str | None = Field(
        default=None,
        description="Source des ratios Valorisation d'entrée (ex. « Yahoo Finance »). None si inconnue.",
    )


def _request_ratios_traces(request: AnalyzeRequest) -> dict[str, str | None]:
    """Reconstruit les 6 champs de traçabilité (Graham + earnings + valuation) depuis les ratios d'une requête.

    Évite la répétition du triplet d'appels aux quatre points de construction d'AnalyzeResponse.
    """
    graham_fetched, graham_source = _graham_ratios_trace(request.ratios)
    earnings_fetched, earnings_source = _earnings_ratios_trace(request.earnings_ratios)
    valuation_fetched, valuation_source = _valuation_ratios_trace(request.valuation_ratios)
    return {
        "ratios_fetched_at": graham_fetched,
        "ratios_source": graham_source,
        "earnings_ratios_fetched_at": earnings_fetched,
        "earnings_ratios_source": earnings_source,
        "valuation_ratios_fetched_at": valuation_fetched,
        "valuation_ratios_source": valuation_source,
    }


def _build_input_data(request: AnalyzeRequest) -> str:
    """Sérialise les ratios d'entrée (JSONB) ; Graham à plat, earnings/valuation sous clés dédiées.

    Graham reste à plat car les lecteurs valident input_data comme GrahamRatios (extra='ignore'
    ignore les sous-clés) — rétrocompat des lignes antérieures. mode='json' : datetime → ISO.
    """
    payload: dict = (
        request.ratios.model_dump(mode="json") if request.ratios is not None else {}
    )
    if request.earnings_ratios is not None:
        payload["earnings_ratios"] = request.earnings_ratios.model_dump(mode="json")
    if request.valuation_ratios is not None:
        payload["valuation_ratios"] = request.valuation_ratios.model_dump(mode="json")
    return _json.dumps(payload)


class HistoryEntry(BaseModel):
    analysis_id: str
    ticker: str
    workflow: str
    skills_applied: list[str]
    cost_usd: float
    defensive_score: int | None
    earnings_verdict: str | None
    graham_verdict: str | None
    created_at: str
    tags: list[str] = Field(default_factory=list)


class HistoryResponse(BaseModel):
    ticker: str | None
    entries: list[HistoryEntry]
    next_before: str | None


class PagedHistoryResponse(BaseModel):
    """Pagination offset/limit pour /history-paged (Sprint 90)."""

    ticker: str | None
    q: str | None
    entries: list[HistoryEntry]
    page: int
    page_size: int
    total_count: int
    total_pages: int


class TickerMetrics(BaseModel):
    ticker: str
    analyses: int
    cost_usd: float


class MetricsResponse(BaseModel):
    period_days: int
    total_analyses: int
    total_cost_usd: float
    avg_cost_per_analysis: float
    cache_hit_ratio_avg: float
    top_tickers: list[TickerMetrics]
    skills_usage: dict[str, int]
    # coût USD attribué par skill (coût de l'analyse réparti également entre ses skills)
    skills_cost: dict[str, float] = {}
    # taux de cache moyen agrégé par workflow_name
    cache_by_workflow: dict[str, float] = {}
    # coût USD total par jour (clé YYYY-MM-DD) — tendance quotidienne (Sprint 112)
    daily_cost: dict[str, float] = {}


class SkillAnalysisEntry(BaseModel):
    analysis_id: str
    ticker: str
    workflow_name: str
    cost_usd: float
    created_at: str


class SkillAnalysesResponse(BaseModel):
    skill: str
    period_days: int
    entries: list[SkillAnalysisEntry]


class Orchestrator:
    """
    Orchestre le workflow company_analysis selon la section 9.1 de l'architecture.
    Phase 3 : graham → earnings_quality → dorsey_moat → buffett_quality
              → stock_valuation_triangulation → investment_thesis_builder
              → munger_mental_models → canadian_tax_considerations.
    """

    def __init__(
        self,
        db_pool: asyncpg.Pool,
        graham_skill: GrahamAnalysisSkill,
        earnings_skill: EarningsQualitySkill,
        dorsey_skill: DorseyMoatSkill | None = None,
        buffett_skill: BuffettQualitySkill | None = None,
        valuation_skill: StockValuationSkill | None = None,
        thesis_skill: ThesisBuilderSkill | None = None,
        munger_skill: MungerMentalSkill | None = None,
        canadian_tax_skill: CanadianTaxSkill | None = None,
        lynch_skill: LynchCategoriesSkill | None = None,
        fisher_skill: FisherScuttlebuttSkill | None = None,
        klarman_skill: KlarmanMarginSkill | None = None,
        greenblatt_skill: GreenblattSkill | None = None,
        damodaran_skill: DamodararNarrativeSkill | None = None,
        marks_skill: MarksCyclesSkill | None = None,
        pabrai_skill: PabraiDhandhoSkill | None = None,
        esg_skill: EsgSimplifiedSkill | None = None,
    ) -> None:
        self._db = db_pool
        self._graham = graham_skill
        self._earnings = earnings_skill
        self._dorsey = dorsey_skill
        self._buffett = buffett_skill
        self._valuation = valuation_skill
        self._thesis = thesis_skill
        self._munger = munger_skill
        self._canadian_tax = canadian_tax_skill
        self._lynch = lynch_skill
        self._fisher = fisher_skill
        self._klarman = klarman_skill
        self._greenblatt = greenblatt_skill
        self._damodaran = damodaran_skill
        self._marks = marks_skill
        self._pabrai = pabrai_skill
        self._esg = esg_skill

    def _planned_skill_ids(self, request: AnalyzeRequest) -> list[str]:
        """Liste ordonnée des skills qui s'exécuteront réellement pour cette requête.

        Reflète exactement les conditions d'exécution de stream_company_analysis
        (appartenance au workflow + présence des données + dépendances). Permet
        d'annoncer au client le nombre total d'étapes avant le streaming.
        """
        try:
            allowed: frozenset[str] | None = frozenset(
                s.skill_id for s in _workflow_router.route(request.workflow)
            )
        except ValueError:
            allowed = None

        def _in(skill_id: str) -> bool:
            return allowed is None or skill_id in allowed

        planned: list[str] = []
        if _in("graham_analysis") and request.ratios is not None:
            planned.append("graham_analysis")
        if _in("earnings_quality") and request.earnings_ratios is not None:
            planned.append("earnings_quality")
        if _in("dorsey_moat") and request.dorsey_ratios is not None and self._dorsey is not None:
            planned.append("dorsey_moat")
        if _in("buffett_quality") and request.buffett_ratios is not None and self._buffett is not None:
            planned.append("buffett_quality")
        if (
            _in("stock_valuation_triangulation")
            and request.valuation_ratios is not None
            and self._valuation is not None
        ):
            planned.append("stock_valuation_triangulation")
        thesis_planned = (
            _in("investment_thesis_builder")
            and bool(request.thesis_ratios)
            and self._thesis is not None
        )
        if thesis_planned:
            planned.append("investment_thesis_builder")
        # munger dépend de l'exécution effective de thesis (thesis_output non None)
        if (
            _in("munger_mental_models")
            and bool(request.munger_ratios)
            and self._munger is not None
            and thesis_planned
        ):
            planned.append("munger_mental_models")
        if (
            _in("canadian_tax_considerations")
            and request.tax_input is not None
            and self._canadian_tax is not None
        ):
            planned.append("canadian_tax_considerations")
        if _in("lynch_categories") and request.lynch_ratios is not None and self._lynch is not None:
            planned.append("lynch_categories")
        if _in("fisher_scuttlebutt") and request.fisher_input is not None and self._fisher is not None:
            planned.append("fisher_scuttlebutt")
        if _in("klarman_margin") and request.klarman_input is not None and self._klarman is not None:
            planned.append("klarman_margin")
        if (
            _in("greenblatt_magic_formula")
            and request.greenblatt_input is not None
            and self._greenblatt is not None
        ):
            planned.append("greenblatt_magic_formula")
        if (
            _in("damodaran_narrative")
            and request.damodaran_input is not None
            and self._damodaran is not None
        ):
            planned.append("damodaran_narrative")
        if _in("marks_cycles_risk") and request.marks_input is not None and self._marks is not None:
            planned.append("marks_cycles_risk")
        if _in("pabrai_dhandho") and request.pabrai_input is not None and self._pabrai is not None:
            planned.append("pabrai_dhandho")
        # esg n'est pas filtré par le workflow (cf. stream_company_analysis)
        if request.esg_input is not None and self._esg is not None:
            planned.append("esg_simplified")
        return planned

    async def run_company_analysis(
        self,
        request: AnalyzeRequest,
        cache: AnalysisCacheService | None = None,
        observability: ObservabilityService | None = None,
        composite_history_service: "CompositeHistoryService | None" = None,
        esg_history_service: "EsgHistoryService | None" = None,
    ) -> AnalyzeResponse:
        """
        Exécute le workflow company_analysis.
        Étape 0 : vérifie le cache Redis avant tout appel Claude (si cache fourni).
        Chaque skill n'est appelé que si ses ratios sont fournis (ou flag activé).
        """
        # --- Étape 0 : Cache Redis (circuit court) ---
        if cache is not None:
            cached = await cache.get(request.ticker, request.workflow, request.ratios)
            if cached is not None:
                logger.debug(
                    "Cache hit pour %s/%s — 0 appel Claude", request.ticker, request.workflow
                )
                return cached.model_copy(update={"cost_usd": 0.0})

        # --- Étape 0b : Cache composite_score (circuit court DB) ---
        if composite_history_service is not None:
            try:
                recent = await composite_history_service.get_recent(request.ticker)
            except Exception:
                logger.warning(
                    "Échec vérification cache composite pour %s", request.ticker, exc_info=True
                )
                recent = None
            if recent is not None:
                logger.debug(
                    "Cache composite hit pour %s — score=%.1f label=%s (depuis_cache_composite=True)",
                    request.ticker, recent.score, recent.label,
                )
                return AnalyzeResponse(
                    analysis_id="cached_composite",
                    ticker=request.ticker,
                    workflow=request.workflow,
                    skills_applied=[],
                    cost_usd=0.0,
                    created_at=datetime.now(timezone.utc).isoformat(),
                    composite_score=CompositeScore(
                        score=recent.score,
                        label=recent.label,
                        skills_inclus=[],
                        skills_exclus=[],
                        detail={},
                    ),
                    depuis_cache_composite=True,
                    **_request_ratios_traces(request),
                )

        # Résolution du workflow → ensemble des skills autorisés
        try:
            _steps = _workflow_router.route(request.workflow)
            _allowed: frozenset[str] | None = frozenset(s.skill_id for s in _steps)
        except ValueError:
            logger.warning(
                "Workflow inconnu '%s' — tous les skills activés par défaut", request.workflow
            )
            _allowed = None  # None = pas de filtre (compatibilité descendante)

        skills_applied: list[str] = []
        total_cost = 0.0
        all_usages: list[UsageDetail] = []

        # --- Étape 1 : Graham (si dans le workflow et ratios fournis) ---
        graham_output: GrahamAnalysisOutput | None = None

        if (_allowed is None or "graham_analysis" in _allowed) and request.ratios is not None:
            graham_input = GrahamAnalysisInput(ticker=request.ticker, ratios=request.ratios)
            _t = time.monotonic()
            graham_output, graham_usage = await self._graham.execute(graham_input)
            _elapsed_ms = int((time.monotonic() - _t) * 1000)
            if observability:
                asyncio.create_task(
                    observability.record_skill_execution(SkillTrace(
                        skill_id="graham_analysis",
                        ticker=request.ticker,
                        cost_usd=graham_usage.cost_usd,
                        latency_ms=_elapsed_ms,
                        cache_hit=False,
                        tokens_input=graham_usage.tokens_input,
                        tokens_output=graham_usage.tokens_output,
                        created_at=datetime.now(timezone.utc),
                    ))
                )
            skills_applied.append("graham_analysis")
            total_cost += graham_usage.cost_usd
            all_usages.append(graham_usage)

        # --- Étape 2 : Earnings quality (si dans le workflow et données fournies) ---
        earnings_output: EarningsQualityOutput | None = None

        if (
            (_allowed is None or "earnings_quality" in _allowed)
            and request.earnings_ratios is not None
        ):
            graham_ctx: GrahamContext | None = None
            if graham_output is not None:
                graham_ctx = GrahamContext(
                    verdict=graham_output.verdict,
                    defensive_score=graham_output.defensive_score,
                    marge_securite=graham_output.marge_securite,
                    drapeaux_rouges=graham_output.drapeaux_rouges,
                )
            earnings_input = EarningsQualityInput(
                ticker=request.ticker,
                ratios=request.earnings_ratios,
                graham_context=graham_ctx,
            )
            _t = time.monotonic()
            earnings_output, earnings_usage = await self._earnings.execute(earnings_input)
            _elapsed_ms = int((time.monotonic() - _t) * 1000)
            if observability:
                asyncio.create_task(observability.record_skill_execution(SkillTrace(
                    skill_id="earnings_quality", ticker=request.ticker,
                    cost_usd=earnings_usage.cost_usd, latency_ms=_elapsed_ms, cache_hit=False,
                    tokens_input=earnings_usage.tokens_input, tokens_output=earnings_usage.tokens_output,
                    created_at=datetime.now(timezone.utc),
                )))
            skills_applied.append("earnings_quality")
            total_cost += earnings_usage.cost_usd
            all_usages.append(earnings_usage)

        # --- Étape 3 : Dorsey moat (si dans le workflow et données fournies) ---
        dorsey_output: DorseyMoatOutput | None = None

        if (
            (_allowed is None or "dorsey_moat" in _allowed)
            and request.dorsey_ratios is not None and self._dorsey is not None
        ):
            earnings_ctx: DorseyEarningsContext | None = None
            if earnings_output is not None:
                earnings_ctx = DorseyEarningsContext(
                    verdict=earnings_output.verdict,
                    z_score=earnings_output.z_score.z_score,
                    m_score=earnings_output.m_score.m_score,
                    f_score=earnings_output.f_score.f_score,
                    drapeaux_rouges=earnings_output.drapeaux_rouges,
                )
            dorsey_input = DorseyMoatInput(
                ticker=request.ticker,
                ratios=request.dorsey_ratios,
                earnings_context=earnings_ctx,
            )
            _t = time.monotonic()
            dorsey_output, dorsey_usage = await self._dorsey.execute(dorsey_input)
            _elapsed_ms = int((time.monotonic() - _t) * 1000)
            if observability:
                asyncio.create_task(observability.record_skill_execution(SkillTrace(
                    skill_id="dorsey_moat", ticker=request.ticker,
                    cost_usd=dorsey_usage.cost_usd, latency_ms=_elapsed_ms, cache_hit=False,
                    tokens_input=dorsey_usage.tokens_input, tokens_output=dorsey_usage.tokens_output,
                    created_at=datetime.now(timezone.utc),
                )))
            skills_applied.append("dorsey_moat")
            total_cost += dorsey_usage.cost_usd
            all_usages.append(dorsey_usage)

        # --- Étape 4 : Buffett quality (si dans le workflow et données fournies) ---
        buffett_output: BuffettQualityOutput | None = None

        if (
            (_allowed is None or "buffett_quality" in _allowed)
            and request.buffett_ratios is not None and self._buffett is not None
        ):
            dorsey_ctx: BuffettDorseyContext | None = None
            if dorsey_output is not None:
                dorsey_ctx = BuffettDorseyContext(
                    moat_type=dorsey_output.moat_type,
                    sources=[
                        s.source for s in dorsey_output.sources_identifiees
                        if s.intensite in {"FORTE", "MODÉRÉE"}
                    ],
                    roic_durability=dorsey_output.roic_durability,
                )
            buffett_input = BuffettQualityInput(
                ticker=request.ticker,
                ratios=request.buffett_ratios,
                dorsey_context=dorsey_ctx,
            )
            _t = time.monotonic()
            buffett_output, buffett_usage = await self._buffett.execute(buffett_input)
            _elapsed_ms = int((time.monotonic() - _t) * 1000)
            if observability:
                asyncio.create_task(observability.record_skill_execution(SkillTrace(
                    skill_id="buffett_quality", ticker=request.ticker,
                    cost_usd=buffett_usage.cost_usd, latency_ms=_elapsed_ms, cache_hit=False,
                    tokens_input=buffett_usage.tokens_input, tokens_output=buffett_usage.tokens_output,
                    created_at=datetime.now(timezone.utc),
                )))
            skills_applied.append("buffett_quality")
            total_cost += buffett_usage.cost_usd
            all_usages.append(buffett_usage)

        # --- Étape 5 : Stock valuation triangulation (si dans le workflow et données fournies) ---
        valuation_output: StockValuationOutput | None = None

        if (
            (_allowed is None or "stock_valuation_triangulation" in _allowed)
            and request.valuation_ratios is not None and self._valuation is not None
        ):
            graham_ctx_val: ValuationGrahamContext | None = None
            if graham_output is not None:
                graham_ctx_val = ValuationGrahamContext(
                    verdict=graham_output.verdict,
                    defensive_score=graham_output.defensive_score,
                    marge_securite=graham_output.marge_securite,
                    valeur_intrinseque_simple=graham_output.valeur_intrinseque_simple,
                )
            earnings_ctx_val: ValuationEarningsContext | None = None
            if earnings_output is not None:
                earnings_ctx_val = ValuationEarningsContext(
                    verdict=earnings_output.verdict,
                    z_score=earnings_output.z_score.z_score,
                    f_score=earnings_output.f_score.f_score,
                )
            dorsey_ctx_val: ValuationDorseyContext | None = None
            if dorsey_output is not None:
                dorsey_ctx_val = ValuationDorseyContext(
                    moat_type=dorsey_output.moat_type,
                    roic_durability=dorsey_output.roic_durability,
                )
            buffett_ctx_val: ValuationBuffettContext | None = None
            if buffett_output is not None:
                buffett_ctx_val = ValuationBuffettContext(
                    quality_score=buffett_output.quality_score,
                    verdict=buffett_output.verdict,
                    owner_earnings=buffett_output.owner_earnings,
                )
            valuation_input = StockValuationInput(
                ticker=request.ticker,
                ratios=request.valuation_ratios,
                graham_context=graham_ctx_val,
                earnings_context=earnings_ctx_val,
                dorsey_context=dorsey_ctx_val,
                buffett_context=buffett_ctx_val,
            )
            _t = time.monotonic()
            valuation_output, valuation_usage = await self._valuation.execute(valuation_input)
            _elapsed_ms = int((time.monotonic() - _t) * 1000)
            if observability:
                asyncio.create_task(observability.record_skill_execution(SkillTrace(
                    skill_id="stock_valuation_triangulation", ticker=request.ticker,
                    cost_usd=valuation_usage.cost_usd, latency_ms=_elapsed_ms, cache_hit=False,
                    tokens_input=valuation_usage.tokens_input, tokens_output=valuation_usage.tokens_output,
                    created_at=datetime.now(timezone.utc),
                )))
            skills_applied.append("stock_valuation_triangulation")
            total_cost += valuation_usage.cost_usd
            all_usages.append(valuation_usage)

        # --- Étape 6 : investment_thesis_builder (si dans le workflow et activé) ---
        thesis_output: ThesisBuilderOutput | None = None

        if (
            (_allowed is None or "investment_thesis_builder" in _allowed)
            and request.thesis_ratios and self._thesis is not None
        ):
            all_contexts = AllSkillContexts(
                graham=graham_output,
                earnings_quality=earnings_output,
                dorsey=dorsey_output,
                buffett=buffett_output,
                valuation=valuation_output,
            )
            thesis_input = ThesisBuilderInput(
                ticker=request.ticker,
                all_contexts=all_contexts,
            )
            _t = time.monotonic()
            thesis_output, thesis_usage = await self._thesis.execute(thesis_input)
            _elapsed_ms = int((time.monotonic() - _t) * 1000)
            if observability:
                asyncio.create_task(observability.record_skill_execution(SkillTrace(
                    skill_id="investment_thesis_builder", ticker=request.ticker,
                    cost_usd=thesis_usage.cost_usd, latency_ms=_elapsed_ms, cache_hit=False,
                    tokens_input=thesis_usage.tokens_input, tokens_output=thesis_usage.tokens_output,
                    created_at=datetime.now(timezone.utc),
                )))
            skills_applied.append("investment_thesis_builder")
            total_cost += thesis_usage.cost_usd
            all_usages.append(thesis_usage)

        # --- Étape 7 : munger_mental_models (si dans le workflow et activé) ---
        munger_output: MungerOutput | None = None

        if (
            (_allowed is None or "munger_mental_models" in _allowed)
            and request.munger_ratios and self._munger is not None and thesis_output is not None
        ):
            thesis_ctx = ThesisContext(
                ticker=request.ticker,
                verdict_final=thesis_output.verdict_final,
                position_size_pct=thesis_output.position_size_pct,
                scenario_bull_probabilite=thesis_output.scenario_bull.probabilite,
                scenario_base_probabilite=thesis_output.scenario_base.probabilite,
                scenario_bear_probabilite=thesis_output.scenario_bear.probabilite,
                synthese_narrative=thesis_output.synthese_narrative,
                kill_criteria=thesis_output.kill_criteria,
                devils_advocate=thesis_output.devils_advocate,
            )
            munger_input = MungerInput(ticker=request.ticker, thesis_context=thesis_ctx)
            _t = time.monotonic()
            munger_output, munger_usage = await self._munger.execute(munger_input)
            _elapsed_ms = int((time.monotonic() - _t) * 1000)
            if observability:
                asyncio.create_task(observability.record_skill_execution(SkillTrace(
                    skill_id="munger_mental_models", ticker=request.ticker,
                    cost_usd=munger_usage.cost_usd, latency_ms=_elapsed_ms, cache_hit=False,
                    tokens_input=munger_usage.tokens_input, tokens_output=munger_usage.tokens_output,
                    created_at=datetime.now(timezone.utc),
                )))
            skills_applied.append("munger_mental_models")
            total_cost += munger_usage.cost_usd
            all_usages.append(munger_usage)

        # --- Étape 8 : canadian_tax_considerations (si dans le workflow et tax_input fourni) ---
        tax_output: CanadianTaxOutput | None = None

        if (
            (_allowed is None or "canadian_tax_considerations" in _allowed)
            and request.tax_input is not None and self._canadian_tax is not None
        ):
            _t = time.monotonic()
            tax_output, tax_usage = await self._canadian_tax.execute(request.tax_input)
            _elapsed_ms = int((time.monotonic() - _t) * 1000)
            if observability:
                asyncio.create_task(observability.record_skill_execution(SkillTrace(
                    skill_id="canadian_tax_considerations", ticker=request.ticker,
                    cost_usd=tax_usage.cost_usd, latency_ms=_elapsed_ms, cache_hit=False,
                    tokens_input=tax_usage.tokens_input, tokens_output=tax_usage.tokens_output,
                    created_at=datetime.now(timezone.utc),
                )))
            skills_applied.append("canadian_tax_considerations")
            total_cost += tax_usage.cost_usd
            all_usages.append(tax_usage)

        # --- Étape 9 : lynch_categories (si dans le workflow et lynch_ratios fournis) ---
        lynch_output: LynchOutput | None = None

        if (
            (_allowed is None or "lynch_categories" in _allowed)
            and request.lynch_ratios is not None and self._lynch is not None
        ):
            lynch_input = LynchInput(ticker=request.ticker, ratios=request.lynch_ratios)
            _t = time.monotonic()
            lynch_output, lynch_usage = await self._lynch.execute(lynch_input)
            _elapsed_ms = int((time.monotonic() - _t) * 1000)
            if observability:
                asyncio.create_task(observability.record_skill_execution(SkillTrace(
                    skill_id="lynch_categories", ticker=request.ticker,
                    cost_usd=lynch_usage.cost_usd, latency_ms=_elapsed_ms, cache_hit=False,
                    tokens_input=lynch_usage.tokens_input, tokens_output=lynch_usage.tokens_output,
                    created_at=datetime.now(timezone.utc),
                )))
            skills_applied.append("lynch_categories")
            total_cost += lynch_usage.cost_usd
            all_usages.append(lynch_usage)

        # --- Étape 10 : fisher_scuttlebutt (si dans le workflow et fisher_input fourni) ---
        fisher_output: FisherOutput | None = None

        if (
            (_allowed is None or "fisher_scuttlebutt" in _allowed)
            and request.fisher_input is not None and self._fisher is not None
        ):
            _t = time.monotonic()
            fisher_output, fisher_usage = await self._fisher.execute(request.fisher_input)
            _elapsed_ms = int((time.monotonic() - _t) * 1000)
            if observability:
                asyncio.create_task(observability.record_skill_execution(SkillTrace(
                    skill_id="fisher_scuttlebutt", ticker=request.ticker,
                    cost_usd=fisher_usage.cost_usd, latency_ms=_elapsed_ms, cache_hit=False,
                    tokens_input=fisher_usage.tokens_input, tokens_output=fisher_usage.tokens_output,
                    created_at=datetime.now(timezone.utc),
                )))
            skills_applied.append("fisher_scuttlebutt")
            total_cost += fisher_usage.cost_usd
            all_usages.append(fisher_usage)

        # --- Étape 11 : klarman_margin (si dans le workflow et klarman_input fourni) ---
        klarman_output: KlarmanOutput | None = None

        if (
            (_allowed is None or "klarman_margin" in _allowed)
            and request.klarman_input is not None and self._klarman is not None
        ):
            _t = time.monotonic()
            klarman_output, klarman_usage = await self._klarman.execute(request.klarman_input)
            _elapsed_ms = int((time.monotonic() - _t) * 1000)
            if observability:
                asyncio.create_task(observability.record_skill_execution(SkillTrace(
                    skill_id="klarman_margin", ticker=request.ticker,
                    cost_usd=klarman_usage.cost_usd, latency_ms=_elapsed_ms, cache_hit=False,
                    tokens_input=klarman_usage.tokens_input, tokens_output=klarman_usage.tokens_output,
                    created_at=datetime.now(timezone.utc),
                )))
            skills_applied.append("klarman_margin")
            total_cost += klarman_usage.cost_usd
            all_usages.append(klarman_usage)

        # --- Étape 12 : greenblatt_magic_formula (si dans le workflow et greenblatt_input fourni) ---
        greenblatt_output: GreenblattOutput | None = None

        if (
            (_allowed is None or "greenblatt_magic_formula" in _allowed)
            and request.greenblatt_input is not None and self._greenblatt is not None
        ):
            _t = time.monotonic()
            greenblatt_output, greenblatt_usage = await self._greenblatt.execute(request.greenblatt_input)
            _elapsed_ms = int((time.monotonic() - _t) * 1000)
            if observability:
                asyncio.create_task(observability.record_skill_execution(SkillTrace(
                    skill_id="greenblatt_magic_formula", ticker=request.ticker,
                    cost_usd=greenblatt_usage.cost_usd, latency_ms=_elapsed_ms, cache_hit=False,
                    tokens_input=greenblatt_usage.tokens_input, tokens_output=greenblatt_usage.tokens_output,
                    created_at=datetime.now(timezone.utc),
                )))
            skills_applied.append("greenblatt_magic_formula")
            total_cost += greenblatt_usage.cost_usd
            all_usages.append(greenblatt_usage)

        # --- Étape 13 : damodaran_narrative (si dans le workflow et damodaran_input fourni) ---
        damodaran_output: DamodararOutput | None = None

        if (
            (_allowed is None or "damodaran_narrative" in _allowed)
            and request.damodaran_input is not None and self._damodaran is not None
        ):
            _t = time.monotonic()
            damodaran_output, damodaran_usage = await self._damodaran.execute(request.damodaran_input)
            _elapsed_ms = int((time.monotonic() - _t) * 1000)
            if observability:
                asyncio.create_task(observability.record_skill_execution(SkillTrace(
                    skill_id="damodaran_narrative", ticker=request.ticker,
                    cost_usd=damodaran_usage.cost_usd, latency_ms=_elapsed_ms, cache_hit=False,
                    tokens_input=damodaran_usage.tokens_input, tokens_output=damodaran_usage.tokens_output,
                    created_at=datetime.now(timezone.utc),
                )))
            skills_applied.append("damodaran_narrative")
            total_cost += damodaran_usage.cost_usd
            all_usages.append(damodaran_usage)

        # --- Étape 14 : marks_cycles_risk (si dans le workflow et marks_input fourni) ---
        marks_output: MarksOutput | None = None

        if (
            (_allowed is None or "marks_cycles_risk" in _allowed)
            and request.marks_input is not None and self._marks is not None
        ):
            _t = time.monotonic()
            marks_output, marks_usage = await self._marks.execute(request.marks_input)
            _elapsed_ms = int((time.monotonic() - _t) * 1000)
            if observability:
                asyncio.create_task(observability.record_skill_execution(SkillTrace(
                    skill_id="marks_cycles_risk", ticker=request.ticker,
                    cost_usd=marks_usage.cost_usd, latency_ms=_elapsed_ms, cache_hit=False,
                    tokens_input=marks_usage.tokens_input, tokens_output=marks_usage.tokens_output,
                    created_at=datetime.now(timezone.utc),
                )))
            skills_applied.append("marks_cycles_risk")
            total_cost += marks_usage.cost_usd
            all_usages.append(marks_usage)

        # --- Étape 15 : pabrai_dhandho (si dans le workflow et pabrai_input fourni) ---
        pabrai_output: PabraiOutput | None = None

        if (
            (_allowed is None or "pabrai_dhandho" in _allowed)
            and request.pabrai_input is not None and self._pabrai is not None
        ):
            _t = time.monotonic()
            pabrai_output, pabrai_usage = await self._pabrai.execute(request.pabrai_input)
            _elapsed_ms = int((time.monotonic() - _t) * 1000)
            if observability:
                asyncio.create_task(observability.record_skill_execution(SkillTrace(
                    skill_id="pabrai_dhandho", ticker=request.ticker,
                    cost_usd=pabrai_usage.cost_usd, latency_ms=_elapsed_ms, cache_hit=False,
                    tokens_input=pabrai_usage.tokens_input, tokens_output=pabrai_usage.tokens_output,
                    created_at=datetime.now(timezone.utc),
                )))
            skills_applied.append("pabrai_dhandho")
            total_cost += pabrai_usage.cost_usd
            all_usages.append(pabrai_usage)

        # --- Étape 16 : esg_simplified (si esg_input fourni) ---
        esg_output: EsgOutput | None = None

        if request.esg_input is not None and self._esg is not None:
            _t = time.monotonic()
            esg_output, esg_usage = await self._esg.execute(request.esg_input)
            _elapsed_ms = int((time.monotonic() - _t) * 1000)
            if observability:
                asyncio.create_task(observability.record_skill_execution(SkillTrace(
                    skill_id="esg_simplified", ticker=request.ticker,
                    cost_usd=esg_usage.cost_usd, latency_ms=_elapsed_ms, cache_hit=False,
                    tokens_input=esg_usage.tokens_input, tokens_output=esg_usage.tokens_output,
                    created_at=datetime.now(timezone.utc),
                )))
            skills_applied.append("esg_simplified")
            total_cost += esg_usage.cost_usd
            all_usages.append(esg_usage)

            # Sprint 89 — persiste le score ESG dans esg_score_history (best-effort)
            if esg_history_service is not None:
                try:
                    await esg_history_service.record(
                        ticker=request.ticker,
                        score=float(esg_output.esg_score),
                    )
                except Exception:
                    logger.warning(
                        "Échec enregistrement esg_score_history pour %s",
                        request.ticker, exc_info=True,
                    )

        analysis_id = await self._persist(
            request, graham_output, earnings_output, dorsey_output, buffett_output,
            valuation_output, thesis_output, munger_output, tax_output,
            lynch_output, fisher_output, klarman_output,
            greenblatt_output, damodaran_output, marks_output, pabrai_output,
            all_usages, esg_output=esg_output,
        )

        inter_skill_conflicts = _detect_inter_skill_conflicts(
            graham_output, buffett_output, earnings_output, dorsey_output
        )

        composite = compute_composite_score(
            graham_verdict=graham_output.defensive_verdict if graham_output else None,
            graham_confidence=graham_output.confidence_score if graham_output else 0.0,
            buffett_verdict=buffett_output.verdict if buffett_output else None,
            buffett_confidence=buffett_output.confidence_score if buffett_output else 0.0,
            valuation_verdict=valuation_output.verdict if valuation_output else None,
            valuation_confidence=getattr(valuation_output, "confidence_score", 0.0) if valuation_output else 0.0,
            moat_type=dorsey_output.moat_type if dorsey_output else None,
            moat_confidence=dorsey_output.confidence_score if dorsey_output else 0.0,
            earnings_verdict=earnings_output.verdict if earnings_output else None,
            earnings_confidence=earnings_output.confidence_score if earnings_output else 0.0,
            marks_signal=marks_output.recommandation_timing if marks_output else None,
            marks_confidence=1.0,
        )

        if composite is not None and composite_history_service is not None:
            try:
                await composite_history_service.record(
                    ticker=request.ticker,
                    score=composite.score,
                    label=composite.label,
                    workflow=request.workflow,
                )
            except Exception:
                logger.warning("Échec enregistrement composite_score_history pour %s", request.ticker, exc_info=True)

        response = AnalyzeResponse(
            analysis_id=str(analysis_id),
            ticker=request.ticker,
            workflow=request.workflow,
            skills_applied=skills_applied,
            graham=graham_output,
            earnings_quality=earnings_output,
            dorsey=dorsey_output,
            buffett=buffett_output,
            valuation=valuation_output,
            thesis=thesis_output,
            munger=munger_output,
            canadian_tax=tax_output,
            lynch=lynch_output,
            fisher=fisher_output,
            klarman=klarman_output,
            greenblatt=greenblatt_output,
            damodaran=damodaran_output,
            marks=marks_output,
            pabrai=pabrai_output,
            esg=esg_output,
            cost_usd=total_cost,
            created_at=datetime.now(timezone.utc).isoformat(),
            inter_skill_conflicts=inter_skill_conflicts,
            composite_score=composite,
            **_request_ratios_traces(request),
        )

        # --- Étape finale : mise en cache pour les prochains appels ---
        if cache is not None:
            await cache.set(request.ticker, request.workflow, request.ratios, response)

        return response

    async def stream_company_analysis(
        self,
        request: AnalyzeRequest,
        cache: AnalysisCacheService | None = None,
        observability: ObservabilityService | None = None,
        composite_history_service: "CompositeHistoryService | None" = None,
        esg_history_service: "EsgHistoryService | None" = None,
    ) -> AsyncGenerator[dict, None]:
        """
        Version streaming de run_company_analysis.
        Yield des events SSE (dict {event, data}) après chaque skill complété.

        Events émis :
        - {"event": "plan", "data": {"skills": list[str]}}  # skills qui vont s'exécuter
        - {"event": "skill_start", "data": {"skill_id": str}}
        - {"event": "skill_result", "data": {"skill_id": str, "result": dict}}
        - {"event": "complete", "data": AnalyzeResponse.model_dump()}
        - {"event": "cached", "data": AnalyzeResponse.model_dump()}
        - {"event": "error", "data": {"message": str}}
        """
        # --- Étape 0 : Cache Redis (circuit court) ---
        if cache is not None:
            cached = await cache.get(request.ticker, request.workflow, request.ratios)
            if cached is not None:
                logger.debug(
                    "Cache hit (stream) pour %s/%s", request.ticker, request.workflow
                )
                yield {"event": "cached", "data": cached.model_copy(update={"cost_usd": 0.0}).model_dump()}
                return

        # --- Étape 0b : Cache composite_score (circuit court DB) ---
        if composite_history_service is not None:
            try:
                recent = await composite_history_service.get_recent(request.ticker)
            except Exception:
                logger.warning(
                    "Échec vérification cache composite (stream) pour %s", request.ticker, exc_info=True
                )
                recent = None
            if recent is not None:
                logger.debug(
                    "Cache composite hit (stream) pour %s — score=%.1f label=%s",
                    request.ticker, recent.score, recent.label,
                )
                cached_response = AnalyzeResponse(
                    analysis_id="cached_composite",
                    ticker=request.ticker,
                    workflow=request.workflow,
                    skills_applied=[],
                    cost_usd=0.0,
                    created_at=datetime.now(timezone.utc).isoformat(),
                    composite_score=CompositeScore(
                        score=recent.score,
                        label=recent.label,
                        skills_inclus=[],
                        skills_exclus=[],
                        detail={},
                    ),
                    depuis_cache_composite=True,
                    **_request_ratios_traces(request),
                )
                yield {"event": "cached", "data": cached_response.model_dump()}
                return

        try:
            _steps = _workflow_router.route(request.workflow)
            _allowed: frozenset[str] | None = frozenset(s.skill_id for s in _steps)
        except ValueError:
            logger.warning(
                "Workflow inconnu '%s' (stream) — tous les skills activés", request.workflow
            )
            _allowed = None

        # Annonce la liste ordonnée des skills qui vont s'exécuter (barre de progression client)
        yield {"event": "plan", "data": {"skills": self._planned_skill_ids(request)}}

        skills_applied: list[str] = []
        total_cost = 0.0
        all_usages: list[UsageDetail] = []

        graham_output: GrahamAnalysisOutput | None = None
        if (_allowed is None or "graham_analysis" in _allowed) and request.ratios is not None:
            yield {"event": "skill_start", "data": {"skill_id": "graham_analysis"}}
            graham_input = GrahamAnalysisInput(ticker=request.ticker, ratios=request.ratios)
            _t = time.monotonic()
            graham_output, graham_usage = await self._graham.execute(graham_input)
            _elapsed_ms = int((time.monotonic() - _t) * 1000)
            if observability:
                asyncio.create_task(observability.record_skill_execution(SkillTrace(
                    skill_id="graham_analysis", ticker=request.ticker,
                    cost_usd=graham_usage.cost_usd, latency_ms=_elapsed_ms, cache_hit=False,
                    tokens_input=graham_usage.tokens_input, tokens_output=graham_usage.tokens_output,
                    created_at=datetime.now(timezone.utc),
                )))
            skills_applied.append("graham_analysis")
            total_cost += graham_usage.cost_usd
            all_usages.append(graham_usage)
            yield {"event": "skill_result", "data": {"skill_id": "graham_analysis", "result": graham_output.model_dump()}}

        earnings_output: EarningsQualityOutput | None = None
        if (
            (_allowed is None or "earnings_quality" in _allowed)
            and request.earnings_ratios is not None
        ):
            yield {"event": "skill_start", "data": {"skill_id": "earnings_quality"}}
            graham_ctx: GrahamContext | None = None
            if graham_output is not None:
                graham_ctx = GrahamContext(
                    verdict=graham_output.verdict,
                    defensive_score=graham_output.defensive_score,
                    marge_securite=graham_output.marge_securite,
                    drapeaux_rouges=graham_output.drapeaux_rouges,
                )
            earnings_input = EarningsQualityInput(
                ticker=request.ticker, ratios=request.earnings_ratios, graham_context=graham_ctx,
            )
            _t = time.monotonic()
            earnings_output, earnings_usage = await self._earnings.execute(earnings_input)
            _elapsed_ms = int((time.monotonic() - _t) * 1000)
            if observability:
                asyncio.create_task(observability.record_skill_execution(SkillTrace(
                    skill_id="earnings_quality", ticker=request.ticker,
                    cost_usd=earnings_usage.cost_usd, latency_ms=_elapsed_ms, cache_hit=False,
                    tokens_input=earnings_usage.tokens_input, tokens_output=earnings_usage.tokens_output,
                    created_at=datetime.now(timezone.utc),
                )))
            skills_applied.append("earnings_quality")
            total_cost += earnings_usage.cost_usd
            all_usages.append(earnings_usage)
            yield {"event": "skill_result", "data": {"skill_id": "earnings_quality", "result": earnings_output.model_dump()}}

        dorsey_output: DorseyMoatOutput | None = None
        if (
            (_allowed is None or "dorsey_moat" in _allowed)
            and request.dorsey_ratios is not None and self._dorsey is not None
        ):
            yield {"event": "skill_start", "data": {"skill_id": "dorsey_moat"}}
            earnings_ctx: DorseyEarningsContext | None = None
            if earnings_output is not None:
                earnings_ctx = DorseyEarningsContext(
                    verdict=earnings_output.verdict,
                    z_score=earnings_output.z_score.z_score,
                    m_score=earnings_output.m_score.m_score,
                    f_score=earnings_output.f_score.f_score,
                    drapeaux_rouges=earnings_output.drapeaux_rouges,
                )
            dorsey_input = DorseyMoatInput(
                ticker=request.ticker, ratios=request.dorsey_ratios, earnings_context=earnings_ctx,
            )
            _t = time.monotonic()
            dorsey_output, dorsey_usage = await self._dorsey.execute(dorsey_input)
            _elapsed_ms = int((time.monotonic() - _t) * 1000)
            if observability:
                asyncio.create_task(observability.record_skill_execution(SkillTrace(
                    skill_id="dorsey_moat", ticker=request.ticker,
                    cost_usd=dorsey_usage.cost_usd, latency_ms=_elapsed_ms, cache_hit=False,
                    tokens_input=dorsey_usage.tokens_input, tokens_output=dorsey_usage.tokens_output,
                    created_at=datetime.now(timezone.utc),
                )))
            skills_applied.append("dorsey_moat")
            total_cost += dorsey_usage.cost_usd
            all_usages.append(dorsey_usage)
            yield {"event": "skill_result", "data": {"skill_id": "dorsey_moat", "result": dorsey_output.model_dump()}}

        buffett_output: BuffettQualityOutput | None = None
        if (
            (_allowed is None or "buffett_quality" in _allowed)
            and request.buffett_ratios is not None and self._buffett is not None
        ):
            yield {"event": "skill_start", "data": {"skill_id": "buffett_quality"}}
            dorsey_ctx: BuffettDorseyContext | None = None
            if dorsey_output is not None:
                dorsey_ctx = BuffettDorseyContext(
                    moat_type=dorsey_output.moat_type,
                    sources=[s.source for s in dorsey_output.sources_identifiees if s.intensite in {"FORTE", "MODÉRÉE"}],
                    roic_durability=dorsey_output.roic_durability,
                )
            buffett_input = BuffettQualityInput(
                ticker=request.ticker, ratios=request.buffett_ratios, dorsey_context=dorsey_ctx,
            )
            _t = time.monotonic()
            buffett_output, buffett_usage = await self._buffett.execute(buffett_input)
            _elapsed_ms = int((time.monotonic() - _t) * 1000)
            if observability:
                asyncio.create_task(observability.record_skill_execution(SkillTrace(
                    skill_id="buffett_quality", ticker=request.ticker,
                    cost_usd=buffett_usage.cost_usd, latency_ms=_elapsed_ms, cache_hit=False,
                    tokens_input=buffett_usage.tokens_input, tokens_output=buffett_usage.tokens_output,
                    created_at=datetime.now(timezone.utc),
                )))
            skills_applied.append("buffett_quality")
            total_cost += buffett_usage.cost_usd
            all_usages.append(buffett_usage)
            yield {"event": "skill_result", "data": {"skill_id": "buffett_quality", "result": buffett_output.model_dump()}}

        valuation_output: StockValuationOutput | None = None
        if (
            (_allowed is None or "stock_valuation_triangulation" in _allowed)
            and request.valuation_ratios is not None and self._valuation is not None
        ):
            yield {"event": "skill_start", "data": {"skill_id": "stock_valuation_triangulation"}}
            graham_ctx_val: ValuationGrahamContext | None = None
            if graham_output is not None:
                graham_ctx_val = ValuationGrahamContext(
                    verdict=graham_output.verdict, defensive_score=graham_output.defensive_score,
                    marge_securite=graham_output.marge_securite,
                    valeur_intrinseque_simple=graham_output.valeur_intrinseque_simple,
                )
            earnings_ctx_val: ValuationEarningsContext | None = None
            if earnings_output is not None:
                earnings_ctx_val = ValuationEarningsContext(
                    verdict=earnings_output.verdict,
                    z_score=earnings_output.z_score.z_score,
                    f_score=earnings_output.f_score.f_score,
                )
            dorsey_ctx_val: ValuationDorseyContext | None = None
            if dorsey_output is not None:
                dorsey_ctx_val = ValuationDorseyContext(
                    moat_type=dorsey_output.moat_type, roic_durability=dorsey_output.roic_durability,
                )
            buffett_ctx_val: ValuationBuffettContext | None = None
            if buffett_output is not None:
                buffett_ctx_val = ValuationBuffettContext(
                    quality_score=buffett_output.quality_score,
                    verdict=buffett_output.verdict,
                    owner_earnings=buffett_output.owner_earnings,
                )
            valuation_input = StockValuationInput(
                ticker=request.ticker, ratios=request.valuation_ratios,
                graham_context=graham_ctx_val, earnings_context=earnings_ctx_val,
                dorsey_context=dorsey_ctx_val, buffett_context=buffett_ctx_val,
            )
            _t = time.monotonic()
            valuation_output, valuation_usage = await self._valuation.execute(valuation_input)
            _elapsed_ms = int((time.monotonic() - _t) * 1000)
            if observability:
                asyncio.create_task(observability.record_skill_execution(SkillTrace(
                    skill_id="stock_valuation_triangulation", ticker=request.ticker,
                    cost_usd=valuation_usage.cost_usd, latency_ms=_elapsed_ms, cache_hit=False,
                    tokens_input=valuation_usage.tokens_input, tokens_output=valuation_usage.tokens_output,
                    created_at=datetime.now(timezone.utc),
                )))
            skills_applied.append("stock_valuation_triangulation")
            total_cost += valuation_usage.cost_usd
            all_usages.append(valuation_usage)
            yield {"event": "skill_result", "data": {"skill_id": "stock_valuation_triangulation", "result": valuation_output.model_dump()}}

        thesis_output: ThesisBuilderOutput | None = None
        if (
            (_allowed is None or "investment_thesis_builder" in _allowed)
            and request.thesis_ratios and self._thesis is not None
        ):
            yield {"event": "skill_start", "data": {"skill_id": "investment_thesis_builder"}}
            all_contexts = AllSkillContexts(
                graham=graham_output, earnings_quality=earnings_output,
                dorsey=dorsey_output, buffett=buffett_output, valuation=valuation_output,
            )
            thesis_input = ThesisBuilderInput(ticker=request.ticker, all_contexts=all_contexts)
            _t = time.monotonic()
            thesis_output, thesis_usage = await self._thesis.execute(thesis_input)
            _elapsed_ms = int((time.monotonic() - _t) * 1000)
            if observability:
                asyncio.create_task(observability.record_skill_execution(SkillTrace(
                    skill_id="investment_thesis_builder", ticker=request.ticker,
                    cost_usd=thesis_usage.cost_usd, latency_ms=_elapsed_ms, cache_hit=False,
                    tokens_input=thesis_usage.tokens_input, tokens_output=thesis_usage.tokens_output,
                    created_at=datetime.now(timezone.utc),
                )))
            skills_applied.append("investment_thesis_builder")
            total_cost += thesis_usage.cost_usd
            all_usages.append(thesis_usage)
            yield {"event": "skill_result", "data": {"skill_id": "investment_thesis_builder", "result": thesis_output.model_dump()}}

        munger_output: MungerOutput | None = None
        if (
            (_allowed is None or "munger_mental_models" in _allowed)
            and request.munger_ratios and self._munger is not None and thesis_output is not None
        ):
            yield {"event": "skill_start", "data": {"skill_id": "munger_mental_models"}}
            thesis_ctx = ThesisContext(
                ticker=request.ticker, verdict_final=thesis_output.verdict_final,
                position_size_pct=thesis_output.position_size_pct,
                scenario_bull_probabilite=thesis_output.scenario_bull.probabilite,
                scenario_base_probabilite=thesis_output.scenario_base.probabilite,
                scenario_bear_probabilite=thesis_output.scenario_bear.probabilite,
                synthese_narrative=thesis_output.synthese_narrative,
                kill_criteria=thesis_output.kill_criteria,
                devils_advocate=thesis_output.devils_advocate,
            )
            munger_input = MungerInput(ticker=request.ticker, thesis_context=thesis_ctx)
            _t = time.monotonic()
            munger_output, munger_usage = await self._munger.execute(munger_input)
            _elapsed_ms = int((time.monotonic() - _t) * 1000)
            if observability:
                asyncio.create_task(observability.record_skill_execution(SkillTrace(
                    skill_id="munger_mental_models", ticker=request.ticker,
                    cost_usd=munger_usage.cost_usd, latency_ms=_elapsed_ms, cache_hit=False,
                    tokens_input=munger_usage.tokens_input, tokens_output=munger_usage.tokens_output,
                    created_at=datetime.now(timezone.utc),
                )))
            skills_applied.append("munger_mental_models")
            total_cost += munger_usage.cost_usd
            all_usages.append(munger_usage)
            yield {"event": "skill_result", "data": {"skill_id": "munger_mental_models", "result": munger_output.model_dump()}}

        tax_output: CanadianTaxOutput | None = None
        if (
            (_allowed is None or "canadian_tax_considerations" in _allowed)
            and request.tax_input is not None and self._canadian_tax is not None
        ):
            yield {"event": "skill_start", "data": {"skill_id": "canadian_tax_considerations"}}
            _t = time.monotonic()
            tax_output, tax_usage = await self._canadian_tax.execute(request.tax_input)
            _elapsed_ms = int((time.monotonic() - _t) * 1000)
            if observability:
                asyncio.create_task(observability.record_skill_execution(SkillTrace(
                    skill_id="canadian_tax_considerations", ticker=request.ticker,
                    cost_usd=tax_usage.cost_usd, latency_ms=_elapsed_ms, cache_hit=False,
                    tokens_input=tax_usage.tokens_input, tokens_output=tax_usage.tokens_output,
                    created_at=datetime.now(timezone.utc),
                )))
            skills_applied.append("canadian_tax_considerations")
            total_cost += tax_usage.cost_usd
            all_usages.append(tax_usage)
            yield {"event": "skill_result", "data": {"skill_id": "canadian_tax_considerations", "result": tax_output.model_dump()}}

        lynch_output: LynchOutput | None = None
        if (
            (_allowed is None or "lynch_categories" in _allowed)
            and request.lynch_ratios is not None and self._lynch is not None
        ):
            yield {"event": "skill_start", "data": {"skill_id": "lynch_categories"}}
            lynch_input = LynchInput(ticker=request.ticker, ratios=request.lynch_ratios)
            _t = time.monotonic()
            lynch_output, lynch_usage = await self._lynch.execute(lynch_input)
            _elapsed_ms = int((time.monotonic() - _t) * 1000)
            if observability:
                asyncio.create_task(observability.record_skill_execution(SkillTrace(
                    skill_id="lynch_categories", ticker=request.ticker,
                    cost_usd=lynch_usage.cost_usd, latency_ms=_elapsed_ms, cache_hit=False,
                    tokens_input=lynch_usage.tokens_input, tokens_output=lynch_usage.tokens_output,
                    created_at=datetime.now(timezone.utc),
                )))
            skills_applied.append("lynch_categories")
            total_cost += lynch_usage.cost_usd
            all_usages.append(lynch_usage)
            yield {"event": "skill_result", "data": {"skill_id": "lynch_categories", "result": lynch_output.model_dump()}}

        fisher_output: FisherOutput | None = None
        if (
            (_allowed is None or "fisher_scuttlebutt" in _allowed)
            and request.fisher_input is not None and self._fisher is not None
        ):
            yield {"event": "skill_start", "data": {"skill_id": "fisher_scuttlebutt"}}
            _t = time.monotonic()
            fisher_output, fisher_usage = await self._fisher.execute(request.fisher_input)
            _elapsed_ms = int((time.monotonic() - _t) * 1000)
            if observability:
                asyncio.create_task(observability.record_skill_execution(SkillTrace(
                    skill_id="fisher_scuttlebutt", ticker=request.ticker,
                    cost_usd=fisher_usage.cost_usd, latency_ms=_elapsed_ms, cache_hit=False,
                    tokens_input=fisher_usage.tokens_input, tokens_output=fisher_usage.tokens_output,
                    created_at=datetime.now(timezone.utc),
                )))
            skills_applied.append("fisher_scuttlebutt")
            total_cost += fisher_usage.cost_usd
            all_usages.append(fisher_usage)
            yield {"event": "skill_result", "data": {"skill_id": "fisher_scuttlebutt", "result": fisher_output.model_dump()}}

        klarman_output: KlarmanOutput | None = None
        if (
            (_allowed is None or "klarman_margin" in _allowed)
            and request.klarman_input is not None and self._klarman is not None
        ):
            yield {"event": "skill_start", "data": {"skill_id": "klarman_margin"}}
            _t = time.monotonic()
            klarman_output, klarman_usage = await self._klarman.execute(request.klarman_input)
            _elapsed_ms = int((time.monotonic() - _t) * 1000)
            if observability:
                asyncio.create_task(observability.record_skill_execution(SkillTrace(
                    skill_id="klarman_margin", ticker=request.ticker,
                    cost_usd=klarman_usage.cost_usd, latency_ms=_elapsed_ms, cache_hit=False,
                    tokens_input=klarman_usage.tokens_input, tokens_output=klarman_usage.tokens_output,
                    created_at=datetime.now(timezone.utc),
                )))
            skills_applied.append("klarman_margin")
            total_cost += klarman_usage.cost_usd
            all_usages.append(klarman_usage)
            yield {"event": "skill_result", "data": {"skill_id": "klarman_margin", "result": klarman_output.model_dump()}}

        greenblatt_output: GreenblattOutput | None = None
        if (
            (_allowed is None or "greenblatt_magic_formula" in _allowed)
            and request.greenblatt_input is not None and self._greenblatt is not None
        ):
            yield {"event": "skill_start", "data": {"skill_id": "greenblatt_magic_formula"}}
            _t = time.monotonic()
            greenblatt_output, greenblatt_usage = await self._greenblatt.execute(request.greenblatt_input)
            _elapsed_ms = int((time.monotonic() - _t) * 1000)
            if observability:
                asyncio.create_task(observability.record_skill_execution(SkillTrace(
                    skill_id="greenblatt_magic_formula", ticker=request.ticker,
                    cost_usd=greenblatt_usage.cost_usd, latency_ms=_elapsed_ms, cache_hit=False,
                    tokens_input=greenblatt_usage.tokens_input, tokens_output=greenblatt_usage.tokens_output,
                    created_at=datetime.now(timezone.utc),
                )))
            skills_applied.append("greenblatt_magic_formula")
            total_cost += greenblatt_usage.cost_usd
            all_usages.append(greenblatt_usage)
            yield {"event": "skill_result", "data": {"skill_id": "greenblatt_magic_formula", "result": greenblatt_output.model_dump()}}

        damodaran_output: DamodararOutput | None = None
        if (
            (_allowed is None or "damodaran_narrative" in _allowed)
            and request.damodaran_input is not None and self._damodaran is not None
        ):
            yield {"event": "skill_start", "data": {"skill_id": "damodaran_narrative"}}
            _t = time.monotonic()
            damodaran_output, damodaran_usage = await self._damodaran.execute(request.damodaran_input)
            _elapsed_ms = int((time.monotonic() - _t) * 1000)
            if observability:
                asyncio.create_task(observability.record_skill_execution(SkillTrace(
                    skill_id="damodaran_narrative", ticker=request.ticker,
                    cost_usd=damodaran_usage.cost_usd, latency_ms=_elapsed_ms, cache_hit=False,
                    tokens_input=damodaran_usage.tokens_input, tokens_output=damodaran_usage.tokens_output,
                    created_at=datetime.now(timezone.utc),
                )))
            skills_applied.append("damodaran_narrative")
            total_cost += damodaran_usage.cost_usd
            all_usages.append(damodaran_usage)
            yield {"event": "skill_result", "data": {"skill_id": "damodaran_narrative", "result": damodaran_output.model_dump()}}

        marks_output: MarksOutput | None = None
        if (
            (_allowed is None or "marks_cycles_risk" in _allowed)
            and request.marks_input is not None and self._marks is not None
        ):
            yield {"event": "skill_start", "data": {"skill_id": "marks_cycles_risk"}}
            _t = time.monotonic()
            marks_output, marks_usage = await self._marks.execute(request.marks_input)
            _elapsed_ms = int((time.monotonic() - _t) * 1000)
            if observability:
                asyncio.create_task(observability.record_skill_execution(SkillTrace(
                    skill_id="marks_cycles_risk", ticker=request.ticker,
                    cost_usd=marks_usage.cost_usd, latency_ms=_elapsed_ms, cache_hit=False,
                    tokens_input=marks_usage.tokens_input, tokens_output=marks_usage.tokens_output,
                    created_at=datetime.now(timezone.utc),
                )))
            skills_applied.append("marks_cycles_risk")
            total_cost += marks_usage.cost_usd
            all_usages.append(marks_usage)
            yield {"event": "skill_result", "data": {"skill_id": "marks_cycles_risk", "result": marks_output.model_dump()}}

        pabrai_output: PabraiOutput | None = None
        if (
            (_allowed is None or "pabrai_dhandho" in _allowed)
            and request.pabrai_input is not None and self._pabrai is not None
        ):
            yield {"event": "skill_start", "data": {"skill_id": "pabrai_dhandho"}}
            _t = time.monotonic()
            pabrai_output, pabrai_usage = await self._pabrai.execute(request.pabrai_input)
            _elapsed_ms = int((time.monotonic() - _t) * 1000)
            if observability:
                asyncio.create_task(observability.record_skill_execution(SkillTrace(
                    skill_id="pabrai_dhandho", ticker=request.ticker,
                    cost_usd=pabrai_usage.cost_usd, latency_ms=_elapsed_ms, cache_hit=False,
                    tokens_input=pabrai_usage.tokens_input, tokens_output=pabrai_usage.tokens_output,
                    created_at=datetime.now(timezone.utc),
                )))
            skills_applied.append("pabrai_dhandho")
            total_cost += pabrai_usage.cost_usd
            all_usages.append(pabrai_usage)
            yield {"event": "skill_result", "data": {"skill_id": "pabrai_dhandho", "result": pabrai_output.model_dump()}}

        esg_output: EsgOutput | None = None
        if request.esg_input is not None and self._esg is not None:
            yield {"event": "skill_start", "data": {"skill_id": "esg_simplified"}}
            _t = time.monotonic()
            esg_output, esg_usage = await self._esg.execute(request.esg_input)
            _elapsed_ms = int((time.monotonic() - _t) * 1000)
            if observability:
                asyncio.create_task(observability.record_skill_execution(SkillTrace(
                    skill_id="esg_simplified", ticker=request.ticker,
                    cost_usd=esg_usage.cost_usd, latency_ms=_elapsed_ms, cache_hit=False,
                    tokens_input=esg_usage.tokens_input, tokens_output=esg_usage.tokens_output,
                    created_at=datetime.now(timezone.utc),
                )))
            skills_applied.append("esg_simplified")
            total_cost += esg_usage.cost_usd
            all_usages.append(esg_usage)
            yield {"event": "skill_result", "data": {"skill_id": "esg_simplified", "result": esg_output.model_dump()}}

            # Sprint 89 — persiste le score ESG (best-effort) en mode stream
            if esg_history_service is not None:
                try:
                    await esg_history_service.record(
                        ticker=request.ticker,
                        score=float(esg_output.esg_score),
                    )
                except Exception:
                    logger.warning(
                        "Échec enregistrement esg_score_history (stream) pour %s",
                        request.ticker, exc_info=True,
                    )

        analysis_id = await self._persist(
            request, graham_output, earnings_output, dorsey_output, buffett_output,
            valuation_output, thesis_output, munger_output, tax_output,
            lynch_output, fisher_output, klarman_output,
            greenblatt_output, damodaran_output, marks_output, pabrai_output,
            all_usages, esg_output=esg_output,
        )

        inter_skill_conflicts = _detect_inter_skill_conflicts(
            graham_output, buffett_output, earnings_output, dorsey_output
        )

        composite = compute_composite_score(
            graham_verdict=graham_output.defensive_verdict if graham_output else None,
            graham_confidence=graham_output.confidence_score if graham_output else 0.0,
            buffett_verdict=buffett_output.verdict if buffett_output else None,
            buffett_confidence=buffett_output.confidence_score if buffett_output else 0.0,
            valuation_verdict=valuation_output.verdict if valuation_output else None,
            valuation_confidence=getattr(valuation_output, "confidence_score", 0.0) if valuation_output else 0.0,
            moat_type=dorsey_output.moat_type if dorsey_output else None,
            moat_confidence=dorsey_output.confidence_score if dorsey_output else 0.0,
            earnings_verdict=earnings_output.verdict if earnings_output else None,
            earnings_confidence=earnings_output.confidence_score if earnings_output else 0.0,
            marks_signal=marks_output.recommandation_timing if marks_output else None,
            marks_confidence=1.0,
        )

        if composite is not None and composite_history_service is not None:
            try:
                await composite_history_service.record(
                    ticker=request.ticker,
                    score=composite.score,
                    label=composite.label,
                    workflow=request.workflow,
                )
            except Exception:
                logger.warning("Échec enregistrement composite_score_history (stream) pour %s", request.ticker, exc_info=True)

        response = AnalyzeResponse(
            analysis_id=str(analysis_id),
            ticker=request.ticker,
            workflow=request.workflow,
            skills_applied=skills_applied,
            graham=graham_output,
            earnings_quality=earnings_output,
            dorsey=dorsey_output,
            buffett=buffett_output,
            valuation=valuation_output,
            thesis=thesis_output,
            munger=munger_output,
            canadian_tax=tax_output,
            lynch=lynch_output,
            fisher=fisher_output,
            klarman=klarman_output,
            greenblatt=greenblatt_output,
            damodaran=damodaran_output,
            marks=marks_output,
            pabrai=pabrai_output,
            esg=esg_output,
            cost_usd=total_cost,
            created_at=datetime.now(timezone.utc).isoformat(),
            inter_skill_conflicts=inter_skill_conflicts,
            composite_score=composite,
            **_request_ratios_traces(request),
        )

        if cache is not None:
            await cache.set(request.ticker, request.workflow, request.ratios, response)

        yield {"event": "complete", "data": response.model_dump()}

    async def _persist(
        self,
        request: AnalyzeRequest,
        graham_output: GrahamAnalysisOutput | None,
        earnings_output: EarningsQualityOutput | None,
        dorsey_output: DorseyMoatOutput | None,
        buffett_output: BuffettQualityOutput | None,
        valuation_output: StockValuationOutput | None,
        thesis_output: ThesisBuilderOutput | None,
        munger_output: MungerOutput | None,
        tax_output: CanadianTaxOutput | None,
        lynch_output: LynchOutput | None,
        fisher_output: FisherOutput | None,
        klarman_output: KlarmanOutput | None,
        greenblatt_output: GreenblattOutput | None,
        damodaran_output: DamodararOutput | None,
        marks_output: MarksOutput | None,
        pabrai_output: PabraiOutput | None,
        usages: list[UsageDetail],
        esg_output: EsgOutput | None = None,
    ) -> str:
        """Insère l'analyse agrégée dans analysis_history et retourne l'UUID généré."""
        skills_list: list[str] = []
        if graham_output:
            skills_list.append("graham_analysis")
        if earnings_output:
            skills_list.append("earnings_quality")
        if dorsey_output:
            skills_list.append("dorsey_moat")
        if buffett_output:
            skills_list.append("buffett_quality")
        if valuation_output:
            skills_list.append("stock_valuation_triangulation")
        if thesis_output:
            skills_list.append("investment_thesis_builder")
        if munger_output:
            skills_list.append("munger_mental_models")
        if tax_output:
            skills_list.append("canadian_tax_considerations")
        if lynch_output:
            skills_list.append("lynch_categories")
        if fisher_output:
            skills_list.append("fisher_scuttlebutt")
        if klarman_output:
            skills_list.append("klarman_margin")
        if greenblatt_output:
            skills_list.append("greenblatt_magic_formula")
        if damodaran_output:
            skills_list.append("damodaran_narrative")
        if marks_output:
            skills_list.append("marks_cycles_risk")
        if pabrai_output:
            skills_list.append("pabrai_dhandho")
        if esg_output:
            skills_list.append("esg_simplified")
        skills_used = _json.dumps(skills_list)

        input_data = _build_input_data(request)

        result_dict: dict = {}
        if graham_output:
            result_dict["graham"] = graham_output.model_dump()
        if earnings_output:
            result_dict["earnings_quality"] = earnings_output.model_dump()
        if dorsey_output:
            result_dict["dorsey_moat"] = dorsey_output.model_dump()
        if buffett_output:
            result_dict["buffett_quality"] = buffett_output.model_dump()
        if valuation_output:
            result_dict["stock_valuation"] = valuation_output.model_dump()
        if thesis_output:
            result_dict["investment_thesis_builder"] = thesis_output.model_dump()
        if munger_output:
            result_dict["munger_mental_models"] = munger_output.model_dump()
        if tax_output:
            result_dict["canadian_tax_considerations"] = tax_output.model_dump()
        if lynch_output:
            result_dict["lynch_categories"] = lynch_output.model_dump()
        if fisher_output:
            result_dict["fisher_scuttlebutt"] = fisher_output.model_dump()
        if klarman_output:
            result_dict["klarman_margin"] = klarman_output.model_dump()
        if greenblatt_output:
            result_dict["greenblatt_magic_formula"] = greenblatt_output.model_dump()
        if damodaran_output:
            result_dict["damodaran_narrative"] = damodaran_output.model_dump()
        if marks_output:
            result_dict["marks_cycles_risk"] = marks_output.model_dump()
        if pabrai_output:
            result_dict["pabrai_dhandho"] = pabrai_output.model_dump()
        if esg_output:
            result_dict["esg_simplified"] = esg_output.model_dump()
        result = _json.dumps(result_dict)

        total_cost = sum(u.cost_usd for u in usages)
        total_tokens_input = sum(u.tokens_input for u in usages)
        total_tokens_output = sum(u.tokens_output for u in usages)
        total_tokens_cache_r = sum(u.tokens_cache_read for u in usages)
        total_tokens_cache_c = sum(u.tokens_cache_creation for u in usages)

        price_at_analysis: float | None = request.ratios.price if request.ratios is not None else None

        row = await self._db.fetchrow(
            """
            INSERT INTO analysis_history (
                ticker, workflow_name, skills_used, input_data, result,
                cost_usd, tokens_input, tokens_output,
                tokens_cache_read, tokens_cache_creation, price_at_analysis
            )
            VALUES ($1, $2, $3::jsonb, $4::jsonb, $5::jsonb, $6, $7, $8, $9, $10, $11)
            RETURNING id
            """,
            request.ticker,
            request.workflow,
            skills_used,
            input_data,
            result,
            total_cost,
            total_tokens_input,
            total_tokens_output,
            total_tokens_cache_r,
            total_tokens_cache_c,
            price_at_analysis,
        )

        return str(row["id"])

    async def get_metrics(self, days: int = 30) -> MetricsResponse:
        """Agrège les métriques depuis analysis_history sur la période demandée."""
        global_row = await self._db.fetchrow(
            """
            SELECT
                COUNT(*)                                                    AS total,
                COALESCE(SUM(cost_usd), 0)                                  AS total_cost,
                COALESCE(AVG(
                    CASE
                        WHEN tokens_input + tokens_cache_read + tokens_cache_creation > 0
                        THEN tokens_cache_read::float
                             / (tokens_input + tokens_cache_read + tokens_cache_creation)
                        ELSE 0
                    END
                ), 0)                                                        AS avg_cache_hit
            FROM analysis_history
            WHERE created_at >= NOW() - ($1 || ' days')::interval
            """,
            str(days),
        )

        ticker_rows = await self._db.fetch(
            """
            SELECT ticker, COUNT(*) AS nb, SUM(cost_usd) AS total_cost
            FROM analysis_history
            WHERE created_at >= NOW() - ($1 || ' days')::interval
            GROUP BY ticker
            ORDER BY total_cost DESC
            LIMIT 20
            """,
            str(days),
        )

        skill_rows = await self._db.fetch(
            """
            SELECT skill,
                   COUNT(*) AS nb,
                   COALESCE(
                       SUM(cost_usd / NULLIF(jsonb_array_length(skills_used), 0)), 0
                   ) AS cost
            FROM analysis_history,
                 jsonb_array_elements_text(skills_used) AS skill
            WHERE created_at >= NOW() - ($1 || ' days')::interval
            GROUP BY skill
            ORDER BY nb DESC
            """,
            str(days),
        )

        workflow_rows = await self._db.fetch(
            """
            SELECT
                workflow_name,
                COALESCE(AVG(
                    CASE
                        WHEN tokens_input + tokens_cache_read + tokens_cache_creation > 0
                        THEN tokens_cache_read::float
                             / (tokens_input + tokens_cache_read + tokens_cache_creation)
                        ELSE 0
                    END
                ), 0) AS cache_ratio
            FROM analysis_history
            WHERE created_at >= NOW() - ($1 || ' days')::interval
            GROUP BY workflow_name
            ORDER BY workflow_name
            """,
            str(days),
        )

        daily_rows = await self._db.fetch(
            """
            SELECT to_char(date_trunc('day', created_at), 'YYYY-MM-DD') AS day,
                   COALESCE(SUM(cost_usd), 0)                            AS cost
            FROM analysis_history
            WHERE created_at >= NOW() - ($1 || ' days')::interval
            GROUP BY day
            ORDER BY day
            """,
            str(days),
        )

        total = int(global_row["total"])
        total_cost = float(global_row["total_cost"])

        return MetricsResponse(
            period_days=days,
            total_analyses=total,
            total_cost_usd=round(total_cost, 6),
            avg_cost_per_analysis=round(total_cost / total, 6) if total > 0 else 0.0,
            cache_hit_ratio_avg=round(float(global_row["avg_cache_hit"]), 4),
            top_tickers=[
                TickerMetrics(
                    ticker=row["ticker"],
                    analyses=int(row["nb"]),
                    cost_usd=round(float(row["total_cost"]), 6),
                )
                for row in ticker_rows
            ],
            skills_usage={row["skill"]: int(row["nb"]) for row in skill_rows},
            skills_cost={
                row["skill"]: round(float(row["cost"]), 6) for row in skill_rows
            },
            cache_by_workflow={
                row["workflow_name"]: round(float(row["cache_ratio"]), 4)
                for row in workflow_rows
            },
            daily_cost={
                row["day"]: round(float(row["cost"]), 6) for row in daily_rows
            },
        )

    async def get_skill_analyses(
        self, skill: str, days: int = 30, limit: int = 100
    ) -> SkillAnalysesResponse:
        """Liste les analyses ayant utilisé `skill` sur la période (drill-down Sprint 112)."""
        rows = await self._db.fetch(
            """
            SELECT id, ticker, workflow_name, cost_usd, created_at
            FROM analysis_history
            WHERE created_at >= NOW() - ($1 || ' days')::interval
              AND skills_used @> $2::jsonb
            ORDER BY created_at DESC
            LIMIT $3
            """,
            str(days),
            _json.dumps([skill]),
            limit,
        )
        return SkillAnalysesResponse(
            skill=skill,
            period_days=days,
            entries=[
                SkillAnalysisEntry(
                    analysis_id=str(row["id"]),
                    ticker=row["ticker"],
                    workflow_name=row["workflow_name"],
                    cost_usd=round(float(row["cost_usd"]), 6),
                    created_at=row["created_at"].isoformat(),
                )
                for row in rows
            ],
        )

    async def get_history(
        self,
        ticker: str | None = None,
        q: str | None = None,
        limit: int = 10,
        before: datetime | None = None,
        from_dt: datetime | None = None,
        to_dt: datetime | None = None,
        tags: list[str] | None = None,
    ) -> HistoryResponse:
        """
        Retourne les analyses passées, triées par date décroissante.
        ticker  : filtre exact (obligatoire si q absent).
        q       : filtre full-text ILIKE sur ticker, workflow et verdicts JSONB.
        from_dt : borne inférieure incluse sur created_at (ISO 8601).
        to_dt   : borne supérieure incluse sur created_at (ISO 8601).
        tags    : ne garde que les analyses dont l'annotation porte TOUS ces tags (`@>`).
        Utilise un cursor sur created_at pour la pagination stable.
        """
        rows = await self._db.fetch(
            """
            SELECT h.id, h.ticker, h.workflow_name, h.skills_used, h.cost_usd,
                   h.result, h.created_at, a.tags
            FROM analysis_history h
            LEFT JOIN annotations a ON a.analysis_id = h.id
            WHERE ($1::text IS NULL OR h.ticker = $1)
              AND ($2::text IS NULL OR (
                    h.ticker        ILIKE '%' || $2 || '%'
                 OR h.workflow_name ILIKE '%' || $2 || '%'
                 OR (h.result->>'graham')          ILIKE '%' || $2 || '%'
                 OR (h.result->>'earnings_quality') ILIKE '%' || $2 || '%'
              ))
              AND ($3::timestamptz IS NULL OR h.created_at < $3)
              AND ($5::timestamptz IS NULL OR h.created_at >= $5)
              AND ($6::timestamptz IS NULL OR h.created_at <= $6)
              AND ($7::text[] IS NULL OR a.tags @> $7::text[])
            ORDER BY h.created_at DESC
            LIMIT $4
            """,
            ticker,
            q,
            before,
            limit + 1,
            from_dt,
            to_dt,
            tags,
        )

        has_more = len(rows) > limit
        rows = rows[:limit]

        entries = [_row_to_history_entry(row) for row in rows]

        next_before = entries[-1].created_at if has_more and entries else None

        return HistoryResponse(ticker=ticker, entries=entries, next_before=next_before)


    async def get_history_paged(
        self,
        ticker: str | None = None,
        q: str | None = None,
        page: int = 1,
        page_size: int = 10,
        from_dt: "datetime | None" = None,
        to_dt: "datetime | None" = None,
        fast_count: bool = False,
        tags: list[str] | None = None,
    ) -> "PagedHistoryResponse":
        """
        Pagination offset/limit avec total_count (Sprint 90).
        Execute deux requetes en parallele : SELECT LIMIT/OFFSET et SELECT COUNT(*).
        fast_count=True : estimation rapide via pg_class.reltuples (sans filtre uniquement).
        tags : ne garde que les analyses dont l'annotation porte TOUS ces tags (`@>`).
        """
        offset = (page - 1) * page_size

        async def _fetch_rows():
            return await self._db.fetch(
                """
                SELECT h.id, h.ticker, h.workflow_name, h.skills_used, h.cost_usd,
                       h.result, h.created_at, a.tags
                FROM analysis_history h
                LEFT JOIN annotations a ON a.analysis_id = h.id
                WHERE ($1::text IS NULL OR h.ticker = $1)
                  AND ($2::text IS NULL OR (
                        h.ticker        ILIKE '%' || $2 || '%'
                     OR h.workflow_name ILIKE '%' || $2 || '%'
                     OR (h.result->>'graham')          ILIKE '%' || $2 || '%'
                     OR (h.result->>'earnings_quality') ILIKE '%' || $2 || '%'
                  ))
                  AND ($3::timestamptz IS NULL OR h.created_at >= $3)
                  AND ($4::timestamptz IS NULL OR h.created_at <= $4)
                  AND ($7::text[] IS NULL OR a.tags @> $7::text[])
                ORDER BY h.created_at DESC
                LIMIT $5 OFFSET $6
                """,
                ticker, q, from_dt, to_dt, page_size, offset, tags,
            )

        async def _fetch_count():
            # fast_count uniquement sans filtre : pg_class donne un total global, pas filtré
            if fast_count and not any([ticker, q, from_dt, to_dt, tags]):
                return await self._db.fetchval(
                    "SELECT reltuples::bigint FROM pg_class WHERE relname = 'analysis_history'"
                )
            return await self._db.fetchval(
                """
                SELECT COUNT(*)
                FROM analysis_history h
                LEFT JOIN annotations a ON a.analysis_id = h.id
                WHERE ($1::text IS NULL OR h.ticker = $1)
                  AND ($2::text IS NULL OR (
                        h.ticker        ILIKE '%' || $2 || '%'
                     OR h.workflow_name ILIKE '%' || $2 || '%'
                     OR (h.result->>'graham')          ILIKE '%' || $2 || '%'
                     OR (h.result->>'earnings_quality') ILIKE '%' || $2 || '%'
                  ))
                  AND ($3::timestamptz IS NULL OR h.created_at >= $3)
                  AND ($4::timestamptz IS NULL OR h.created_at <= $4)
                  AND ($5::text[] IS NULL OR a.tags @> $5::text[])
                """,
                ticker, q, from_dt, to_dt, tags,
            )

        rows, total_count = await asyncio.gather(_fetch_rows(), _fetch_count())
        total_count = int(total_count or 0)

        entries = [_row_to_history_entry(row) for row in rows]

        total_pages = max(1, (total_count + page_size - 1) // page_size) if total_count > 0 else 1

        return PagedHistoryResponse(
            ticker=ticker,
            q=q,
            entries=entries,
            page=page,
            page_size=page_size,
            total_count=total_count,
            total_pages=total_pages,
        )

    async def delete_analysis(self, analysis_id: str) -> bool:
        """Supprime une analyse et son annotation éventuelle ; retourne True si trouvée."""
        try:
            # Supprime l'annotation orpheline — pas de FK cascade sur cette table
            await self._db.execute(
                "DELETE FROM annotations WHERE analysis_id = $1::uuid",
                analysis_id,
            )
            result = await self._db.execute(
                "DELETE FROM analysis_history WHERE id = $1::uuid",
                analysis_id,
            )
        except asyncpg.exceptions.InvalidTextRepresentationError:
            return False
        return result == "DELETE 1"
