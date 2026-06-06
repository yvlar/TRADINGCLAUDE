"""Mappe un dépassement de quota (couche service) vers un `429` HTTP (couche endpoint)."""
from __future__ import annotations

from fastapi import HTTPException

from app.services.quota_service import QuotaExceededError


def quota_exceeded_http(err: QuotaExceededError) -> HTTPException:
    """`QuotaExceededError` → `HTTPException` 429, avec `Retry-After` si la borne est temporelle."""
    headers = {"Retry-After": str(err.retry_after_s)} if err.retry_after_s is not None else None
    return HTTPException(status_code=429, detail=err.message, headers=headers)
