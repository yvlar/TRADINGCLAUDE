"""Tests du garde-fou admin _require_admin — fail-closed en production (E1-S1)."""
from __future__ import annotations

from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from app.api.endpoints.admin import _require_admin


def _fake_request(*, api_key_service=None, api_key_record=...) -> SimpleNamespace:
    """Construit un Request minimal pour exercer _require_admin sans middleware."""
    state = SimpleNamespace()
    if api_key_record is not ...:
        state.api_key_record = api_key_record
    return SimpleNamespace(
        app=SimpleNamespace(state=SimpleNamespace(api_key_service=api_key_service)),
        state=state,
    )


def test_require_admin_prod_sans_config_refuse(monkeypatch: pytest.MonkeyPatch):
    """Prod + API_KEY vide + aucun service DB → 401 (avant le fix : bypass)."""
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.delenv("API_KEY", raising=False)
    with pytest.raises(HTTPException) as exc:
        _require_admin(_fake_request())
    assert exc.value.status_code == 401


def test_require_admin_dev_sans_config_bypass(monkeypatch: pytest.MonkeyPatch):
    """En dev, le bypass complet est conservé (rétrocompat)."""
    monkeypatch.setenv("APP_ENV", "dev")
    monkeypatch.delenv("API_KEY", raising=False)
    assert _require_admin(_fake_request()) is None


def test_require_admin_role_reader_refuse(monkeypatch: pytest.MonkeyPatch):
    """Un enregistrement non-admin est refusé même en dev."""
    monkeypatch.setenv("APP_ENV", "dev")
    record = SimpleNamespace(role="reader")
    svc = object()  # service présent → pas de bypass
    with pytest.raises(HTTPException) as exc:
        _require_admin(_fake_request(api_key_service=svc, api_key_record=record))
    assert exc.value.status_code == 403
