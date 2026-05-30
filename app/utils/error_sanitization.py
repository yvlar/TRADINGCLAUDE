from __future__ import annotations

import logging
from uuid import uuid4

from fastapi import HTTPException


def log_internal_error(exc: Exception, logger: logging.Logger, context: str) -> str:
    """Log le détail complet côté serveur, corrélé par un identifiant, et le retourne.

    Le détail brut (`str(exc)`) peut exposer des contraintes DB (ex. unicité email →
    énumération d'utilisateurs) — il ne sort jamais dans le body HTTP/SSE, seulement
    dans les logs serveur. Le `correlation_id` permet de relier la réponse au log.
    """
    correlation_id = str(uuid4())
    logger.error("%s [correlation_id=%s]", context, correlation_id, exc_info=exc)
    return correlation_id


def sanitized_http_500(exc: Exception, logger: logging.Logger, context: str) -> HTTPException:
    """Construit une HTTPException 500 au body générique ; log le détail serveur-side."""
    correlation_id = log_internal_error(exc, logger, context)
    return HTTPException(
        status_code=500,
        detail=f"Erreur interne (correlation_id={correlation_id})",
    )
