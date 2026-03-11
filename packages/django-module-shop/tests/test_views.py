"""Tests for module-shop views (ADR-137 Phase 3)."""

import uuid
from unittest.mock import MagicMock

import pytest
from django.contrib.auth import get_user_model
from django.test import RequestFactory

from django_module_shop.views import (
    activate_view,
    cancel_view,
    catalogue_view,
    detail_view,
)

User = get_user_model()


@pytest.fixture
def rf():
    return RequestFactory()


@pytest.fixture
def user(db):
    return User.objects.create_user(
        username="alice",
        password="pw",
    )


def _attach_tenant(request, user):
    """Attach tenant + user + session to request."""
    request.user = user
    request.tenant_id = uuid.uuid4()
    request.tenant = MagicMock(
        tenant_id=request.tenant_id,
        plan_code="starter",
        name="Acme",
    )
    from django.contrib.sessions.backends.db import (
        SessionStore,
    )

    request.session = SessionStore()
    from django.contrib.messages.storage.fallback import (
        FallbackStorage,
    )

    setattr(request, "_messages", FallbackStorage(request))
    return request


class TestCatalogueView:
    def test_should_redirect_without_tenant(
        self,
        rf,
        user,
    ):
        request = rf.get("/modules/")
        request.user = user
        request.tenant_id = None
        request.tenant = None
        resp = catalogue_view(request)
        assert resp.status_code == 302

    def test_should_render_with_tenant(self, rf, user):
        request = rf.get("/modules/")
        _attach_tenant(request, user)
        resp = catalogue_view(request)
        assert resp.status_code == 200


class TestDetailView:
    def test_should_404_for_unknown_module(
        self,
        rf,
        user,
    ):
        request = rf.get("/modules/nonexistent/")
        _attach_tenant(request, user)
        resp = detail_view(request, code="nonexistent")
        assert resp.status_code == 404

    def test_should_render_known_module(
        self,
        rf,
        user,
    ):
        request = rf.get("/modules/risk/")
        _attach_tenant(request, user)
        resp = detail_view(request, code="risk")
        assert resp.status_code == 200


class TestActivateView:
    def test_should_redirect_get_to_detail(
        self,
        rf,
        user,
    ):
        request = rf.get("/modules/risk/activate/")
        _attach_tenant(request, user)
        resp = activate_view(request, code="risk")
        assert resp.status_code == 302

    def test_should_redirect_to_billing_hub(
        self,
        rf,
        user,
    ):
        request = rf.post("/modules/risk/activate/")
        _attach_tenant(request, user)
        resp = activate_view(request, code="risk")
        assert resp.status_code == 302
        assert "billing.test/checkout" in resp.url
        assert "module=risk" in resp.url

    def test_should_reject_non_bookable_module(
        self,
        rf,
        user,
    ):
        request = rf.post("/modules/locked/activate/")
        _attach_tenant(request, user)
        resp = activate_view(request, code="locked")
        assert resp.status_code == 302

    def test_should_404_unknown_module(
        self,
        rf,
        user,
    ):
        request = rf.post("/modules/xxx/activate/")
        _attach_tenant(request, user)
        resp = activate_view(request, code="xxx")
        assert resp.status_code == 404


class TestCancelView:
    def test_should_redirect_get(self, rf, user):
        request = rf.get("/modules/risk/cancel/")
        _attach_tenant(request, user)
        resp = cancel_view(request, code="risk")
        assert resp.status_code == 302

    def test_should_send_cancel_request(
        self,
        rf,
        user,
    ):
        request = rf.post("/modules/risk/cancel/")
        _attach_tenant(request, user)
        resp = cancel_view(request, code="risk")
        assert resp.status_code == 302
