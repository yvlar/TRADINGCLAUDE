from __future__ import annotations

from typing import Protocol, runtime_checkable

from app.skills.tier2.earnings_quality.schemas import EarningsQualityRatios
from app.skills.tier2.graham_analysis.schemas import GrahamRatios
from app.skills.tier2.stock_valuation.schemas import ValuationRatios


@runtime_checkable
class FinancialDataProvider(Protocol):
    """Contrat commun d'un fournisseur de données tier1 — découple les skills de la source."""

    async def extract(self, ticker: str) -> GrahamRatios:
        """Ratios Graham. HTTPException 404 si ticker inconnu ou données insuffisantes."""
        ...

    async def extract_valuation(self, ticker: str) -> ValuationRatios:
        """Ratios de valorisation. HTTPException 404 si données insuffisantes."""
        ...

    async def extract_earnings_quality(self, ticker: str) -> EarningsQualityRatios | None:
        """Ratios de qualité des bénéfices ; None si états financiers indisponibles."""
        ...

    async def get_price(self, ticker: str) -> float | None:
        """Cours actuel ; None en cas d'indisponibilité — ne lève jamais d'exception."""
        ...
