"""Tests for billing-hub internal API (ADR-118 Pilot).

Tests activate/deactivate endpoints with HMAC authentication.
"""

from __future__ import annotations

import hashlib
import hmac as hmac_mod
import json
import time
import uuid

import pytest
from django.test import Client

HMAC_SECRET = "test-hmac-secret-2026"
ENDPOINT_ACTIVATE = "/api/v1/internal/billing/activate"
ENDPOINT_DEACTIVATE = "/api/v1/internal/billing/deactivate"


def _sign(payload: dict, secret: str = HMAC_SECRET) -> dict:
    """Create HMAC-SHA256 headers matching billing-hub sign_request()."""
    timestamp = str(int(time.time()))
    body = json.dumps(payload, sort_keys=True)
    signature = hmac_mod.new(
        secret.encode(),
        f"{timestamp}.{body}".encode(),
        hashlib.sha256,
    ).hexdigest()
    return {
        "HTTP_X_BILLING_TIMESTAMP": timestamp,
        "HTTP_X_BILLING_SIGNATURE": signature,
        "HTTP_AUTHORIZATION": "Bearer hmac",
    }


def _post(client: Client, url: str, payload: dict, **extra):
    """POST JSON with HMAC headers."""
    headers = _sign(payload)
    headers.update(extra)
    body = json.dumps(payload, sort_keys=True)
    resp = client.post(
        url,
        data=body,
        content_type="application/json",
        **headers,
    )
    return {"status_code": resp.status_code, "data": resp.json()}


def _post_with_secret(client, url, payload, secret):
    """POST with a specific HMAC secret."""
    timestamp = str(int(time.time()))
    body = json.dumps(payload, sort_keys=True)
    signature = hmac_mod.new(
        secret.encode(),
        f"{timestamp}.{body}".encode(),
        hashlib.sha256,
    ).hexdigest()
    resp = client.post(
        url,
        data=body,
        content_type="application/json",
        HTTP_X_BILLING_TIMESTAMP=timestamp,
        HTTP_X_BILLING_SIGNATURE=signature,
        HTTP_AUTHORIZATION="Bearer hmac",
    )
    return {"status_code": resp.status_code, "data": resp.json()}


@pytest.fixture
def api_client():
    return Client()


@pytest.fixture(autouse=True)
def _hmac_settings(settings):
    settings.BILLING_HMAC_SECRET = HMAC_SECRET
    settings.BILLING_HMAC_SECRET_PREV = ""


# ── Activate ─────────────────────────────────────────────


@pytest.mark.django_db
def test_should_create_tenant_and_user(api_client):
    tenant_id = str(uuid.uuid4())
    payload = {
        "tenant_id": tenant_id,
        "email": "alice@firma.de",
        "plan": "professional",
        "modules": ["risk", "gbu"],
    }
    result = _post(api_client, ENDPOINT_ACTIVATE, payload)

    assert result["status_code"] == 200
    assert result["data"]["status"] == "activated"
    assert result["data"]["tenant_id"] == tenant_id
    assert result["data"]["org_created"] is True


@pytest.mark.django_db
def test_should_be_idempotent(api_client):
    tenant_id = str(uuid.uuid4())
    payload = {
        "tenant_id": tenant_id,
        "email": "bob@firma.de",
        "plan": "starter",
        "modules": ["gbu"],
    }
    r1 = _post(api_client, ENDPOINT_ACTIVATE, payload)
    r2 = _post(api_client, ENDPOINT_ACTIVATE, payload)

    assert r1["status_code"] == 200
    assert r2["status_code"] == 200
    assert r1["data"]["tenant_id"] == r2["data"]["tenant_id"]
    assert r2["data"]["org_created"] is False


