"""Tests for billing models."""

from __future__ import annotations

import pytest
from django.test import TestCase

from billing.models import BillingEvent


@pytest.mark.django_db
class TestBillingEvent(TestCase):
    def test_create_billing_event(self):
        event = BillingEvent.objects.create(
            stripe_event_id="evt_test_001",
            event_type="checkout.session.completed",
            payload={"id": "evt_test_001", "type": "checkout.session.completed"},
        )
        assert event.pk is not None
        assert event.processed is False
        assert event.error == ""
        assert str(event) == "checkout.session.completed (evt_test_001)"

    def test_billing_event_idempotency(self):
        BillingEvent.objects.create(
            stripe_event_id="evt_unique",
            event_type="invoice.paid",
            payload={},
        )
        assert BillingEvent.objects.filter(stripe_event_id="evt_unique").count() == 1

    def test_billing_event_ordering(self):
        BillingEvent.objects.create(stripe_event_id="evt_a", event_type="x", payload={})
        BillingEvent.objects.create(stripe_event_id="evt_b", event_type="y", payload={})
        ids = list(BillingEvent.objects.values_list("stripe_event_id", flat=True))
        assert ids[0] == "evt_b"
