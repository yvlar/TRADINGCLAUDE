from __future__ import annotations

from openai import AsyncOpenAI


class EmbeddingClient:
    """Wrapper async autour de l'API OpenAI pour text-embedding-3-small."""

    _MODEL = "text-embedding-3-small"

    def __init__(self, api_key: str) -> None:
        self._client = AsyncOpenAI(api_key=api_key)

    async def embed(self, text: str) -> list[float]:
        """Retourne le vecteur d'embedding pour un texte."""
        response = await self._client.embeddings.create(
            model=self._MODEL,
            input=text,
        )
        return response.data[0].embedding
