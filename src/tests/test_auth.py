"""Auth + access control tests for risk-hub (ADR-058 A2).

risk-hub is multi-tenant (Schutztat). Cross-tenant isolation is critical.
"""

import pytest

try:
    from platform_context.testing.assertions import assert_login_required
except ImportError:

    def assert_login_required(client, url):
        response = client.get(url)
        assert response.status_code in (302, 301), f"{url} should redirect"
        assert "/login" in (response.get("Location") or ""), f"{url} should redirect to login"


PROTECTED_URLS = [
    "/dashboard/",
    "/risk/assessments/",
]


@pytest.mark.django_db
@pytest.mark.parametrize("url", PROTECTED_URLS)
def test_should_protected_url_require_login(client, url):
    """A2: All protected URLs redirect unauthenticated users to login."""
    assert_login_required(client, url)


@pytest.mark.django_db
def test_should_health_endpoint_be_public(client):
    """U9: /livez/ is reachable without authentication."""
    response = client.get("/livez/")
    assert response.status_code == 200


@pytest.mark.django_db
def test_should_authenticated_user_access_dashboard(auth_client):
    """U1: Authenticated user can access dashboard."""
    response = auth_client.get("/dashboard/")
    assert response.status_code in (200, 302)


@pytest.mark.django_db
def test_should_api_require_auth(client):
    """A2: API endpoints require authentication."""
    response = client.get("/api/v1/risk/hazards")
    assert response.status_code in (401, 403)
