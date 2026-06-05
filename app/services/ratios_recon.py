from __future__ import annotations

import json
from typing import TYPE_CHECKING, TypeGuard, TypeVar

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


def _ratios_trace(
    ratios: "GrahamRatios | EarningsQualityRatios | ValuationRatios | None",
) -> tuple[str | None, str | None]:
    """Extrait (date ISO de récupération, source) d'un objet ratios pour la traçabilité de la réponse.

    Source unique des trois schémas ratios (Graham/earnings/valuation portent les mêmes champs
    `ratios_fetched_at`/`ratios_source` — Sprint 153, fin de la triplication). `None` → `(None, None)` ;
    source conservée même si la date manque (honnêteté None).
    """
    if ratios is None:
        return None, None
    fetched = ratios.ratios_fetched_at.isoformat() if ratios.ratios_fetched_at is not None else None
    return fetched, ratios.ratios_source


def has_ratios_source(
    ratios: "GrahamRatios | EarningsQualityRatios | ValuationRatios | None",
) -> "TypeGuard[GrahamRatios | EarningsQualityRatios | ValuationRatios]":
    """True si l'objet ratios porte une source OU une date de récupération (traçabilité affichable).

    Prédicat partagé : le rendu PDF n'ajoute une ligne « Source des ratios » que sous cette
    condition (honnêteté None — parité Graham/earnings/valuation). `None` → False. `TypeGuard`
    pour restreindre l'objet en non-None au site d'appel (accès ratios_source/ratios_fetched_at).
    """
    return ratios is not None and (
        ratios.ratios_fetched_at is not None or ratios.ratios_source is not None
    )


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


def reconstruct_ratios_traces(row) -> dict[str, str | dict[str, str] | None]:
    """Reconstruit les champs de traçabilité d'AnalyzeResponse depuis input_data.

    Six champs source+date (Graham + earnings + valuation) + la provenance par ratio Graham.
    Source unique partagée par les endpoints `/report` et `/ticker-report` : sans elle, chaque
    chemin de reconstruction PDF dérive (cf. earnings/valuation oubliés côté `/report`).
    Parse `input_data` une seule fois pour les trois skills.
    """
    from app.skills.tier2.earnings_quality.schemas import EarningsQualityRatios
    from app.skills.tier2.graham_analysis.schemas import GrahamRatios
    from app.skills.tier2.stock_valuation.schemas import ValuationRatios

    data = parse_input_data(row)
    graham = _validate(GrahamRatios, data)
    graham_fetched, graham_source = _ratios_trace(graham)
    earnings_fetched, earnings_source = _ratios_trace(
        _validate(EarningsQualityRatios, data.get("earnings_ratios") if data else None)
    )
    valuation_fetched, valuation_source = _ratios_trace(
        _validate(ValuationRatios, data.get("valuation_ratios") if data else None)
    )
    return {
        "ratios_fetched_at": graham_fetched,
        "ratios_source": graham_source,
        "earnings_ratios_fetched_at": earnings_fetched,
        "earnings_ratios_source": earnings_source,
        "valuation_ratios_fetched_at": valuation_fetched,
        "valuation_ratios_source": valuation_source,
        "ratios_provenance": graham.ratios_provenance if graham is not None else None,
    }
