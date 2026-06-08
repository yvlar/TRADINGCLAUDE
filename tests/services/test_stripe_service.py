"""Tests unitaires StripeService — facturation Stripe (E4-S7).

SDK Stripe et asyncpg mockés — aucun appel réseau ni DB réels (validation runtime =
job CI migrations + `tests/integration/test_stripe_billing_webhook.py`).
"""
from __future__ import annotations

import json
import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import stripe

from app.services.stripe_service import (
    InvalidWebhookSignatureError,
    NoStripeCustomerError,
    StripeService,
)

_PRICES = {"free": "price_free", "pro": "price_pro"}


def _service(pool: AsyncMock, *, secret="sk_test_x", webhook="whsec_x") -> StripeService:
    return StripeService(
        pool, secret_key=secret, webhook_secret=webhook, price_by_plan=_PRICES
    )


def _sub_event(
    event_type: str,
    tenant_id: str,
    *,
    price_id: str = "price_pro",
    status: str = "active",
    sub_id: str = "sub_1",
    customer: str = "cus_1",
) -> dict:
    return {
        "id": "evt_" + uuid.uuid4().hex,
        "type": event_type,
        "data": {
            "object": {
                "id": sub_id,
                "customer": customer,
                "status": status,
                "metadata": {"tenant_id": tenant_id},
                "items": {"data": [{"price": {"id": price_id}}]},
            }
        },
    }


class TestConfig:
    def test_is_configured_vrai_si_cles_presentes(self):
        assert _service(AsyncMock()).is_configured is True

    @pytest.mark.parametrize("secret,webhook", [(None, "whsec"), ("sk", None), (None, None)])
    def test_is_configured_faux_si_cle_manquante(self, secret, webhook):
        svc = _service(AsyncMock(), secret=secret, webhook=webhook)
        assert svc.is_configured is False

    def test_plan_for_price_mappe_et_repli_free(self):
        svc = _service(AsyncMock())
        assert svc.plan_for_price("price_pro") == "pro"
        assert svc.plan_for_price("price_inconnu") == "free"
        assert svc.plan_for_price(None) == "free"


class TestVerifyEvent:
    def test_signature_valide_retourne_event_parse(self):
        """La signature OK → retourne le payload JSON parsé (dicts natifs), pas le StripeObject."""
        svc = _service(AsyncMock())
        payload = json.dumps({"id": "evt_1", "type": "x"}).encode()
        # Patch ciblé de construct_event uniquement (les classes d'erreur stripe restent réelles).
        with patch.object(stripe.Webhook, "construct_event", return_value=object()):
            event = svc.verify_event(payload, "t=1,v1=abc")
        assert event["id"] == "evt_1"

    def test_signature_invalide_leve_invalid(self):
        svc = _service(AsyncMock())
        with patch.object(
            stripe.Webhook, "construct_event", side_effect=ValueError("bad signature")
        ):
            with pytest.raises(InvalidWebhookSignatureError):
                svc.verify_event(b"{}", "t=1,v1=forged")

    def test_sans_webhook_secret_leve_invalid(self):
        svc = _service(AsyncMock(), webhook=None)
        with pytest.raises(InvalidWebhookSignatureError):
            svc.verify_event(b"{}", "t=1,v1=abc")


