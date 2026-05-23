from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, ClassVar

from pydantic import BaseModel


@dataclass
class SkillConfig:
    """
    Configuration partagée par tous les skills Tier 2.
    Injectée depuis le lifespan FastAPI — un seul objet créé au démarrage.
    """

    timeout_s: float = 60.0
    max_retries: int = 3
    tracer: Any = None  # LangfuseTracer | None — Any pour éviter l'import circulaire


class Citation(BaseModel):
    """Référence RAG retournée par get_citations. Liste vide en Phase 0."""

    source: str
    extrait: str
    score: float


class UsageDetail(BaseModel):
    """Compteurs de tokens et coût d'un appel Claude — remontés par execute()."""

    tokens_input: int
    tokens_output: int
    tokens_cache_read: int
    tokens_cache_creation: int
    cost_usd: float
    model: str


class SkillBase(ABC):
    """Classe de base dont héritent tous les skills Tier 2 (section 3.2)."""

    skill_id: ClassVar[str]
    tier: ClassVar[int]
    description: ClassVar[str]

    @abstractmethod
    async def execute(self, input_data: BaseModel) -> tuple[BaseModel, UsageDetail]:
        """Exécute le skill via l'API Claude. Retourne (output, usage_detail)."""
        ...

    def get_system_prompt(self) -> list[dict[str, Any]]:
        """Retourne le system prompt formaté avec cache_control (section 8.2)."""
        raise NotImplementedError

    async def get_citations(self, query: str, k: int = 5) -> list[Citation]:
        """Recherche RAG dans Qdrant. Retourne une liste vide en Phase 0."""
        return []
