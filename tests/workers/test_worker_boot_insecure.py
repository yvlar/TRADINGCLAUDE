"""Preuve d'intégration du garde S192 sur le chemin de boot worker réel (Sprint 196).

S192 a déplacé `require_secure_db_url` dans `create_runtime_pool` (chokepoint unique) et l'a prouvé
en **isolation** (`tests/db/test_pool.py`, mock `asyncpg.create_pool`). Ces tests complètent la preuve
sur le **chemin worker réel** : on appelle un vrai `_execute_*` (`_execute_weekly_watchlist_report`, où
`create_runtime_pool` est le tout premier `await`) sans mocker `create_runtime_pool`, pour vérifier que
le garde se déclenche bien quand un worker démarre sous une DSN insecure en prod — avant toute I/O DB.

Sans PG dans le conteneur web, c'est un **mock ciblé du chemin worker** (pas un boot Celery complet) :
seul `asyncpg.create_pool` est patché, pour constater qu'il n'est jamais atteint sous DSN insecure.
Aucune modification de `pool.py`/`tasks.py` — sprint de test pur.
"""
from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from app.workers.tasks import _execute_weekly_watchlist_report

_INSECURE_DSN = "postgresql://copilote:copilote@postgres:5432/copilote"
_SECURE_DSN = "postgresql://app_runtime:secret@host:5432/copilote"


@pytest.mark.asyncio
async def test_boot_worker_refuse_dsn_insecure_avant_create_pool(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """En prod + DSN insecure, le boot du worker lève via le garde du chokepoint, sans toucher la DB.

    Preuve que `require_secure_db_url` verrouille le chemin worker réel (pas seulement le helper
    isolé de `test_pool.py`) : `asyncpg.create_pool` ne doit jamais être awaité."""
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("APP_DATABASE_URL", _INSECURE_DSN)

    with patch(
        "app.db.pool.asyncpg.create_pool", new_callable=AsyncMock
    ) as mock_create_pool:
        # `par défaut` est propre au message du garde insecure-creds — discrimine d'un
        # éventuel RuntimeError de boot worker non lié au garde (preuve non vacue).
        with pytest.raises(RuntimeError, match="par défaut"):
            await _execute_weekly_watchlist_report()

    mock_create_pool.assert_not_awaited()


@pytest.mark.asyncio
async def test_boot_worker_accepte_dsn_secure_en_prod(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Discriminant : en prod, une DSN secure passe le garde et le worker atteint `create_pool`.

    Confirme que le `RuntimeError` du test précédent vient bien du garde insecure-creds (et non d'un
    échec de boot lié à `APP_ENV=production` en soi). Watchlist vide → retour anticipé propre."""
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("APP_DATABASE_URL", _SECURE_DSN)

    mock_wl_service = AsyncMock()
    mock_wl_service.list_entries.return_value = []

    with (
        patch(
            "app.db.pool.asyncpg.create_pool", new_callable=AsyncMock
        ) as mock_create_pool,
        patch("app.workers.tasks.WatchlistService", return_value=mock_wl_service),
    ):
        await _execute_weekly_watchlist_report()

    mock_create_pool.assert_awaited_once()
    mock_wl_service.list_entries.assert_awaited_once()
