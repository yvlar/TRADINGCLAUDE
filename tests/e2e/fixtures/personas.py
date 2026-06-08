"""Personas de test E2E + service utilisateur en mémoire.

Le harnais E2E mocke `asyncpg.create_pool` par un pool générique qui ne sait pas
authentifier un vrai compte. Sans remplacement, le flux email/mot de passe + JWT
cookie échoue (authenticate → None → 401), et `AuthContext.authMe()` redirige
toujours vers /login. `InMemoryUserService` rejoue fidèlement le contrat de
`UserService` (argon2 réel) pour que le parcours d'auth traverse réellement le
navigateur, tout en restant déterministe et sans PostgreSQL.
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from uuid import UUID

from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError

# Mêmes paramètres que app/services/user_service.py — parité de comportement.
_ph = PasswordHasher(time_cost=2, memory_cost=65536, parallelism=2)
# Hash factice VALIDE (vrai argon2) pour le chemin timing-safe : vérifier un mot de
# passe contre lui lève VerifyMismatchError (rattrapé), pas InvalidHash (→ 500).
_DUMMY_HASH = _ph.hash("dummy-timing-safe-constant")


@dataclass(frozen=True)
class Persona:
    """Identité de test réutilisable à travers les suites E2E.

    `history_volume` n'est pas persisté côté backend (le pool est mocké) : il
    documente le volume d'historique que les tests simuleront via interception
    réseau (`helpers.network.mock_json`).
    """

    cle: str
    email: str
    password: str
    role: str = "reader"
    is_active: bool = True
    label: str = ""
    description: str = ""
    history_volume: int = 0


# Mot de passe conforme à la politique d'inscription (≥ 12, maj/min/chiffre/spécial).
_DEFAULT_PWD = "Test1234!@#$"

# Nom du tenant legacy — `tenants.name` du backfill (`0003_tenants.py`). Le vrai `UserService`
# résout ce nom par JOIN (Sprint 169) ; les endpoints lisent `user["tenant_name"]` (accès direct,
# pas `.get`) → l'absence de la clé lèverait un KeyError → 500 et casserait tout le flux d'auth E2E.
_LEGACY_TENANT_NAME = "Legacy"

# Plan par défaut du tenant — `tenants.plan DEFAULT 'free'` (`0007_plan_limits.py`). Le vrai
# `UserService` le résout par JOIN (Sprint 173) ; les endpoints lisent `user["plan"]` (accès
# direct, pas `.get` — `auth.py` /me/login/register) → l'absence de la clé lèverait un KeyError
# → 500 et casserait tout le flux d'auth E2E (même piège que `tenant_name`, régression S173).
_DEFAULT_PLAN = "free"

PERSONAS: dict[str, Persona] = {
    "empty": Persona(
        cle="empty",
        email="vide@example.com",
        password=_DEFAULT_PWD,
        role="reader",
        label="Utilisateur vide",
        description="Compte fraîchement créé, aucune analyse ni watchlist.",
        history_volume=0,
    ),
    "standard": Persona(
        cle="standard",
        email="standard@example.com",
        password=_DEFAULT_PWD,
        role="reader",
        label="Utilisateur standard",
        description="Usage nominal : quelques analyses, watchlist modeste.",
        history_volume=12,
    ),
    "premium": Persona(
        cle="premium",
        email="premium@example.com",
        password=_DEFAULT_PWD,
        role="reader",
        label="Utilisateur premium",
        description="Usage intensif : tous les workflows, exports PDF.",
        history_volume=120,
    ),
    "admin": Persona(
        cle="admin",
        email="admin@example.com",
        password=_DEFAULT_PWD,
        role="admin",
        label="Administrateur",
        description="Accès aux endpoints /admin (gestion des clés API).",
        history_volume=40,
    ),
    "suspended": Persona(
        cle="suspended",
        email="suspendu@example.com",
        password=_DEFAULT_PWD,
        role="reader",
        is_active=False,
        label="Compte suspendu",
        description="is_active=False → toute connexion doit échouer en 401.",
        history_volume=8,
    ),
    "massive": Persona(
        cle="massive",
        email="massif@example.com",
        password=_DEFAULT_PWD,
        role="reader",
        label="Compte avec historique massif",
        description="Des milliers d'analyses — stress de pagination et de rendu.",
        history_volume=5000,
    ),
}


class _UserPoolShim:
    """Mince adaptateur exposant `fetchrow` pour `/auth/forgot-password`.

    L'endpoint interroge `user_service._pool.fetchrow("SELECT id ... WHERE email")`
    directement ; on rejoue uniquement cette requête.
    """

    def __init__(self, service: "InMemoryUserService") -> None:
        self._service = service

    async def fetchrow(self, query: str, *args: object, **kwargs: object) -> dict | None:
        if "FROM users WHERE email" in query and args:
            email = str(args[0]).lower()
            user_id = self._service._by_email.get(email)
            return {"id": user_id} if user_id else None
        return None

    async def execute(self, *args: object, **kwargs: object) -> str:
        return "UPDATE 1"


@dataclass
class InMemoryUserService:
    """Implémentation en mémoire du contrat `UserService` pour les E2E."""

    _users: dict[UUID, dict] = field(default_factory=dict)
    _by_email: dict[str, UUID] = field(default_factory=dict)

    def __post_init__(self) -> None:
        self._pool = _UserPoolShim(self)

    @classmethod
    def with_personas(cls, personas: dict[str, Persona] | None = None) -> "InMemoryUserService":
        service = cls()
        for persona in (personas or PERSONAS).values():
            service._seed(persona)
        return service

    def _seed(self, persona: Persona) -> UUID:
        from app.models.tenant import LEGACY_TENANT_ID

        user_id = uuid.uuid4()
        self._users[user_id] = {
            "id": user_id,
            "email": persona.email.lower(),
            "hashed_password": _ph.hash(persona.password),
            "role": persona.role,
            "is_active": persona.is_active,
            "tenant_id": LEGACY_TENANT_ID,
            "tenant_name": _LEGACY_TENANT_NAME,
            "plan": _DEFAULT_PLAN,
            "created_at": datetime.now(timezone.utc),
        }
        self._by_email[persona.email.lower()] = user_id
        return user_id

    @staticmethod
    def _public(row: dict, *, with_hash: bool = False) -> dict:
        keys = ["id", "email", "role", "is_active", "tenant_id", "tenant_name", "plan", "created_at"]
        if with_hash:
            keys.append("hashed_password")
        return {k: row[k] for k in keys if k in row}

    async def create_user(
        self, email: str, password: str, tenant_id: UUID | None = None
    ) -> dict:
        from app.models.tenant import LEGACY_TENANT_ID
        from app.services.user_service import EmailAlreadyExistsError

        norm = email.lower()
        if norm in self._by_email:
            raise EmailAlreadyExistsError(f"Email déjà utilisé : {email}")
        user_id = uuid.uuid4()
        self._users[user_id] = {
            "id": user_id,
            "email": norm,
            "hashed_password": _ph.hash(password),
            "role": "reader",
            "is_active": True,
            "tenant_id": tenant_id or LEGACY_TENANT_ID,
            "tenant_name": _LEGACY_TENANT_NAME,
            "plan": _DEFAULT_PLAN,
            "created_at": datetime.now(timezone.utc),
        }
        self._by_email[norm] = user_id
        return self._public(self._users[user_id])

    async def authenticate(self, email: str, password: str) -> dict | None:
        user_id = self._by_email.get(email.lower())
        row = self._users.get(user_id) if user_id else None
        candidate = row["hashed_password"] if row else _DUMMY_HASH
        try:
            _ph.verify(candidate, password)
            valid = True
        except VerifyMismatchError:
            valid = False
        if not valid or row is None or not row["is_active"]:
            return None
        return self._public(row, with_hash=True)

    async def get_by_id(self, user_id: UUID) -> dict | None:
        row = self._users.get(user_id)
        return self._public(row) if row else None

    async def update_last_login(self, user_id: UUID) -> None:
        if user_id in self._users:
            self._users[user_id]["last_login_at"] = datetime.now(timezone.utc)

    async def get_hashed_password(self, user_id: UUID) -> str | None:
        row = self._users.get(user_id)
        return row["hashed_password"] if row else None

    async def update_password(self, user_id: UUID, new_password: str) -> None:
        if user_id in self._users:
            self._users[user_id]["hashed_password"] = _ph.hash(new_password)
