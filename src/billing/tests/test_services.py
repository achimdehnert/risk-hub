"""Tests for billing services."""

from __future__ import annotations

from unittest.mock import patch

import pytest

from billing.models import StripeCustomer
from billing.services import (
    activate_subscription,
    get_or_create_customer,
    suspend_subscription,
)


@pytest.fixture
def org(db):
    from tenancy.models import Organization

    return Organization.objects.create(
        name="Billing Test Org",
        slug="billing-test-org",
        tenant_id="22222222-2222-2222-2222-222222222222",
    )


@pytest.fixture
def dt_org(db, org):
    from django_tenancy.models import Organization as DtOrg

    obj, _ = DtOrg.objects.get_or_create(slug=org.slug, defaults={"name": org.name})
    return obj


@pytest.mark.django_db
class TestGetOrCreateCustomer:
    def test_returns_existing_customer_id(self, org):
        StripeCustomer.objects.create(
            organization=org,
            stripe_customer_id="cus_existing",
        )
        result = get_or_create_customer(org)
        assert result == "cus_existing"

    def test_creates_new_customer_via_stripe(self, org):
        mock_customer = {"id": "cus_new_123"}
        with patch("billing.services.stripe") as mock_stripe:
            mock_stripe.api_key = ""
            mock_stripe.Customer.create.return_value = mock_customer
            result = get_or_create_customer(org)
        assert result == "cus_new_123"
        assert StripeCustomer.objects.filter(organization=org).exists()


@pytest.mark.django_db
class TestActivateSubscription:
    def test_activates_plan_modules(self, org):
        from django_tenancy.module_models import ModuleSubscription

        activate_subscription(org, "starter", "sub_123", "price_abc")
        subs = ModuleSubscription.objects.filter(tenant_id=org.tenant_id)
        assert subs.filter(module="gbu").exists()

    def test_unknown_plan_activates_nothing(self, org):
        from django_tenancy.module_models import ModuleSubscription

        activate_subscription(org, "nonexistent_plan", "sub_x", "price_x")
        assert ModuleSubscription.objects.filter(tenant_id=org.tenant_id).count() == 0


@pytest.mark.django_db
class TestSuspendSubscription:
    def test_suspends_active_modules(self, org, dt_org):
        from django_tenancy.module_models import ModuleSubscription

        ModuleSubscription.objects.create(
            organization_id=dt_org.pk,
            tenant_id=org.tenant_id,
            module="gbu",
            status=ModuleSubscription.Status.ACTIVE,
            plan_code="starter",
        )
        suspend_subscription(org)
        sub = ModuleSubscription.objects.get(tenant_id=org.tenant_id, module="gbu")
        assert sub.status == ModuleSubscription.Status.SUSPENDED

    def test_no_active_modules_is_safe(self, org):
        suspend_subscription(org)  # no exception
