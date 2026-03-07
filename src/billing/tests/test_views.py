"""Tests for billing views."""

from __future__ import annotations

from unittest.mock import patch

import pytest
from django.test import RequestFactory
from django.contrib.auth import get_user_model

from billing.views import checkout_cancel, checkout_success, stripe_webhook

User = get_user_model()


@pytest.fixture
def rf():
    return RequestFactory()


@pytest.fixture
def user(db):
    return User.objects.create_user(
        username="billinguser",
        password="testpass",
        email="billing@test.de",
    )


class TestCheckoutSuccess:
    def test_returns_200_with_plan(self, rf, user):
        request = rf.get("/billing/success/", {"plan": "professional"})
        request.user = user
        response = checkout_success(request)
        assert response.status_code == 200
        assert b"professional" in response.content

    def test_returns_200_without_plan(self, rf, user):
        request = rf.get("/billing/success/")
        request.user = user
        response = checkout_success(request)
        assert response.status_code == 200


class TestCheckoutCancel:
    def test_redirects_to_home(self, rf, user):
        request = rf.get("/billing/cancel/")
        request.user = user
        response = checkout_cancel(request)
        assert response.status_code == 302
        assert response["Location"] == "/"


@pytest.mark.django_db
class TestStripeWebhook:
    def test_invalid_signature_returns_400(self, rf):
        request = rf.post(
            "/billing/webhook/",
            data=b'{"id": "evt_test"}',
            content_type="application/json",
        )
        request.META["HTTP_STRIPE_SIGNATURE"] = "invalid"
        with patch("billing.views.stripe.Webhook.construct_event") as mock_construct:
            import stripe

            mock_construct.side_effect = stripe.error.SignatureVerificationError(
                "bad sig", "invalid"
            )
            response = stripe_webhook(request)
        assert response.status_code == 400

    def test_duplicate_event_returns_200(self, rf):
        from billing.models import BillingEvent

        BillingEvent.objects.create(
            stripe_event_id="evt_dup",
            event_type="checkout.session.completed",
            payload={},
            processed=True,
        )
        fake_event = {
            "id": "evt_dup",
            "type": "checkout.session.completed",
            "data": {"object": {}},
        }
        request = rf.post(
            "/billing/webhook/",
            data=b'{"id": "evt_dup"}',
            content_type="application/json",
        )
        with patch("billing.views.stripe.Webhook.construct_event", return_value=fake_event):
            response = stripe_webhook(request)
        assert response.status_code == 200

    def test_unknown_event_type_returns_200(self, rf):
        fake_event = {
            "id": "evt_unknown",
            "type": "unknown.event.type",
            "data": {"object": {}},
        }
        request = rf.post(
            "/billing/webhook/",
            data=b'{"id": "evt_unknown"}',
            content_type="application/json",
        )
        with patch("billing.views.stripe.Webhook.construct_event", return_value=fake_event):
            response = stripe_webhook(request)
        assert response.status_code == 200
