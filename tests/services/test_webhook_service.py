"""Tests CI pour WebhookService — aucun appel HTTP réel (httpx mocké)."""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import httpx
import pytest

from app.services.webhook_service import WebhookService

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_mock_response(status_code: int = 200) -> MagicMock:
    """Crée un faux httpx.Response avec raise_for_status() neutre."""
    resp = MagicMock()
    resp.status_code = status_code
    resp.raise_for_status = MagicMock()
    return resp


# ---------------------------------------------------------------------------
# Test 1 : WEBHOOK_URL absent → toutes les méthodes retournent False sans exception
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_send_price_alert_sans_url_retourne_false(monkeypatch):
    monkeypatch.delenv("WEBHOOK_URL", raising=False)
    service = WebhookService()
    result = await service.send_price_alert("BNS", 65.0, 0.10, "divergence")
    assert result is False


@pytest.mark.asyncio
async def test_send_composite_alert_sans_url_retourne_false(monkeypatch):
    monkeypatch.delenv("WEBHOOK_URL", raising=False)
    service = WebhookService()
    result = await service.send_composite_alert("TD", 55.0, "Modéré")
    assert result is False


@pytest.mark.asyncio
async def test_send_watchlist_summary_sans_url_retourne_false(monkeypatch):
    monkeypatch.delenv("WEBHOOK_URL", raising=False)
    service = WebhookService()
    result = await service.send_watchlist_summary(3, [])
    assert result is False


# ---------------------------------------------------------------------------
# Test 2 : Payload JSON — champs requis présents (text, ticker, type)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_payload_price_alert_champs_requis(monkeypatch):
    """Le payload d'une alerte prix contient text, ticker et type='price'."""
    monkeypatch.setenv("WEBHOOK_URL", "http://webhook.test/hook")
    monkeypatch.delenv("WEBHOOK_SECRET", raising=False)

    captured: list[dict] = []

    async def mock_post(self_client, url, *, json=None, headers=None):
        captured.append(json)
        return _make_mock_response(200)

    with patch.object(httpx.AsyncClient, "post", mock_post):
        service = WebhookService()
        result = await service.send_price_alert("BNS", 65.50, 0.10, "divergence")

    assert result is True
    assert len(captured) == 1
    payload = captured[0]
    assert "text" in payload
    assert payload["ticker"] == "BNS"
    assert payload["type"] == "price"
    assert payload["prix"] == pytest.approx(65.50)
    assert payload["seuil"] == pytest.approx(0.10)


@pytest.mark.asyncio
async def test_payload_composite_alert_champs_requis(monkeypatch):
    """Le payload d'une alerte composite contient text, ticker et type='composite'."""
    monkeypatch.setenv("WEBHOOK_URL", "http://webhook.test/hook")
    monkeypatch.delenv("WEBHOOK_SECRET", raising=False)

    captured: list[dict] = []

    async def mock_post(self_client, url, *, json=None, headers=None):
        captured.append(json)
        return _make_mock_response(200)

    with patch.object(httpx.AsyncClient, "post", mock_post):
        service = WebhookService()
        result = await service.send_composite_alert("TD", 72.3, "Fort")

    assert result is True
    payload = captured[0]
    assert "text" in payload
    assert payload["ticker"] == "TD"
    assert payload["type"] == "composite"
    assert payload["score"] == pytest.approx(72.3)
    assert payload["label"] == "Fort"


@pytest.mark.asyncio
async def test_payload_watchlist_summary_champs_requis(monkeypatch):
    """Le payload du résumé hebdomadaire contient text et type='summary'."""
    monkeypatch.setenv("WEBHOOK_URL", "http://webhook.test/hook")
    monkeypatch.delenv("WEBHOOK_SECRET", raising=False)

    captured: list[dict] = []

    async def mock_post(self_client, url, *, json=None, headers=None):
        captured.append(json)
        return _make_mock_response(200)

    alertes = [{"ticker": "BNS", "score": 4}]
    with patch.object(httpx.AsyncClient, "post", mock_post):
        service = WebhookService()
        result = await service.send_watchlist_summary(5, alertes)

    assert result is True
    payload = captured[0]
    assert "text" in payload
    assert payload["type"] == "summary"
    assert payload["nb_positions"] == 5
    assert payload["alertes"] == alertes


