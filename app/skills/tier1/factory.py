from __future__ import annotations

import logging
import os

from app.skills.tier1.base import FinancialDataProvider
from app.skills.tier1.fallback_provider import FallbackDataProvider
from app.skills.tier1.fmp_provider import FmpProvider
from app.skills.tier1.yahoo_finance import YahooFinanceExtractor

logger = logging.getLogger(__name__)


def build_data_provider() -> FinancialDataProvider:
    """
    Construit le fournisseur tier1 : Yahoo Finance seul, ou Yahoo → FMP en repli si
    FMP_API_KEY est présente. Absence de clé = comportement historique inchangé.
    """
    yahoo = YahooFinanceExtractor()
    fmp_key = os.getenv("FMP_API_KEY")
    if fmp_key:
        logger.info("Fournisseur tier1 : Yahoo Finance avec repli FMP")
        return FallbackDataProvider(yahoo, FmpProvider(fmp_key))
    return yahoo
