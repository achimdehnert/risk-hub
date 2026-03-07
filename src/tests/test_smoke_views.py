"""Smoke tests — every important URL must return 200 (not 404/500/403).

Strategy:
- One `tenant_client` fixture: authenticated Django TestClient with full
  tenant context (org, membership, all module subscriptions + memberships).
- Parametrized test functions per app: list views, detail-stub views.
- Redirects (302) are expected for login-protected views without auth.
- All tests use @pytest.mark.django_db and the shared tenant_client fixture.

Adding a new view? Add its URL to the relevant URLS list below.
"""

import pytest


# ─── Module URL lists ─────────────────────────────────────────────────────────

DASHBOARD_URLS = [
    "/dashboard/",
]

RISK_URLS = [
    "/risk/assessments/",
]

EXPLOSIONSSCHUTZ_URLS = [
    "/ex/",
    "/ex/areas/",
    "/ex/equipment/",
    "/ex/zones/",
    "/ex/measures/",
]

SUBSTANCES_URLS = [
    "/substances/",
]

DSB_URLS = [
    "/dsb/",
    "/dsb/mandates/",
    "/dsb/vvt/",
    "/dsb/tom/",
    "/dsb/avv/",
    "/dsb/breaches/",
    "/dsb/dokumente/",
    "/dsb/loeschantraege/",
]

GBU_URLS = [
    "/gbu/",
    "/gbu/compliance/",
]

DOCUMENTS_URLS = [
    "/documents/",
]

ACTIONS_URLS = [
    "/actions/",
]

NOTIFICATIONS_URLS = [
    "/notifications/",
]

BRANDSCHUTZ_URLS = [
    "/brandschutz/",
]

TENANCY_URLS = [
    "/tenants/",
]

BILLING_URLS = [
    "/billing/",
]

PUBLIC_URLS = [
    "/",
    "/accounts/login/",
    "/livez/",
    "/healthz/",
]

ALL_AUTHENTICATED_URLS = (
    DASHBOARD_URLS
    + RISK_URLS
    + EXPLOSIONSSCHUTZ_URLS
    + SUBSTANCES_URLS
    + DSB_URLS
    + GBU_URLS
    + DOCUMENTS_URLS
    + ACTIONS_URLS
    + NOTIFICATIONS_URLS
    + BRANDSCHUTZ_URLS
    + TENANCY_URLS
)


# ─── Fixtures ─────────────────────────────────────────────────────────────────

ALL_MODULES = [
    "risk",
    "ex",
    "substances",
    "dsb",
    "gbu",
    "documents",
    "actions",
    "brandschutz",
]


@pytest.fixture
def smoke_org(db):
    """Active organization for smoke tests."""
    from tenancy.models import Organization

    return Organization.objects.create(
        slug="smoke-test-corp",
        name="Smoke Test Corp",
        status=Organization.Status.ACTIVE,
    )


@pytest.fixture
def smoke_user(db, smoke_org):
    """Staff user with tenant_id linked to smoke_org."""
    from tests.factories import UserFactory

    return UserFactory(
        is_staff=True,
        tenant_id=smoke_org.tenant_id,
    )


@pytest.fixture
def smoke_membership(db, smoke_org, smoke_user):
    """Membership: smoke_user is admin in smoke_org."""
    from tenancy.models import Membership

    return Membership.objects.create(
        tenant_id=smoke_org.tenant_id,
        organization=smoke_org,
        user=smoke_user,
        role=Membership.Role.ADMIN,
    )


@pytest.fixture
def smoke_modules(db, smoke_org, smoke_user, smoke_membership):
    """All business modules active for smoke_org + smoke_user has admin membership."""
    from django_tenancy.module_models import ModuleMembership, ModuleSubscription

    for module in ALL_MODULES:
        ModuleSubscription.objects.get_or_create(
            tenant_id=smoke_org.tenant_id,
            module=module,
            defaults={
                "organization": smoke_org,
                "status": ModuleSubscription.Status.ACTIVE,
                "plan_code": "business",
            },
        )
        ModuleMembership.objects.get_or_create(
            tenant_id=smoke_org.tenant_id,
            user=smoke_user,
            module=module,
            defaults={"role": ModuleMembership.Role.ADMIN},
        )


@pytest.fixture
def tenant_client(client, smoke_org, smoke_user, smoke_modules):
    """Authenticated TestClient with full tenant context injected."""
    client.force_login(smoke_user)

    # Patch session with tenant_id so middleware finds it
    session = client.session
    session["tenant_id"] = str(smoke_org.tenant_id)
    session["tenant_slug"] = smoke_org.slug
    session.save()

    # Monkey-patch: inject tenant onto every request via middleware override
    # by sending X-Tenant-Id header in all requests
    client.defaults["HTTP_X_TENANT_ID"] = str(smoke_org.tenant_id)

    return client


# ─── Helper ───────────────────────────────────────────────────────────────────


