"""Tests de la résolution d'IP client à l'épreuve du spoof X-Forwarded-For (E1-S2)."""
from __future__ import annotations

from types import SimpleNamespace

import pytest

from app.utils.client_ip import resolve_client_ip, trusted_proxies_from_env


def _request(peer: str | None, xff: str | None = None) -> SimpleNamespace:
    headers: dict[str, str] = {}
    if xff is not None:
        headers["X-Forwarded-For"] = xff
    client = SimpleNamespace(host=peer) if peer is not None else None
    return SimpleNamespace(client=client, headers=headers)


class TestResolveClientIp:
    def test_proxy_non_confiance_ignore_xff(self):
        # XFF forgé par un client direct → ignoré (anti-spoof).
        req = _request("203.0.113.9", xff="1.2.3.4")
        assert resolve_client_ip(req, {"10.0.0.1"}) == "203.0.113.9"

    def test_proxy_confiance_utilise_xff(self):
        req = _request("10.0.0.1", xff="1.2.3.4")
        assert resolve_client_ip(req, {"10.0.0.1"}) == "1.2.3.4"

    def test_proxy_confiance_prend_la_premiere_entree(self):
        req = _request("10.0.0.1", xff="1.2.3.4, 5.6.7.8")
        assert resolve_client_ip(req, {"10.0.0.1"}) == "1.2.3.4"

    def test_proxy_confiance_sans_xff_retombe_sur_peer(self):
        req = _request("10.0.0.1")
        assert resolve_client_ip(req, {"10.0.0.1"}) == "10.0.0.1"

    def test_xff_vide_retombe_sur_peer(self):
        req = _request("10.0.0.1", xff="   ")
        assert resolve_client_ip(req, {"10.0.0.1"}) == "10.0.0.1"

    def test_client_absent_retourne_unknown(self):
        req = _request(None)
        assert resolve_client_ip(req, set()) == "unknown"


class TestTrustedProxiesFromEnv:
    def test_absent_vide(self, monkeypatch: pytest.MonkeyPatch):
        monkeypatch.delenv("TRUSTED_PROXY_IPS", raising=False)
        assert trusted_proxies_from_env() == frozenset()

    def test_csv_parse(self, monkeypatch: pytest.MonkeyPatch):
        monkeypatch.setenv("TRUSTED_PROXY_IPS", "10.0.0.1, 10.0.0.2 ")
        assert trusted_proxies_from_env() == frozenset({"10.0.0.1", "10.0.0.2"})

    def test_blancs_ignores(self, monkeypatch: pytest.MonkeyPatch):
        monkeypatch.setenv("TRUSTED_PROXY_IPS", " , ,")
        assert trusted_proxies_from_env() == frozenset()
