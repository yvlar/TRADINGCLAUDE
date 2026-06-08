"""Mappe un dépassement de quota (couche service) vers un `429` HTTP (couche endpoint)."""
from __future__ import annotations

from fastapi import HTTPException

from app.services.quota_service import QuotaExceededError


def quota_exceeded_http(err: QuotaExceededError) -> HTTPException:
    """`QuotaExceededError` → `HTTPException` 429, avec `Retry-After` si la borne est temporelle.

    Le `detail` est un dict structuré (et non le seul message) pour que le front affiche un
    bandeau d'upgrade ciblé (plan courant, borne atteinte, restant). N'expose que les champs de
    quota déjà destinés au client — aucune donnée sensible (cohérent Sprint 125).
    """
    headers = {"Retry-After": str(err.retry_after_s)} if err.retry_after_s is not None else None
    detail = {
        "message": err.message,
        "plan": err.plan,
        "used": err.used,
        "limit": err.limit,
        "remaining": max(0, err.limit - err.used),
    }
    return HTTPException(status_code=429, detail=detail, headers=headers)
