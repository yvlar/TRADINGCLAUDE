"""Tests du garde-fou admin _require_admin — fail-closed en production (E1-S1)."""
from __future__ import annotations

from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from app.api.endpoints.admin import _require_admin


def _fake_request(
    *, api_key_service=None, api_key_record=..., user_id=None, user_role=None
) -> SimpleNamespace:
    """Construit un Request minimal pour exercer _require_admin sans middleware."""
    state = SimpleNamespace()
    if api_key_record is not ...:
        state.api_key_record = api_key_record
    if user_id is not None:
        state.user_id = user_id
        state.user_role = user_role
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


def test_require_admin_jwt_reader_refuse(monkeypatch: pytest.MonkeyPatch):
    """E4-S10 : un utilisateur web JWT non-admin (record None mais user_id posé) → 403."""
    monkeypatch.setenv("APP_ENV", "dev")
    svc = object()  # service présent → pas de bypass dev
    req = _fake_request(api_key_service=svc, api_key_record=None, user_id="u1", user_role="reader")
    with pytest.raises(HTTPException) as exc:
        _require_admin(req)
    assert exc.value.status_code == 403


def test_require_admin_jwt_admin_accepte(monkeypatch: pytest.MonkeyPatch):
    """E4-S10 : un utilisateur web JWT admin est accepté (record None, user_role=admin)."""
    monkeypatch.setenv("APP_ENV", "dev")
    svc = object()
    req = _fake_request(api_key_service=svc, api_key_record=None, user_id="u1", user_role="admin")
    assert _require_admin(req) is None


def test_require_admin_cle_env_sans_user_id_admin_implicite(monkeypatch: pytest.MonkeyPatch):
    """E4-S10 : la clé env (record None, AUCUN user_id) reste admin implicite."""
    monkeypatch.setenv("APP_ENV", "production")
    svc = object()
    assert _require_admin(_fake_request(api_key_service=svc, api_key_record=None)) is None
