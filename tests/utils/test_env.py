"""Tests unitaires du détecteur d'environnement (source unique fail-closed)."""
from __future__ import annotations

import pytest

from app.utils.env import is_dev_environment


class TestIsDevEnvironment:
    @pytest.mark.parametrize("app_env", ["dev", "development", "test", "testing"])
    def test_environnements_dev_reconnus(
        self, monkeypatch: pytest.MonkeyPatch, app_env: str
    ):
        monkeypatch.setenv("APP_ENV", app_env)
        assert is_dev_environment() is True

    def test_casse_et_espaces_tolerees(self, monkeypatch: pytest.MonkeyPatch):
        monkeypatch.setenv("APP_ENV", "  DeV  ")
        assert is_dev_environment() is True

    @pytest.mark.parametrize("app_env", ["production", "prod", "staging", "qa"])
    def test_environnements_non_dev(
        self, monkeypatch: pytest.MonkeyPatch, app_env: str
    ):
        monkeypatch.setenv("APP_ENV", app_env)
        assert is_dev_environment() is False

    def test_absent_traite_comme_production(self, monkeypatch: pytest.MonkeyPatch):
        # Défaut sûr : APP_ENV non posé → production (pas de bypass).
        monkeypatch.delenv("APP_ENV", raising=False)
        assert is_dev_environment() is False

    def test_vide_traite_comme_production(self, monkeypatch: pytest.MonkeyPatch):
        monkeypatch.setenv("APP_ENV", "")
        assert is_dev_environment() is False
