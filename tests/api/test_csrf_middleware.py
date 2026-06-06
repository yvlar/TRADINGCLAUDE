"""Tests du CSRFMiddleware — fail-closed en prod + comparaison timing-safe (E1-S1)."""
from __future__ import annotations

import hmac as _hmac

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from app.middleware.csrf import CSRFMiddleware


def _make_csrf_app() -> FastAPI:
    """App minimale protégée par le CSRFMiddleware."""
    app = FastAPI()
    app.add_middleware(CSRFMiddleware)

    @app.post("/mutate")
    async def mutate():
        return {"ok": True}

    return app


async def _post(app: FastAPI, **kwargs):
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as c:
        return await c.post("/mutate", **kwargs)


async def test_csrf_prod_sans_token_403(monkeypatch: pytest.MonkeyPatch):
    """Prod + API_KEY vide + aucun token CSRF → 403 (avant le fix : 200)."""
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.delenv("API_KEY", raising=False)
    r = await _post(_make_csrf_app())
    assert r.status_code == 403


async def test_csrf_prod_token_valide_200(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("APP_ENV", "production")
    r = await _post(
        _make_csrf_app(),
        headers={"Cookie": "csrf_token=tok123", "X-CSRF-Token": "tok123"},
    )
    assert r.status_code == 200


async def test_csrf_prod_token_mismatch_403(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("APP_ENV", "production")
    r = await _post(
        _make_csrf_app(),
        headers={"Cookie": "csrf_token=tok123", "X-CSRF-Token": "autre"},
    )
    assert r.status_code == 403


async def test_csrf_dev_bypass_200(monkeypatch: pytest.MonkeyPatch):
    """En dev, le bypass est conservé (rétrocompat)."""
    monkeypatch.setenv("APP_ENV", "dev")
    r = await _post(_make_csrf_app())
    assert r.status_code == 200


async def test_csrf_bearer_exempt_meme_en_prod(monkeypatch: pytest.MonkeyPatch):
    """Les requêtes Bearer (clés programmatiques) restent exemptées de CSRF."""
    monkeypatch.setenv("APP_ENV", "production")
    r = await _post(
        _make_csrf_app(), headers={"Authorization": "Bearer une-cle-api"}
    )
    assert r.status_code == 200


async def test_csrf_utilise_compare_digest(monkeypatch: pytest.MonkeyPatch):
    """La comparaison passe par hmac.compare_digest (timing-safe), pas par !=."""
    monkeypatch.setenv("APP_ENV", "production")
    calls: list[tuple[str, str]] = []
    real = _hmac.compare_digest

    def _spy(a, b):
        calls.append((a, b))
        return real(a, b)

    monkeypatch.setattr("app.middleware.csrf.hmac.compare_digest", _spy)
    r = await _post(
        _make_csrf_app(),
        headers={"Cookie": "csrf_token=z", "X-CSRF-Token": "z"},
    )
    assert r.status_code == 200
    assert calls == [("z", "z")]
