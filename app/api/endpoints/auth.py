from __future__ import annotations

import logging
import os
import uuid
from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Cookie, HTTPException, Request, Response, status
from fastapi.responses import JSONResponse

from app.models.auth import (
    AuthResponse,
    ForgotPasswordRequest,
    LoginRequest,
    RegisterRequest,
    ResetPasswordRequest,
    UserPublic,
)
from app.services.user_service import EmailAlreadyExistsError

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["auth"])

_ACCESS_TOKEN_TTL_MIN = 15
_REFRESH_TOKEN_TTL_DAYS = 30
_REFRESH_TOKEN_REMEMBER_TTL_DAYS = 90
_CSRF_TOKEN_TTL_DAYS = 90
_LOGIN_RATE_LIMIT_MAX = 5
_LOGIN_RATE_LIMIT_WINDOW_S = 900  # 15 minutes


def _is_secure_cookies() -> bool:
    """Cookies Secure uniquement en production (HTTPS requis)."""
    return os.environ.get("SECURE_COOKIES", "false").lower() == "true"


def _set_auth_cookies(
    response: Response,
    access_token: str,
    refresh_token: str,
    csrf_token: str,
    remember_me: bool = False,
) -> None:
    """Pose les trois cookies d'authentification sur la réponse."""
    secure = _is_secure_cookies()
    refresh_ttl = (
        _REFRESH_TOKEN_REMEMBER_TTL_DAYS if remember_me else _REFRESH_TOKEN_TTL_DAYS
    )

    response.set_cookie(
        key="access_token",
        value=access_token,
        httponly=True,
        secure=secure,
        samesite="lax",
        max_age=_ACCESS_TOKEN_TTL_MIN * 60,
    )
    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        httponly=True,
        secure=secure,
        samesite="lax",
        path="/auth/refresh",
        max_age=refresh_ttl * 86400,
    )
    # Cookie non-httpOnly pour que le frontend puisse le lire (double-submit CSRF)
    response.set_cookie(
        key="csrf_token",
        value=csrf_token,
        httponly=False,
        secure=secure,
        samesite="lax",
        max_age=_CSRF_TOKEN_TTL_DAYS * 86400,
    )


def _clear_auth_cookies(response: Response) -> None:
    """Supprime les trois cookies d'authentification."""
    for key in ("access_token", "refresh_token", "csrf_token"):
        response.delete_cookie(key=key, path="/", samesite="lax")
    response.delete_cookie(key="refresh_token", path="/auth/refresh", samesite="lax")


async def _get_current_user(request: Request) -> dict:
    """Dépendance : extrait et valide le JWT du cookie access_token."""
    token = request.cookies.get("access_token")
    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Non authentifié")

    auth_token_service = getattr(request.app.state, "auth_token_service", None)
    if not auth_token_service:
        raise HTTPException(status_code=503, detail="Service d'authentification indisponible")

    payload = auth_token_service.decode_access_token(token)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token invalide ou expiré",
        )

    jti = payload.get("jti", "")
    if jti and await auth_token_service.is_jti_blacklisted(jti):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token révoqué",
        )

    return payload


@router.post("/register", response_model=AuthResponse, status_code=status.HTTP_201_CREATED)
async def register(request: Request, body: RegisterRequest, response: Response) -> AuthResponse:
    """Crée un compte utilisateur et démarre une session."""
    user_service = request.app.state.user_service
    auth_token_service = request.app.state.auth_token_service

    try:
        user = await user_service.create_user(body.email, body.password)
    except EmailAlreadyExistsError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Un compte avec cet email existe déjà",
        )

    user_id = UUID(str(user["id"]))
    access_token = auth_token_service.create_access_token(
        user_id=user_id,
        email=user["email"],
        role=user["role"],
    )
    refresh_token = await auth_token_service.create_refresh_token(user_id=user_id)
    csrf_token = str(uuid.uuid4())

    _set_auth_cookies(response, access_token, refresh_token, csrf_token)

    logger.info("Inscription réussie pour %s", user["email"])

    return AuthResponse(
        user=UserPublic(
            id=user_id,
            email=user["email"],
            role=user["role"],
            created_at=user["created_at"],
        ),
        message="Compte créé avec succès",
    )


@router.post("/login", response_model=AuthResponse)
async def login(request: Request, body: LoginRequest, response: Response) -> AuthResponse:
    """Authentifie un utilisateur et pose les cookies de session."""
    redis_pool = getattr(request.app.state, "redis_pool", None)
    user_service = request.app.state.user_service
    auth_token_service = request.app.state.auth_token_service

    # Rate limiting par IP : 5 tentatives / 15 minutes
    client_ip = request.client.host if request.client else "unknown"
    if redis_pool:
        rate_key = f"rate_limit:login:{client_ip}"
        attempts: int = await redis_pool.incr(rate_key)
        if attempts == 1:
            await redis_pool.expire(rate_key, _LOGIN_RATE_LIMIT_WINDOW_S)
        if attempts > _LOGIN_RATE_LIMIT_MAX:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Trop de tentatives. Réessayez dans 15 minutes.",
            )

    user = await user_service.authenticate(body.email, body.password)

    if user is None:
        # Message générique — ne révèle pas si l'email existe
        logger.warning("Tentative de connexion échouée depuis %s", client_ip)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email ou mot de passe incorrect",
        )

    if redis_pool:
        # Réinitialise le compteur après un succès
        await redis_pool.delete(f"rate_limit:login:{client_ip}")

    user_id = UUID(str(user["id"]))
    access_token = auth_token_service.create_access_token(
        user_id=user_id,
        email=user["email"],
        role=user["role"],
    )
    refresh_token = await auth_token_service.create_refresh_token(
        user_id=user_id,
        remember_me=body.remember_me,
    )
    csrf_token = str(uuid.uuid4())

    _set_auth_cookies(response, access_token, refresh_token, csrf_token, body.remember_me)
    await user_service.update_last_login(user_id)

    logger.info("Connexion réussie : %s depuis %s", user["email"], client_ip)

    return AuthResponse(
        user=UserPublic(
            id=user_id,
            email=user["email"],
            role=user["role"],
            created_at=user["created_at"],
        ),
        message="Connexion réussie",
    )


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(
    request: Request,
    response: Response,
    access_token: str | None = Cookie(default=None),
    refresh_token: str | None = Cookie(default=None),
) -> None:
    """Déconnecte l'utilisateur : blacklist le JWT + supprime le refresh token."""
    auth_token_service = getattr(request.app.state, "auth_token_service", None)

    if auth_token_service and access_token:
        payload = auth_token_service.decode_access_token(access_token)
        if payload:
            jti = payload.get("jti", "")
            exp = payload.get("exp", 0)
            if jti:
                remaining_s = max(0, int(exp - datetime.now(timezone.utc).timestamp()))
                await auth_token_service.blacklist_jti(jti, remaining_s)

    if auth_token_service and refresh_token:
        await auth_token_service.invalidate_refresh_token(refresh_token)

    _clear_auth_cookies(response)
    logger.info("Déconnexion effectuée")


