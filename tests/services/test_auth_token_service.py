"""Tests unitaires du durcissement sécurité d'AuthTokenService (Sprint 125)."""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from app.services.auth_token_service import AuthTokenService


def _make_service(redis_client: AsyncMock) -> AuthTokenService:
    return AuthTokenService(db_pool=MagicMock(), redis_client=redis_client)


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
