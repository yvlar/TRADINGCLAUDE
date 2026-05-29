from __future__ import annotations

import logging

from fastapi import APIRouter, Request
from pydantic import BaseModel, Field, model_validator

from app.services.screener import ScreenerService
from app.skills.tier2.graham_analysis.schemas import GrahamRatios
from app.utils.error_sanitization import sanitized_http_500
from app.utils.ticker_sanitizer import sanitize_ticker

logger = logging.getLogger(__name__)

router = APIRouter()


class ScreenRequest(BaseModel):
    """Corps de la requête POST /screen."""

    tickers: list[str]
    workflow: str = "value_graham"
    ratios_map: dict[str, GrahamRatios] | None = None
    max_parallel: int = Field(default=5, ge=1, le=10)
    # Filtres post-analyse Sprint 58 — appliqués en AND, tickers en échec toujours inclus
    composite_label: str | None = None          # "FORT" | "MODERE" | "FAIBLE"
    min_composite_score: float | None = None    # exclut score < seuil
    filter_workflow: str | None = None          # filtre sur workflow_utilise

    @model_validator(mode="after")
    def validate_tickers(self) -> ScreenRequest:
        if not self.tickers:
            raise ValueError("Au moins un ticker requis")
        if len(self.tickers) > 20:
            raise ValueError("Maximum 20 tickers par appel")
        self.tickers = [sanitize_ticker(t) for t in self.tickers]
        return self


class ScreenEntry(BaseModel):
    """Résultat d'analyse pour un ticker individuel."""

    ticker: str
    defensive_score: int | None
    verdict: str | None
    composite_score: float | None = None
    composite_label: str | None = None
    workflow_utilise: str
    cost_usd: float
    depuis_cache: bool = False
    # Date ISO 8601 de l'analyse sous-jacente — issue du cache ou de l'analyse fraîche.
    # None pour les tickers en échec. Sert d'indicateur de fraîcheur côté frontend.
    analyzed_at: str | None = None
    erreur: str | None


class ScreenResult(BaseModel):
    """Résultat agrégé du screener multi-tickers."""

    tickers_analyses: int
    tickers_echec: int
    tickers_depuis_cache: int
    cout_total_usd: float
    resultats: list[ScreenEntry]
    workflow: str
    duration_ms: int


@router.post(
    "/screen",
    response_model=ScreenResult,
    summary="Screener multi-tickers",
    description=(
        "Analyse une liste de tickers en parallèle via le workflow sélectionné. "
        "Les résultats sont triés par defensive_score décroissant (échecs en bas). "
        "Supporte ratios_map pour surcharger l'auto-extraction Yahoo Finance. "
        "Maximum 20 tickers par appel, timeout global 120s."
    ),
)
async def screen(request: Request, body: ScreenRequest) -> ScreenResult:
    """Lance le screener sur la liste de tickers fournie."""
    screener: ScreenerService = request.app.state.screener
    try:
        return await screener.screen(body)
    except Exception as exc:
        raise sanitized_http_500(exc, logger, f"Erreur screener sur {body.tickers}") from exc


@router.delete(
    "/cache/{ticker}",
    summary="Invalider le cache d'un ticker (admin)",
    description="Supprime toutes les entrées de cache Redis pour ce ticker. Requiert Bearer auth.",
)
async def invalidate_cache(request: Request, ticker: str) -> dict[str, int]:
    """Supprime toutes les entrées cache du ticker et retourne le nombre supprimé."""
    cache = getattr(request.app.state, "analysis_cache", None)
    if cache is None:
        return {"supprimees": 0}
    count = await cache.invalidate(ticker.upper())
    return {"supprimees": count}