@router.post("/refresh")
async def refresh(
    request: Request,
    response: Response,
    refresh_token: str | None = Cookie(default=None),
) -> JSONResponse:
    """Rotation du refresh token : invalide l'ancien, génère de nouveaux tokens."""
    if not refresh_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token manquant",
        )

    auth_token_service = getattr(request.app.state, "auth_token_service", None)
    user_service = getattr(request.app.state, "user_service", None)
    if not auth_token_service or not user_service:
        raise HTTPException(status_code=503, detail="Service d'authentification indisponible")

    result = await auth_token_service.rotate_refresh_token(refresh_token)
    if result is None:
        _clear_auth_cookies(response)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token invalide ou expiré",
        )

    new_refresh_token, user_id = result
    user = await user_service.get_by_id(user_id)
    if not user:
        _clear_auth_cookies(response)
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Utilisateur introuvable")

    new_access_token = auth_token_service.create_access_token(
        user_id=user_id,
        email=user["email"],
        role=user["role"],
    )
    csrf_token = str(uuid.uuid4())

    _set_auth_cookies(response, new_access_token, new_refresh_token, csrf_token)
    logger.info("Refresh token rotation effectuée pour user %s", user_id)

    return JSONResponse({"message": "Tokens rafraîchis"})


@router.get("/me", response_model=UserPublic)
async def me(request: Request) -> UserPublic:
    """Retourne les infos de l'utilisateur authentifié via cookie."""
    payload = await _get_current_user(request)
    user_service = request.app.state.user_service
    user = await user_service.get_by_id(UUID(payload["sub"]))
    if not user:
        raise HTTPException(status_code=404, detail="Utilisateur introuvable")

    return UserPublic(
        id=user["id"],
        email=user["email"],
        role=user["role"],
        created_at=user["created_at"],
    )


@router.post("/forgot-password", status_code=status.HTTP_204_NO_CONTENT)
async def forgot_password(request: Request, body: ForgotPasswordRequest) -> None:
    """
    Envoie un email de réinitialisation.

    Délai identique que l'email existe ou non (anti-énumération).
    """
    user_service = request.app.state.user_service
    password_reset_service = request.app.state.password_reset_service

    row = await user_service._pool.fetchrow(
        "SELECT id FROM users WHERE email = LOWER($1)",
        body.email,
    )

    # Toujours répondre après la même durée, même si l'email est inconnu
    if row is None:
        logger.info("Demande de reset pour email inconnu (silencieux)")
        return

    user_id = UUID(str(row["id"]))
    token = password_reset_service.create_reset_token(user_id)

    frontend_url = os.environ.get("FRONTEND_URL", "http://localhost:5173")
    reset_link = f"{frontend_url}/reset-password?token={token}"

    await password_reset_service.send_reset_email(body.email, reset_link)
    logger.info("Email de réinitialisation envoyé à %s", body.email)


@router.post("/reset-password", status_code=status.HTTP_204_NO_CONTENT)
async def reset_password(request: Request, body: ResetPasswordRequest) -> None:
    """Réinitialise le mot de passe avec le token reçu par email."""
    user_service = request.app.state.user_service
    password_reset_service = request.app.state.password_reset_service

    user_id = password_reset_service.verify_reset_token(body.token)
    if user_id is None:
        raise HTTPException(status_code=400, detail="Token invalide ou expiré")

    user = await user_service.get_by_id(user_id)
    if not user:
        raise HTTPException(status_code=400, detail="Token invalide ou expiré")

    await user_service.update_password(user_id, body.new_password)
    logger.info("Mot de passe réinitialisé pour user %s", user_id)


# Stubs MFA — architecture prête, implémentation future
@router.post("/mfa/setup", status_code=status.HTTP_501_NOT_IMPLEMENTED)
async def mfa_setup() -> JSONResponse:
    """Stub MFA setup — non implémenté dans ce sprint."""
    return JSONResponse({"detail": "MFA non encore disponible"}, status_code=501)


@router.post("/mfa/verify", status_code=status.HTTP_501_NOT_IMPLEMENTED)
async def mfa_verify() -> JSONResponse:
    """Stub MFA verify — non implémenté dans ce sprint."""
    return JSONResponse({"detail": "MFA non encore disponible"}, status_code=501)
