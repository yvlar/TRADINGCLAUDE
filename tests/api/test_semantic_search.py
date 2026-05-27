"""Tests Sprint 106 — GET /semantic-search."""
from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from app.api.main import app as fastapi_app
from app.rag.service import RagService
from app.skills.base import Citation


def _make_citation(
    source: str = "graham-stock-screening/references/graham-defensif.md",
    extrait: str = "L'investisseur défensif applique 8 critères stricts.",
    score: float = 0.91,
) -> Citation:
    return Citation(source=source, extrait=extrait, score=score)


# ---------------------------------------------------------------------------
# Test 1 : 200 avec résultats quand le RAG est activé
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_semantic_search_200_avec_resultats(client):
    """GET /semantic-search?q=... → 200, rag_enabled=true, résultats mappés."""
    mock_service = AsyncMock(spec=RagService)
    mock_service.search.return_value = [
        _make_citation(score=0.92),
        _make_citation(source="buffett-quality-investing/SKILL.md", score=0.81),
    ]
    fastapi_app.state.rag_service = mock_service

    resp = await client.get("/semantic-search?q=marge de securite")

    assert resp.status_code == 200
    data = resp.json()
    assert data["query"] == "marge de securite"
    assert data["rag_enabled"] is True
    assert len(data["results"]) == 2
    assert data["results"][0]["score"] == 0.92
    assert "source" in data["results"][0]
    assert "extrait" in data["results"][0]
    mock_service.search.assert_awaited_once_with("marge de securite", k=5)


# ---------------------------------------------------------------------------
# Test 2 : rag_enabled=false quand le RAG est désactivé (rag_service None)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_semantic_search_rag_desactive(client):
    """RAG désactivé (OPENAI_API_KEY absente) → 200, rag_enabled=false, results=[]."""
    fastapi_app.state.rag_service = None

    resp = await client.get("/semantic-search?q=moat economique")

    assert resp.status_code == 200
    data = resp.json()
    assert data["rag_enabled"] is False
    assert data["results"] == []


# ---------------------------------------------------------------------------
# Test 3 : paramètre k propagé au service
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_semantic_search_k_propage(client):
    """Le paramètre k est transmis à rag_service.search()."""
    mock_service = AsyncMock(spec=RagService)
    mock_service.search.return_value = [_make_citation()]
    fastapi_app.state.rag_service = mock_service

    resp = await client.get("/semantic-search?q=accruals Sloan&k=3")

    assert resp.status_code == 200
    mock_service.search.assert_awaited_once_with("accruals Sloan", k=3)


# ---------------------------------------------------------------------------
# Test 4 : 422 si query absente ou trop courte
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_semantic_search_422_query_absente(client):
    """GET /semantic-search sans q → 422."""
    resp = await client.get("/semantic-search")
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_semantic_search_422_query_trop_courte(client):
    """q d'un seul caractère → 422 (min_length=2)."""
    resp = await client.get("/semantic-search?q=a")
    assert resp.status_code == 422
