from __future__ import annotations

import json
import logging
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, ClassVar

import anthropic
from pydantic import ValidationError

from app.rag.service import RagService
from app.services.financial_calculations import (
    AltmanComponents,
    BeneishComponents,
    MontierSignal,
    PiotroskiCriterion,
    _montier_interpretation,
    _piotroski_interpretation,
    _sloan_interpretation,
    altman_z_score_detail,
    beneish_m_score_detail,
    montier_c_signaux,
    piotroski_f_criteria,
    sloan_accrual_ratio,
)
from app.skills.base import Citation, SkillBase, SkillConfig, UsageDetail
from app.utils.costs import calculate_cost
from app.utils.retry import call_claude_with_retry
from app.utils.tool_schema import build_tool_schema

from .schemas import EarningsQualityInput, EarningsQualityOutput, EarningsQualityRatios

logger = logging.getLogger(__name__)

# Schéma dérivé de Pydantic — confidence_score (computed) et champs post-assignés exclus.
# Les scores numériques restent dans le schéma (le LLM les peuple) mais sont écrasés
# post-parse par les valeurs Python déterministes (Sprint 128).
_EARNINGS_TOOL_SCHEMA = build_tool_schema(
    EarningsQualityOutput,
    exclude={"confidence_score", "citations", "cost_usd"},
)


@dataclass(frozen=True)
class _ScoresDeterministes:
    """Scores + sous-composantes calculés en Python — autorité sur les valeurs du LLM.

    `m` et `z` portent les intermédiaires (8 indices Beneish, termes X1-X5 Altman)
    substitués post-parse au même titre que les scores agrégés (Sprint 131).
    `f_criteria`/`c_signaux` portent le détail par signal F/C, substitué de même
    (Sprint 142) ; None dans les mêmes cas que le score agrégé correspondant.
    `f_interpretation`/`c_interpretation` portent le libellé au niveau cadre dérivé
    du score agrégé déterministe (Sprint 143, parité M/Z) ; None quand le score l'est.
    `sloan_interpretation` est le libellé du ratio d'accruals dérivé de `accrual_ratio`
    (Sprint 148, parité M/Z/F/C) ; toujours une str (None → "DONNEES_MANQUANTES").
    """

    m: BeneishComponents
    z: AltmanComponents
    f_score: int | None
    c_score: int | None
    accrual_ratio: float | None
    f_criteria: list[PiotroskiCriterion] | None
    c_signaux: list[MontierSignal] | None
    f_interpretation: str | None
    c_interpretation: str | None
    sloan_interpretation: str


