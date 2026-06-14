from __future__ import annotations

import logging
import math
import os
from datetime import datetime, timezone
from typing import Any

import httpx
from fastapi import HTTPException

from app.skills.tier1.base import FinancialDataProvider
from app.skills.tier2.earnings_quality.schemas import EarningsQualityRatios
from app.skills.tier2.graham_analysis.schemas import GrahamRatios
from app.skills.tier2.stock_valuation.schemas import ValuationRatios

logger = logging.getLogger(__name__)

_FMP_BASE_URL = "https://financialmodelingprep.com/api/v3"

# Source littérale des ratios extraits — jamais dispersée en littéral (cf. donnees-financieres.md)
RATIOS_SOURCE = "Financial Modeling Prep"

FINANCIAL_SECTORS: frozenset[str] = frozenset(
    {"Financial Services", "Banks", "Insurance", "Financial", "Financials"}
)


def _first(payload: Any) -> dict[str, Any]:
    """FMP renvoie une liste à un élément ; retourne le premier dict ou un dict vide."""
    if isinstance(payload, list) and payload and isinstance(payload[0], dict):
        return payload[0]
    if isinstance(payload, dict):
        return payload
    return {}


def _num(source: dict[str, Any], *keys: str) -> float | None:
    """
    Premier champ numérique fini trouvé parmi `keys` — None sinon.
    Les clés multiples absorbent les variations de nommage entre endpoints FMP
    (ex. debtEquityRatioTTM vs debtToEquityTTM), comme le repli de yahoo_finance.
    """
    for key in keys:
        value = source.get(key)
        if value is None:
            continue
        try:
            f = float(value)
        except (TypeError, ValueError):
            continue
        if math.isfinite(f):
            return f
    return None


