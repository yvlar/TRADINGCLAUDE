"""Tests pour l'endpoint GET /performance/{ticker} et la fonction _compute_rendement."""
from __future__ import annotations

import datetime
import uuid
from unittest.mock import AsyncMock

import pytest

from app.api.endpoints.performance import _compute_rendement, _extract_composite_score
from app.api.main import app

# ---------------------------------------------------------------------------
# Tests unitaires — _compute_rendement (logique pure, pas de mock nécessaire)
# ---------------------------------------------------------------------------


class TestRendementCalcul:
    def test_rendement_positif(self):
        """(120 - 100) / 100 * 100 = 20.0"""
        assert _compute_rendement(100.0, 120.0) == 20.0

    def test_rendement_negatif(self):
        """(80 - 100) / 100 * 100 = -20.0"""
        assert _compute_rendement(100.0, 80.0) == -20.0

    def test_rendement_nul(self):
        """Cours inchangé → 0.0"""
        assert _compute_rendement(100.0, 100.0) == 0.0

    def test_rendement_none_si_price_at_manquant(self):
        assert _compute_rendement(None, 120.0) is None

    def test_rendement_none_si_price_current_manquant(self):
        assert _compute_rendement(100.0, None) is None

    def test_rendement_none_si_price_at_zero(self):
        """Division par zéro protégée."""
        assert _compute_rendement(0.0, 120.0) is None

    def test_rendement_arrondi_deux_decimales(self):
        assert _compute_rendement(3.0, 4.0) == pytest.approx(33.33, abs=0.01)


# ---------------------------------------------------------------------------
# Tests unitaires — _extract_composite_score
# ---------------------------------------------------------------------------


class TestExtractCompositeScore:
    def test_extrait_score_present(self):
        result_json = '{"composite_score": {"score": 72.5, "label": "FORT"}}'
        assert _extract_composite_score(result_json) == 72.5

    def test_retourne_none_si_absent(self):
        assert _extract_composite_score("{}") is None

    def test_retourne_none_si_json_invalide(self):
        assert _extract_composite_score("not-json") is None

    def test_retourne_none_si_composite_score_pas_dict(self):
        assert _extract_composite_score('{"composite_score": null}') is None


# ---------------------------------------------------------------------------
# Tests d'intégration — endpoint GET /performance/{ticker}
# ---------------------------------------------------------------------------


_MOCK_ROW = {
    "id": uuid.UUID("550e8400-e29b-41d4-a716-446655440000"),
    "created_at": datetime.datetime(2026, 1, 15, 10, 0, 0, tzinfo=datetime.timezone.utc),
    "price_at_analysis": 100.0,
    "result": "{}",
    "workflow_name": "value_graham",
}

_MOCK_ROW_SANS_PRIX = {
    "id": uuid.UUID("550e8400-e29b-41d4-a716-446655440001"),
    "created_at": datetime.datetime(2026, 1, 10, 10, 0, 0, tzinfo=datetime.timezone.utc),
    "price_at_analysis": None,
    "result": "{}",
    "workflow_name": "value_graham",
}


class TestPerformanceEndpoint:
    async def test_performance_retourne_200(self, client):
        app.state.db_pool.fetch = AsyncMock(return_value=[_MOCK_ROW])
        app.state.yahoo_extractor.get_price = AsyncMock(return_value=120.0)

        r = await client.get("/performance/MSFT")
        assert r.status_code == 200

    async def test_performance_retourne_ticker_et_entries(self, client):
        app.state.db_pool.fetch = AsyncMock(return_value=[_MOCK_ROW])
        app.state.yahoo_extractor.get_price = AsyncMock(return_value=120.0)

        data = (await client.get("/performance/MSFT")).json()
        assert data["ticker"] == "MSFT"
        assert len(data["entries"]) == 1

    async def test_performance_calcule_rendement_positif(self, client):
        app.state.db_pool.fetch = AsyncMock(return_value=[_MOCK_ROW])
        app.state.yahoo_extractor.get_price = AsyncMock(return_value=120.0)

        entry = (await client.get("/performance/MSFT")).json()["entries"][0]
        assert entry["rendement_pct"] == 20.0

    async def test_performance_rendement_none_si_price_at_manquant(self, client):
        app.state.db_pool.fetch = AsyncMock(return_value=[_MOCK_ROW_SANS_PRIX])
        app.state.yahoo_extractor.get_price = AsyncMock(return_value=120.0)

        entry = (await client.get("/performance/MSFT")).json()["entries"][0]
        assert entry["rendement_pct"] is None
        assert entry["price_at_analysis"] is None

    async def test_performance_rendement_none_si_prix_actuel_indisponible(self, client):
        app.state.db_pool.fetch = AsyncMock(return_value=[_MOCK_ROW])
        app.state.yahoo_extractor.get_price = AsyncMock(return_value=None)

        entry = (await client.get("/performance/MSFT")).json()["entries"][0]
        assert entry["rendement_pct"] is None
        assert entry["price_current"] is None

    async def test_performance_ticker_inconnu_retourne_liste_vide(self, client):
        app.state.db_pool.fetch = AsyncMock(return_value=[])
        app.state.yahoo_extractor.get_price = AsyncMock(return_value=None)

        data = (await client.get("/performance/NODB")).json()
        assert data["entries"] == []

    async def test_performance_ticker_invalide_retourne_422(self, client):
        r = await client.get("/performance/invalid ticker!")
        assert r.status_code == 422

    async def test_performance_retourne_price_current(self, client):
        app.state.db_pool.fetch = AsyncMock(return_value=[_MOCK_ROW])
        app.state.yahoo_extractor.get_price = AsyncMock(return_value=85.0)

        entry = (await client.get("/performance/MSFT")).json()["entries"][0]
        assert entry["price_current"] == 85.0
        assert entry["rendement_pct"] == pytest.approx(-15.0, abs=0.01)
