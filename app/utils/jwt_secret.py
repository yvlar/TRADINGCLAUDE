from __future__ import annotations

import logging
import os

from app.utils.env import is_dev_environment

logger = logging.getLogger(__name__)

_DEV_FALLBACK_SECRET = "dev-secret-change-in-production"


def resolve_jwt_secret() -> str:
    """Retourne le secret JWT signataire ; lève RuntimeError hors dev/test si absent.

    Fail-fast en production : un `JWT_SECRET_KEY` absent ferait signer tous les
    tokens HS256 avec une valeur publique connue → bypass d'authentification
    complet. Le repli de développement n'est toléré que si `APP_ENV` vaut
    explicitement un environnement non-production (dev/test). APP_ENV absent est
    traité comme production (refus) — le défaut sûr.
    """
    secret = os.environ.get("JWT_SECRET_KEY", "")
    if secret:
        return secret

    if is_dev_environment():
        logger.warning(
            "JWT_SECRET_KEY absent — repli sur le secret de développement (APP_ENV non-prod)",
        )
        return _DEV_FALLBACK_SECRET

    raise RuntimeError(
        "JWT_SECRET_KEY est obligatoire hors développement. "
        "Définir JWT_SECRET_KEY (≥ 32 caractères) ou APP_ENV=dev pour le développement local."
    )
