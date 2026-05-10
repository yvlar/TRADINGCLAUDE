from __future__ import annotations

import logging

from app.rag.client import RagClient
from app.rag.embeddings import EmbeddingClient
from app.skills.base import Citation

logger = logging.getLogger(__name__)


class RagService:
    """Façade utilisée par les skills : embed la query, cherche dans Qdrant."""

    def __init__(self, rag_client: RagClient, embedder: EmbeddingClient) -> None:
        self._rag = rag_client
        self._embedder = embedder

    async def search(self, query: str, k: int = 5) -> list[Citation]:
        """Recherche sémantique dans le corpus RAG."""
        try:
            vector = await self._embedder.embed(query)
            return await self._rag.search(vector, k=k)
        except Exception:
            logger.exception("Erreur RAG lors de la recherche — citations vides retournées")
            return []
