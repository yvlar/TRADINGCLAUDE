"""Tests /healthz — validation de l'endpoint pour le déploiement production."""
from __future__ import annotations

import pytest


@pytest.mark.asyncio
async def test_healthz_retourne_ok(client):
    """GET /healthz retourne {"status": "ok"}."""
    response = await client.get("/healthz")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"


@pytest.mark.asyncio
async def test_healthz_inclut_version(client):
    """GET /healthz inclut un champ version non vide."""
    response = await client.get("/healthz")
    assert response.status_code == 200
    data = response.json()
    assert "version" in data
    assert data["version"]
