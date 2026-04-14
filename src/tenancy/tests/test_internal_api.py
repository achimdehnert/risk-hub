"""Tests for tenancy.internal_api — billing webhook activate/deactivate (ADR-118)."""

import hashlib
import hmac
import json
import time
import uuid

import pytest
from django.http import HttpRequest
from django.test import RequestFactory, override_settings

from tenancy.internal_api import (
    BillingHmacAuth,
    _unique_slug,
    _verify_hmac,
    activate,
    deactivate,
)
from tenancy.models import Membership, Organization

HMAC_SECRET = "test-billing-secret-2024"


def _make_request(payload: dict, secret: str = HMAC_SECRET) -> HttpRequest:
    """Build a signed request with HMAC headers."""
    body = json.dumps(payload)
    ts = str(int(time.time()))
    sig = hmac.new(
        secret.encode(),
        f"{ts}.{body}".encode(),
        hashlib.sha256,
    ).hexdigest()
    rf = RequestFactory()
    request = rf.post(
        "/api/internal/activate",
        data=body,
        content_type="application/json",
        HTTP_X_BILLING_TIMESTAMP=ts,
        HTTP_X_BILLING_SIGNATURE=sig,
        HTTP_AUTHORIZATION=f"Bearer {sig}",
    )
    return request


@pytest.mark.django_db
class TestVerifyHmac:
    """_verify_hmac integration tests."""

    @override_settings(BILLING_HMAC_SECRET=HMAC_SECRET)
    def test_should_verify_valid_request(self):
        request = _make_request({"tenant_id": str(uuid.uuid4())})
        assert _verify_hmac(request, HMAC_SECRET) is True

    def test_should_reject_missing_headers(self):
        rf = RequestFactory()
        request = rf.post("/api/internal/activate", data="{}", content_type="application/json")
        assert _verify_hmac(request, HMAC_SECRET) is False

    def test_should_reject_invalid_timestamp(self):
        rf = RequestFactory()
        request = rf.post(
            "/api/internal/activate",
            data="{}",
            content_type="application/json",
            HTTP_X_BILLING_TIMESTAMP="not-a-number",
            HTTP_X_BILLING_SIGNATURE="some-sig",
        )
        assert _verify_hmac(request, HMAC_SECRET) is False


@pytest.mark.django_db
class TestBillingHmacAuth:
    """BillingHmacAuth authenticator tests."""

    @override_settings(BILLING_HMAC_SECRET=HMAC_SECRET, BILLING_HMAC_SECRET_PREV="")
    def test_should_authenticate_valid_request(self):
        auth = BillingHmacAuth()
        request = _make_request({"test": True})
        result = auth.authenticate(request, "dummy-token")
        assert result == "hmac-ok"

    @override_settings(BILLING_HMAC_SECRET=HMAC_SECRET, BILLING_HMAC_SECRET_PREV="")
    def test_should_reject_wrong_secret(self):
        auth = BillingHmacAuth()
        request = _make_request({"test": True}, secret="wrong-secret")
        result = auth.authenticate(request, "dummy-token")
        assert result is None

    @override_settings(BILLING_HMAC_SECRET="", BILLING_HMAC_SECRET_PREV="")
    def test_should_reject_when_secret_not_configured(self):
        auth = BillingHmacAuth()
        request = _make_request({"test": True})
        result = auth.authenticate(request, "dummy-token")
        assert result is None

    @override_settings(
        BILLING_HMAC_SECRET="new-secret",
        BILLING_HMAC_SECRET_PREV=HMAC_SECRET,
    )
    def test_should_accept_previous_secret_during_rotation(self):
        auth = BillingHmacAuth()
        request = _make_request({"test": True}, secret=HMAC_SECRET)
        result = auth.authenticate(request, "dummy-token")
        assert result == "hmac-ok-prev"


@pytest.mark.django_db
class TestUniqueSlug:
    """_unique_slug helper tests."""

    def test_should_generate_slug_from_email(self):
        slug = _unique_slug("john.doe@example.com")
        assert slug == "johndoe" or slug.startswith("johndoe")

    def test_should_handle_collision(self):
        Organization.objects.create(slug="johndoe", name="First")
        slug = _unique_slug("john.doe@example.com")
        assert slug == "johndoe-1"

    def test_should_handle_multiple_collisions(self):
        Organization.objects.create(slug="johndoe", name="First")
        Organization.objects.create(slug="johndoe-1", name="Second")
        slug = _unique_slug("john.doe@example.com")
        assert slug == "johndoe-2"

    def test_should_handle_empty_prefix(self):
        slug = _unique_slug("@example.com")
        assert slug == "org"


