from __future__ import annotations

from typing import Literal

from pydantic import BaseModel

ScreenerSortKey = Literal["score", "ticker", "cost", "composite", "freshness"]


class ScreenerSort(BaseModel):
    """État de tri du Screener — colonne active et sens."""

    key: ScreenerSortKey
    asc: bool


class ScreenerPreferences(BaseModel):
    """Préférences Screener persistées par utilisateur (tri + filtres de label)."""

    sort: ScreenerSort | None = None
    filter: list[str] | None = None
