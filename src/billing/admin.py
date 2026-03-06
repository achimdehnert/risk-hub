"""Billing admin — read-only views for StripeCustomer, StripeSubscription, BillingEvent."""

from django.contrib import admin

from billing.models import BillingEvent, StripeCustomer, StripeSubscription


@admin.register(StripeCustomer)
class StripeCustomerAdmin(admin.ModelAdmin):
    list_display = ("organization", "stripe_customer_id", "created_at")
    search_fields = ("organization__name", "stripe_customer_id")
    readonly_fields = ("stripe_customer_id", "created_at")


@admin.register(StripeSubscription)
class StripeSubscriptionAdmin(admin.ModelAdmin):
    list_display = (
        "organization",
        "plan_code",
        "status",
        "current_period_end",
        "cancel_at_period_end",
        "updated_at",
    )
    list_filter = ("status", "plan_code")
    search_fields = ("organization__name", "stripe_subscription_id")
    readonly_fields = (
        "stripe_subscription_id",
        "stripe_price_id",
        "created_at",
        "updated_at",
    )


@admin.register(BillingEvent)
class BillingEventAdmin(admin.ModelAdmin):
    list_display = ("event_type", "stripe_event_id", "processed", "received_at")
    list_filter = ("processed", "event_type")
    search_fields = ("stripe_event_id", "event_type")
    readonly_fields = ("stripe_event_id", "event_type", "payload", "received_at")
