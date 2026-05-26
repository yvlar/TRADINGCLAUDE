"""Endpoint Sprint 106 — GET /semantic-search.

Expose la recherche sémantique RAG (collection investment_knowledge) au frontend.
Retourne les passages de référence les plus proches avec leur citation.
rag_service est None si OPENAI_API_KEY est absente → rag_enabled=false, results=[].
"""
from __future__ import annotations

import logging

from fastapi import APIRouter, Query, Request
from pydantic import BaseModel

from app.rag.service import RagService
from app.skills.base import Citation

logger = logging.getLogger(__name__)

router = APIRouter()


class SemanticSearchResponse(BaseModel):
    """Réponse de GET /semantic-search."""

    query: str
    rag_enabled: bool
    results: list[Citation]


@router.get(
    "/semantic-search",
    response_model=SemanticSearchResponse,
    summary="Recherche sémantique dans le corpus RAG",
    description=(
        "Recherche en langage naturel dans la base de connaissances investissement "
        "(formules, seuils, frameworks). Retourne les k passages les plus proches "
        "avec source et score de similarité. rag_enabled=false si le RAG est "
        "désactivé (OPENAI_API_KEY absente)."
    ),
)
async def semantic_search(
    request: Request,
    q: str = Query(..., min_length=2, max_length=500),
    k: int = Query(default=5, ge=1, le=20),
) -> SemanticSearchResponse:
    rag_service: RagService | None = getattr(request.app.state, "rag_service", None)
    if rag_service is None:
        return SemanticSearchResponse(query=q, rag_enabled=False, results=[])
    results = await rag_service.search(q, k=k)
    return SemanticSearchResponse(query=q, rag_enabled=True, results=results)
