from __future__ import annotations

import hashlib
import logging
import uuid
from datetime import datetime, timedelta, timezone
from uuid import UUID

import asyncpg
import jwt
import redis.asyncio as aioredis

from app.utils.jwt_secret import resolve_jwt_secret

logger = logging.getLogger(__name__)

_ALGORITHM = "HS256"
_ACCESS_TOKEN_TTL_MIN = 15
_REFRESH_TOKEN_TTL_DAYS = 30
_REFRESH_TOKEN_REMEMBER_TTL_DAYS = 90


def _sha256(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


class AuthTokenService:
    """Génération et validation des JWT access tokens et refresh tokens UUID."""

    def __init__(self, db_pool: asyncpg.Pool, redis_client: aioredis.Redis) -> None:
        self._pool = db_pool
        self._redis = redis_client
        self._secret = resolve_jwt_secret()

    def create_access_token(self, user_id: UUID, email: str, role: str) -> str:
        """Crée un JWT HS256 avec TTL de 15 minutes."""
        now = datetime.now(timezone.utc)
        jti = str(uuid.uuid4())
        payload = {
            "sub": str(user_id),
            "email": email,
            "role": role,
            "jti": jti,
            "iat": now,
            "exp": now + timedelta(minutes=_ACCESS_TOKEN_TTL_MIN),
        }
        return jwt.encode(payload, self._secret, algorithm=_ALGORITHM)

    def decode_access_token(self, token: str) -> dict | None:
        """Décode et valide un JWT. Retourne None si invalide ou expiré."""
        try:
            # require exp/sub : un token valide ne peut être accepté sans expiration
            # ni sujet (défense en profondeur — revue E1-S4).
            payload = jwt.decode(
                token,
                self._secret,
                algorithms=[_ALGORITHM],
                options={"require": ["exp", "sub"]},
            )
            return payload
        except jwt.PyJWTError:
            return None

    async def is_jti_blacklisted(self, jti: str) -> bool:
        """Vérifie si un JTI est blacklisté ; fail-closed si Redis est indisponible."""
        try:
            result = await self._redis.get(f"blacklist:jti:{jti}")
        except Exception:
            # fail-closed : en cas de doute (panne Redis), on refuse le token plutôt
            # que d'ouvrir l'accès — l'inverse du rate-limiting qui tolère fail-open
            logger.warning("Vérification blacklist JTI impossible (Redis) — token refusé par défaut")
            return True
        return result is not None

    async def blacklist_jti(self, jti: str, ttl_seconds: int) -> None:
        """Ajoute un JTI à la blacklist Redis avec TTL = durée restante du token."""
        if ttl_seconds > 0:
            await self._redis.setex(f"blacklist:jti:{jti}", ttl_seconds, "1")

    async def create_refresh_token(
        self,
        user_id: UUID,
        family: UUID | None = None,
        remember_me: bool = False,
    ) -> str:
        """Génère un refresh token UUID opaque, le stocke haché en DB."""
        token = str(uuid.uuid4())
        token_hash = _sha256(token)
        token_family = family or uuid.uuid4()
        ttl_days = _REFRESH_TOKEN_REMEMBER_TTL_DAYS if remember_me else _REFRESH_TOKEN_TTL_DAYS
        expires_at = datetime.now(timezone.utc) + timedelta(days=ttl_days)

        await self._pool.execute(
            """
            INSERT INTO refresh_tokens (user_id, token_hash, family, expires_at)
            VALUES ($1, $2, $3, $4)
            """,
            user_id,
            token_hash,
            token_family,
            expires_at,
        )
        return token

    async def rotate_refresh_token(self, old_token: str) -> tuple[str, UUID] | None:
        """
        Rotation : invalide l'ancien token, crée un nouveau dans la même famille.

        Retourne (nouveau_token, user_id) ou None si le token est invalide/utilisé.
        Si le token est déjà marqué used → vol détecté → invalide toute la famille.
        """
        old_hash = _sha256(old_token)
        row = await self._pool.fetchrow(
            "SELECT id, user_id, family, used, expires_at FROM refresh_tokens WHERE token_hash = $1",
            old_hash,
        )

        if row is None:
            return None

        # Détection de réutilisation — vol potentiel détecté
        if row["used"]:
            logger.warning(
                "Réutilisation de refresh token détectée pour user %s — famille %s invalidée",
                row["user_id"],
                row["family"],
            )
            await self._pool.execute(
                "DELETE FROM refresh_tokens WHERE family = $1",
                row["family"],
            )
            return None

        if datetime.now(timezone.utc) > row["expires_at"]:
            await self._pool.execute("DELETE FROM refresh_tokens WHERE id = $1", row["id"])
            return None

        # Marquer l'ancien comme utilisé
        await self._pool.execute(
            "UPDATE refresh_tokens SET used = TRUE WHERE id = $1",
            row["id"],
        )

        new_token = await self.create_refresh_token(
            user_id=row["user_id"],
            family=row["family"],
        )
        return new_token, UUID(str(row["user_id"]))

    async def invalidate_refresh_token(self, token: str) -> None:
        """Supprime le refresh token de la DB (logout)."""
        token_hash = _sha256(token)
        await self._pool.execute(
            "DELETE FROM refresh_tokens WHERE token_hash = $1",
            token_hash,
        )

    async def invalidate_all_user_tokens(self, user_id: UUID) -> None:
        """Supprime tous les refresh tokens d'un utilisateur (déconnexion totale)."""
        await self._pool.execute(
            "DELETE FROM refresh_tokens WHERE user_id = $1",
            user_id,
        )