def _scores_depuis_ratios(
    ratios: EarningsQualityRatios, is_financial: bool
) -> _ScoresDeterministes:
    """Mappe EarningsQualityRatios → les cinq scores déterministes (financial_calculations)."""
    f_criteria = piotroski_f_criteria(
        net_income_t=ratios.net_income_t,
        total_assets_t=ratios.total_assets_t,
        total_assets_t1=ratios.total_assets_t1,
        net_income_t1=ratios.net_income_t1,
        cfo_t=ratios.cfo_t,
        ltd_t=ratios.ltd_t,
        ltd_t1=ratios.ltd_t1,
        current_assets_t=ratios.current_assets_t,
        current_liabilities_t=ratios.current_liabilities_t,
        current_assets_t1=ratios.current_assets_t1,
        current_liabilities_t1=ratios.current_liabilities_t1,
        sales_t=ratios.sales_t,
        sales_t1=ratios.sales_t1,
        cogs_t=ratios.cogs_t,
        cogs_t1=ratios.cogs_t1,
        shares_issued_net=ratios.shares_issued_net,
        is_financial=is_financial,
    )
    c_signaux = montier_c_signaux(
        net_income_t=ratios.net_income_t,
        cfo_t=ratios.cfo_t,
        net_income_t1=ratios.net_income_t1,
        cfo_t1=ratios.cfo_t1,
        receivables_t=ratios.receivables_t,
        receivables_t1=ratios.receivables_t1,
        sales_t=ratios.sales_t,
        sales_t1=ratios.sales_t1,
        inventory_t=ratios.inventory_t,
        inventory_t1=ratios.inventory_t1,
        cogs_t=ratios.cogs_t,
        cogs_t1=ratios.cogs_t1,
        depreciation_t=ratios.depreciation_t,
        depreciation_t1=ratios.depreciation_t1,
        ppe_gross_t=ratios.ppe_gross_t,
        ppe_gross_t1=ratios.ppe_gross_t1,
        total_assets_t=ratios.total_assets_t,
        total_assets_t1=ratios.total_assets_t1,
    )
    # Score agrégé dérivé une fois (source unique) → l'interprétation cadre s'en déduit.
    f_score = None if f_criteria is None else sum(1 for c in f_criteria if c.passe)
    c_score = None if c_signaux is None else sum(1 for s in c_signaux if s.present)
    # accrual_ratio dérivé une fois (source unique) → l'interprétation Sloan s'en déduit.
    accrual_ratio = sloan_accrual_ratio(
        net_income_t=ratios.net_income_t,
        cfo_t=ratios.cfo_t,
        total_assets_t=ratios.total_assets_t,
        total_assets_t1=ratios.total_assets_t1,
    )
    return _ScoresDeterministes(
        m=beneish_m_score_detail(
            receivables_t=ratios.receivables_t,
            receivables_t1=ratios.receivables_t1,
            sales_t=ratios.sales_t,
            sales_t1=ratios.sales_t1,
            cogs_t=ratios.cogs_t,
            cogs_t1=ratios.cogs_t1,
            current_assets_t=ratios.current_assets_t,
            current_assets_t1=ratios.current_assets_t1,
            ppe_net_t=ratios.ppe_net_t,
            ppe_net_t1=ratios.ppe_net_t1,
            total_assets_t=ratios.total_assets_t,
            total_assets_t1=ratios.total_assets_t1,
            depreciation_t=ratios.depreciation_t,
            depreciation_t1=ratios.depreciation_t1,
            sga_t=ratios.sga_t,
            sga_t1=ratios.sga_t1,
            net_income_t=ratios.net_income_t,
            cfo_t=ratios.cfo_t,
            ltd_t=ratios.ltd_t,
            ltd_t1=ratios.ltd_t1,
            current_liabilities_t=ratios.current_liabilities_t,
            current_liabilities_t1=ratios.current_liabilities_t1,
            is_financial=is_financial,
        ),
        z=altman_z_score_detail(
            current_assets=ratios.current_assets_t,
            current_liabilities=ratios.current_liabilities_t,
            retained_earnings=ratios.retained_earnings_t,
            ebit=ratios.ebit_t,
            total_assets=ratios.total_assets_t,
            total_liabilities=ratios.total_liabilities_t,
            sales=ratios.sales_t,
            market_value_equity=ratios.market_cap_t,
            book_value_equity=ratios.book_equity_t,
            variant="original",
            is_financial=is_financial,
        ),
        f_score=f_score,
        c_score=c_score,
        accrual_ratio=accrual_ratio,
        f_criteria=f_criteria,
        c_signaux=c_signaux,
        f_interpretation=None if f_score is None else _piotroski_interpretation(f_score),
        c_interpretation=None if c_score is None else _montier_interpretation(c_score),
        sloan_interpretation=_sloan_interpretation(accrual_ratio),
    )


def _fmt(valeur: float | int | None) -> str:
    """Rend un score pour le prompt — DONNÉES_MANQUANTES si non calculable."""
    if valeur is None:
        return "DONNÉES_MANQUANTES"
    return f"{valeur:.3f}" if isinstance(valeur, float) else str(valeur)


