"""
Tenant Isolation Tests — risk-hub (ADR-074)

Verifies that row-level tenant isolation via tenant_id works correctly:
- Organization data from Tenant A is invisible to Tenant B
- Site objects are scoped by tenant_id
- ApiKey access is isolated per tenant

These tests are MANDATORY CI-Gate (ADR-074 Layer 1 + Layer 2).
"""

import uuid

import pytest


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def tenant_a_id():
    return uuid.UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")


@pytest.fixture
def tenant_b_id():
    return uuid.UUID("bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb")


@pytest.fixture
def org_a(db, tenant_a_id):
    from django_tenancy.models import Organization
    return Organization.objects.create(
        tenant_id=tenant_a_id,
        name="Organisation A",
        slug="org-a",
    )


@pytest.fixture
def org_b(db, tenant_b_id):
    from django_tenancy.models import Organization
    return Organization.objects.create(
        tenant_id=tenant_b_id,
        name="Organisation B",
        slug="org-b",
    )


# ---------------------------------------------------------------------------
# Layer 1: Isolation Tests — Organization
# ---------------------------------------------------------------------------

@pytest.mark.django_db
def test_organization_isolated_by_tenant(org_a, org_b, tenant_a_id, tenant_b_id):
    """KRITISCH: Organisation von Tenant A darf bei Tenant B nicht sichtbar sein."""
    from django_tenancy.models import Organization

    results_b = Organization.objects.filter(tenant_id=tenant_b_id)
    assert not results_b.filter(pk=org_a.pk).exists(), (
        "ISOLATION FAILURE: Tenant B kann Organisation von Tenant A sehen!"
    )

    results_a = Organization.objects.filter(tenant_id=tenant_a_id)
    assert not results_a.filter(pk=org_b.pk).exists(), (
        "ISOLATION FAILURE: Tenant A kann Organisation von Tenant B sehen!"
    )


@pytest.mark.django_db
def test_site_isolated_by_tenant_id(db, org_a, org_b, tenant_a_id, tenant_b_id):
    """Site-Objekte sind nach tenant_id isoliert."""
    from tenancy.models import Site

    site_a = Site.objects.create(
        tenant_id=tenant_a_id,
        organization=org_a,
        name="Standort A",
    )

    results_b = Site.objects.filter(tenant_id=tenant_b_id)
    assert not results_b.filter(pk=site_a.pk).exists(), (
        "ISOLATION FAILURE: Tenant B kann Site von Tenant A sehen!"
    )


@pytest.mark.django_db
def test_two_tenants_have_independent_site_counts(db, org_a, org_b, tenant_a_id, tenant_b_id):
    """Tenant A und B haben unabhängige Site-Datensätze."""
    from tenancy.models import Site

    Site.objects.create(tenant_id=tenant_a_id, organization=org_a, name="Site A1")
    Site.objects.create(tenant_id=tenant_a_id, organization=org_a, name="Site A2")
    Site.objects.create(tenant_id=tenant_b_id, organization=org_b, name="Site B1")

    assert Site.objects.filter(tenant_id=tenant_a_id).count() == 2
    assert Site.objects.filter(tenant_id=tenant_b_id).count() == 1


# ---------------------------------------------------------------------------
# Layer 2: Propagation Tests — ApiKey isolation
# ---------------------------------------------------------------------------

@pytest.mark.django_db
def test_api_key_isolated_by_tenant(db, tenant_a_id, tenant_b_id):
    """ApiKey von Tenant A ist bei Tenant B nicht sichtbar."""
    from identity.models import ApiKey

    import hashlib

    key_a = ApiKey.objects.create(
        tenant_id=tenant_a_id,
        name="Key A",
        key_prefix="AAAA1234",
        key_hash=hashlib.sha256(b"secret-a").hexdigest(),
    )

    results_b = ApiKey.objects.filter(tenant_id=tenant_b_id)
    assert not results_b.filter(pk=key_a.pk).exists(), (
        "ISOLATION FAILURE: Tenant B kann ApiKey von Tenant A sehen!"
    )


@pytest.mark.django_db
def test_tenant_id_filter_returns_only_own_objects(db, tenant_a_id, tenant_b_id):
    """filter(tenant_id=...) gibt ausschließlich eigene Objekte zurück."""
    from tenancy.models import Site
    from django_tenancy.models import Organization

    org_a = Organization.objects.create(tenant_id=tenant_a_id, name="OrgA2", slug="org-a2")
    org_b = Organization.objects.create(tenant_id=tenant_b_id, name="OrgB2", slug="org-b2")

    Site.objects.create(tenant_id=tenant_a_id, organization=org_a, name="Sa")
    Site.objects.create(tenant_id=tenant_b_id, organization=org_b, name="Sb")

    for site in Site.objects.filter(tenant_id=tenant_a_id):
        assert site.tenant_id == tenant_a_id, (
            f"ISOLATION FAILURE: Site {site.pk} hat tenant_id={site.tenant_id}"
        )