@pytest.mark.django_db
def test_should_reactivate_suspended_org(api_client):
    from tenancy.models import Organization

    tenant_id = str(uuid.uuid4())
    payload = {
        "tenant_id": tenant_id,
        "email": "carol@firma.de",
        "plan": "business",
        "modules": ["risk", "ex"],
    }
    _post(api_client, ENDPOINT_ACTIVATE, payload)

    org = Organization.objects.get(tenant_id=tenant_id)
    org.status = Organization.Status.SUSPENDED
    org.is_readonly = True
    org.save()

    result = _post(api_client, ENDPOINT_ACTIVATE, payload)
    assert result["status_code"] == 200

    org.refresh_from_db()
    assert org.status == Organization.Status.ACTIVE
    assert org.is_readonly is False


@pytest.mark.django_db
def test_should_reject_without_hmac(api_client):
    payload = {
        "tenant_id": str(uuid.uuid4()),
        "email": "nobody@firma.de",
        "plan": "starter",
    }
    body = json.dumps(payload, sort_keys=True)
    resp = api_client.post(
        ENDPOINT_ACTIVATE,
        data=body,
        content_type="application/json",
    )
    assert resp.status_code == 401


@pytest.mark.django_db
def test_should_reject_expired_timestamp(api_client):
    payload = {
        "tenant_id": str(uuid.uuid4()),
        "email": "expired@firma.de",
        "plan": "starter",
    }
    timestamp = str(int(time.time()) - 600)
    body = json.dumps(payload, sort_keys=True)
    signature = hmac_mod.new(
        HMAC_SECRET.encode(),
        f"{timestamp}.{body}".encode(),
        hashlib.sha256,
    ).hexdigest()
    resp = api_client.post(
        ENDPOINT_ACTIVATE,
        data=body,
        content_type="application/json",
        HTTP_X_BILLING_TIMESTAMP=timestamp,
        HTTP_X_BILLING_SIGNATURE=signature,
        HTTP_AUTHORIZATION="Bearer hmac",
    )
    assert resp.status_code == 401


# ── Deactivate ───────────────────────────────────────────


@pytest.mark.django_db
def test_should_suspend_existing_org(api_client):
    tenant_id = str(uuid.uuid4())
    activate_payload = {
        "tenant_id": tenant_id,
        "email": "dave@firma.de",
        "plan": "professional",
        "modules": ["risk"],
    }
    _post(api_client, ENDPOINT_ACTIVATE, activate_payload)

    deactivate_payload = {
        "tenant_id": tenant_id,
        "reason": "trial_expired",
    }
    result = _post(
        api_client,
        ENDPOINT_DEACTIVATE,
        deactivate_payload,
    )

    assert result["status_code"] == 200
    assert result["data"]["status"] == "suspended"

    from tenancy.models import Organization

    org = Organization.objects.get(tenant_id=tenant_id)
    assert org.is_readonly is True
    assert org.status == Organization.Status.SUSPENDED
    assert org.deactivation_reason == "trial_expired"
    assert org.gdpr_delete_at is not None


@pytest.mark.django_db
def test_should_handle_unknown_tenant(api_client):
    payload = {
        "tenant_id": str(uuid.uuid4()),
        "reason": "cancelled",
    }
    result = _post(api_client, ENDPOINT_DEACTIVATE, payload)

    assert result["status_code"] == 200
    assert result["data"]["status"] == "not_found"


# ── Dual-Secret Rotation ────────────────────────────────


@pytest.mark.django_db
def test_should_accept_previous_secret(api_client, settings):
    settings.BILLING_HMAC_SECRET_PREV = "old-secret-2025"
    tenant_id = str(uuid.uuid4())
    payload = {
        "tenant_id": tenant_id,
        "email": "rotation@firma.de",
        "plan": "starter",
        "modules": ["gbu"],
    }
    result = _post_with_secret(
        api_client,
        ENDPOINT_ACTIVATE,
        payload,
        "old-secret-2025",
    )
    assert result["status_code"] == 200
    assert result["data"]["status"] == "activated"
