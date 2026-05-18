"""Service de backtesting retrospectif du signal composite (Sprint 50)."""
from __future__ import annotations

import asyncio
import json
import logging
import statistics
from datetime import date, timedelta
from typing import Any

import asyncpg

from app.models.backtest import BacktestResult, BucketResult

logger = logging.getLogger(__name__)

_FORT_MIN = 70.0
_MODERE_MIN = 40.0

_BUCKET_ORDER = ["FORT", "MODERE", "FAIBLE", "NO_SIGNAL"]


def _classify_score(score: float | None) -> str:
    if score is None:
        return "NO_SIGNAL"
    if score >= _FORT_MIN:
        return "FORT"
    if score >= _MODERE_MIN:
        return "MODERE"
    return "FAIBLE"


def _fetch_price_at_date(ticker: str, target_date: date) -> float | None:
    """Recupere le prix cloture au jour target_date (ou le plus proche apres) via yfinance."""
    try:
        import yfinance as yf

        end = target_date + timedelta(days=7)
        hist = yf.Ticker(ticker).history(
            start=target_date.isoformat(),
            end=end.isoformat(),
            auto_adjust=True,
        )
        if hist.empty:
            return None
        return float(hist["Close"].iloc[0])
    except Exception:
        logger.debug("yfinance echec prix historique %s @ %s", ticker, target_date)
        return None


def _fetch_current_price(ticker: str) -> float | None:
    """Recupere le prix courant via yfinance."""
    try:
        import yfinance as yf

        hist = yf.Ticker(ticker).history(period="2d", auto_adjust=True)
        if hist.empty:
            return None
        return float(hist["Close"].iloc[-1])
    except Exception:
        logger.debug("yfinance echec prix courant %s", ticker)
        return None


def _compute_return(price_entry: float | None, price_current: float | None) -> float | None:
    if price_entry is None or price_current is None or price_entry == 0.0:
        return None
    return (price_current - price_entry) / price_entry


def _compute_max_drawdown(ticker: str, entry_date: date) -> float | None:
    """Calcule le max drawdown (fraction) depuis entry_date jusqu'a aujourd'hui."""
    try:
        import yfinance as yf

        hist = yf.Ticker(ticker).history(
            start=entry_date.isoformat(),
            end=date.today().isoformat(),
            auto_adjust=True,
        )
        if hist.empty or len(hist) < 2:
            return None
        closes = list(hist["Close"])
        peak = closes[0]
        max_dd = 0.0
        for price in closes[1:]:
            if price > peak:
                peak = price
            dd = (price - peak) / peak
            if dd < max_dd:
                max_dd = dd
        return max_dd
    except Exception:
        return None


def _aggregate_bucket(
    label: str,
    ticker_data: list[dict[str, Any]],
) -> BucketResult:
    """Calcule les metriques agreges pour un bucket."""
    tickers = [d["ticker"] for d in ticker_data]
    rendements = [d["rendement"] for d in ticker_data if d["rendement"] is not None]
    drawdowns = [d["max_drawdown"] for d in ticker_data if d["max_drawdown"] is not None]

    return BucketResult(
        label=label,
        tickers=tickers,
        rendement_moyen=round(statistics.mean(rendements), 4) if rendements else None,
        rendement_median=round(statistics.median(rendements), 4) if rendements else None,
        max_drawdown=round(min(drawdowns), 4) if drawdowns else None,
    )


