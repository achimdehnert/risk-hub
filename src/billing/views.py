"""Billing views — Checkout redirect, Customer Portal, Stripe Webhook."""

from __future__ import annotations

import json
import logging

import stripe
from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.http import HttpRequest, HttpResponse
from django.shortcuts import redirect
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from django_tenancy.models import Organization

from billing.constants import get_price_id
from billing.models import BillingEvent
from billing.services import create_checkout_session, create_portal_session
from billing.webhooks import EVENT_HANDLERS

logger = logging.getLogger(__name__)


def _get_organization(request: HttpRequest) -> Organization | None:
    tenant_id = getattr(request, "tenant_id", None)
    if not tenant_id:
        return None
    try:
        return Organization.objects.get(tenant_id=tenant_id)
    except Organization.DoesNotExist:
        return None


@login_required
def checkout_redirect(request: HttpRequest) -> HttpResponse:
    """Create a Stripe Checkout Session and redirect the user to it."""
    plan = request.GET.get("plan", "professional")
    billing = request.GET.get("billing", "monthly")

    price_id = get_price_id(plan, billing)
    if not price_id:
        logger.error("[billing] No price_id configured for plan=%s billing=%s", plan, billing)
        return HttpResponse(
            "Plan nicht konfiguriert. Bitte kontaktieren Sie den Support.", status=400
        )

    org = _get_organization(request)
    if not org:
        return redirect(settings.LOGIN_URL)

    base_url = request.build_absolute_uri("/")
    success_url = f"{base_url}billing/success/?plan={plan}"
    cancel_url = f"{base_url}billing/cancel/"

    try:
        checkout_url = create_checkout_session(
            organization=org,
            price_id=price_id,
            plan_code=plan,
            success_url=success_url,
            cancel_url=cancel_url,
        )
        return redirect(checkout_url)
    except Exception:
        logger.exception("[billing] Failed to create checkout session for org=%s", org.pk)
        return HttpResponse("Fehler beim Starten des Checkouts.", status=500)


@login_required
def portal_redirect(request: HttpRequest) -> HttpResponse:
    """Redirect to the Stripe Customer Portal."""
    org = _get_organization(request)
    if not org:
        return redirect(settings.LOGIN_URL)

    return_url = request.build_absolute_uri("/dashboard/")
    try:
        portal_url = create_portal_session(org, return_url)
        return redirect(portal_url)
    except Exception:
        logger.exception("[billing] Failed to create portal session for org=%s", org.pk)
        return HttpResponse("Fehler beim Öffnen des Kundenportals.", status=500)


@login_required
def checkout_success(request: HttpRequest) -> HttpResponse:
    """Landing page after successful checkout."""
    plan = request.GET.get("plan", "")
    return HttpResponse(
        f"""
        <!doctype html><html lang="de"><head>
        <meta charset="utf-8"><meta http-equiv="refresh" content="3;url=/dashboard/">
        <title>Aktivierung erfolgreich</title>
        <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/css/bootstrap.min.css"
              rel="stylesheet">
        </head><body class="d-flex align-items-center justify-content-center min-vh-100 bg-light">
        <div class="text-center">
            <div class="display-1 mb-3">✅</div>
            <h2 class="fw-bold">Plan <strong>{plan}</strong> aktiviert!</h2>
            <p class="text-muted">Sie werden in 3 Sekunden zum Dashboard weitergeleitet…</p>
            <a href="/dashboard/" class="btn btn-primary mt-2">Jetzt zum Dashboard</a>
        </div></body></html>
        """
    )


@login_required
def checkout_cancel(request: HttpRequest) -> HttpResponse:
    """Landing page when checkout is cancelled."""
    return redirect("/")


@csrf_exempt
@require_POST
def stripe_webhook(request: HttpRequest) -> HttpResponse:
    """Receive and process Stripe webhook events."""
    payload = request.body
    sig_header = request.META.get("HTTP_STRIPE_SIGNATURE", "")
    webhook_secret = settings.STRIPE_WEBHOOK_SECRET

    try:
        event = stripe.Webhook.construct_event(payload, sig_header, webhook_secret)
    except stripe.error.SignatureVerificationError:
        logger.warning("[billing] Webhook signature verification failed")
        return HttpResponse(status=400)
    except Exception:
        logger.exception("[billing] Webhook parsing error")
        return HttpResponse(status=400)

    event_id = event["id"]
    event_type = event["type"]

    if BillingEvent.objects.filter(stripe_event_id=event_id).exists():
        logger.info("[billing] Duplicate webhook event %s — skipped", event_id)
        return HttpResponse(status=200)

    billing_event = BillingEvent.objects.create(
        stripe_event_id=event_id,
        event_type=event_type,
        payload=json.loads(payload),
    )

    handler = EVENT_HANDLERS.get(event_type)
    if handler:
        try:
            handler(event)
            billing_event.processed = True
            billing_event.save(update_fields=["processed"])
            logger.info("[billing] Event %s (%s) processed", event_id, event_type)
        except Exception as exc:
            billing_event.error = str(exc)
            billing_event.save(update_fields=["error"])
            logger.exception("[billing] Handler failed for event %s", event_id)
            return HttpResponse(status=500)
    else:
        logger.debug("[billing] No handler for event type %s", event_type)

    return HttpResponse(status=200)
