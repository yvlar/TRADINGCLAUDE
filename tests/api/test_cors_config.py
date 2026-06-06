"""Tests de la résolution CORS — fail-fast en production (E1-S1)."""
from __future__ import annotations

import pytest

from app.api.main import _DEV_CORS_ORIGINS, _resolve_cors_origins


def test_cors_prod_vide_leve_runtimeerror(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.delenv("CORS_ORIGINS", raising=False)
    with pytest.raises(RuntimeError, match="CORS_ORIGINS"):
        _resolve_cors_origins()


def test_cors_prod_absent_app_env_leve(monkeypatch: pytest.MonkeyPatch):
    # APP_ENV absent → traité comme production → refus si CORS_ORIGINS vide.
    monkeypatch.delenv("APP_ENV", raising=False)
    monkeypatch.delenv("CORS_ORIGINS", raising=False)
    with pytest.raises(RuntimeError):
        _resolve_cors_origins()


def test_cors_dev_vide_repli_localhost(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("APP_ENV", "dev")
    monkeypatch.delenv("CORS_ORIGINS", raising=False)
    assert _resolve_cors_origins() == _DEV_CORS_ORIGINS


def test_cors_origines_explicites_respectees(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("CORS_ORIGINS", "https://app.x , https://b.y")
    assert _resolve_cors_origins() == ["https://app.x", "https://b.y"]
