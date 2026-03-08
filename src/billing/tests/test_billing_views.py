"""Tests for billing views — checkout_success, checkout_cancel, portal redirect."""
from __future__ import annotations

import pytest
from django.test import RequestFactory

from billing.views import checkout_cancel, checkout_success


@pytest.fixture
def rf():
    return RequestFactory()


@pytest.fixture
def fixture_user(db):
    from tests.factories import UserFactory

    return UserFactory()


def _req(rf, user, tenant_id=None, method="GET", path="/billing/"):
    r = rf.get(path)
    r.user = user
    r.tenant_id = tenant_id
    r.tenant = None
    return r


# ── checkout_success ────────────────────────────────────────────────────────


@pytest.mark.django_db
class TestCheckoutSuccessView:
    def test_should_return_200(self, rf, fixture_user):
        req = _req(rf, fixture_user)
        req.GET = req.GET.copy()
        req.GET["plan"] = "professional"
        resp = checkout_success(req)
        assert resp.status_code == 200

    def test_should_contain_plan_name(self, rf, fixture_user):
        req = _req(rf, fixture_user)
        req.GET = req.GET.copy()
        req.GET["plan"] = "enterprise"
        resp = checkout_success(req)
        assert b"enterprise" in resp.content

    def test_should_work_without_plan_param(self, rf, fixture_user):
        req = _req(rf, fixture_user)
        resp = checkout_success(req)
        assert resp.status_code == 200


# ── checkout_cancel ─────────────────────────────────────────────────────


@pytest.mark.django_db
class TestCheckoutCancelView:
    def test_should_redirect(self, rf, fixture_user):
        req = _req(rf, fixture_user)
        resp = checkout_cancel(req)
        assert resp.status_code == 302
        assert resp["Location"] == "/"


# ── checkout_redirect — no tenant → redirect to login ────────────────────


@pytest.mark.django_db
def test_checkout_redirect_without_tenant_redirects(client, db):
    from tests.factories import UserFactory

    user = UserFactory()
    client.force_login(user)
    resp = client.get("/billing/checkout/?plan=professional&billing=monthly")
    # Without tenant context → redirect (to login or /)
    assert resp.status_code in (302, 400)


# ── portal_redirect — no tenant → redirect to login ─────────────────────


@pytest.mark.django_db
def test_portal_redirect_without_tenant_redirects(client, db):
    from tests.factories import UserFactory

    user = UserFactory()
    client.force_login(user)
    resp = client.get("/billing/portal/")
    assert resp.status_code == 302


# ── Billing smoke — anon redirects ────────────────────────────────────────


@pytest.mark.django_db
@pytest.mark.parametrize("url", ["/billing/", "/billing/checkout/", "/billing/portal/"])
def test_billing_anon_redirects_not_500(client, url):
    resp = client.get(url, follow=False)
    assert resp.status_code not in (500, 404), f"Unexpected {resp.status_code} on {url}"
