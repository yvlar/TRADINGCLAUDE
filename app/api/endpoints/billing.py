"""Endpoints de facturation Stripe (E4-S7) — webhook + création de checkout.

`POST /billing/webhook` est **auth-exempté** (`EXEMPT_PATHS`/`CSRF_EXEMPT_PATHS`) : sa
seule authentification est la signature `Stripe-Signature`, vérifiée AVANT tout traitement.
`POST /billing/checkout` reste authentifié (cookie JWT) — c'est le tenant courant qui souscrit.
"""
from __future__ import annotations

import logging
import os

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from app.api.endpoints.auth import _get_current_user
from app.db.tenant_context import get_current_tenant
from app.services.stripe_service import InvalidWebhookSignatureError, StripeService
from app.utils.error_sanitization import sanitized_http_500

logger = logging.getLogger(__name__)

router = APIRouter(tags=["billing"])


class CheckoutRequest(BaseModel):
    plan: str


class CheckoutResponse(BaseModel):
    checkout_url: str


def _service(request: Request) -> StripeService:
    """Retourne le StripeService configuré ou lève 503 (facturation désactivée)."""
    service: StripeService | None = getattr(request.app.state, "stripe_service", None)
    if service is None or not service.is_configured:
        raise HTTPException(status_code=503, detail="Facturation Stripe non configurée")
    return service


@router.post("/billing/webhook", summary="Webhook Stripe (signature vérifiée, idempotent)")
async def stripe_webhook(request: Request) -> dict[str, bool]:
    """Reçoit les événements Stripe : signature → idempotence → synchronisation du plan."""
    service = _service(request)
    payload = await request.body()
    signature = request.headers.get("Stripe-Signature", "")
    try:
        event = service.verify_event(payload, signature)
    except InvalidWebhookSignatureError:
        # Aucune mutation : la signature est la seule authn — on rejette avant tout traitement.
        raise HTTPException(status_code=400, detail="Signature Stripe invalide")
    try:
        await service.handle_event(event)
    except Exception as exc:
        raise sanitized_http_500(exc, logger, "Erreur lors du traitement d'un webhook Stripe") from exc
    return {"received": True}


@router.post(
    "/billing/checkout",
    response_model=CheckoutResponse,
    summary="Crée une session de checkout d'abonnement pour le tenant courant",
)
async def create_checkout(request: Request, body: CheckoutRequest) -> CheckoutResponse:
    """Crée une session de checkout Stripe et retourne son URL (401 si non authentifié)."""
    await _get_current_user(request)
    service = _service(request)
    frontend_url = os.environ.get("FRONTEND_URL", "http://localhost:5173")
    try:
        url = await service.create_checkout_session(
            get_current_tenant(),
            body.plan,
            success_url=f"{frontend_url}/billing?status=success",
            cancel_url=f"{frontend_url}/billing?status=cancel",
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise sanitized_http_500(exc, logger, "Erreur lors de la création du checkout Stripe") from exc
    return CheckoutResponse(checkout_url=url)
