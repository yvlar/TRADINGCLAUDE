from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel

from app.orchestrator.core import AnalyzeRequest, AnalyzeResponse, Orchestrator
from app.skills.tier1.base import FinancialDataProvider
from app.skills.tier2.earnings_quality.schemas import EarningsQualityRatios
from app.skills.tier2.graham_analysis.schemas import GrahamRatios
from app.utils.error_sanitization import sanitized_http_500

logger = logging.getLogger(__name__)

router = APIRouter(tags=["extract"])


class ExtractResponse(BaseModel):
    """Ratios extraits automatiquement depuis Yahoo Finance."""

    graham: GrahamRatios
    earnings_quality: EarningsQualityRatios | None = None


def get_yahoo_extractor(request: Request) -> FinancialDataProvider:
    return request.app.state.yahoo_extractor


@router.get(
    "/extract",
    response_model=ExtractResponse,
    summary="Extrait les ratios depuis Yahoo Finance (Graham + Qualité bénéfices)",
)
async def extract_ratios(
    ticker: str,
    yahoo_extractor: FinancialDataProvider = Depends(get_yahoo_extractor),
) -> ExtractResponse:
    """
    Extrait automatiquement les ratios Graham et (si disponibles) les données
    pour le skill earnings_quality depuis Yahoo Finance.
    Retourne 404 si le ticker est inconnu ou si les données Graham sont insuffisantes.
    earnings_quality peut être null si les états financiers détaillés ne sont pas disponibles.
    """
    graham = await yahoo_extractor.extract(ticker)
    earnings_quality = await yahoo_extractor.extract_earnings_quality(ticker)
    return ExtractResponse(graham=graham, earnings_quality=earnings_quality)


@router.post(
    "/analyze-auto",
    response_model=AnalyzeResponse,
    summary="Extraction automatique + analyse complète",
)
async def analyze_auto(
    ticker: str,
    request: Request,
    yahoo_extractor: FinancialDataProvider = Depends(get_yahoo_extractor),
) -> AnalyzeResponse:
    """
    Extrait automatiquement les ratios (Yahoo Finance) puis lance le workflow analyze complet.
    Équivalent à GET /extract suivi de POST /analyze avec les ratios extraits.
    Retourne 404 si le ticker est inconnu.
    """
    ratios = await yahoo_extractor.extract(ticker)
    analyze_request = AnalyzeRequest(ticker=ticker, ratios=ratios)
    orchestrator: Orchestrator = request.app.state.orchestrator
    try:
        return await orchestrator.run_company_analysis(analyze_request)
    except Exception as exc:
        raise sanitized_http_500(exc, logger, f"Erreur lors de analyze-auto pour {ticker}") from exc
