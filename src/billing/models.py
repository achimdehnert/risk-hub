"""Stripe billing models — StripeCustomer, StripeSubscription, BillingEvent."""

from __future__ import annotations

import uuid

from django.db import models
from tenancy.models import Organization


class StripeCustomer(models.Model):
    """One-to-one mapping between an Organization and a Stripe Customer."""

    organization = models.OneToOneField(
        Organization,
        on_delete=models.CASCADE,
        related_name="stripe_customer",
    )
    stripe_customer_id = models.CharField(max_length=100, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "billing_stripe_customer"

    def __str__(self) -> str:
        return f"{self.organization.name} → {self.stripe_customer_id}"


class StripeSubscription(models.Model):
    """Active Stripe Subscription for an Organization."""

    class Status(models.TextChoices):
        TRIALING = "trialing", "Trial"
        ACTIVE = "active", "Aktiv"
        PAST_DUE = "past_due", "Zahlung überfällig"
        CANCELED = "canceled", "Gekündigt"
        UNPAID = "unpaid", "Unbezahlt"
        INCOMPLETE = "incomplete", "Unvollständig"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        related_name="stripe_subscriptions",
    )
    stripe_subscription_id = models.CharField(max_length=100, unique=True)
    stripe_price_id = models.CharField(max_length=100)
    plan_code = models.CharField(
        max_length=50,
        help_text="starter / professional / business / enterprise",
    )
    status = models.CharField(
        max_length=30,
        choices=Status.choices,
        default=Status.TRIALING,
    )
    current_period_start = models.DateTimeField(null=True, blank=True)
    current_period_end = models.DateTimeField(null=True, blank=True)
    cancel_at_period_end = models.BooleanField(default=False)
    canceled_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "billing_stripe_subscription"
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"{self.organization.name} [{self.plan_code}] {self.status}"

    @property
    def is_active(self) -> bool:
        return self.status in (self.Status.ACTIVE, self.Status.TRIALING)


class BillingEvent(models.Model):
    """Immutable audit log of all received Stripe webhook events."""

    stripe_event_id = models.CharField(max_length=100, unique=True)
    event_type = models.CharField(max_length=100)
    payload = models.JSONField()
    processed = models.BooleanField(default=False)
    error = models.TextField(blank=True, default="")
    received_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "billing_event"
        ordering = ["-received_at"]

    def __str__(self) -> str:
        return f"{self.event_type} ({self.stripe_event_id})"
