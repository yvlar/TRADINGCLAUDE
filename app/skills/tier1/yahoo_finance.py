from __future__ import annotations

import asyncio
import logging
import math
from datetime import datetime
from typing import Any

from fastapi import HTTPException

from app.skills.tier2.earnings_quality.schemas import EarningsQualityRatios
from app.skills.tier2.graham_analysis.schemas import GrahamRatios
from app.skills.tier2.stock_valuation.schemas import ValuationRatios

logger = logging.getLogger(__name__)


def _compute_eps_growth(income: Any, shares: float) -> tuple[float, int | None]:
    """
    Calcule la croissance totale du BPA depuis income_stmt sur l'horizon réellement disponible.
    Retourne (croissance_totale, horizon_ans) : croissance en fraction (0.74 = +74 %) et le
    nombre d'années couvertes (intervalles entre exercices = nb de points - 1). Honnêteté du
    label : N points annuels couvrent N-1 années de croissance, pas N (ni « 10 ans »).
    Retourne (0.0, None) si le calcul est impossible — None signale « horizon inconnu », ce qui
    déclenche le repli de source côté appelant.
    """
    if income is None or shares <= 0:
        return 0.0, None
    ni_row = None
    for key in ("Net Income", "Net Income Common Stockholders", "NetIncome"):
        if key in income.index:
            ni_row = income.loc[key]
            break
    if ni_row is None:
        return 0.0, None
    values: list[float] = []
    for v in ni_row:
        try:
            f = float(v)
            if not math.isnan(f):
                values.append(f)
        except (TypeError, ValueError):
            continue
    if len(values) < 2:
        return 0.0, None
    # yfinance trie les colonnes du plus récent au plus ancien
    eps_recent = values[0] / shares
    eps_oldest = values[-1] / shares
    if eps_oldest <= 0:
        return 0.0, None
    return round((eps_recent / eps_oldest) - 1.0, 4), len(values) - 1


def _compute_dividend_years(dividends: Any) -> int | None:
    """
    Compte les années consécutives avec au moins un dividende depuis l'année courante.
    Retourne None si données indisponibles, 0 si la série est vide.
    """
    if dividends is None:
        return None
    if hasattr(dividends, "empty") and dividends.empty:
        return 0
    try:
        years_with_divs: set[int] = set(dividends.index.year)
    except AttributeError:
        return None
    current_year = datetime.now().year
    consecutive = 0
    year = current_year
    while year in years_with_divs:
        consecutive += 1
        year -= 1
    return consecutive


def _compute_no_deficit_years(income: Any, shares: float) -> int | None:
    """
    Compte les années avec bénéfice net positif dans income_stmt.
    Retourne None si données insuffisantes.
    """
    if income is None or shares <= 0:
        return None
    ni_row = None
    for key in ("Net Income", "Net Income Common Stockholders", "NetIncome"):
        if key in income.index:
            ni_row = income.loc[key]
            break
    if ni_row is None:
        return None
    total = 0
    positive = 0
    for v in ni_row:
        try:
            f = float(v)
            if not math.isnan(f):
                total += 1
                if f > 0:
                    positive += 1
        except (TypeError, ValueError):
            continue
    return positive if total > 0 else None

FINANCIAL_SECTORS: frozenset[str] = frozenset(
    {"Financial Services", "Banks", "Insurance", "Financial"}
)


