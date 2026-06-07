from __future__ import annotations

import logging
from uuid import UUID

import asyncpg
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError

from app.models.tenant import LEGACY_TENANT_ID

logger = logging.getLogger(__name__)

# Paramètres argon2 conformes à la spec : temps CPU=2, mémoire=64 Mo, parallélisme=2
_ph = PasswordHasher(time_cost=2, memory_cost=65536, parallelism=2)


class EmailAlreadyExistsError(Exception):
    pass


class UserService:
    """Gestion des comptes utilisateurs : inscription, authentification, lookup."""

    def __init__(self, db_pool: asyncpg.Pool) -> None:
        self._pool = db_pool

    async def create_user(
        self, email: str, password: str, tenant_id: UUID | None = None
    ) -> dict:
        """Crée un compte utilisateur ; à défaut de tenant_id, rattache au tenant legacy."""
        hashed = _ph.hash(password)
        tenant = tenant_id or LEGACY_TENANT_ID
        try:
            # Sous-requête corrélée sur la ligne insérée : un seul aller-retour pour
            # le nom du tenant (INSERT ... RETURNING ne peut pas faire de JOIN).
            row = await self._pool.fetchrow(
                """
                INSERT INTO users (email, hashed_password, tenant_id)
                VALUES (LOWER($1), $2, $3)
                RETURNING id, email, role, tenant_id, created_at,
                          (SELECT name FROM tenants WHERE id = users.tenant_id)
                              AS tenant_name
                """,
                email,
                hashed,
                tenant,
            )
        except asyncpg.UniqueViolationError:
            raise EmailAlreadyExistsError(f"Email déjà utilisé : {email}")
        return dict(row)

    async def authenticate(self, email: str, password: str) -> dict | None:
        """
        Vérifie les identifiants. Retourne None si invalides (timing-safe via argon2).

        Exécute toujours le hash verify pour résister aux attaques par timing.
        """
        row = await self._pool.fetchrow(
            "SELECT u.id, u.email, u.hashed_password, u.role, u.is_active, u.tenant_id, "
            "u.created_at, t.name AS tenant_name "
            "FROM users u JOIN tenants t ON u.tenant_id = t.id WHERE u.email = LOWER($1)",
            email,
        )

        # Toujours hasher un dummy si l'utilisateur n'existe pas (timing-safe)
        dummy_hash = "$argon2id$v=19$m=65536,t=2,p=2$dummy$dummy"
        candidate_hash = row["hashed_password"] if row else dummy_hash

        try:
            _ph.verify(candidate_hash, password)
            valid = True
        except VerifyMismatchError:
            valid = False
        except Exception:
            valid = False

        if not valid or row is None or not row["is_active"]:
            return None

        return dict(row)

    async def get_by_id(self, user_id: UUID) -> dict | None:
        """Retourne un utilisateur (avec le nom de son tenant) par UUID, ou None."""
        row = await self._pool.fetchrow(
            "SELECT u.id, u.email, u.role, u.is_active, u.tenant_id, u.created_at, "
            "t.name AS tenant_name "
            "FROM users u JOIN tenants t ON u.tenant_id = t.id WHERE u.id = $1",
            user_id,
        )
        return dict(row) if row else None

    async def update_last_login(self, user_id: UUID) -> None:
        """Met à jour le timestamp de dernière connexion."""
        await self._pool.execute(
            "UPDATE users SET last_login_at = NOW() WHERE id = $1",
            user_id,
        )

    async def get_hashed_password(self, user_id: UUID) -> str | None:
        """Retourne le hash courant du mot de passe (utilisé pour invalider les tokens reset)."""
        row = await self._pool.fetchrow(
            "SELECT hashed_password FROM users WHERE id = $1",
            user_id,
        )
        return row["hashed_password"] if row else None

    async def update_password(self, user_id: UUID, new_password: str) -> None:
        """Réinitialise le mot de passe avec un nouveau hash argon2."""
        new_hash = _ph.hash(new_password)
        await self._pool.execute(
            "UPDATE users SET hashed_password = $1 WHERE id = $2",
            new_hash,
            user_id,
        )
        logger.info("Mot de passe mis à jour pour user %s", user_id)
