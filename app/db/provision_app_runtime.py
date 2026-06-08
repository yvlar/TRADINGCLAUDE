"""Provisionne le mot de passe de connexion du rôle runtime `app_runtime` (Ops S182).

La migration `0011` crée le rôle `app_runtime` **sans mot de passe** (hygiène secrets : aucun
secret en version). Ce module pose son mot de passe de connexion au boot, depuis le mot de passe
porté par `APP_DATABASE_URL` (source unique — exactement celui avec lequel le runtime se
connectera), via le rôle superuser de `DATABASE_URL` (réservé aux migrations/ops).

Idempotent (`ALTER ROLE` rejoué sans effet de bord). **No-op** si `APP_DATABASE_URL` est absente
(dev sous repli `DATABASE_URL`) ou sans mot de passe. Le mot de passe n'apparaît jamais dans le
texte SQL ni les logs : il transite comme paramètre lié vers un GUC de transaction lu par
`format('%L', …)` côté serveur.
"""
from __future__ import annotations

import asyncio
import logging
import os
from urllib.parse import unquote, urlsplit

import asyncpg

from app.utils.security_config import _DEFAULT_DB_URL

logger = logging.getLogger(__name__)

_ROLE = "app_runtime"


def _extract_password(dsn: str) -> str | None:
    """Mot de passe (décodé) porté par une DSN PostgreSQL, ou None s'il est absent."""
    encoded = urlsplit(dsn).password
    return unquote(encoded) if encoded else None


async def provision() -> bool:
    """Pose le mot de passe de `app_runtime` depuis `APP_DATABASE_URL`. Retourne True si posé."""
    app_url = os.environ.get("APP_DATABASE_URL")
    if not app_url:
        logger.info("APP_DATABASE_URL absente — repli dev, provisionnement de %s ignoré", _ROLE)
        return False
    password = _extract_password(app_url)
    if not password:
        logger.warning("APP_DATABASE_URL sans mot de passe — provisionnement de %s ignoré", _ROLE)
        return False

    admin_url = os.environ.get("DATABASE_URL") or _DEFAULT_DB_URL
    conn = await asyncpg.connect(admin_url)
    try:
        # Mot de passe en paramètre lié → GUC de transaction → format('%L') côté serveur : jamais
        # concaténé dans le texte SQL (anti-injection + jamais loggé). is_local=true : portée txn.
        async with conn.transaction():
            await conn.execute("SELECT set_config('app.provision_pwd', $1, true)", password)
            await conn.execute(
                f"DO $$ BEGIN EXECUTE format('ALTER ROLE {_ROLE} LOGIN PASSWORD %L', "
                "current_setting('app.provision_pwd')); END $$;"
            )
        logger.info("Mot de passe du rôle %s provisionné", _ROLE)
        return True
    finally:
        await conn.close()


if __name__ == "__main__":  # pragma: no cover
    logging.basicConfig(level=os.environ.get("LOG_LEVEL", "INFO"))
    asyncio.run(provision())