def _injecter_scores(data: dict[str, Any], scores: _ScoresDeterministes) -> None:
    """
    Écrase les scores numériques ET leurs sous-composantes du bloc LLM par les valeurs
    Python (Sprint 128 pour les scores agrégés, Sprint 131 pour les indices/termes,
    Sprint 142 pour les critères F / signaux C détaillés, Sprint 143 pour les libellés
    d'interprétation au niveau cadre F/C — parité avec M/Z déjà déterministes).
    Les champs entiers (f/c_score) n'acceptent pas None — si le calcul Python échoue
    (donnée manquante / financière), la valeur LLM est conservée pour respecter le schéma.
    """
    # Les champs des dataclasses (8 indices + m_score ; x1-x5 + variante + z_score) sont
    # nommés exactement comme ceux de MScoreDetail/ZScoreDetail → asdict() les substitue en
    # bloc. `interpretation` est désormais lui aussi déterministe (dérivé du score Python +
    # is_financial) et écrase le libellé du LLM — élimine la dérive de vocabulaire (golden).
    data.setdefault("m_score", {}).update(asdict(scores.m))
    data.setdefault("z_score", {}).update(asdict(scores.z))
    # accrual_ratio (nullable) ET son interprétation (toujours str) substitués sans gate :
    # _sloan_interpretation rend "DONNEES_MANQUANTES" si l'accrual est None (Sprint 148,
    # parité M/Z/F/C — élimine la dérive de vocabulaire du libellé LLM).
    bloc_sloan = data.setdefault("sloan", {})
    bloc_sloan["accrual_ratio"] = scores.accrual_ratio
    bloc_sloan["interpretation"] = scores.sloan_interpretation
    # f_score/f_criteria (resp. c_score/c_signaux) sont None ensemble : sous le gate
    # non-None, l'entier et la liste détaillée sont cohérents (sum(passe) == f_score).
    # PiotroskiCriterion/MontierSignal sont nommés comme FScoreCriterion/CScoreSignal
    # → asdict() produit des dicts directement validables.
    # `interpretation` est dérivée du score agrégé déterministe → écrase le libellé LLM
    # (élimine la dérive de vocabulaire, comme pour M/Z). Sous le gate non-None, le score
    # est garanti non-None donc l'interprétation l'est aussi (schéma exige str non-None).
    if scores.f_criteria is not None:
        bloc_f = data.setdefault("f_score", {})
        bloc_f["f_score"] = scores.f_score
        bloc_f["criteria"] = [asdict(c) for c in scores.f_criteria]
        bloc_f["interpretation"] = scores.f_interpretation
    if scores.c_signaux is not None:
        bloc_c = data.setdefault("c_score", {})
        bloc_c["c_score"] = scores.c_score
        bloc_c["signaux"] = [asdict(s) for s in scores.c_signaux]
        bloc_c["interpretation"] = scores.c_interpretation


def _str_vers_liste(valeur: str) -> list[str]:
    """Convertit une chaîne (idéalement une liste JSON) en list[str] de façon défensive.

    Haiku émet parfois `drapeaux_rouges` comme chaîne JSON ; on récupère le cas propre,
    sinon on isole le premier fragment lisible (le reste, corrompu, sera régénéré au retry).
    """
    texte = valeur.strip()
    if not texte:
        return []
    try:
        parsed = json.loads(texte)
    except (json.JSONDecodeError, ValueError):
        for ligne in texte.splitlines():
            fragment = ligne.strip().strip(' []",').strip()
            if fragment:
                return [fragment]
        return []
    if isinstance(parsed, list):
        return [str(x).strip() for x in parsed if str(x).strip()]
    texte_parsed = str(parsed).strip()
    return [texte_parsed] if texte_parsed else []


