"""Tests unitaires du durcissement sécurité d'AuthTokenService (Sprint 125)."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import jwt
import pytest

from app.services.auth_token_service import AuthTokenService


def _make_service(redis_client: AsyncMock) -> AuthTokenService:
    return AuthTokenService(db_pool=MagicMock(), redis_client=redis_client)


class TestJwtRoundTrip:
    """Migration python-jose → PyJWT : parité encode/décode + rejet des tokens invalides (E1-S4)."""

    def _service(self, monkeypatch: pytest.MonkeyPatch) -> AuthTokenService:
        monkeypatch.setenv("APP_ENV", "test")
        monkeypatch.setenv("JWT_SECRET_KEY", "secret-de-test-suffisamment-long-1234")
        return _make_service(AsyncMock())

    def test_encode_puis_decode_preserve_les_claims(self, monkeypatch: pytest.MonkeyPatch):
        service = self._service(monkeypatch)
        uid = uuid4()
        token = service.create_access_token(uid, "yves@example.com", "admin")
        payload = service.decode_access_token(token)
        assert payload is not None
        assert payload["sub"] == str(uid)
        assert payload["email"] == "yves@example.com"
        assert payload["role"] == "admin"
        assert payload["jti"]

    def test_token_falsifie_rejete(self, monkeypatch: pytest.MonkeyPatch):
        service = self._service(monkeypatch)
        token = service.create_access_token(uuid4(), "a@b.co", "reader")
        assert service.decode_access_token(token + "tamper") is None

    def test_signature_etrangere_rejetee(self, monkeypatch: pytest.MonkeyPatch):
        service = self._service(monkeypatch)
        forged = jwt.encode(
            {"sub": "x"}, "un-secret-etranger-suffisamment-long-32c", algorithm="HS256"
        )
        assert service.decode_access_token(forged) is None

    def test_token_expire_rejete(self, monkeypatch: pytest.MonkeyPatch):
        service = self._service(monkeypatch)
        expired = jwt.encode(
            {"sub": "x", "exp": datetime.now(timezone.utc) - timedelta(minutes=1)},
            service._secret,
            algorithm="HS256",
        )
        assert service.decode_access_token(expired) is None

    def test_chaine_non_jwt_rejetee(self, monkeypatch: pytest.MonkeyPatch):
        service = self._service(monkeypatch)
        assert service.decode_access_token("pas-un-jwt-du-tout") is None


class TestSecretFailFast:
    def test_init_sans_secret_hors_dev_leve(self, monkeypatch: pytest.MonkeyPatch):
        monkeypatch.delenv("JWT_SECRET_KEY", raising=False)
        monkeypatch.setenv("APP_ENV", "production")
        with pytest.raises(RuntimeError, match="JWT_SECRET_KEY"):
            _make_service(AsyncMock())

    def test_init_avec_secret_ok(self, monkeypatch: pytest.MonkeyPatch):
        monkeypatch.setenv("JWT_SECRET_KEY", "secret-de-prod-suffisamment-long-32c")
        monkeypatch.setenv("APP_ENV", "production")
        service = _make_service(AsyncMock())
        assert service._secret == "secret-de-prod-suffisamment-long-32c"


class TestBlacklistFailClosed:
    async def test_redis_down_refuse_le_token(self, monkeypatch: pytest.MonkeyPatch):
        monkeypatch.setenv("APP_ENV", "test")
        redis = AsyncMock()
        redis.get = AsyncMock(side_effect=ConnectionError("Redis indisponible"))
        service = _make_service(redis)
        # fail-closed : panne Redis → token considéré comme révoqué (True)
        assert await service.is_jti_blacklisted("jti-abc") is True

    async def test_jti_present_renvoie_true(self, monkeypatch: pytest.MonkeyPatch):
        monkeypatch.setenv("APP_ENV", "test")
        redis = AsyncMock()
        redis.get = AsyncMock(return_value=b"1")
        service = _make_service(redis)
        assert await service.is_jti_blacklisted("jti-revoque") is True

    async def test_jti_absent_renvoie_false(self, monkeypatch: pytest.MonkeyPatch):
        monkeypatch.setenv("APP_ENV", "test")
        redis = AsyncMock()
        redis.get = AsyncMock(return_value=None)
        service = _make_service(redis)
        assert await service.is_jti_blacklisted("jti-valide") is False
