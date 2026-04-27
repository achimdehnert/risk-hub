"""Conftest for projects tests — re-exports shared fixtures."""

import uuid

import factory
import pytest
from factory.django import DjangoModelFactory


class _UserFactory(DjangoModelFactory):
    class Meta:
        model = "identity.User"

    username = factory.Sequence(lambda n: f"proj_user_{n}")
    email = factory.LazyAttribute(lambda o: f"{o.username}@example.com")
    password = factory.PostGenerationMethodCall("set_password", "testpass123")
    is_active = True


@pytest.fixture
def fixture_user(db):
    return _UserFactory()


@pytest.fixture
def fixture_tenant(db, fixture_user):
    from tenancy.models import Membership, Organization

    org = Organization.objects.create(
        slug=f"proj-test-{uuid.uuid4().hex[:6]}",
        name="Projects Test Org",
    )
    Membership.objects.create(
        tenant_id=org.tenant_id,
        organization=org,
        user=fixture_user,
        role=Membership.Role.MEMBER,
    )
    return org
