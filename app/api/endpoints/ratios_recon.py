from __future__ import annotations

import json
from typing import TYPE_CHECKING, TypeVar

from pydantic import BaseModel

from app.orchestrator.core import (
    _earnings_ratios_trace,
    _graham_ratios_trace,
    _valuation_ratios_trace,
)

if TYPE_CHECKING:
    from app.skills.tier2.earnings_quality.schemas import EarningsQualityRatios
    from app.skills.tier2.graham_analysis.schemas import GrahamRatios
    from app.skills.tier2.stock_valuation.schemas import ValuationRatios

_RatiosT = TypeVar("_RatiosT", bound=BaseModel)


def parse_input_data(row) -> dict | None:
    """Parse la colonne input_data (JSONB) en dict ; None si absent, illisible ou vide."""
    raw = row["input_data"]
    if raw is None:
        return None
    try:
        data: dict = json.loads(raw) if isinstance(raw, str) else dict(raw)
    except (ValueError, TypeError):
        return None
    return data or None


def extract_graham_ratios(row) -> "GrahamRatios | None":
    """Parse les ratios Graham depuis la racine d'input_data ; None si absents ou non conformes."""
    from app.skills.tier2.graham_analysis.schemas import GrahamRatios

    data = parse_input_data(row)
    if data is None:
        return None
    try:
        return GrahamRatios.model_validate(data)
    except Exception:
        return None


def _extract_sub_ratios(row, key: str, model_cls: type[_RatiosT]) -> "_RatiosT | None":
    """Valide la sous-clé `key` d'input_data en `model_cls` ; None si absente/illisible/non conforme."""
    data = parse_input_data(row)
    if data is None:
        return None
    sous_data = data.get(key)
    if not sous_data:
        return None
    try:
        return model_cls.model_validate(sous_data)
    except Exception:
        return None


def extract_earnings_ratios(row) -> "EarningsQualityRatios | None":
    """Parse les ratios earnings depuis la clé dédiée d'input_data ; None si absents/non conformes."""
    from app.skills.tier2.earnings_quality.schemas import EarningsQualityRatios

    return _extract_sub_ratios(row, "earnings_ratios", EarningsQualityRatios)


def extract_valuation_ratios(row) -> "ValuationRatios | None":
    """Parse les ratios valorisation depuis la clé dédiée d'input_data ; None si absents/non conformes."""
    from app.skills.tier2.stock_valuation.schemas import ValuationRatios

    return _extract_sub_ratios(row, "valuation_ratios", ValuationRatios)


def reconstruct_ratios_traces(row) -> dict[str, str | None]:
    """Reconstruit les 6 champs de traçabilité (Graham + earnings + valuation) depuis input_data.

    Source unique partagée par les endpoints `/report` et `/ticker-report` : sans elle,
    chaque chemin de reconstruction PDF dérive (cf. earnings/valuation oubliés côté `/report`).
    """
    graham_fetched, graham_source = _graham_ratios_trace(extract_graham_ratios(row))
    earnings_fetched, earnings_source = _earnings_ratios_trace(extract_earnings_ratios(row))
    valuation_fetched, valuation_source = _valuation_ratios_trace(extract_valuation_ratios(row))
    return {
        "ratios_fetched_at": graham_fetched,
        "ratios_source": graham_source,
        "earnings_ratios_fetched_at": earnings_fetched,
        "earnings_ratios_source": earnings_source,
        "valuation_ratios_fetched_at": valuation_fetched,
        "valuation_ratios_source": valuation_source,
    }
