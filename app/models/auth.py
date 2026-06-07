from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, EmailStr, field_validator


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str

    @field_validator("password")
    @classmethod
    def validate_password_strength(cls, v: str) -> str:
        """Valide les critères de complexité du mot de passe."""
        if len(v) < 12:
            raise ValueError("Minimum 12 caractères requis")
        if not any(c.isupper() for c in v):
            raise ValueError("Au moins une majuscule requise")
        if not any(c.islower() for c in v):
            raise ValueError("Au moins une minuscule requise")
        if not any(c.isdigit() for c in v):
            raise ValueError("Au moins un chiffre requis")
        specials = set("!@#$%^&*()_+-=[]{}|;':\",./<>?")
        if not any(c in specials for c in v):
            raise ValueError("Au moins un caractère spécial requis")
        return v


class LoginRequest(BaseModel):
    email: EmailStr
    password: str
    remember_me: bool = False


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str

    @field_validator("new_password")
    @classmethod
    def validate_new_password(cls, v: str) -> str:
        """Valide les critères de complexité du nouveau mot de passe."""
        if len(v) < 12:
            raise ValueError("Minimum 12 caractères requis")
        if not any(c.isupper() for c in v):
            raise ValueError("Au moins une majuscule requise")
        if not any(c.islower() for c in v):
            raise ValueError("Au moins une minuscule requise")
        if not any(c.isdigit() for c in v):
            raise ValueError("Au moins un chiffre requis")
        specials = set("!@#$%^&*()_+-=[]{}|;':\",./<>?")
        if not any(c in specials for c in v):
            raise ValueError("Au moins un caractère spécial requis")
        return v


class UserPublic(BaseModel):
    # tenant_id + tenant_name exposés depuis le Sprint 169 (E4-S4) : le contexte tenant
    # est désormais threadé (E3-S4) et borné (E4-S2/S3), l'omission délibérée du Sprint 161
    # n'a plus lieu d'être — le client en a besoin pour l'UI multi-tenant.
    # plan exposé au Sprint 173 (E4-S8) : la page Facturation lit le plan courant du tenant
    # pour choisir le CTA (souscrire vs gérer l'abonnement) — réutilise /auth/me plutôt qu'un
    # endpoint dédié (le plan est déjà une colonne `tenants`, résolue par le même JOIN).
    id: UUID
    email: str
    role: str
    tenant_id: UUID
    tenant_name: str
    plan: str
    created_at: datetime


class AuthResponse(BaseModel):
    user: UserPublic
    message: str
