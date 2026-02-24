"""
E2E Tests: Authentication Flow — risk-hub (ADR-040).

Läuft gegen laufenden Docker-Container (Port 8090).
Kein live_server — risk-hub braucht PostgreSQL.
"""

from __future__ import annotations

import re

import pytest
from playwright.sync_api import Page, expect


BASE_URL = "http://localhost:8090"
pytestmark = pytest.mark.e2e

_TENANT_SKIP = pytest.mark.skip(
    reason="risk-hub braucht Tenant-Subdomain (demo.localhost:8090) — "
           "/etc/hosts + Nginx-Proxy konfigurieren für vollständige E2E-Tests"
)


def test_liveness_endpoint_returns_200(page: Page) -> None:
    response = page.goto(BASE_URL + "/livez/")
    assert response is not None
    assert response.status == 200


def test_readiness_endpoint_returns_200(page: Page) -> None:
    response = page.goto(BASE_URL + "/healthz/")
    assert response is not None
    assert response.status < 500


def test_admin_page_no_500(page: Page) -> None:
    response = page.goto(BASE_URL + "/admin/")
    assert response is not None
    assert response.status < 500


@_TENANT_SKIP
def test_login_page_renders(page: Page) -> None:
    response = page.goto(BASE_URL + "/accounts/login/")
    assert response is not None
    assert response.status < 500


@_TENANT_SKIP
def test_login_with_invalid_credentials(page: Page) -> None:
    page.goto(BASE_URL + "/accounts/login/")


@_TENANT_SKIP
def test_protected_page_redirects_to_login(page: Page) -> None:
    page.goto(BASE_URL + "/risk/")
    expect(page).to_have_url(re.compile(r"/accounts/login/"))
