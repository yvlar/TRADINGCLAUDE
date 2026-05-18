"""Modeles Pydantic pour le backtesting composite (Sprint 50)."""
from __future__ import annotations

from datetime import date
from typing import Literal

from pydantic import BaseModel, Field, model_validator


class BucketResult(BaseModel):
    """Resultats agreges pour un bucket de signal composite."""

    label: Literal["FORT", "MODERE", "FAIBLE", "NO_SIGNAL"]
    tickers: list[str] = Field(default_factory=list)
    rendement_moyen: float | None = None
    rendement_median: float | None = None
    max_drawdown: float | None = None


class BacktestRequest(BaseModel):
    """Requete de backtesting composite."""

    tickers: list[str]
    start_date: date = Field(default_factory=lambda: date(2024, 1, 1))
    benchmark: Literal["SPY", "XIU.TO"] = "SPY"

    @model_validator(mode="after")
    def valider_requete(self) -> "BacktestRequest":
        if len(self.tickers) > 30:
            raise ValueError("Maximum 30 tickers par requete de backtesting")
        if self.start_date < date(2023, 1, 1):
            raise ValueError("start_date doit etre >= 2023-01-01")
        if self.start_date >= date.today():
            raise ValueError("start_date doit etre dans le passe")
        return self


class BacktestResult(BaseModel):
    """Resultats complets du backtesting composite."""

    periode_start: date
    periode_end: date
    benchmark: str
    benchmark_return: float | None = None
    buckets: list[BucketResult] = Field(default_factory=list)
    signal_alpha: float | None = None
    tickers_analyses: int = 0
    erreurs: list[str] = Field(default_factory=list)
