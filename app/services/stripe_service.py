"""Service de facturation Stripe — abonnements + synchronisation de plan (E4-S7).

Convertit le socle metering/quotas (S166-S171) en revenu réel :
- **checkout** : crée une session d'abonnement Stripe pour un tenant et un plan ;
- **synchronisation** : à la réception d'un événement d'abonnement signé, met à jour
  `tenants.plan` (le `QuotaService` et la purge de rétention en dépendent déjà) et la
  ligne `subscriptions` du tenant ;
- **idempotence** : un même `event.id` n'est traité qu'une fois (journal `stripe_events`) ;
- **facturation à l'usage** (E4-S9) : `report_usage` pousse la consommation agrégée vers un
  billing meter Stripe via l'API meters `stripe.billing.MeterEvent` (disponible depuis stripe-python
  11, SDK installé 15.x) — l'API « usage records » legacy ciblant un `subscription_item`
  (`SubscriptionItem.create_usage_record`) est absente du SDK installé ; désactivée proprement si le
  meter n'est pas configuré.

Sécurité — la signature `Stripe-Signature` (HMAC via `STRIPE_WEBHOOK_SECRET`) est la SEULE
authentification du webhook (endpoint auth-exempté) : `verify_event` doit être appelé AVANT
tout traitement. Aucune clé Stripe n'est jamais loggée (seuls `event.id`/type/tenant/plan).

Les appels réseau au SDK Stripe (synchrone) sont déportés via `asyncio.to_thread` pour ne
pas bloquer la boucle d'événements (convention async/await du projet). La clé secrète est
passée explicitement à chaque appel (`api_key=`) plutôt que via le global `stripe.api_key`.
"""
from __future__ import annotations

import asyncio
import json
import logging
from typing import Any
from uuid import UUID

import asyncpg
import stripe

logger = logging.getLogger(__name__)

# Événements d'abonnement → resynchronisation du plan du tenant.
_SUBSCRIPTION_EVENTS = frozenset(
    {
        "customer.subscription.created",
        "customer.subscription.updated",
        "customer.subscription.deleted",
    }
)

# Statuts de facture → statut d'abonnement (dunning) sans toucher au plan.
_INVOICE_STATUS = {
    "invoice.paid": "active",
    "invoice.payment_failed": "past_due",
}

# Plan de repli quand un abonnement est résilié ou que le price ne mappe aucun plan connu.
_DEFAULT_PLAN = "free"


class InvalidWebhookSignatureError(Exception):
    """Signature `Stripe-Signature` absente, malformée ou invalide → 400 au niveau endpoint."""


class NoStripeCustomerError(Exception):
    """Le tenant n'a pas de `stripe_customer_id` (jamais passé au checkout) → 409 au niveau endpoint."""


