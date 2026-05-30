"""Tests unitaires du résolveur de secret JWT (fail-fast hors dev/test)."""
from __future__ import annotations

import pytest

from app.utils.jwt_secret import _DEV_FALLBACK_SECRET, resolve_jwt_secret


class TestResolveJwtSecret:
    def test_retourne_le_secret_configure(self, monkeypatch: pytest.MonkeyPatch):
        monkeypatch.setenv("JWT_SECRET_KEY", "un-vrai-secret-de-production-32cars")
        monkeypatch.setenv("APP_ENV", "production")
        assert resolve_jwt_secret() == "un-vrai-secret-de-production-32cars"

    @pytest.mark.parametrize("app_env", ["dev", "development", "test", "testing"])
    def test_repli_dev_si_secret_absent(self, monkeypatch: pytest.MonkeyPatch, app_env: str):
        monkeypatch.delenv("JWT_SECRET_KEY", raising=False)
        monkeypatch.setenv("APP_ENV", app_env)
        assert resolve_jwt_secret() == _DEV_FALLBACK_SECRET

    def test_fail_fast_en_production(self, monkeypatch: pytest.MonkeyPatch):
        monkeypatch.delenv("JWT_SECRET_KEY", raising=False)
        monkeypatch.setenv("APP_ENV", "production")
        with pytest.raises(RuntimeError, match="JWT_SECRET_KEY"):
            resolve_jwt_secret()

    def test_fail_fast_si_app_env_absent(self, monkeypatch: pytest.MonkeyPatch):
        # APP_ENV absent → traité comme production (défaut sûr)
        monkeypatch.delenv("JWT_SECRET_KEY", raising=False)
        monkeypatch.delenv("APP_ENV", raising=False)
        with pytest.raises(RuntimeError):
            resolve_jwt_secret()

    def test_secret_vide_traite_comme_absent(self, monkeypatch: pytest.MonkeyPatch):
        monkeypatch.setenv("JWT_SECRET_KEY", "")
        monkeypatch.setenv("APP_ENV", "production")
        with pytest.raises(RuntimeError):
            resolve_jwt_secret()
