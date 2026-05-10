from __future__ import annotations

import logging

from qdrant_client import AsyncQdrantClient
from qdrant_client.http.models import Distance, VectorParams

from app.skills.base import Citation

logger = logging.getLogger(__name__)

_DIMS = 1536


class RagClient:
    """Wrapper async autour de QdrantClient pour la recherche vectorielle."""

    def __init__(self, url: str, collection: str) -> None:
        self._client = AsyncQdrantClient(url=url)
        self._collection = collection

    async def ensure_collection(self) -> None:
        """Crée la collection si absente. Idempotent."""
        existing = await self._client.get_collections()
        names = {c.name for c in existing.collections}
        if self._collection not in names:
            await self._client.create_collection(
                collection_name=self._collection,
                vectors_config=VectorParams(size=_DIMS, distance=Distance.COSINE),
            )
            logger.warning(
                "Collection '%s' absente — créée vide. Lancer scripts/ingest_rag.py.",
                self._collection,
            )

    async def search(
        self, query_vector: list[float], k: int = 5
    ) -> list[Citation]:
        """Recherche les k chunks les plus proches et retourne des Citations."""
        results = await self._client.search(
            collection_name=self._collection,
            query_vector=query_vector,
            limit=k,
            with_payload=True,
        )
        return [
            Citation(
                source=r.payload["source_file"],
                extrait=r.payload["chunk_text"],
                score=r.score,
            )
            for r in results
        ]

    async def close(self) -> None:
        await self._client.close()
