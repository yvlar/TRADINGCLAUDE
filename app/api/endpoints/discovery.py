"""Endpoints découverte par catégorie — page « Découvrir » pour débutants.

Lecture seule du précalculé (`discovery_suggestions`) : aucun appel Claude ni
yfinance sur le chemin requête. Le rafraîchissement vit dans le worker Celery
(`run_discovery_refresh`). Design : docs/design-decouverte-debutant.md.
"""
from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException, Request

from app.models.discovery import DiscoveryCategoriesResponse, DiscoveryCategoryResponse
from app.services.discovery_service import DiscoveryService
from app.utils.error_sanitization import sanitized_http_500

logger = logging.getLogger(__name__)

router = APIRouter()


def _get_service(request: Request) -> DiscoveryService:
    service: DiscoveryService | None = getattr(request.app.state, "discovery_service", None)
    if service is None:
        raise HTTPException(status_code=503, detail="Service de découverte indisponible")
    return service


@router.get(
    "/discovery/categories",
    response_model=DiscoveryCategoriesResponse,
    summary="Liste des catégories de découverte",
    description=(
        "Grille de cartes de la page Découvrir : catégories en langage débutant "
        "avec compteur de suggestions et date du dernier rafraîchissement."
    ),
)
async def list_discovery_categories(request: Request) -> DiscoveryCategoriesResponse:
    service = _get_service(request)
    try:
        return DiscoveryCategoriesResponse(categories=await service.list_categories())
    except HTTPException:
        raise
    except Exception as exc:
        raise sanitized_http_500(exc, logger, "Erreur listage catégories découverte") from exc


@router.get(
    "/discovery/{category_id}",
    response_model=DiscoveryCategoryResponse,
    summary="Suggestions précalculées d'une catégorie",
    description=(
        "Titres de qualité d'une catégorie (gate composite + earnings + dividende), "
        "avec badge de risque, phrase « pourquoi » et indication de compte. "
        "404 si la catégorie est inconnue ; liste vide si pas encore rafraîchie."
    ),
)
async def get_discovery_category(request: Request, category_id: str) -> DiscoveryCategoryResponse:
    service = _get_service(request)
    try:
        return await service.get_category(category_id)
    except HTTPException:
        raise
    except Exception as exc:
        raise sanitized_http_500(
            exc, logger, f"Erreur lecture catégorie découverte {category_id}"
        ) from exc
