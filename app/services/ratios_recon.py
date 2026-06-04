from __future__ import annotations

import json
from typing import TYPE_CHECKING, TypeVar

from pydantic import BaseModel

if TYPE_CHECKING:
    from app.skills.tier2.earnings_quality.schemas import EarningsQualityRatios
    from app.skills.tier2.graham_analysis.schemas import GrahamRatios
    from app.skills.tier2.stock_valuation.schemas import ValuationRatios

_RatiosT = TypeVar("_RatiosT", bound=BaseModel)


# ---------------------------------------------------------------------------
# Extraction (date ISO, source) d'un objet ratios — logique partagée par la
# construction de réponse (orchestrateur) et la reconstruction depuis l'historique.
# ---------------------------------------------------------------------------


def _graham_ratios_trace(ratios: "GrahamRatios | None") -> tuple[str | None, str | None]:
    """Extrait (date ISO de récupération, source) des ratios Graham pour la traçabilité de la réponse."""
    if ratios is None:
        return None, None
    fetched = ratios.ratios_fetched_at.isoformat() if ratios.ratios_fetched_at is not None else None
    return fetched, ratios.ratios_source


def _earnings_ratios_trace(
    ratios: "EarningsQualityRatios | None",
) -> tuple[str | None, str | None]:
    """Extrait (date ISO de récupération, source) des ratios Qualité bénéfices — calque de _graham_ratios_trace."""
    if ratios is None:
        return None, None
    fetched = ratios.ratios_fetched_at.isoformat() if ratios.ratios_fetched_at is not None else None
    return fetched, ratios.ratios_source


def _valuation_ratios_trace(
    ratios: "ValuationRatios | None",
) -> tuple[str | None, str | None]:
    """Extrait (date ISO de récupération, source) des ratios Valorisation — calque de _graham_ratios_trace."""
    if ratios is None:
        return None, None
    fetched = ratios.ratios_fetched_at.isoformat() if ratios.ratios_fetched_at is not None else None
    return fetched, ratios.ratios_source


# ---------------------------------------------------------------------------
# Reconstruction depuis une ligne analysis_history (input_data JSONB).
# ---------------------------------------------------------------------------


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


def _validate(model_cls: type[_RatiosT], data: dict | None) -> "_RatiosT | None":
    """Valide `data` en `model_cls` ; None si vide ou non conforme (jamais d'exception)."""
    if not data:
        return None
    try:
        return model_cls.model_validate(data)
    except Exception:
        return None


def extract_graham_ratios(row) -> "GrahamRatios | None":
    """Parse les ratios Graham depuis la racine d'input_data ; None si absents ou non conformes."""
    from app.skills.tier2.graham_analysis.schemas import GrahamRatios

    return _validate(GrahamRatios, parse_input_data(row))


def extract_earnings_ratios(row) -> "EarningsQualityRatios | None":
    """Parse les ratios earnings depuis la clé dédiée d'input_data ; None si absents/non conformes."""
    from app.skills.tier2.earnings_quality.schemas import EarningsQualityRatios

    data = parse_input_data(row)
    return _validate(EarningsQualityRatios, data.get("earnings_ratios") if data else None)


def extract_valuation_ratios(row) -> "ValuationRatios | None":
    """Parse les ratios valorisation depuis la clé dédiée d'input_data ; None si absents/non conformes."""
    from app.skills.tier2.stock_valuation.schemas import ValuationRatios

    data = parse_input_data(row)
    return _validate(ValuationRatios, data.get("valuation_ratios") if data else None)


def reconstruct_ratios_traces(row) -> dict[str, str | None]:
    """Reconstruit les 6 champs de traçabilité (Graham + earnings + valuation) depuis input_data.

    Source unique partagée par les endpoints `/report` et `/ticker-report` : sans elle, chaque
    chemin de reconstruction PDF dérive (cf. earnings/valuation oubliés côté `/report`).
    Parse `input_data` une seule fois pour les trois skills.
    """
    from app.skills.tier2.earnings_quality.schemas import EarningsQualityRatios
    from app.skills.tier2.graham_analysis.schemas import GrahamRatios
    from app.skills.tier2.stock_valuation.schemas import ValuationRatios

    data = parse_input_data(row)
    graham_fetched, graham_source = _graham_ratios_trace(_validate(GrahamRatios, data))
    earnings_fetched, earnings_source = _earnings_ratios_trace(
        _validate(EarningsQualityRatios, data.get("earnings_ratios") if data else None)
    )
    valuation_fetched, valuation_source = _valuation_ratios_trace(
        _validate(ValuationRatios, data.get("valuation_ratios") if data else None)
    )
    return {
        "ratios_fetched_at": graham_fetched,
        "ratios_source": graham_source,
        "earnings_ratios_fetched_at": earnings_fetched,
        "earnings_ratios_source": earnings_source,
        "valuation_ratios_fetched_at": valuation_fetched,
        "valuation_ratios_source": valuation_source,
    }
