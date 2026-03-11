"""Tests for billing webhook handlers."""

from __future__ import annotations

import pytest

from billing.webhooks import (
    EVENT_HANDLERS,
    handle_checkout_session_completed,
    handle_invoice_payment_failed,
    handle_invoice_payment_succeeded,
)


def _make_event(event_type, obj):
    return {"id": "evt_test", "type": event_type, "data": {"object": obj}}


@pytest.mark.django_db
class TestHandleCheckoutSessionCompleted:
    def test_non_subscription_mode_is_skipped(self):
        event = _make_event("checkout.session.completed", {"mode": "payment"})
        handle_checkout_session_completed(event)  # no exception

    def test_missing_tenant_id_logs_warning(self):
        from unittest.mock import patch

        event = _make_event(
            "checkout.session.completed",
            {"mode": "subscription", "subscription": "sub_123", "metadata": {}},
        )
        with patch("billing.webhooks.logger") as mock_log:
            handle_checkout_session_completed(event)
        mock_log.warning.assert_called_once()

    def test_unknown_tenant_id_skips(self):
        from unittest.mock import patch

        event = _make_event(
            "checkout.session.completed",
            {
                "mode": "subscription",
                "subscription": "sub_123",
                "metadata": {
                    "tenant_id": "00000000-0000-0000-0000-000000000000",
                    "plan_code": "professional",
                },
            },
        )
        with patch("billing.webhooks.logger") as mock_log:
            handle_checkout_session_completed(event)
        mock_log.warning.assert_called_once()


class TestHandleInvoicePaymentFailed:
    def test_logs_warning(self):
        from unittest.mock import patch

        event = _make_event(
            "invoice.payment_failed",
            {"customer": "cus_abc", "attempt_count": 2},
        )
        with patch("billing.webhooks.logger") as mock_log:
            handle_invoice_payment_failed(event)
        mock_log.warning.assert_called_once()


@pytest.mark.django_db
class TestHandleInvoicePaymentSucceeded:
    def test_no_subscription_id_returns_early(self):
        event = _make_event("invoice.payment_succeeded", {"subscription": None})
        handle_invoice_payment_succeeded(event)  # no exception

    def test_updates_period_end(self):
        from billing.models import StripeSubscription
        from tenancy.models import Organization

        org = Organization.objects.create(
            name="Test Org",
            slug="test-org-inv",
            tenant_id="11111111-1111-1111-1111-111111111111",
        )
        StripeSubscription.objects.create(
            organization=org,
            stripe_subscription_id="sub_inv_test",
            stripe_price_id="price_x",
            plan_code="professional",
            status="active",
        )
        event = _make_event(
            "invoice.payment_succeeded",
            {
                "subscription": "sub_inv_test",
                "lines": {"data": [{"period": {"end": 1800000000}}]},
            },
        )
        handle_invoice_payment_succeeded(event)
        sub = StripeSubscription.objects.get(stripe_subscription_id="sub_inv_test")
        assert sub.current_period_end is not None


class TestEventHandlersDict:
    def test_all_five_handlers_registered(self):
        expected = {
            "checkout.session.completed",
            "customer.subscription.updated",
            "customer.subscription.deleted",
            "invoice.payment_failed",
            "invoice.payment_succeeded",
        }
        assert set(EVENT_HANDLERS.keys()) == expected
