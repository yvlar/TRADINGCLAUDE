"""Tests unitaires du mapping `QuotaExceededError` → `HTTPException` 429 (Sprint 189)."""
from __future__ import annotations

from app.services.quota_service import QuotaExceededError
from app.utils.quota_http import quota_exceeded_http


def test_detail_structure_avec_borne_temporelle() -> None:
    """Borne mensuelle : `detail` structuré + en-tête `Retry-After`."""
    err = QuotaExceededError(
        "Quota mensuel atteint (plan free : 50/50 analyses).",
        plan="free",
        used=50,
        limit=50,
        retry_after_s=3600,
    )
    http = quota_exceeded_http(err)
    assert http.status_code == 429
    assert http.detail == {
        "message": "Quota mensuel atteint (plan free : 50/50 analyses).",
        "plan": "free",
        "used": 50,
        "limit": 50,
        "remaining": 0,
    }
    assert http.headers == {"Retry-After": "3600"}


def test_remaining_borne_basse_jamais_negatif() -> None:
    """`remaining` est borné à 0 même si `used` dépasse `limit` (borne screener)."""
    err = QuotaExceededError(
        "Liste de 10 tickers au-delà de la borne du plan free (max 5).",
        plan="free",
        used=10,
        limit=5,
        retry_after_s=None,
    )
    http = quota_exceeded_http(err)
    assert http.detail["remaining"] == 0
    # Borne de taille (pas temporelle) → aucun en-tête Retry-After.
    assert http.headers is None