# ---------------------------------------------------------------------------
# Test 3 : Header X-Webhook-Secret envoyé si WEBHOOK_SECRET configuré
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_secret_header_envoye_si_configure(monkeypatch):
    monkeypatch.setenv("WEBHOOK_URL", "http://webhook.test/hook")
    monkeypatch.setenv("WEBHOOK_SECRET", "mon-secret-test")

    captured_headers: list[dict] = []

    async def mock_post(self_client, url, *, json=None, headers=None):
        captured_headers.append(headers or {})
        return _make_mock_response(200)

    with patch.object(httpx.AsyncClient, "post", mock_post):
        service = WebhookService()
        await service.send_composite_alert("RY", 60.0, "Modéré")

    assert captured_headers[0].get("X-Webhook-Secret") == "mon-secret-test"


# ---------------------------------------------------------------------------
# Test 4 : Retry sur erreur réseau — 1 retry puis False + incrément nb_erreurs
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_retry_sur_connect_error(monkeypatch):
    """Un ConnectError déclenche 1 retry, puis retourne False et incrémente nb_erreurs."""
    monkeypatch.setenv("WEBHOOK_URL", "http://webhook.test/hook")
    monkeypatch.delenv("WEBHOOK_SECRET", raising=False)

    appels = 0

    async def mock_post_raises(self_client, url, *, json=None, headers=None):
        nonlocal appels
        appels += 1
        raise httpx.ConnectError("connexion refusée")

    with patch.object(httpx.AsyncClient, "post", mock_post_raises):
        service = WebhookService()
        result = await service.send_price_alert("BNS", 65.0, 0.10, "divergence")

    assert result is False
    assert appels == 2  # 1 essai + 1 retry
    assert service.nb_erreurs == 1


# ---------------------------------------------------------------------------
# Test 5 : Succès met à jour derniere_notification et ne touche pas nb_erreurs
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_succes_met_a_jour_derniere_notification(monkeypatch):
    monkeypatch.setenv("WEBHOOK_URL", "http://webhook.test/hook")
    monkeypatch.delenv("WEBHOOK_SECRET", raising=False)

    async def mock_post(self_client, url, *, json=None, headers=None):
        return _make_mock_response(200)

    with patch.object(httpx.AsyncClient, "post", mock_post):
        service = WebhookService()
        assert service.derniere_notification is None
        assert service.nb_erreurs == 0
        result = await service.send_composite_alert("SHOP", 80.0, "Fort")

    assert result is True
    assert service.derniere_notification is not None
    assert service.nb_erreurs == 0


# ---------------------------------------------------------------------------
# Test 6 : Erreur HTTP 4xx/5xx → False + incrément nb_erreurs (pas de retry)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_erreur_http_status_incremente_nb_erreurs(monkeypatch):
    monkeypatch.setenv("WEBHOOK_URL", "http://webhook.test/hook")
    monkeypatch.delenv("WEBHOOK_SECRET", raising=False)

    async def mock_post_http_error(self_client, url, *, json=None, headers=None):
        resp = MagicMock()
        resp.status_code = 403
        resp.raise_for_status.side_effect = httpx.HTTPStatusError(
            "403 Forbidden", request=MagicMock(), response=resp
        )
        return resp

    with patch.object(httpx.AsyncClient, "post", mock_post_http_error):
        service = WebhookService()
        result = await service.send_price_alert("BNS", 65.0, 0.10, "divergence")

    assert result is False
    assert service.nb_erreurs == 1


# ---------------------------------------------------------------------------
# Test 7 : url_configuree reflect l'état de la variable d'environnement
# ---------------------------------------------------------------------------

def test_url_configuree_false_sans_env(monkeypatch):
    monkeypatch.delenv("WEBHOOK_URL", raising=False)
    service = WebhookService()
    assert service.url_configuree is False


def test_url_configuree_true_avec_env(monkeypatch):
    monkeypatch.setenv("WEBHOOK_URL", "http://hooks.slack.com/xxx")
    service = WebhookService()
    assert service.url_configuree is True