class TestCheckout:
    @pytest.mark.asyncio
    async def test_checkout_cree_customer_et_retourne_url(self):
        pool = AsyncMock()
        pool.fetchrow = AsyncMock(return_value=None)  # aucun customer existant
        pool.execute = AsyncMock()
        svc = _service(pool)
        tid = uuid.uuid4()
        with patch("app.services.stripe_service.stripe") as st:
            st.Customer.create = MagicMock(return_value={"id": "cus_new"})
            st.checkout.Session.create = MagicMock(return_value={"url": "https://stripe/checkout"})
            url = await svc.create_checkout_session(
                tid, "pro", success_url="https://s", cancel_url="https://c"
            )
        assert url == "https://stripe/checkout"
        st.Customer.create.assert_called_once()
        # Le price du plan pro est transmis à la session.
        _, kwargs = st.checkout.Session.create.call_args
        assert kwargs["line_items"][0]["price"] == "price_pro"
        assert kwargs["metadata"]["tenant_id"] == str(tid)

    @pytest.mark.asyncio
    async def test_checkout_reutilise_customer_existant(self):
        pool = AsyncMock()
        pool.fetchrow = AsyncMock(return_value={"stripe_customer_id": "cus_existing"})
        pool.execute = AsyncMock()
        svc = _service(pool)
        with patch("app.services.stripe_service.stripe") as st:
            st.Customer.create = MagicMock()
            st.checkout.Session.create = MagicMock(return_value={"url": "https://u"})
            await svc.create_checkout_session(
                uuid.uuid4(), "pro", success_url="https://s", cancel_url="https://c"
            )
        st.Customer.create.assert_not_called()

    @pytest.mark.asyncio
    async def test_checkout_plan_inconnu_leve_value_error(self):
        svc = _service(AsyncMock())
        with pytest.raises(ValueError):
            await svc.create_checkout_session(
                uuid.uuid4(), "entreprise", success_url="https://s", cancel_url="https://c"
            )


class TestBillingPortal:
    @pytest.mark.asyncio
    async def test_portal_retourne_url_pour_customer_existant(self):
        pool = AsyncMock()
        pool.fetchrow = AsyncMock(return_value={"stripe_customer_id": "cus_existing"})
        svc = _service(pool)
        with patch("app.services.stripe_service.stripe") as st:
            st.billing_portal.Session.create = MagicMock(return_value={"url": "https://stripe/portal"})
            url = await svc.create_billing_portal_session(
                uuid.uuid4(), return_url="https://app/facturation"
            )
        assert url == "https://stripe/portal"
        _, kwargs = st.billing_portal.Session.create.call_args
        assert kwargs["customer"] == "cus_existing"
        assert kwargs["return_url"] == "https://app/facturation"

    @pytest.mark.asyncio
    async def test_portal_sans_customer_leve_no_customer(self):
        """Aucune ligne subscriptions → NoStripeCustomerError (jamais de customer fabriqué)."""
        pool = AsyncMock()
        pool.fetchrow = AsyncMock(return_value=None)
        svc = _service(pool)
        with pytest.raises(NoStripeCustomerError):
            await svc.create_billing_portal_session(uuid.uuid4(), return_url="https://app")

    @pytest.mark.asyncio
    async def test_portal_customer_null_leve_no_customer(self):
        pool = AsyncMock()
        pool.fetchrow = AsyncMock(return_value={"stripe_customer_id": None})
        svc = _service(pool)
        with pytest.raises(NoStripeCustomerError):
            await svc.create_billing_portal_session(uuid.uuid4(), return_url="https://app")


class TestMeteredConfig:
    def test_is_metered_configured_vrai_si_secret_et_event_name(self):
        svc = StripeService(
            AsyncMock(), secret_key="sk", webhook_secret="whsec",
            price_by_plan=_PRICES, meter_event_name="usage_skill",
        )
        assert svc.is_metered_configured is True

    @pytest.mark.parametrize("secret,event_name", [(None, "usage"), ("sk", None), ("sk", "")])
    def test_is_metered_configured_faux_si_cle_ou_event_absent(self, secret, event_name):
        svc = StripeService(
            AsyncMock(), secret_key=secret, webhook_secret="whsec",
            price_by_plan=_PRICES, meter_event_name=event_name,
        )
        assert svc.is_metered_configured is False

    def test_is_metered_independant_de_webhook_secret(self):
        """Le webhook secret ne conditionne pas le report d'usage (distinct de is_configured)."""
        svc = StripeService(
            AsyncMock(), secret_key="sk", webhook_secret=None,
            price_by_plan=_PRICES, meter_event_name="usage_skill",
        )
        assert svc.is_metered_configured is True
        assert svc.is_configured is False


