"""Tests Sprint 77 — send_esg_alert() dans WebhookService."""
from __future__ import annotations

import os
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from app.services.webhook_service import WebhookService


def _make_mock_response(status_code: int = 200) -> MagicMock:
    resp = MagicMock()
    resp.status_code = status_code
    resp.raise_for_status = MagicMock()
    return resp


# ---------------------------------------------------------------------------
# Test 1 : WEBHOOK_URL absent → retourne False sans exception
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_send_esg_alert_sans_url_retourne_false(monkeypatch):
    monkeypatch.delenv("WEBHOOK_URL", raising=False)
    service = WebhookService()
    result = await service.send_esg_alert("BNS", 3.0, 5.0)
    assert result is False


# ---------------------------------------------------------------------------
# Test 2 : Payload — champs obligatoires présents
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_send_esg_alert_payload_champs_requis(monkeypatch):
    """Le payload contient type='esg_alert', ticker, esg_score, threshold, timestamp."""
    monkeypatch.setenv("WEBHOOK_URL", "http://webhook.test/hook")
    captured: list[dict] = []

    async def mock_post_capture(self_inner, payload: dict) -> bool:
        captured.append(payload)
        return True

    with patch.object(WebhookService, "_post", mock_post_capture):
        service = WebhookService()
        await service.send_esg_alert("BNS", 3.2, 5.0)

    assert len(captured) == 1
    p = captured[0]
    assert p["type"] == "esg_alert"
    assert p["ticker"] == "BNS"
    assert p["esg_score"] == 3.2
    assert p["threshold"] == 5.0
    assert "timestamp" in p


# ---------------------------------------------------------------------------
# Test 3 : Appel HTTP réel mocké — succès 200
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_send_esg_alert_succes_http(monkeypatch):
    """send_esg_alert retourne True si le webhook HTTP répond 200."""
    monkeypatch.setenv("WEBHOOK_URL", "http://webhook.test/hook")

    mock_resp = _make_mock_response(200)
    mock_client = AsyncMock()
    mock_client.post.return_value = mock_resp
    mock_ctx = AsyncMock()
    mock_ctx.__aenter__.return_value = mock_client
    mock_ctx.__aexit__.return_value = None

    with patch("app.services.webhook_service.httpx.AsyncClient", return_value=mock_ctx):
        service = WebhookService()
        result = await service.send_esg_alert("TD", 2.5, 5.0)

    assert result is True


# ---------------------------------------------------------------------------
# Test 4 : Erreur réseau → retourne False sans propager
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_send_esg_alert_erreur_reseau_retourne_false(monkeypatch):
    monkeypatch.setenv("WEBHOOK_URL", "http://webhook.test/hook")

    mock_client = AsyncMock()
    mock_client.post.side_effect = httpx.RequestError("connexion refusée")
    mock_ctx = AsyncMock()
    mock_ctx.__aenter__.return_value = mock_client
    mock_ctx.__aexit__.return_value = None

    with patch("app.services.webhook_service.httpx.AsyncClient", return_value=mock_ctx):
        service = WebhookService()
        result = await service.send_esg_alert("RY", 1.0, 5.0)

    assert result is False


# ---------------------------------------------------------------------------
# Test 5 : Payload ticker et score sont ceux fournis (pas de mutation)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_send_esg_alert_payload_valeurs_exactes(monkeypatch):
    monkeypatch.setenv("WEBHOOK_URL", "http://webhook.test/hook")
    captured: list[dict] = []

    async def mock_post_capture(self_inner, payload: dict) -> bool:
        captured.append(payload)
        return True

    with patch.object(WebhookService, "_post", mock_post_capture):
        service = WebhookService()
        await service.send_esg_alert("NA.TO", 4.9, 7.0)

    p = captured[0]
    assert p["ticker"] == "NA.TO"
    assert p["esg_score"] == 4.9
    assert p["threshold"] == 7.0
