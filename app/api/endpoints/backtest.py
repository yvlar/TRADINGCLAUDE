"""Endpoint GET /backtest/composite -- backtesting retrospectif du signal composite."""
from __future__ import annotations

import logging
from datetime import date

from fastapi import APIRouter, HTTPException, Query, Request
from typing import Literal

from app.models.backtest import BacktestResult
from app.services.backtest import BacktestService
from app.utils.ticker_sanitizer import sanitize_ticker

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get(
    "/backtest/composite",
    response_model=BacktestResult,
    summary="Backtesting retrospectif du signal composite par bucket FORT/MODERE/FAIBLE",
)
async def backtest_composite(
    request: Request,
    tickers: str = Query(description="Tickers separes par virgule, max 30"),
    start_date: date = Query(default=date(2024, 1, 1), description="Date de debut >= 2023-01-01"),
    benchmark: Literal["SPY", "XIU.TO"] = Query(default="SPY"),
) -> BacktestResult:
    """
    Pour chaque ticker, recupere le premier composite_score enregistre depuis start_date
    dans analysis_history, classe dans FORT/MODERE/FAIBLE, calcule le rendement jusqu'a
    aujourd'hui via yfinance, et compare au benchmark.
    """
    ticker_list = [sanitize_ticker(t.strip()) for t in tickers.split(",") if t.strip()]

    if len(ticker_list) == 0:
        raise HTTPException(status_code=400, detail="Au moins un ticker requis")
    if len(ticker_list) > 30:
        raise HTTPException(status_code=400, detail="Maximum 30 tickers par requete")
    if start_date < date(2023, 1, 1):
        raise HTTPException(status_code=400, detail="start_date doit etre >= 2023-01-01")
    if start_date >= date.today():
        raise HTTPException(status_code=400, detail="start_date doit etre dans le passe")

    db_pool = request.app.state.db_pool
    service = BacktestService(db_pool=db_pool)

    logger.info(
        "Backtest composite : %d tickers, start=%s, benchmark=%s",
        len(ticker_list), start_date, benchmark,
    )

    return await service.run_backtest(
        tickers=ticker_list,
        start_date=start_date,
        benchmark=benchmark,
    )
