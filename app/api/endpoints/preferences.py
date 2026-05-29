from __future__ import annotations

import logging

from fastapi import APIRouter, Request
from pydantic import ValidationError

from app.api.endpoints.auth import _get_current_user
from app.models.preferences import ScreenerPreferences
from app.services.user_preferences_service import get_preference, upsert_preference

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/preferences", tags=["preferences"])

# Clé de stockage dans user_preferences pour les préférences du Screener
_SCREENER_KEY = "screener"


@router.get("/screener", response_model=ScreenerPreferences)
async def get_screener_preferences(request: Request) -> ScreenerPreferences:
    """Retourne le tri + les filtres Screener de l'utilisateur authentifié (401 sinon)."""
    payload = await _get_current_user(request)
    stored = await get_preference(request.app.state.db_pool, payload["sub"], _SCREENER_KEY)
    if stored is None:
        return ScreenerPreferences()
    try:
        return ScreenerPreferences.model_validate(stored)
    except ValidationError:
        # Préférence héritée/corrompue : traiter comme absente (le client retombe sur localStorage)
        logger.warning("Préférence Screener illisible — ignorée")
        return ScreenerPreferences()


@router.put("/screener", response_model=ScreenerPreferences)
async def put_screener_preferences(
    body: ScreenerPreferences, request: Request
) -> ScreenerPreferences:
    """Persiste le tri + les filtres Screener pour l'utilisateur authentifié (401 sinon)."""
    payload = await _get_current_user(request)
    await upsert_preference(
        request.app.state.db_pool, payload["sub"], _SCREENER_KEY, body.model_dump()
    )
    return body
