from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, field_validator

from app.skills.tier2.graham_analysis.schemas import GrahamRatios
from app.utils.ticker_sanitizer import sanitize_ticker


class WatchlistEntry(BaseModel):
    id: str
    ticker: str
    workflow: str = "value_graham"
    ratios: GrahamRatios | None = None
    score_alerte_min: int | None = None
    created_at: datetime
    last_analyzed_at: datetime | None = None
    last_score: int | None = None
    last_verdict: str | None = None
    last_intrinsic_value: float | None = None
    last_price_checked: float | None = None
    price_alert_threshold_pct: float = 0.10


class WatchlistCreate(BaseModel):
    ticker: str
    workflow: str = "value_graham"
    ratios: GrahamRatios | None = None
    score_alerte_min: int | None = None

    @field_validator("ticker")
    @classmethod
    def valider_ticker(cls, v: str) -> str:
        return sanitize_ticker(v)