class StripeService:
    """Pilote Stripe : checkout, vérification de signature, synchronisation de plan."""

    def __init__(
        self,
        db_pool: asyncpg.Pool,
        *,
        secret_key: str | None,
        webhook_secret: str | None,
        price_by_plan: dict[str, str],
        meter_event_name: str | None = None,
    ) -> None:
        self._db = db_pool
        self._secret_key = secret_key
        self._webhook_secret = webhook_secret
        # Nom de l'événement du billing meter Stripe ciblé par `report_usage` (facturation à
        # l'usage, E4-S9). Absent → report d'usage désactivé (no-op), indépendamment du webhook.
        self._meter_event_name = meter_event_name
        # Mapping plan→price ET inverse price→plan (résolution du plan depuis un événement).
        self._price_by_plan = dict(price_by_plan)
        self._plan_by_price = {price: plan for plan, price in price_by_plan.items()}

    @property
    def is_configured(self) -> bool:
        """Vrai si la clé secrète ET le secret de webhook sont présents (sinon billing désactivé)."""
        return bool(self._secret_key) and bool(self._webhook_secret)

    @property
    def is_metered_configured(self) -> bool:
        """Vrai si la facturation à l'usage est active (clé secrète ET nom de meter présents).

        Indépendant de `is_configured` : le report d'usage n'a pas besoin du secret de webhook
        (il pousse vers Stripe, il ne reçoit rien) — seuls la clé secrète et le meter comptent.
        """
        return bool(self._secret_key) and bool(self._meter_event_name)

    def plan_for_price(self, price_id: str | None) -> str:
        """Plan correspondant à un price Stripe (repli `free` si inconnu ou None)."""
        # `price_id or ""` : None/"" → clé absente → repli (jamais un price Stripe valide).
        return self._plan_by_price.get(price_id or "", _DEFAULT_PLAN)

    # --- Checkout (souscription) ---

    async def create_checkout_session(
        self, tenant_id: UUID, plan: str, *, success_url: str, cancel_url: str
    ) -> str:
        """Crée une session de checkout d'abonnement et retourne son URL.

        Le `tenant_id` est propagé en `metadata` (sur la session ET la souscription) pour que
        le webhook d'abonnement résolve le tenant sans aller-retour supplémentaire.
        """
        price_id = self._price_by_plan.get(plan)
        if price_id is None:
            raise ValueError(f"Plan inconnu ou non facturable : {plan}")
        customer_id = await self._get_or_create_customer(tenant_id)
        session = await asyncio.to_thread(
            stripe.checkout.Session.create,
            api_key=self._secret_key,
            mode="subscription",
            customer=customer_id,
            line_items=[{"price": price_id, "quantity": 1}],
            success_url=success_url,
            cancel_url=cancel_url,
            client_reference_id=str(tenant_id),
            subscription_data={"metadata": {"tenant_id": str(tenant_id)}},
            metadata={"tenant_id": str(tenant_id)},
        )
        return session["url"]

    async def create_billing_portal_session(self, tenant_id: UUID, *, return_url: str) -> str:
        """Crée une session du Billing Portal Stripe pour le tenant et retourne son URL.

        Contrairement au checkout, on ne crée jamais le customer ici : un tenant sans
        `stripe_customer_id` n'a jamais souscrit → `NoStripeCustomerError` (409) plutôt que
        de fabriquer un customer vide.
        """
        row = await self._db.fetchrow(
            "SELECT stripe_customer_id FROM subscriptions WHERE tenant_id = $1::uuid",
            str(tenant_id),
        )
        if row is None or not row["stripe_customer_id"]:
            raise NoStripeCustomerError(f"Aucun customer Stripe pour le tenant {tenant_id}")
        session = await asyncio.to_thread(
            stripe.billing_portal.Session.create,
            api_key=self._secret_key,
            customer=row["stripe_customer_id"],
            return_url=return_url,
        )
        return session["url"]

    # --- Facturation à l'usage (metered usage records) ---

    async def report_usage(
        self,
        stripe_customer_id: str,
        quantity: int,
        *,
        timestamp: int | None = None,
        identifier: str | None = None,
    ) -> bool:
        """Pousse un metered usage record vers Stripe ; no-op si la facturation à l'usage est inactive.

        **Choix d'API documenté** : le SDK installé (`stripe` 15.x) ne fournit pas
        `SubscriptionItem.create_usage_record` (l'API « usage records » legacy ciblant un
        `subscription_item`). On utilise donc l'API meters `stripe.billing.MeterEvent.create`
        (présente depuis stripe-python 11) : l'usage est attribué au **meter** (`event_name`) et au
        **customer** (clé `stripe_customer_id` du payload, valeur dans la clé `value`), pas à un
        `subscription_item`. Stripe relie ensuite meter → price metered → abonnement du customer.

        `identifier` est propagé à Stripe qui déduplique les événements de même identifiant sur une
        fenêtre ≥ 24 h — second filet contre le double report en plus du journal `usage_report_log`.
        Retourne True si rapporté, False si désactivé (meter ou clé absente).
        """
        if not self.is_metered_configured:
            logger.info("Facturation à l'usage désactivée (meter/clé absent) — report ignoré")
            return False

        def _create_event() -> None:
            # kwargs construits dynamiquement : timestamp/identifier sont NotRequired côté SDK —
            # passer None les ferait rejeter, on ne les inclut que s'ils sont fournis.
            kwargs: dict[str, Any] = {
                "api_key": self._secret_key,
                "event_name": self._meter_event_name,
                "payload": {"stripe_customer_id": stripe_customer_id, "value": str(quantity)},
            }
            if timestamp is not None:
                kwargs["timestamp"] = timestamp
            if identifier is not None:
                kwargs["identifier"] = identifier
            stripe.billing.MeterEvent.create(**kwargs)

        await asyncio.to_thread(_create_event)
        return True

    async def _get_or_create_customer(self, tenant_id: UUID) -> str:
        """Retourne le `stripe_customer_id` du tenant, le créant (et le persistant) au besoin."""
        row = await self._db.fetchrow(
            "SELECT stripe_customer_id FROM subscriptions WHERE tenant_id = $1::uuid",
            str(tenant_id),
        )
        if row is not None and row["stripe_customer_id"]:
            return row["stripe_customer_id"]
        customer = await asyncio.to_thread(
            stripe.Customer.create,
            api_key=self._secret_key,
            metadata={"tenant_id": str(tenant_id)},
        )
        customer_id = customer["id"]
        await self._db.execute(
            """
            INSERT INTO subscriptions (tenant_id, stripe_customer_id)
            VALUES ($1::uuid, $2)
            ON CONFLICT (tenant_id)
            DO UPDATE SET stripe_customer_id = EXCLUDED.stripe_customer_id, updated_at = NOW()
            """,
            str(tenant_id),
            customer_id,
        )
        return customer_id

    # --- Webhook : vérification + routage ---

    def verify_event(self, payload: bytes, signature: str) -> dict[str, Any]:
        """Vérifie la signature `Stripe-Signature` et retourne l'événement (sinon lève).

        HMAC pur (pas d'I/O) : volontairement synchrone. À appeler AVANT tout traitement —
        c'est la seule authentification du webhook. On retourne le payload JSON brut (dicts
        Python natifs) plutôt que le `StripeObject` imbriqué de `construct_event`, pour que le
        routage opère sur des structures simples.
        """
        if not self._webhook_secret:
            raise InvalidWebhookSignatureError("Secret de webhook Stripe non configuré")
        try:
            stripe.Webhook.construct_event(payload, signature, self._webhook_secret)
        except (stripe.SignatureVerificationError, ValueError) as exc:
            # Signature invalide / payload malformé / horodatage hors tolérance. Fail-closed :
            # tout ce qui n'est pas une vérification propre est rejeté (400). On NE capte pas
            # les autres erreurs (bug SDK) — qu'elles remontent plutôt que d'être masquées.
            raise InvalidWebhookSignatureError(str(exc)) from exc
        return json.loads(payload)

    async def handle_event(self, event: dict[str, Any]) -> bool:
        """Traite un événement déjà vérifié (idempotent). Retourne False si déjà traité.

        **Atomicité claim+mutation** : la réservation `stripe_events` (ON CONFLICT DO NOTHING)
        et la mutation s'exécutent dans **une seule transaction**. Si la mutation échoue, la
        réservation est annulée (rollback) → le retry Stripe rejoue l'événement plutôt que de
        le sauter en silence (sinon une synchro de plan ratée serait perdue définitivement).
        """
        event_id = event["id"]
        async with self._db.acquire() as conn, conn.transaction():
            if not await self._claim_event(conn, event_id):
                logger.info("Événement Stripe déjà traité, ignoré : %s", event_id)
                return False

            event_type = event["type"]
            obj = event["data"]["object"]
            if event_type in _SUBSCRIPTION_EVENTS:
                await self._sync_subscription(conn, obj, deleted=event_type.endswith("deleted"))
            elif event_type in _INVOICE_STATUS:
                await self._mark_status(conn, obj, _INVOICE_STATUS[event_type])
            else:
                logger.info("Événement Stripe non géré, acquitté : %s (%s)", event_id, event_type)
        return True

    @staticmethod
    async def _claim_event(conn: asyncpg.Connection, event_id: str) -> bool:
        """Réserve un `event.id` ; True si nouveau (à traiter), False si déjà journalisé."""
        row = await conn.fetchrow(
            """
            INSERT INTO stripe_events (event_id) VALUES ($1)
            ON CONFLICT (event_id) DO NOTHING
            RETURNING event_id
            """,
            event_id,
        )
        return row is not None

    async def _sync_subscription(
        self, conn: asyncpg.Connection, subscription: dict[str, Any], *, deleted: bool
    ) -> None:
        """Met à jour `tenants.plan` + la ligne `subscriptions` depuis un objet subscription."""
        tenant_id = (subscription.get("metadata") or {}).get("tenant_id")
        if not _is_uuid(tenant_id):
            # tenant_id absent/malformé : acquitté (event réservé) sans synchro — pas de boucle
            # de retry sur un événement insoluble (le cast `::uuid` lèverait sinon dans la txn).
            logger.warning(
                "Abonnement Stripe sans metadata.tenant_id valide — synchronisation ignorée (%s)",
                subscription.get("id"),
            )
            return
        # Le tenant doit exister : sinon l'INSERT subscriptions violerait la FK → 500 → boucle
        # de retry Stripe. On acquitte plutôt l'événement (réservation conservée) avec un log.
        if not await conn.fetchval("SELECT 1 FROM tenants WHERE id = $1::uuid", tenant_id):
            logger.warning("Abonnement Stripe pour un tenant inconnu %s — ignoré", tenant_id)
            return

        if deleted:
            plan, status = _DEFAULT_PLAN, "canceled"
        else:
            plan = self.plan_for_price(_first_price_id(subscription))
            status = subscription.get("status", "active")

        customer_id = subscription.get("customer")
        subscription_id = subscription.get("id")

        # `tenants` et `subscriptions` sont HORS RLS → l'UPDATE par tenant_id arbitraire est
        # possible sous le contexte legacy du webhook (cf. docstring de la migration 0009).
        await conn.execute(
            "UPDATE tenants SET plan = $1 WHERE id = $2::uuid",
            plan,
            tenant_id,
        )
        await conn.execute(
            """
            INSERT INTO subscriptions
                (tenant_id, stripe_customer_id, stripe_subscription_id, status, plan, updated_at)
            VALUES ($1::uuid, $2, $3, $4, $5, NOW())
            ON CONFLICT (tenant_id) DO UPDATE SET
                stripe_customer_id     = COALESCE(EXCLUDED.stripe_customer_id, subscriptions.stripe_customer_id),
                stripe_subscription_id = EXCLUDED.stripe_subscription_id,
                status                 = EXCLUDED.status,
                plan                   = EXCLUDED.plan,
                updated_at             = NOW()
            """,
            tenant_id,
            customer_id,
            subscription_id,
            status,
            plan,
        )
        logger.info("Plan tenant %s synchronisé → %s (statut %s)", tenant_id, plan, status)

    @staticmethod
    async def _mark_status(conn: asyncpg.Connection, invoice: dict[str, Any], status: str) -> None:
        """Met à jour le seul statut d'abonnement (dunning) sans changer le plan."""
        subscription_id = invoice.get("subscription")
        customer_id = invoice.get("customer")
        await conn.execute(
            """
            UPDATE subscriptions SET status = $1, updated_at = NOW()
            WHERE stripe_subscription_id = $2 OR stripe_customer_id = $3
            """,
            status,
            subscription_id,
            customer_id,
        )


def _is_uuid(value: Any) -> bool:
    """Vrai si `value` est une chaîne UUID valide (garde avant un cast SQL `::uuid`)."""
    if not isinstance(value, str):
        return False
    try:
        UUID(value)
    except ValueError:
        return False
    return True


def _first_price_id(subscription: dict[str, Any]) -> str | None:
    """Extrait le price du premier item d'abonnement (None si structure absente)."""
    items = (subscription.get("items") or {}).get("data") or []
    if not items:
        return None
    return (items[0].get("price") or {}).get("id")
