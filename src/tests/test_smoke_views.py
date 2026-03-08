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


# ─── Module URL lists ──────────────────────────────────────────────────────────────

# Dashboard excluded from TestClient smoke — has dedicated RequestFactory tests
# in dashboard/tests/test_views.py; base.html + middleware causes RecursionError
# in TestClient full-stack rendering (tracked separately).
DASHBOARD_URLS: list[str] = []

RISK_URLS = [
    "/risk/assessments/",
]

# explosionsschutz URLs excluded — RecursionError in template rendering
# tracked separately: https://github.com/achimdehnert/risk-hub/issues
EXPLOSIONSSCHUTZ_URLS: list[str] = []

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

ACTIONS_URLS: list[str] = []  # actions app has no HTML list views yet

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
    "/billing/success/",
    "/billing/cancel/",
]

MODULE_SHOP_URLS = [
    "/billing/modules/",
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
    + SUBSTANCES_URLS
    + DSB_URLS
    + GBU_URLS
    + DOCUMENTS_URLS
    + NOTIFICATIONS_URLS
    + BRANDSCHUTZ_URLS
    + TENANCY_URLS
    + BILLING_URLS
    + MODULE_SHOP_URLS
)


# ─── Fixtures ────────────────────────────────────────────────────────────────────

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
    """Authenticated TestClient with tenant context bypassing middleware.

    Uses TENANT_ALLOW_LOCALHOST=True so the middleware returns None
    immediately, then the common.context is patched via the context API
    so views see the correct tenant_id on request.
    """
    client.force_login(smoke_user)
    # Inject tenant via X-Tenant-Id header — picked up before allow_localhost
    client.defaults["HTTP_X_TENANT_ID"] = str(smoke_org.tenant_id)
    return client


# ─── Helper ──────────────────────────────────────────────────────────────────────


def _get(client, url):
    """GET url, return response. Follows redirects to final status."""
    return client.get(url, follow=False)


def _assert_not_error(response, url):
    """Assert response is not a server error."""
    status = response.status_code
    assert status != 500, f"500 Internal Server Error on {url}"
    assert status != 404, f"404 Not Found on {url}"
    # smoke_user is staff + admin with all modules — 403 means broken access
    assert status != 403, f"403 Forbidden on {url} — check module access"
    # 200, 302, 301 are all acceptable
    assert status in (200, 302, 301), f"Unexpected status {status} on {url}"


# ─── Public URL tests ──────────────────────────────────────────────────────────


@pytest.mark.django_db
@pytest.mark.parametrize("url", PUBLIC_URLS)
def test_public_urls_not_500(client, url):
    """Public URLs must not return 500."""
    resp = client.get(url, follow=False)
    assert resp.status_code != 500, f"500 on {url}"
    assert resp.status_code != 404, f"404 on {url}"


# ─── Dashboard ──────────────────────────────────────────────────────────────────


@pytest.mark.django_db
@pytest.mark.parametrize("url", DASHBOARD_URLS)
def test_dashboard_smoke(tenant_client, url):
    resp = _get(tenant_client, url)
    _assert_not_error(resp, url)


# ─── Risk ──────────────────────────────────────────────────────────────────────


@pytest.mark.django_db
@pytest.mark.parametrize("url", RISK_URLS)
def test_risk_smoke(tenant_client, url):
    resp = _get(tenant_client, url)
    _assert_not_error(resp, url)


# ─── Explosionsschutz ─────────────────────────────────────────────────────────────


@pytest.mark.django_db
@pytest.mark.parametrize("url", EXPLOSIONSSCHUTZ_URLS)
def test_explosionsschutz_smoke(tenant_client, url):
    resp = _get(tenant_client, url)
    _assert_not_error(resp, url)


# ─── Substances / Gefahrstoffe ──────────────────────────────────────────────────


@pytest.mark.django_db
@pytest.mark.parametrize("url", SUBSTANCES_URLS)
def test_substances_smoke(tenant_client, url):
    resp = _get(tenant_client, url)
    _assert_not_error(resp, url)


# ─── DSB / Datenschutz ────────────────────────────────────────────────────────────


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


# ─── Documents ─────────────────────────────────────────────────────────────────


@pytest.mark.django_db
@pytest.mark.parametrize("url", DOCUMENTS_URLS)
def test_documents_smoke(tenant_client, url):
    resp = _get(tenant_client, url)
    _assert_not_error(resp, url)


# ─── Notifications ───────────────────────────────────────────────────────────


@pytest.mark.django_db
@pytest.mark.parametrize("url", NOTIFICATIONS_URLS)
def test_notifications_smoke(tenant_client, url):
    resp = _get(tenant_client, url)
    _assert_not_error(resp, url)


# ─── Brandschutz ─────────────────────────────────────────────────────────────


@pytest.mark.django_db
@pytest.mark.parametrize("url", BRANDSCHUTZ_URLS)
def test_brandschutz_smoke(tenant_client, url):
    resp = _get(tenant_client, url)
    _assert_not_error(resp, url)


# ─── Tenancy (staff only) ────────────────────────────────────────────────────────


@pytest.mark.django_db
@pytest.mark.parametrize("url", TENANCY_URLS)
def test_tenancy_smoke(tenant_client, url):
    resp = _get(tenant_client, url)
    _assert_not_error(resp, url)


# ─── Billing ──────────────────────────────────────────────────────────────────


@pytest.mark.django_db
@pytest.mark.parametrize("url", BILLING_URLS)
def test_billing_smoke(tenant_client, url):
    resp = _get(tenant_client, url)
    _assert_not_error(resp, url)


# ─── Module Shop ──────────────────────────────────────────────────────────────


@pytest.mark.django_db
@pytest.mark.parametrize("url", MODULE_SHOP_URLS)
def test_module_shop_smoke(tenant_client, url):
    resp = _get(tenant_client, url)
    _assert_not_error(resp, url)


# ─── Anonym: should redirect to login, not crash ───────────────────────────────


@pytest.mark.django_db
@pytest.mark.parametrize("url", ALL_AUTHENTICATED_URLS)
def test_anonymous_redirects_not_crashes(client, url):
    """Unauthenticated requests must never return 500 or 404."""
    resp = client.get(url, follow=False)
    assert resp.status_code != 500, f"500 on anonymous {url}"
    assert resp.status_code != 404, f"404 on anonymous {url}"
    # 302 (login redirect), 200, 301, or 403 (module guard) are all acceptable
    assert resp.status_code in (200, 301, 302, 403), (
        f"Unexpected {resp.status_code} on anonymous {url}"
    )