class TestReportUsage:
    @staticmethod
    def _metered_service() -> StripeService:
        return StripeService(
            AsyncMock(), secret_key="sk_test_x", webhook_secret="whsec_x",
            price_by_plan=_PRICES, meter_event_name="usage_skill_execution",
        )

    @pytest.mark.asyncio
    async def test_report_transmet_customer_quantity_timestamp(self):
        svc = self._metered_service()
        with patch("app.services.stripe_service.stripe") as st:
            st.billing.MeterEvent.create = MagicMock(return_value={"id": "mtr_1"})
            await svc.report_usage("cus_42", 7, timestamp=1717848000, identifier="t:1717848000")
        _, kwargs = st.billing.MeterEvent.create.call_args
        assert kwargs["event_name"] == "usage_skill_execution"
        assert kwargs["payload"] == {"stripe_customer_id": "cus_42", "value": "7"}
        assert kwargs["timestamp"] == 1717848000
        assert kwargs["identifier"] == "t:1717848000"

    @pytest.mark.asyncio
    async def test_report_passe_la_cle_par_appel(self):
        """api_key transmise par appel (jamais via le global stripe.api_key)."""
        svc = self._metered_service()
        with patch("app.services.stripe_service.stripe") as st:
            st.billing.MeterEvent.create = MagicMock(return_value={})
            await svc.report_usage("cus_1", 3, timestamp=1717848000)
        _, kwargs = st.billing.MeterEvent.create.call_args
        assert kwargs["api_key"] == "sk_test_x"

    @pytest.mark.asyncio
    async def test_report_sans_identifier_ne_transmet_pas_identifier(self):
        svc = self._metered_service()
        with patch("app.services.stripe_service.stripe") as st:
            st.billing.MeterEvent.create = MagicMock(return_value={})
            await svc.report_usage("cus_1", 1, timestamp=1717848000)
        _, kwargs = st.billing.MeterEvent.create.call_args
        assert "identifier" not in kwargs

    @pytest.mark.asyncio
    async def test_report_noop_si_meter_non_configure(self):
        """Sans STRIPE_METER_EVENT_NAME → no-op (aucun appel SDK), jamais d'erreur."""
        svc = StripeService(
            AsyncMock(), secret_key="sk", webhook_secret="whsec",
            price_by_plan=_PRICES, meter_event_name=None,
        )
        with patch("app.services.stripe_service.stripe") as st:
            st.billing.MeterEvent.create = MagicMock()
            await svc.report_usage("cus_1", 5, timestamp=1717848000)
        st.billing.MeterEvent.create.assert_not_called()

    @pytest.mark.asyncio
    async def test_report_aucune_cle_dans_les_logs(self, caplog):
        """La clé secrète ne doit jamais apparaître dans les logs du report."""
        import logging

        svc = self._metered_service()
        with patch("app.services.stripe_service.stripe") as st:
            st.billing.MeterEvent.create = MagicMock(return_value={})
            with caplog.at_level(logging.INFO, logger="app.services.stripe_service"):
                await svc.report_usage("cus_1", 2, timestamp=1717848000)
        assert "sk_test_x" not in caplog.text