@pytest.mark.django_db
class TestActivateEndpoint:
    """activate() function tests (called by billing-hub)."""

    def test_should_create_org_and_user(self):
        tenant_id = uuid.uuid4()
        request = _make_request({})  # request object needed for Django Ninja
        from tenancy.internal_api import ActivatePayload

        payload = ActivatePayload(
            tenant_id=tenant_id,
            email="new@example.com",
            plan="business",
            modules=["risk", "dsb"],
        )
        response = activate(request, payload)
        assert response.status == "activated"
        assert response.org_created is True
        assert response.user_created is True

        org = Organization.objects.get(tenant_id=tenant_id)
        assert org.plan_code == "business"
        assert org.status == Organization.Status.ACTIVE

        ms = Membership.objects.filter(tenant_id=tenant_id).first()
        assert ms is not None
        assert ms.role == Membership.Role.OWNER

    def test_should_be_idempotent(self):
        tenant_id = uuid.uuid4()
        request = _make_request({})
        from tenancy.internal_api import ActivatePayload

        payload = ActivatePayload(
            tenant_id=tenant_id,
            email="repeat@example.com",
            plan="starter",
        )
        r1 = activate(request, payload)
        assert r1.org_created is True

        r2 = activate(request, payload)
        assert r2.org_created is False
        assert r2.user_created is False

        assert Organization.objects.filter(tenant_id=tenant_id).count() == 1

    def test_should_reactivate_suspended_org(self):
        tenant_id = uuid.uuid4()
        Organization.objects.create(
            tenant_id=tenant_id,
            slug="suspended-org",
            name="Suspended",
            status=Organization.Status.SUSPENDED,
            is_readonly=True,
        )
        request = _make_request({})
        from tenancy.internal_api import ActivatePayload

        payload = ActivatePayload(
            tenant_id=tenant_id,
            email="reactivate@example.com",
            plan="business",
        )
        response = activate(request, payload)
        assert response.org_created is False

        org = Organization.objects.get(tenant_id=tenant_id)
        assert org.status == Organization.Status.ACTIVE
        assert org.is_readonly is False
        assert org.gdpr_delete_at is None

    def test_should_set_trial_status_when_trial_ends_at_provided(self):
        tenant_id = uuid.uuid4()
        request = _make_request({})
        from tenancy.internal_api import ActivatePayload

        payload = ActivatePayload(
            tenant_id=tenant_id,
            email="trial@example.com",
            plan="trial",
            trial_ends_at="2099-12-31T23:59:59+00:00",
        )
        response = activate(request, payload)
        assert response.org_created is True

        org = Organization.objects.get(tenant_id=tenant_id)
        assert org.status == Organization.Status.TRIAL


@pytest.mark.django_db
class TestDeactivateEndpoint:
    """deactivate() function tests."""

    def test_should_suspend_and_set_readonly(self):
        org = Organization.objects.create(
            slug="to-deactivate",
            name="Active Corp",
            status=Organization.Status.ACTIVE,
        )
        request = _make_request({})
        from tenancy.internal_api import DeactivatePayload

        payload = DeactivatePayload(
            tenant_id=org.tenant_id,
            reason="subscription ended",
        )
        response = deactivate(request, payload)
        assert response.status == "suspended"

        org.refresh_from_db()
        assert org.status == Organization.Status.SUSPENDED
        assert org.is_readonly is True
        assert org.gdpr_delete_at is not None
        assert "subscription ended" in org.deactivation_reason

    def test_should_handle_nonexistent_tenant(self):
        request = _make_request({})
        from tenancy.internal_api import DeactivatePayload

        payload = DeactivatePayload(
            tenant_id=uuid.uuid4(),
            reason="test",
        )
        response = deactivate(request, payload)
        assert response.status == "not_found"

    def test_should_set_default_reason(self):
        org = Organization.objects.create(
            slug="no-reason",
            name="No Reason Corp",
            status=Organization.Status.ACTIVE,
        )
        request = _make_request({})
        from tenancy.internal_api import DeactivatePayload

        payload = DeactivatePayload(tenant_id=org.tenant_id)
        deactivate(request, payload)

        org.refresh_from_db()
        assert "billing-hub" in org.deactivation_reason