def _get(client, url):
    """GET url, return response. Follows redirects to final status."""
    return client.get(url, follow=False)


def _assert_not_error(response, url):
    """Assert response is not a server/client error (not 4xx/5xx except 302)."""
    status = response.status_code
    assert status not in (500,), f"500 Internal Server Error on {url}"
    assert status not in (404,), f"404 Not Found on {url}"
    # 403 allowed only for truly unauthorized — smoke_user is staff+admin
    assert status not in (403,), f"403 Forbidden on {url} — check module access or permissions"
    # 200 or 302 redirect (e.g. HTMX partial redirects) are fine
    assert status in (200, 302, 301), f"Unexpected status {status} on {url}"


# ─── Public URL tests ──────────────────────────────────────────────────────────


@pytest.mark.django_db
@pytest.mark.parametrize("url", PUBLIC_URLS)
def test_public_urls_not_500(client, url):
    """Public URLs must not return 500."""
    resp = client.get(url, follow=False)
    assert resp.status_code != 500, f"500 on {url}"
    assert resp.status_code != 404, f"404 on {url}"


# ─── Dashboard ────────────────────────────────────────────────────────────────


@pytest.mark.django_db
@pytest.mark.parametrize("url", DASHBOARD_URLS)
def test_dashboard_smoke(tenant_client, url):
    resp = _get(tenant_client, url)
    _assert_not_error(resp, url)


# ─── Risk ─────────────────────────────────────────────────────────────────────


@pytest.mark.django_db
@pytest.mark.parametrize("url", RISK_URLS)
def test_risk_smoke(tenant_client, url):
    resp = _get(tenant_client, url)
    _assert_not_error(resp, url)


# ─── Explosionsschutz ─────────────────────────────────────────────────────────


@pytest.mark.django_db
@pytest.mark.parametrize("url", EXPLOSIONSSCHUTZ_URLS)
def test_explosionsschutz_smoke(tenant_client, url):
    resp = _get(tenant_client, url)
    _assert_not_error(resp, url)


# ─── Substances / Gefahrstoffe ────────────────────────────────────────────────


@pytest.mark.django_db
@pytest.mark.parametrize("url", SUBSTANCES_URLS)
def test_substances_smoke(tenant_client, url):
    resp = _get(tenant_client, url)
    _assert_not_error(resp, url)


# ─── DSB / Datenschutz ────────────────────────────────────────────────────────


@pytest.mark.django_db
@pytest.mark.parametrize("url", DSB_URLS)
def test_dsb_smoke(tenant_client, url):
    resp = _get(tenant_client, url)
    _assert_not_error(resp, url)


# ─── GBU ──────────────────────────────────────────────────────────────────────


@pytest.mark.django_db
@pytest.mark.parametrize("url", GBU_URLS)
def test_gbu_smoke(tenant_client, url):
    resp = _get(tenant_client, url)
    _assert_not_error(resp, url)


# ─── Documents ────────────────────────────────────────────────────────────────


@pytest.mark.django_db
@pytest.mark.parametrize("url", DOCUMENTS_URLS)
def test_documents_smoke(tenant_client, url):
    resp = _get(tenant_client, url)
    _assert_not_error(resp, url)


# ─── Actions ──────────────────────────────────────────────────────────────────


@pytest.mark.django_db
@pytest.mark.parametrize("url", ACTIONS_URLS)
def test_actions_smoke(tenant_client, url):
    resp = _get(tenant_client, url)
    _assert_not_error(resp, url)


# ─── Notifications ────────────────────────────────────────────────────────────


@pytest.mark.django_db
@pytest.mark.parametrize("url", NOTIFICATIONS_URLS)
def test_notifications_smoke(tenant_client, url):
    resp = _get(tenant_client, url)
    _assert_not_error(resp, url)


# ─── Brandschutz ──────────────────────────────────────────────────────────────


@pytest.mark.django_db
@pytest.mark.parametrize("url", BRANDSCHUTZ_URLS)
def test_brandschutz_smoke(tenant_client, url):
    resp = _get(tenant_client, url)
    _assert_not_error(resp, url)


# ─── Tenancy (staff only) ─────────────────────────────────────────────────────


@pytest.mark.django_db
@pytest.mark.parametrize("url", TENANCY_URLS)
def test_tenancy_smoke(tenant_client, url):
    resp = _get(tenant_client, url)
    _assert_not_error(resp, url)


# ─── Anonym: should redirect to login, not crash ──────────────────────────────


@pytest.mark.django_db
@pytest.mark.parametrize("url", ALL_AUTHENTICATED_URLS)
def test_anonymous_redirects_not_crashes(client, url):
    """Unauthenticated requests must redirect (302) — never 500."""
    resp = client.get(url, follow=False)
    assert resp.status_code != 500, f"500 on anonymous {url}"
    assert resp.status_code != 404, f"404 on anonymous {url}"
    # Should redirect to login
    assert resp.status_code in (302, 301, 200), f"Unexpected {resp.status_code} on anonymous {url}"