class TestHandleEvent:
    """handle_event ouvre une transaction (acquire + transaction) ; claim+mutation atomiques."""

    @staticmethod
    def _conn(*, claim_new: bool = True, tenant_exists: bool = True) -> AsyncMock:
        conn = AsyncMock()
        conn.fetchrow = AsyncMock(return_value={"event_id": "evt"} if claim_new else None)
        conn.fetchval = AsyncMock(return_value=1 if tenant_exists else None)
        conn.execute = AsyncMock()
        tx = AsyncMock()
        tx.__aenter__ = AsyncMock(return_value=None)
        tx.__aexit__ = AsyncMock(return_value=None)
        conn.transaction = MagicMock(return_value=tx)
        return conn

    @staticmethod
    def _pool(conn: AsyncMock) -> AsyncMock:
        pool = AsyncMock()
        acquire = AsyncMock()
        acquire.__aenter__ = AsyncMock(return_value=conn)
        acquire.__aexit__ = AsyncMock(return_value=None)
        pool.acquire = MagicMock(return_value=acquire)
        return pool

    @pytest.mark.asyncio
    async def test_abonnement_synchronise_plan_pro(self):
        conn = self._conn()
        svc = _service(self._pool(conn))
        tid = str(uuid.uuid4())
        treated = await svc.handle_event(
            _sub_event("customer.subscription.updated", tid, price_id="price_pro")
        )
        assert treated is True
        # Le 1er execute met à jour tenants.plan → 'pro' pour le bon tenant.
        update_tenants = conn.execute.call_args_list[0]
        assert "UPDATE tenants SET plan" in update_tenants.args[0]
        assert update_tenants.args[1] == "pro"
        assert update_tenants.args[2] == tid

    @pytest.mark.asyncio
    async def test_idempotence_event_deja_traite(self):
        conn = self._conn(claim_new=False)  # claim : déjà journalisé
        svc = _service(self._pool(conn))
        treated = await svc.handle_event(
            _sub_event("customer.subscription.updated", str(uuid.uuid4()))
        )
        assert treated is False
        conn.execute.assert_not_awaited()  # aucune mutation sur un doublon

    @pytest.mark.asyncio
    async def test_resiliation_repli_free_et_canceled(self):
        conn = self._conn()
        svc = _service(self._pool(conn))
        tid = str(uuid.uuid4())
        await svc.handle_event(
            _sub_event("customer.subscription.deleted", tid, price_id="price_pro")
        )
        update_tenants = conn.execute.call_args_list[0]
        assert update_tenants.args[1] == "free"  # plan rétrogradé malgré le price pro

    @pytest.mark.asyncio
    async def test_abonnement_sans_tenant_metadata_ignore(self):
        conn = self._conn()
        svc = _service(self._pool(conn))
        event = _sub_event("customer.subscription.updated", "tid-placeholder")
        event["data"]["object"]["metadata"] = {}  # pas de tenant_id
        treated = await svc.handle_event(event)
        assert treated is True  # acquitté (event claimé)
        conn.execute.assert_not_awaited()  # mais aucune synchro

    @pytest.mark.asyncio
    async def test_tenant_id_malforme_ignore_sans_cast_sql(self):
        """metadata.tenant_id non-UUID → acquitté sans aucun accès DB de mutation (pas de cast)."""
        conn = self._conn()
        svc = _service(self._pool(conn))
        event = _sub_event("customer.subscription.updated", "pas-un-uuid")
        treated = await svc.handle_event(event)
        assert treated is True
        conn.fetchval.assert_not_awaited()  # même pas la vérification d'existence
        conn.execute.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_tenant_inconnu_acquitte_sans_mutation(self):
        """tenant_id valide mais absent de `tenants` → acquitté (pas de boucle de retry FK)."""
        conn = self._conn(tenant_exists=False)
        svc = _service(self._pool(conn))
        treated = await svc.handle_event(
            _sub_event("customer.subscription.updated", str(uuid.uuid4()))
        )
        assert treated is True
        conn.execute.assert_not_awaited()  # FK jamais violée

    @pytest.mark.asyncio
    async def test_invoice_payment_failed_marque_past_due(self):
        conn = self._conn()
        svc = _service(self._pool(conn))
        event = {
            "id": "evt_" + uuid.uuid4().hex,
            "type": "invoice.payment_failed",
            "data": {"object": {"subscription": "sub_1", "customer": "cus_1"}},
        }
        await svc.handle_event(event)
        status_update = conn.execute.call_args_list[0]
        assert "UPDATE subscriptions SET status" in status_update.args[0]
        assert status_update.args[1] == "past_due"

    @pytest.mark.asyncio
    async def test_event_non_gere_est_acquitte_sans_mutation(self):
        conn = self._conn()
        svc = _service(self._pool(conn))
        event = {"id": "evt_x", "type": "customer.created", "data": {"object": {}}}
        treated = await svc.handle_event(event)
        assert treated is True
        conn.execute.assert_not_awaited()
