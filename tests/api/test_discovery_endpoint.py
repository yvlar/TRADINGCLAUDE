"""Tests d'intégration des endpoints GET /discovery/* (service mocké via app.state)."""
from __future__ import annotations

from unittest.mock import AsyncMock

import pytest
from fastapi import HTTPException

from app.api.main import app
from app.models.discovery import (
    CategorySummary,
    DiscoveryCategoryResponse,
    DiscoverySuggestion,
)

_AS_OF = "2026-06-11T06:00:00+00:00"


def _summary() -> CategorySummary:
    return CategorySummary(
        id="solides_stables",
        titre="Solides et stables",
        emoji="🟢",
        description="Entreprises établies.",
        niveau_risque="faible",
        nb_suggestions=8,
        as_of=_AS_OF,
    )


def _category_response() -> DiscoveryCategoryResponse:
    return DiscoveryCategoryResponse(
        id="solides_stables",
        titre="Solides et stables",
        emoji="🟢",
        description="Entreprises établies.",
        niveau_risque="faible",
        account_hint="CELI ou non enregistré.",
        as_of=_AS_OF,
        suggestions=[
            DiscoverySuggestion(
                ticker="RY.TO",
                name="Banque Royale du Canada",
                composite_score=78.0,
                composite_label="FORT",
                risk_badge="faible",
                why="Banque Royale du Canada : entreprise établie.",
                dividend_yield=0.041,
                dividend_years=10,
                pe=11.2,
                price=82.40,
                account_hint="CELI ou non enregistré.",
                as_of=_AS_OF,
            )
        ],
    )


@pytest.fixture
def mock_discovery_service():
    service = AsyncMock()
    service.list_categories = AsyncMock(return_value=[_summary()])
    service.get_category = AsyncMock(return_value=_category_response())
    app.state.discovery_service = service
    yield service
    app.state.discovery_service = None


@pytest.mark.asyncio
async def test_list_categories_200(client, mock_discovery_service):
    resp = await client.get("/discovery/categories")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["categories"]) == 1
    assert data["categories"][0]["id"] == "solides_stables"
    assert data["categories"][0]["nb_suggestions"] == 8


@pytest.mark.asyncio
async def test_get_category_200(client, mock_discovery_service):
    resp = await client.get("/discovery/solides_stables")
    assert resp.status_code == 200
    data = resp.json()
    assert data["titre"] == "Solides et stables"
    assert data["suggestions"][0]["ticker"] == "RY.TO"
    assert data["suggestions"][0]["risk_badge"] == "faible"
    mock_discovery_service.get_category.assert_awaited_once_with("solides_stables")


@pytest.mark.asyncio
async def test_get_category_inconnue_404(client, mock_discovery_service):
    mock_discovery_service.get_category = AsyncMock(
        side_effect=HTTPException(status_code=404, detail="Catégorie inconnue : nope")
    )
    resp = await client.get("/discovery/nope")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_service_absent_503(client):
    app.state.discovery_service = None
    resp = await client.get("/discovery/categories")
    assert resp.status_code == 503


@pytest.mark.asyncio
async def test_erreur_interne_500_sanitisee(client, mock_discovery_service):
    mock_discovery_service.list_categories = AsyncMock(side_effect=RuntimeError("DB down"))
    resp = await client.get("/discovery/categories")
    assert resp.status_code == 500
    # le détail interne ne fuit pas dans la réponse (error_sanitization)
    assert "DB down" not in resp.text
