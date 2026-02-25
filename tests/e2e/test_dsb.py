"""
E2E Tests: DSB Module (Datenschutzbeauftragter) — risk-hub (ADR-040).

Läuft gegen laufenden Docker-Container (Port 8090).
Auth-Seiten testen ohne Login (nur Status/Redirect prüfen).
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


def test_dsb_admin_no_500(page: Page) -> None:
    response = page.goto(BASE_URL + "/admin/")
    assert response is not None
    assert response.status < 500


@_TENANT_SKIP
def test_dsb_dashboard_redirects_to_login(page: Page) -> None:
    page.goto(BASE_URL + "/dsb/")
    page.wait_for_load_state("networkidle")
    expect(page).to_have_url(re.compile(r"/accounts/login/"))


@_TENANT_SKIP
def test_dsb_dashboard_no_500(page: Page) -> None:
    response = page.goto(BASE_URL + "/dsb/")
    assert response is not None
    assert response.status < 500


@_TENANT_SKIP
def test_dsb_mandate_list_redirects_to_login(page: Page) -> None:
    page.goto(BASE_URL + "/dsb/mandates/")
    page.wait_for_load_state("networkidle")
    expect(page).to_have_url(re.compile(r"/accounts/login/"))


@_TENANT_SKIP
def test_dsb_mandate_list_no_500(page: Page) -> None:
    response = page.goto(BASE_URL + "/dsb/mandates/")
    assert response is not None
    assert response.status < 500


@_TENANT_SKIP
def test_dsb_vvt_list_redirects_to_login(page: Page) -> None:
    page.goto(BASE_URL + "/dsb/vvt/")
    page.wait_for_load_state("networkidle")
    expect(page).to_have_url(re.compile(r"/accounts/login/"))


@_TENANT_SKIP
def test_dsb_vvt_list_no_500(page: Page) -> None:
    response = page.goto(BASE_URL + "/dsb/vvt/")
    assert response is not None
    assert response.status < 500
