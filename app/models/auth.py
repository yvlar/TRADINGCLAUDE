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
    # tenant_id volontairement absent de la réponse publique (/auth/me) au Sprint 161 :
    # le dict interne de UserService le porte déjà, mais l'exposition côté client n'a
    # de sens qu'avec le threading de contexte tenant (E3-S4, sprint 164).
    id: UUID
    email: str
    role: str
    created_at: datetime


class AuthResponse(BaseModel):
    user: UserPublic
    message: str
