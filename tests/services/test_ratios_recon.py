"""Tests unitaires du module partagé de reconstruction de traçabilité (app/services/ratios_recon.py)."""
from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone

from app.services.ratios_recon import reconstruct_ratios_traces

# Six champs source+date + la provenance par ratio Graham (Sprint 150).
_CLES_TRACE = {
    "ratios_fetched_at",
    "ratios_source",
    "earnings_ratios_fetched_at",
    "earnings_ratios_source",
    "valuation_ratios_fetched_at",
    "valuation_ratios_source",
    "ratios_provenance",
}


def _row(input_data: dict | None) -> dict:
    """Ligne analysis_history simulée (indexable comme asyncpg.Record)."""
    return {
        "id": uuid.UUID("dddddddd-0000-0000-0000-000000000004"),
        "input_data": json.dumps(input_data) if input_data is not None else None,
    }


def test_reconstruct_six_cles_depuis_sous_cles_horodatees(ratios_earnings_msft):
    from app.skills.tier2.stock_valuation.schemas import ValuationRatios

    earnings = ratios_earnings_msft.model_copy(
        update={
            "ratios_fetched_at": datetime(2026, 5, 21, 9, 0, 0, tzinfo=timezone.utc),
            "ratios_source": "Yahoo Finance",
        }
    )
    valuation = ValuationRatios(
        pe=34.2,
        ratios_fetched_at=datetime(2026, 5, 22, 9, 0, 0, tzinfo=timezone.utc),
        ratios_source="Yahoo Finance",
    )
    traces = reconstruct_ratios_traces(
        _row(
            {
                "eps_growth_total": 0.27,
                "price": 245.0,
                "ratios_fetched_at": "2026-05-20T09:00:00+00:00",
                "ratios_source": "Yahoo Finance",
                "earnings_ratios": earnings.model_dump(mode="json"),
                "valuation_ratios": valuation.model_dump(mode="json"),
            }
        )
    )
    assert set(traces.keys()) == _CLES_TRACE
    assert traces["ratios_fetched_at"].startswith("2026-05-20")
    assert traces["earnings_ratios_fetched_at"].startswith("2026-05-21")
    assert traces["valuation_ratios_fetched_at"].startswith("2026-05-22")
    assert {traces["ratios_source"], traces["earnings_ratios_source"], traces["valuation_ratios_source"]} == {
        "Yahoo Finance"
    }


def test_reconstruct_input_data_absent_donne_toutes_none():
    traces = reconstruct_ratios_traces(_row(None))
    assert traces == dict.fromkeys(_CLES_TRACE, None)


def test_reconstruct_ligne_plate_sans_sous_cles_donne_earnings_valuation_none():
    traces = reconstruct_ratios_traces(_row({"eps_growth_total": 0.27, "price": 245.0}))
    assert traces["earnings_ratios_fetched_at"] is None
    assert traces["valuation_ratios_fetched_at"] is None
    assert traces["ratios_provenance"] is None


def test_reconstruct_provenance_graham_depuis_input_data():
    """La provenance par ratio Graham est reconstruite depuis input_data (Sprint 150)."""
    traces = reconstruct_ratios_traces(
        _row(
            {
                "eps_growth_total": 0.27,
                "price": 245.0,
                "ratios_provenance": {"pb": "priceToBook", "debt_equity": "totalDebt"},
            }
        )
    )
    assert traces["ratios_provenance"] == {"pb": "priceToBook", "debt_equity": "totalDebt"}


def test_cles_de_tracabilite_disjointes_des_champs_skill():
    """Invariant protégeant le `**reconstruct_ratios_traces(row), **parsed_fields` des endpoints PDF.

    Les clés de traçabilité doivent être des champs valides d'AnalyzeResponse ET ne jamais
    chevaucher les noms de champs skill (sinon `got multiple values for keyword argument`).
    """
    from app.orchestrator.core import AnalyzeResponse

    champs_reponse = set(AnalyzeResponse.model_fields)
    assert _CLES_TRACE <= champs_reponse

    champs_skill = {
        "graham", "earnings_quality", "dorsey", "buffett", "valuation", "thesis",
        "munger", "canadian_tax", "lynch", "fisher", "klarman", "greenblatt",
        "damodaran", "marks", "pabrai", "esg",
    }
    assert _CLES_TRACE.isdisjoint(champs_skill)
