from __future__ import annotations

import logging

from app.skills.tier1.base import FinancialDataProvider
from app.skills.tier2.earnings_quality.schemas import EarningsQualityRatios
from app.skills.tier2.graham_analysis.schemas import GrahamRatios
from app.skills.tier2.stock_valuation.schemas import ValuationRatios

logger = logging.getLogger(__name__)


class FallbackDataProvider(FinancialDataProvider):
    """
    Compose un fournisseur primaire et un repli (cf. FinancialDataProvider).
    Repli transparent : tente le primaire, bascule sur le secondaire dès qu'il échoue
    (exception, ou None pour les méthodes nullable). L'appelant ignore quelle source a
    répondu — la provenance reste lisible via `ratios_source`. Si les deux échouent,
    l'erreur du secondaire remonte.
    """

    def __init__(
        self, primary: FinancialDataProvider, secondary: FinancialDataProvider
    ) -> None:
        self._primary = primary
        self._secondary = secondary

    async def extract(self, ticker: str) -> GrahamRatios:
        try:
            return await self._primary.extract(ticker)
        except Exception as exc:  # repli volontairement large : toute panne primaire bascule
            logger.warning("Repli secondaire pour extract(%s) : primaire KO (%s)", ticker, exc)
            return await self._secondary.extract(ticker)

    async def extract_valuation(self, ticker: str) -> ValuationRatios:
        try:
            return await self._primary.extract_valuation(ticker)
        except Exception as exc:
            logger.warning(
                "Repli secondaire pour extract_valuation(%s) : primaire KO (%s)", ticker, exc
            )
            return await self._secondary.extract_valuation(ticker)

    async def extract_earnings_quality(self, ticker: str) -> EarningsQualityRatios | None:
        try:
            primary = await self._primary.extract_earnings_quality(ticker)
        except Exception as exc:
            logger.warning(
                "Repli secondaire pour extract_earnings_quality(%s) : primaire KO (%s)",
                ticker, exc,
            )
            primary = None
        if primary is not None:
            return primary
        try:
            return await self._secondary.extract_earnings_quality(ticker)
        except Exception:
            return None

    async def get_price(self, ticker: str) -> float | None:
        primary = await self._primary.get_price(ticker)
        if primary is not None:
            return primary
        return await self._secondary.get_price(ticker)
