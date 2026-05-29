from __future__ import annotations

import logging
import os

logger = logging.getLogger(__name__)

_DEV_FALLBACK_SECRET = "dev-secret-change-in-production"
_DEV_ENVS = {"dev", "development", "test", "testing"}


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

    app_env = os.environ.get("APP_ENV", "").strip().lower()
    if app_env in _DEV_ENVS:
        logger.warning(
            "JWT_SECRET_KEY absent — repli sur le secret de développement (APP_ENV=%s)",
            app_env,
        )
        return _DEV_FALLBACK_SECRET

    raise RuntimeError(
        "JWT_SECRET_KEY est obligatoire hors développement. "
        "Définir JWT_SECRET_KEY (≥ 32 caractères) ou APP_ENV=dev pour le développement local."
    )
