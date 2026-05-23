"""
Fixtures exclusives aux tests @pytest.mark.evals.

IMPORTANT : Ces fixtures font des appels Claude RÉELS.
Ne jamais patcher call_claude_with_retry dans ce module.

Stratégie de connexion :
- Si EVAL_API_URL est défini, pointe sur ce serveur (ex: http://localhost:8000).
- Sinon, utilise ASGITransport in-process (nécessite DB/Redis accessibles).
"""
from __future__ import annotations

import os

import pytest_asyncio
from httpx import ASGITransport, AsyncClient


@pytest_asyncio.fixture
async def eval_client() -> AsyncClient:
    """
    Client HTTP réel connecté à l'API copilote.
    Aucun mock Claude — les appels API sont intentionnellement réels.
    Requiert ANTHROPIC_API_KEY dans l'environnement.

    Si EVAL_API_URL est défini (ex: http://localhost:8000), s'y connecte directement.
    Sinon, lance l'app in-process via ASGITransport (nécessite DB/Redis locaux).
    """
    api_key = os.environ.get("API_KEY", "")
    eval_url = os.environ.get("EVAL_API_URL", "")
    headers = {"Authorization": f"Bearer {api_key}"} if api_key else {}

    if eval_url:
        async with AsyncClient(
            base_url=eval_url,
            headers=headers,
            timeout=120.0,
        ) as client:
            yield client
    else:
        from app.api.main import (
            app,  # import tardif pour éviter side-effects si EVAL_API_URL fourni
        )

        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
            headers=headers,
            timeout=120.0,
        ) as client:
            yield client
