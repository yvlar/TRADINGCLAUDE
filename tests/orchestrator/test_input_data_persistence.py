"""Persistance reconstructible des ratios earnings/valuation dans analysis_history.input_data.

Graham reste sérialisé à plat (rétrocompat) ; earnings/valuation sous clés dédiées pour que
leur traçabilité source+date soit reconstructible par un rapport ultérieur.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone

from app.orchestrator.core import AnalyzeRequest, _build_input_data
from app.skills.tier2.graham_analysis.schemas import GrahamRatios
from app.skills.tier2.stock_valuation.schemas import ValuationRatios

_FETCHED = datetime(2026, 5, 20, 9, 0, 0, tzinfo=timezone.utc)


def _request(**kwargs) -> AnalyzeRequest:
    return AnalyzeRequest(ticker="MSFT", **kwargs)


def test_graham_seul_sans_sous_cles(ratios_msft):
    """request.ratios seul → input_data plat Graham, aucune sous-clé earnings/valuation."""
    payload = json.loads(_build_input_data(_request(ratios=ratios_msft)))
    assert payload["price"] == 420.0
    assert "earnings_ratios" not in payload
    assert "valuation_ratios" not in payload


def test_earnings_valuation_persistes_avec_tracabilite(ratios_msft, ratios_earnings_msft):
    """Les sous-clés portent la source+date pour reconstruction ultérieure."""
    earnings = ratios_earnings_msft.model_copy(
        update={"ratios_fetched_at": _FETCHED, "ratios_source": "Yahoo Finance"}
    )
    valuation = ValuationRatios(
        pe=34.2, ratios_fetched_at=_FETCHED, ratios_source="Yahoo Finance"
    )
    payload = json.loads(
        _build_input_data(
            _request(ratios=ratios_msft, earnings_ratios=earnings, valuation_ratios=valuation)
        )
    )
    assert payload["earnings_ratios"]["ratios_source"] == "Yahoo Finance"
    assert payload["earnings_ratios"]["ratios_fetched_at"].startswith("2026-05-20")
    assert payload["valuation_ratios"]["ratios_source"] == "Yahoo Finance"
    assert payload["valuation_ratios"]["pe"] == 34.2


def test_graham_reste_validable_malgre_sous_cles(ratios_msft, ratios_earnings_msft):
    """Pin rétrocompat : GrahamRatios.model_validate ignore les sous-clés (extra='ignore')."""
    payload = json.loads(
        _build_input_data(_request(ratios=ratios_msft, earnings_ratios=ratios_earnings_msft))
    )
    graham = GrahamRatios.model_validate(payload)
    assert graham.price == 420.0
    assert graham.pe == 34.2


def test_ratios_none_donne_objet_vide():
    """request.ratios None et aucun autre ratio → input_data == '{}' (comportement historique)."""
    assert json.loads(_build_input_data(_request())) == {}


def test_earnings_sans_graham_persiste_quand_meme(ratios_earnings_msft):
    """earnings présent sans Graham → sous-clé persistée, Graham absent (pas de champs requis)."""
    payload = json.loads(_build_input_data(_request(earnings_ratios=ratios_earnings_msft)))
    assert "earnings_ratios" in payload
    assert "price" not in payload
