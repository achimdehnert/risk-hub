"""Billing URL patterns."""

from django.urls import path

from billing import views

app_name = "billing"

urlpatterns = [
    path("checkout/", views.checkout_redirect, name="checkout"),
    path("portal/", views.portal_redirect, name="portal"),
    path("success/", views.checkout_success, name="success"),
    path("cancel/", views.checkout_cancel, name="cancel"),
    path("webhook/", views.stripe_webhook, name="webhook"),
]
