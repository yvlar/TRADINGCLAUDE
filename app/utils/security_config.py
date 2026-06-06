from __future__ import annotations

import logging

from app.utils.env import is_dev_environment

logger = logging.getLogger(__name__)

# Identifiants par défaut du compose de développement — interdits en production.
_INSECURE_DB_CREDENTIALS = ("copilote:copilote@",)


def require_secure_db_url(db_url: str) -> None:
    """Refuse au boot une URL PostgreSQL aux identifiants par défaut hors dev.

    Le mot de passe `copilote` du compose de développement ne doit jamais atteindre
    la production : un secret deviné = accès direct à toutes les données tenant.
    APP_ENV absent est traité comme production (défaut sûr).
    """
    if is_dev_environment():
        return
    if any(marker in db_url for marker in _INSECURE_DB_CREDENTIALS):
        raise RuntimeError(
            "Identifiants PostgreSQL par défaut détectés hors développement. "
            "Définir un POSTGRES_PASSWORD/DATABASE_URL généré (≠ 'copilote') "
            "ou APP_ENV=dev pour le développement local."
        )
