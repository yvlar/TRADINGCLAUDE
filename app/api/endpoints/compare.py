from __future__ import annotations

import logging

from fastapi import APIRouter, Request
from pydantic import BaseModel, model_validator

from app.services.compare_service import CompareResponse, CompareService
from app.utils.error_sanitization import sanitized_http_500
from app.utils.ticker_sanitizer import sanitize_ticker

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/compare", tags=["compare"])


class CompareRequest(BaseModel):
    """Corps de la requête POST /compare."""

    tickers: list[str]

    @model_validator(mode="after")
    def validate_tickers(self) -> CompareRequest:
        if len(self.tickers) < 2:
            raise ValueError("Au moins 2 tickers requis")
        if len(self.tickers) > 5:
            raise ValueError("Maximum 5 tickers par comparaison")
        self.tickers = [sanitize_ticker(t) for t in self.tickers]
        return self


@router.post(
    "",
    response_model=CompareResponse,
    summary="Comparer les dernières analyses de plusieurs tickers",
    description=(
        "Retourne la dernière analyse historique pour 2 à 5 tickers côte à côte. "
        "Aucun appel Claude — données historiques uniquement. "
        "Un ticker absent de l'historique retourne une entrée avec des champs null."
    ),
)
async def compare(request: Request, body: CompareRequest) -> CompareResponse:
    """Retourne les comparaisons sans appel Claude."""
    service: CompareService = request.app.state.compare_service
    try:
        return await service.compare(body.tickers)
    except Exception as exc:
        raise sanitized_http_500(
            exc, logger, f"Erreur lors de la comparaison {body.tickers}"
        ) from exc