def _coerce_payload_llm(data: dict[str, Any]) -> None:
    """Normalise les formes malformées récurrentes de Haiku avant validation Pydantic.

    `drapeaux_rouges` / `recommandation_prochaine_etape` sont parfois émis en chaîne plutôt
    qu'en liste (cas COIN) — on les recoerce pour éviter un ValidationError évitable. Un champ
    structurellement absent (ex : `verdict` avalé par une sortie tronquée) n'est pas inventé :
    il déclenche le retry côté execute().
    """
    dr = data.get("drapeaux_rouges")
    if isinstance(dr, str):
        data["drapeaux_rouges"] = _str_vers_liste(dr)
    elif dr is None:
        data["drapeaux_rouges"] = []

    reco = data.get("recommandation_prochaine_etape")
    if isinstance(reco, str):
        data["recommandation_prochaine_etape"] = _str_vers_liste(reco)


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
        )

        # Scores calculés en Python (déterministes) — le LLM les interprète, ne les recalcule pas.
        # is_financial=False ici car le secteur n'est connu qu'après l'appel ; le gate sectoriel
        # définitif (M/Z/F → None pour une financière) est appliqué post-parse dans execute().
        scores = _scores_depuis_ratios(input_data.ratios, is_financial=False)
        parts.append(
            "## Scores déterministes (calculés en Python — interprète-les, ne les recalcule pas)\n"
            f"- M-Score (Beneish) : {_fmt(scores.m.m_score)}\n"
            f"- Z-Score (Altman, {scores.z.variante}) : {_fmt(scores.z.z_score)}\n"
            f"- F-Score (Piotroski) : {_fmt(scores.f_score)}\n"
            f"- C-Score (Montier) : {_fmt(scores.c_score)}\n"
            f"- Accruals (Sloan) : {_fmt(scores.accrual_ratio)}\n"
            "Ces valeurs (et leurs sous-composantes : indices du M-Score, termes X1-X5 du "
            "Z-Score) font autorité et remplaceront les tiennes ; concentre-toi sur "
            "l'interprétation, les drapeaux rouges et le verdict.\n\n"
        )

        parts.append("Retourne l'analyse structurée via l'outil earnings_quality_output.")

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

        # Une réponse Haiku malformée (drapeaux_rouges en chaîne, verdict avalé par une sortie
        # tronquée) ne doit pas faire échouer toute l'analyse : la coercion déterministe rattrape
        # le cas récupérable, sinon on régénère une fois. Les deux appels sont facturés.
        cout_cumule = 0.0
        derniere_erreur: ValidationError | None = None
        output: EarningsQualityOutput | None = None

        for tentative in range(2):
            t0 = time.perf_counter()
            response = await call_claude_with_retry(
                self._client,
                timeout_s=self._config.timeout_s,
                max_retries=self._config.max_retries,
                model=self._model,
                system=self.get_system_prompt(),
                messages=[{"role": "user", "content": user_message}],
                max_tokens=4096,
                tools=[
                    {"name": "earnings_quality_output", "input_schema": _EARNINGS_TOOL_SCHEMA}
                ],
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

            cout_cumule += calculate_cost(response.usage, self._model)

            data = dict(tool_use_block.input)
            data["citations"] = []
            _coerce_payload_llm(data)
            # Substitution déterministe (Sprint 128) : les scores Python priment sur le bloc LLM.
            # Le gate sectoriel utilise le drapeau is_financial classé par le LLM (M/Z/F → None
            # pour une financière, conformément aux références excluant banques/assureurs/REIT).
            is_financial = bool(data.get("is_financial", False))
            _injecter_scores(data, _scores_depuis_ratios(input_data.ratios, is_financial))

            try:
                output = EarningsQualityOutput.model_validate(data)
                break
            except ValidationError as exc:
                derniere_erreur = exc
                logger.warning(
                    "sortie earnings invalide — nouvelle tentative",
                    extra={
                        "skill_id": self.skill_id,
                        "ticker": input_data.ticker,
                        "tentative": tentative + 1,
                        "erreur": str(exc)[:300],
                    },
                )

        if output is None:
            raise ValueError(
                f"Sortie earnings_quality invalide après 2 tentatives "
                f"(ticker={input_data.ticker})"
            ) from derniere_erreur

        cost_usd = cout_cumule

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
