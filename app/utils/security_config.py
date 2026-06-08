from __future__ import annotations

import logging
import os

from app.utils.env import is_dev_environment

logger = logging.getLogger(__name__)

# Identifiants par défaut du compose de développement — interdits en production.
_INSECURE_DB_CREDENTIALS = ("copilote:copilote@",)

# DSN de repli du compose de dev — rôle `copilote` (SUPERUSER+BYPASSRLS, propriétaire).
_DEFAULT_DB_URL = "postgresql://copilote:copilote@postgres:5432/copilote"


def resolve_app_database_url() -> str:
    """DSN de connexion des pools runtime (API + workers) — rôle `app_runtime`, RLS active.

    `app_runtime` est `NOSUPERUSER`/`NOBYPASSRLS`/non-propriétaire : il **subit** les policies
    RLS multi-tenant. À l'inverse, `DATABASE_URL` porte le rôle `copilote`
    (SUPERUSER+BYPASSRLS) réservé aux migrations Alembic — s'y connecter au runtime rendrait
    **toute** policy RLS inerte. D'où la variable dédiée `APP_DATABASE_URL`.

    Hors dev : son absence est **fatale** (fail-closed — ne jamais démarrer le runtime sous le
    rôle propriétaire en prod). En dev/test : repli sur `DATABASE_URL` (le rôle `copilote` local
    suffit, aucune RLS réelle à isoler).
    """
    app_url = os.environ.get("APP_DATABASE_URL")
    if app_url:
        return app_url
    if is_dev_environment():
        return os.environ.get("DATABASE_URL") or _DEFAULT_DB_URL
    raise RuntimeError(
        "APP_DATABASE_URL absente hors développement — le runtime doit se connecter avec le rôle "
        "app_runtime (NOSUPERUSER/NOBYPASSRLS) pour que la RLS multi-tenant soit active. Définir "
        "APP_DATABASE_URL, ou APP_ENV=dev en local."
    )


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