class BacktestService:
    """Backtesting retrospectif du signal composite sur analysis_history + yfinance."""

    def __init__(self, db_pool: asyncpg.Pool) -> None:
        self._db = db_pool

    async def run_backtest(
        self,
        tickers: list[str],
        start_date: date,
        benchmark: str = "SPY",
    ) -> BacktestResult:
        """Execute le backtesting et retourne les resultats par bucket."""
        today = date.today()
        erreurs: list[str] = []
        bucket_data: dict[str, list[dict[str, Any]]] = {
            "FORT": [],
            "MODERE": [],
            "FAIBLE": [],
            "NO_SIGNAL": [],
        }

        for ticker in tickers:
            try:
                score_row = await self._get_first_score_after(ticker, start_date)

                if score_row is None:
                    bucket_data["NO_SIGNAL"].append({
                        "ticker": ticker,
                        "rendement": None,
                        "max_drawdown": None,
                    })
                    continue

                composite_score, analyse_date, stored_price = score_row
                bucket = _classify_score(composite_score)

                # Prix d'entree : stocke en DB si dispo, sinon yfinance historique
                if stored_price is not None:
                    price_entry = float(stored_price)
                else:
                    price_entry = await asyncio.to_thread(_fetch_price_at_date, ticker, analyse_date)

                price_current = await asyncio.to_thread(_fetch_current_price, ticker)
                rendement = _compute_return(price_entry, price_current)
                max_dd = await asyncio.to_thread(_compute_max_drawdown, ticker, analyse_date)

                bucket_data[bucket].append({
                    "ticker": ticker,
                    "rendement": rendement,
                    "max_drawdown": max_dd,
                })

            except Exception:
                logger.exception("Erreur backtesting pour %s", ticker)
                erreurs.append(ticker)

        # Benchmark
        benchmark_return = await asyncio.to_thread(
            self._fetch_benchmark_return, benchmark, start_date
        )

        buckets = [
            _aggregate_bucket(label, bucket_data[label])
            for label in _BUCKET_ORDER
        ]

        # Signal alpha : rendement FORT vs benchmark
        fort_bucket = next((b for b in buckets if b.label == "FORT"), None)
        signal_alpha: float | None = None
        if fort_bucket and fort_bucket.rendement_moyen is not None and benchmark_return is not None:
            signal_alpha = round(fort_bucket.rendement_moyen - benchmark_return, 4)

        return BacktestResult(
            periode_start=start_date,
            periode_end=today,
            benchmark=benchmark,
            benchmark_return=round(benchmark_return, 4) if benchmark_return is not None else None,
            buckets=buckets,
            signal_alpha=signal_alpha,
            tickers_analyses=len(tickers) - len(erreurs),
            erreurs=erreurs,
        )

    async def _get_first_score_after(
        self,
        ticker: str,
        start_date: date,
    ) -> tuple[float | None, date, float | None] | None:
        """Retourne (composite_score, date_analyse, price_at_analysis) ou None si absent."""
        row = await self._db.fetchrow(
            """
            SELECT result, created_at, price_at_analysis
            FROM analysis_history
            WHERE ticker = $1 AND created_at >= $2
            ORDER BY created_at ASC
            LIMIT 1
            """,
            ticker,
            start_date,
        )
        if row is None:
            return None

        composite_score = self._extract_composite_score(row["result"])
        analyse_date = row["created_at"].date()
        stored_price = row["price_at_analysis"]
        return composite_score, analyse_date, stored_price

    @staticmethod
    def _extract_composite_score(result_json: str | dict) -> float | None:
        try:
            data = result_json if isinstance(result_json, dict) else json.loads(result_json)
            cs = data.get("composite_score")
            if isinstance(cs, dict):
                val = cs.get("score")
                return float(val) if val is not None else None
        except Exception:
            pass
        return None

    @staticmethod
    def _fetch_benchmark_return(benchmark: str, start_date: date) -> float | None:
        """Rendement total du benchmark depuis start_date via yfinance."""
        try:
            import yfinance as yf

            end = date.today()
            hist = yf.Ticker(benchmark).history(
                start=start_date.isoformat(),
                end=end.isoformat(),
                auto_adjust=True,
            )
            if hist.empty or len(hist) < 2:
                return None
            price_start = float(hist["Close"].iloc[0])
            price_end = float(hist["Close"].iloc[-1])
            if price_start == 0.0:
                return None
            return (price_end - price_start) / price_start
        except Exception:
            logger.debug("yfinance echec benchmark %s", benchmark)
            return None
