"""Modèles Pydantic de la découverte par catégorie (page débutant).

Les suggestions sont une donnée de référence GLOBALE (mêmes listes pour tous les
tenants, comme `plan_limits`) — aucun champ tenant, aucun scope RLS.
"""
from __future__ import annotations

from pydantic import BaseModel, Field


class UniverseEntry(BaseModel):
    """Un titre de l'univers d'une catégorie — nom d'affichage contrôlé en config."""

    ticker: str
    name: str


class DiscoveryCategoryConfig(BaseModel):
    """Définition d'une catégorie chargée depuis app/config/discovery_categories.json."""

    id: str
    titre: str
    emoji: str
    description: str
    niveau_risque: str  # "faible" | "moyen" | "élevé"
    workflow: str
    min_composite_score: float
    min_dividend_years: int
    max_suggestions: int
    account_hint: str
    univers: list[UniverseEntry]


class CategorySummary(BaseModel):
    """Métadonnées d'une catégorie pour la grille de cartes (sans les suggestions)."""

    id: str
    titre: str
    emoji: str
    description: str
    niveau_risque: str
    nb_suggestions: int = 0
    as_of: str | None = None  # date ISO du dernier rafraîchissement, None si jamais calculé


class DiscoverySuggestion(BaseModel):
    """Un titre suggéré dans une catégorie — entièrement précalculé (aucun appel live)."""

    ticker: str
    name: str
    composite_score: float | None = None
    composite_label: str | None = None
    risk_badge: str  # "faible" | "moyen" | "élevé"
    why: str
    dividend_yield: float | None = None
    dividend_years: int | None = None
    pe: float | None = None
    price: float | None = None
    account_hint: str
    as_of: str  # date ISO du calcul


class DiscoveryCategoriesResponse(BaseModel):
    """Réponse de GET /discovery/categories."""

    categories: list[CategorySummary]


class DiscoveryCategoryResponse(BaseModel):
    """Réponse de GET /discovery/{category_id}."""

    id: str
    titre: str
    emoji: str
    description: str
    niveau_risque: str
    account_hint: str
    as_of: str | None = None
    suggestions: list[DiscoverySuggestion] = Field(default_factory=list)
