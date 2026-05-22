"""Tests CI pour SlackService — aucun appel HTTP réel (httpx mocké)."""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import httpx
import pytest

from app.services.slack_service import SlackService


def _make_mock_response(status_code: int = 200) -> MagicMock:
    resp = MagicMock()
    resp.status_code = status_code
    resp.raise_for_status = MagicMock()
    return resp


# ---------------------------------------------------------------------------
# Test 1 : send_text() retourne False si SLACK_WEBHOOK_URL absent
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_send_text_sans_url_retourne_false(monkeypatch):
    monkeypatch.delenv("SLACK_WEBHOOK_URL", raising=False)
    service = SlackService()
    result = await service.send_text("test message")
    assert result is False


# ---------------------------------------------------------------------------
# Test 2 : send_text() appelle httpx avec le bon payload JSON si URL présente
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_send_text_avec_url_appelle_httpx(monkeypatch):
    monkeypatch.setenv("SLACK_WEBHOOK_URL", "https://hooks.slack.com/test")

    captured: list[dict] = []

    async def mock_post(self_client, url, *, json=None, **kwargs):
        captured.append(json)
        return _make_mock_response(200)

    with patch.object(httpx.AsyncClient, "post", mock_post):
        service = SlackService()
        result = await service.send_text("message de test Sprint 86")

    assert result is True
    assert len(captured) == 1
    assert captured[0] == {"text": "message de test Sprint 86"}


# ---------------------------------------------------------------------------
# Test 3 : send_esg_alert() retourne False si URL absente
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_send_esg_alert_sans_url_retourne_false(monkeypatch):
    monkeypatch.delenv("SLACK_WEBHOOK_URL", raising=False)
    service = SlackService()
    result = await service.send_esg_alert(ticker="BNS", score=3.0, threshold=5.0)
    assert result is False