class YahooFinanceExtractor:
    """
    Extrait les ratios Graham + valuation depuis Yahoo Finance via yfinance.
    Timeout 10s. HTTPException 404 si ticker inconnu ou données insuffisantes.
    """

    def __init__(self, timeout_s: float = 10.0) -> None:
        self._timeout_s = timeout_s

    def _fetch_info(self, ticker: str) -> dict[str, Any]:
        """Appel synchrone yfinance — lazy import, exécuté dans un thread via run_in_executor."""
        import yfinance as yf  # noqa: PLC0415 — import lazy pour éviter la dépendance au démarrage
        return yf.Ticker(ticker).info

    def _fetch_info_and_history(self, ticker: str) -> dict[str, Any]:
        """
        Appel synchrone yfinance étendu : info + income_stmt + dividends en un seul appel.
        Exécuté dans un thread via run_in_executor.
        """
        import yfinance as yf  # noqa: PLC0415
        t = yf.Ticker(ticker)
        info = t.info
        income: Any = None
        dividends: Any = None
        try:
            income = t.income_stmt
            if income is None or (hasattr(income, "empty") and income.empty):
                income = getattr(t, "financials", None)
        except Exception:
            logger.warning("income_stmt indisponible pour %s", ticker)
        try:
            dividends = t.dividends
        except Exception:
            logger.warning("dividends indisponibles pour %s", ticker)
        return {"info": info, "income": income, "dividends": dividends}

    async def _get_info(self, ticker: str) -> dict[str, Any]:
        """Wrapper async avec timeout pour l'appel synchrone yfinance."""
        loop = asyncio.get_event_loop()
        try:
            info: dict[str, Any] = await asyncio.wait_for(
                loop.run_in_executor(None, self._fetch_info, ticker),
                timeout=self._timeout_s,
            )
        except asyncio.TimeoutError:
            logger.warning("Timeout yfinance pour %s après %.0fs", ticker, self._timeout_s)
            raise HTTPException(
                status_code=504,
                detail=f"Timeout lors de l'extraction Yahoo Finance : {ticker}",
            )
        return info

    async def extract(self, ticker: str) -> GrahamRatios:
        """
        Retourne GrahamRatios peuplé depuis yfinance.
        current_ratio = None si secteur financier (banques, assurances).
        HTTPException 404 si ticker inconnu ou données insuffisantes.
        """
        loop = asyncio.get_event_loop()
        try:
            raw: dict[str, Any] = await asyncio.wait_for(
                loop.run_in_executor(None, self._fetch_info_and_history, ticker),
                timeout=self._timeout_s,
            )
        except asyncio.TimeoutError:
            logger.warning("Timeout yfinance pour %s après %.0fs", ticker, self._timeout_s)
            raise HTTPException(
                status_code=504,
                detail=f"Timeout lors de l'extraction Yahoo Finance : {ticker}",
            )

        info = raw["info"]
        income = raw.get("income")
        dividends = raw.get("dividends")

        price = info.get("currentPrice") or info.get("regularMarketPrice")
        if not info or price is None:
            raise HTTPException(
                status_code=404,
                detail=f"Ticker inconnu ou données insuffisantes : {ticker}",
            )

        sector = info.get("sector", "")
        is_financial = sector in FINANCIAL_SECTORS

        eps_ttm: float | None = info.get("trailingEps")
        pe: float | None = info.get("trailingPE")
        if pe is None and eps_ttm is not None and eps_ttm != 0:
            pe = float(price) / eps_ttm

        raw_de = info.get("debtToEquity")
        # yfinance retourne debtToEquity en % (ex: 45.0 = 45%) → diviser par 100
        debt_equity: float = raw_de / 100.0 if raw_de is not None else 0.0

        revenue = info.get("totalRevenue")
        revenue_bn: float | None = revenue / 1e9 if revenue is not None else None

        shares = info.get("sharesOutstanding")
        eps_growth_total, eps_growth_years = (
            _compute_eps_growth(income, shares) if income is not None and shares else (0.0, None)
        )
        # Repli de source : income_stmt absent/vide → utiliser info.earningsGrowth (croissance
        # annuelle ~1 an publiée par yfinance), tracé explicitement plutôt que de tomber muettement
        # à 0.0 (cf. donnees-financieres.md : toujours tracer la source, jamais d'exception).
        if eps_growth_years is None:
            fallback = info.get("earningsGrowth")
            if fallback is not None:
                eps_growth_total = float(fallback)
                eps_growth_years = 1
                logger.info(
                    "eps_growth %s : repli sur info.earningsGrowth (horizon 1 an) faute d'income_stmt",
                    ticker,
                )
        dividend_years = _compute_dividend_years(dividends)
        no_deficit_years = _compute_no_deficit_years(income, shares) if income is not None and shares else None

        return GrahamRatios(
            pe=pe if pe is not None else 0.0,
            pb=info.get("priceToBook") or 0.0,
            current_ratio=None if is_financial else info.get("currentRatio"),
            debt_equity=debt_equity,
            eps_growth_total=eps_growth_total,
            eps_growth_years=eps_growth_years,
            price=float(price),
            book_value=info.get("bookValue") or 0.0,
            eps_ttm=eps_ttm,
            revenue_bn=revenue_bn,
            dividend_years=dividend_years,
            no_deficit_years=no_deficit_years,
        )

    def _fetch_earnings_data(self, ticker: str) -> dict[str, Any]:
        """Récupère les états financiers yfinance sur 2 exercices (synchrone)."""
        import yfinance as yf  # noqa: PLC0415
        t = yf.Ticker(ticker)
        income = getattr(t, "income_stmt", None)
        if income is None or (hasattr(income, "empty") and income.empty):
            income = getattr(t, "financials", None)
        return {
            "income": income,
            "balance": t.balance_sheet,
            "cashflow": t.cashflow,
            "info": t.info,
        }

    async def extract_earnings_quality(self, ticker: str) -> EarningsQualityRatios | None:
        """
        Extrait EarningsQualityRatios depuis Yahoo Finance (2 exercices consécutifs).
        Retourne None si les données sont insuffisantes — ne lève pas d'exception.
        """
        loop = asyncio.get_event_loop()
        try:
            data: dict[str, Any] = await asyncio.wait_for(
                loop.run_in_executor(None, self._fetch_earnings_data, ticker),
                timeout=self._timeout_s,
            )
        except asyncio.TimeoutError:
            logger.warning("Timeout yfinance earnings pour %s", ticker)
            return None

        income = data.get("income")
        balance = data.get("balance")
        cashflow = data.get("cashflow")
        info = data.get("info") or {}

        if income is None or balance is None or cashflow is None:
            return None
        if income.shape[1] < 2 or balance.shape[1] < 2:
            return None

        def _row(df: Any, *names: str) -> Any | None:
            """Retourne la première ligne trouvée parmi les noms candidats."""
            for name in names:
                if name in df.index:
                    return df.loc[name]
            return None

        def _val(series: Any | None, period: int = 0) -> float | None:
            if series is None or len(series) <= period:
                return None
            import math
            v = series.iloc[period]
            try:
                f = float(v)
                return None if math.isnan(f) else f
            except (TypeError, ValueError):
                return None

        income_rev = _row(income, "Total Revenue", "TotalRevenue")
        income_cogs = _row(income, "Cost Of Revenue", "CostOfRevenue", "Cost of Revenue")
        income_ni = _row(income, "Net Income", "NetIncome", "Net Income Common Stockholders")
        income_ebit = _row(income, "EBIT", "Operating Income", "OperatingIncome", "EBIT")
        income_sga = _row(income, "Selling General Administrative",
                          "Selling General And Administration", "SGA")

        cf_ops = _row(cashflow, "Operating Cash Flow", "Total Cash From Operating Activities",
                      "OperatingCashFlow", "Cash From Operating Activities")
        cf_dep = _row(cashflow, "Depreciation And Amortization", "Reconciled Depreciation",
                      "Depreciation", "DepreciationAndAmortization")

        bal_assets = _row(balance, "Total Assets", "TotalAssets")
        bal_recv = _row(balance, "Accounts Receivable", "Net Receivables", "Receivables",
                        "NetReceivables", "Gross Accounts Receivable")
        bal_curr_a = _row(balance, "Current Assets", "Total Current Assets", "CurrentAssets")
        bal_curr_l = _row(balance, "Current Liabilities", "Total Current Liabilities",
                          "CurrentLiabilities")
        bal_inv = _row(balance, "Inventory")
        bal_ppe_net = _row(balance, "Net PPE", "NetPPE", "Property Plant Equipment Net")
        bal_ppe_gross = _row(balance, "Gross PPE", "GrossPPE")
        bal_ltd = _row(balance, "Long Term Debt", "LongTermDebt")
        bal_re = _row(balance, "Retained Earnings", "RetainedEarnings")
        bal_liab = _row(balance, "Total Liabilities Net Minority Interest",
                        "TotalLiabilitiesNetMinorityInterest", "Total Liabilities")
        bal_equity = _row(balance, "Stockholders Equity", "Common Stock Equity",
                          "Total Equity Gross Minority Interest", "CommonStockEquity")

        # Champs obligatoires — retourner None si l'un est absent
        required_vals = {
            "sales_t": _val(income_rev, 0),
            "sales_t1": _val(income_rev, 1),
            "cogs_t": _val(income_cogs, 0),
            "cogs_t1": _val(income_cogs, 1),
            "net_income_t": _val(income_ni, 0),
            "cfo_t": _val(cf_ops, 0),
            "receivables_t": _val(bal_recv, 0),
            "receivables_t1": _val(bal_recv, 1),
            "total_assets_t": _val(bal_assets, 0),
            "total_assets_t1": _val(bal_assets, 1),
        }
        if any(v is None for v in required_vals.values()):
            logger.warning(
                "EarningsQualityRatios incomplets pour %s : %s",
                ticker,
                [k for k, v in required_vals.items() if v is None],
            )
            return None

        # current_assets et current_liabilities obligatoires dans le schéma
        curr_a = _val(bal_curr_a, 0)
        curr_l = _val(bal_curr_l, 0)
        if curr_a is None or curr_l is None:
            logger.warning("current_assets ou current_liabilities manquants pour %s", ticker)
            return None

        market_cap = info.get("marketCap")

        return EarningsQualityRatios(
            **required_vals,
            net_income_t1=_val(income_ni, 1),
            cfo_t1=_val(cf_ops, 1),
            ebit_t=_val(income_ebit, 0),
            sga_t=_val(income_sga, 0),
            sga_t1=_val(income_sga, 1),
            depreciation_t=_val(cf_dep, 0),
            depreciation_t1=_val(cf_dep, 1),
            current_assets_t=curr_a,
            current_liabilities_t=curr_l,
            inventory_t=_val(bal_inv, 0),
            ppe_net_t=_val(bal_ppe_net, 0),
            ppe_gross_t=_val(bal_ppe_gross, 0),
            ltd_t=_val(bal_ltd, 0),
            retained_earnings_t=_val(bal_re, 0),
            total_liabilities_t=_val(bal_liab, 0),
            market_cap_t=float(market_cap) if market_cap is not None else None,
            book_equity_t=_val(bal_equity, 0),
            current_assets_t1=_val(bal_curr_a, 1),
            current_liabilities_t1=_val(bal_curr_l, 1),
            inventory_t1=_val(bal_inv, 1),
            ppe_net_t1=_val(bal_ppe_net, 1),
            ppe_gross_t1=_val(bal_ppe_gross, 1),
            ltd_t1=_val(bal_ltd, 1),
        )

    async def get_price(self, ticker: str) -> float | None:
        """Retourne le cours actuel depuis Yahoo Finance. None si indisponible — ne lève pas d'exception."""
        try:
            info = await self._get_info(ticker)
            price = info.get("currentPrice") or info.get("regularMarketPrice")
            return float(price) if price is not None else None
        except Exception:
            logger.warning("Impossible d'obtenir le cours actuel pour %s", ticker)
            return None

    async def extract_valuation(self, ticker: str) -> ValuationRatios:
        """
        Retourne ValuationRatios peuplé depuis yfinance.
        HTTPException 404 si ticker inconnu ou données insuffisantes.
        """
        info = await self._get_info(ticker)

        price = info.get("currentPrice") or info.get("regularMarketPrice")
        if not info or price is None:
            raise HTTPException(
                status_code=404,
                detail=f"Ticker inconnu ou données insuffisantes : {ticker}",
            )

        eps_ttm: float | None = info.get("trailingEps")
        pe: float | None = info.get("trailingPE")
        if pe is None and eps_ttm is not None and eps_ttm != 0:
            pe = float(price) / eps_ttm

        raw_de = info.get("debtToEquity")
        debt_equity: float | None = raw_de / 100.0 if raw_de is not None else None

        revenue = info.get("totalRevenue")
        revenue_bn: float | None = revenue / 1e9 if revenue is not None else None

        fcf = info.get("freeCashflow")
        fcf_bn: float | None = fcf / 1e9 if fcf is not None else None

        shares = info.get("sharesOutstanding")
        shares_m: float | None = shares / 1e6 if shares is not None else None

        return ValuationRatios(
            price=float(price),
            eps_ttm=eps_ttm,
            eps_growth_5y=info.get("earningsGrowth"),
            eps_growth_10y=None,
            book_value=info.get("bookValue"),
            revenue_bn=revenue_bn,
            free_cash_flow_bn=fcf_bn,
            roic=None,
            roe=info.get("returnOnEquity"),
            net_margin=info.get("profitMargins"),
            debt_equity=debt_equity,
            pe=pe,
            pb=info.get("priceToBook"),
            ev_ebitda=info.get("enterpriseToEbitda"),
            dividend_yield=info.get("dividendYield"),
            shares_outstanding_m=shares_m,
            sector=info.get("sector"),
        )