class FmpProvider(FinancialDataProvider):
    """
    Fournisseur REST async (Financial Modeling Prep) — implémentation de FinancialDataProvider.
    Pensé comme repli de YahooFinanceExtractor : `httpx` natif async, clé via FMP_API_KEY.
    Couverture partielle assumée : eps_growth/dividendes/déficits non reconstruits depuis
    l'historique (None/0.0 tracé), et extract_earnings_quality retourne None — le repli
    conserve alors la source primaire pour ces dimensions.
    """

    def __init__(self, api_key: str | None = None, timeout_s: float = 10.0) -> None:
        self._api_key = api_key if api_key is not None else os.getenv("FMP_API_KEY", "")
        self._timeout_s = timeout_s

    async def _get(self, path: str) -> Any:
        """Appel GET FMP ; HTTPException 503/504/502 selon l'échec (jamais d'exception brute)."""
        if not self._api_key:
            raise HTTPException(
                status_code=503, detail="FMP_API_KEY absente — fournisseur FMP indisponible"
            )
        try:
            async with httpx.AsyncClient(timeout=self._timeout_s) as client:
                resp = await client.get(
                    f"{_FMP_BASE_URL}/{path}", params={"apikey": self._api_key}
                )
        except httpx.TimeoutException:
            logger.warning("Timeout FMP pour %s après %.0fs", path, self._timeout_s)
            raise HTTPException(status_code=504, detail=f"Timeout FMP : {path}")
        if resp.status_code != 200:
            logger.warning("FMP HTTP %d pour %s", resp.status_code, path)
            raise HTTPException(status_code=502, detail=f"FMP HTTP {resp.status_code} : {path}")
        return resp.json()

    async def extract(self, ticker: str) -> GrahamRatios:
        """Ratios Graham depuis FMP. HTTPException 404 si ticker inconnu."""
        quote = _first(await self._get(f"quote/{ticker}"))
        price = _num(quote, "price")
        if not quote or price is None:
            raise HTTPException(
                status_code=404, detail=f"Ticker inconnu ou données insuffisantes : {ticker}"
            )

        profile = _first(await self._get(f"profile/{ticker}"))
        ratios = _first(await self._get(f"ratios-ttm/{ticker}"))
        metrics = _first(await self._get(f"key-metrics-ttm/{ticker}"))

        is_financial = (profile.get("sector") or "") in FINANCIAL_SECTORS

        pe = _num(quote, "pe") or _num(ratios, "peRatioTTM") or _num(metrics, "peRatioTTM")
        pb = _num(ratios, "priceToBookRatioTTM", "pbRatioTTM") or _num(metrics, "pbRatioTTM")
        book_value = _num(metrics, "bookValuePerShareTTM", "tangibleBookValuePerShareTTM")
        debt_equity = _num(ratios, "debtEquityRatioTTM", "debtToEquityTTM") or _num(
            metrics, "debtToEquityTTM"
        )
        current_ratio = (
            None
            if is_financial
            else _num(ratios, "currentRatioTTM") or _num(metrics, "currentRatioTTM")
        )
        eps_ttm = _num(quote, "eps") or _num(metrics, "netIncomePerShareTTM")

        shares = _num(quote, "sharesOutstanding")
        rev_per_share = _num(metrics, "revenuePerShareTTM")
        revenue_bn = (
            rev_per_share * shares / 1e9
            if rev_per_share is not None and shares is not None
            else None
        )

        return GrahamRatios(
            pe=pe,
            pb=pb,
            current_ratio=current_ratio,
            debt_equity=debt_equity,
            eps_growth_total=0.0,  # historique non reconstruit côté FMP — horizon inconnu
            eps_growth_years=None,
            price=price,
            book_value=book_value,
            eps_ttm=eps_ttm,
            revenue_bn=revenue_bn,
            dividend_years=None,
            no_deficit_years=None,
            ratios_fetched_at=datetime.now(timezone.utc),
            ratios_source=RATIOS_SOURCE,
        )

    async def extract_valuation(self, ticker: str) -> ValuationRatios:
        """Ratios de valorisation depuis FMP. HTTPException 404 si données insuffisantes."""
        quote = _first(await self._get(f"quote/{ticker}"))
        price = _num(quote, "price")
        if not quote or price is None:
            raise HTTPException(
                status_code=404, detail=f"Ticker inconnu ou données insuffisantes : {ticker}"
            )

        profile = _first(await self._get(f"profile/{ticker}"))
        ratios = _first(await self._get(f"ratios-ttm/{ticker}"))
        metrics = _first(await self._get(f"key-metrics-ttm/{ticker}"))

        shares = _num(quote, "sharesOutstanding")
        rev_per_share = _num(metrics, "revenuePerShareTTM")
        revenue_bn = (
            rev_per_share * shares / 1e9
            if rev_per_share is not None and shares is not None
            else None
        )
        fcf_per_share = _num(metrics, "freeCashFlowPerShareTTM")
        fcf_bn = (
            fcf_per_share * shares / 1e9
            if fcf_per_share is not None and shares is not None
            else None
        )

        return ValuationRatios(
            price=price,
            eps_ttm=_num(quote, "eps") or _num(metrics, "netIncomePerShareTTM"),
            book_value=_num(metrics, "bookValuePerShareTTM"),
            revenue_bn=revenue_bn,
            free_cash_flow_bn=fcf_bn,
            roic=_num(metrics, "roicTTM") or _num(ratios, "returnOnCapitalEmployedTTM"),
            roe=_num(ratios, "returnOnEquityTTM"),
            net_margin=_num(ratios, "netProfitMarginTTM"),
            debt_equity=_num(ratios, "debtEquityRatioTTM", "debtToEquityTTM"),
            pe=_num(quote, "pe") or _num(ratios, "peRatioTTM"),
            pb=_num(ratios, "priceToBookRatioTTM") or _num(metrics, "pbRatioTTM"),
            ev_ebitda=_num(ratios, "enterpriseValueMultipleTTM")
            or _num(metrics, "enterpriseValueOverEBITDATTM"),
            dividend_yield=_num(ratios, "dividendYieldTTM", "dividendYielTTM"),
            shares_outstanding_m=shares / 1e6 if shares is not None else None,
            sector=profile.get("sector"),
            ratios_fetched_at=datetime.now(timezone.utc),
            ratios_source=RATIOS_SOURCE,
        )

    async def extract_earnings_quality(self, ticker: str) -> EarningsQualityRatios | None:
        """Non couvert par ce fournisseur — le repli conserve la source primaire."""
        return None

    async def get_price(self, ticker: str) -> float | None:
        """Cours actuel depuis FMP. None sur toute erreur — ne lève jamais d'exception."""
        try:
            quote = _first(await self._get(f"quote/{ticker}"))
            return _num(quote, "price")
        except Exception:
            logger.warning("Impossible d'obtenir le cours FMP pour %s", ticker)
            return None
