"""
E2E Tests: DSB Module (Datenschutzbeauftragter) — risk-hub (ADR-040).

Testet: Dashboard, Mandate-Liste, VVT-Liste, TOMs.
"""

from __future__ import annotations

import pytest
from playwright.sync_api import Page, expect


pytestmark = pytest.mark.e2e


def test_dsb_dashboard_renders(auth_page: Page, live_server) -> None:
    auth_page.goto(live_server.url + "/dsb/")
    auth_page.wait_for_load_state("networkidle")
    assert auth_page.url.endswith("/dsb/") or "/login/" not in auth_page.url
    expect(auth_page.locator("body")).to_be_visible()


def test_dsb_dashboard_no_500(auth_page: Page, live_server) -> None:
    response = auth_page.goto(live_server.url + "/dsb/")
    assert response is not None
    assert response.status < 500, f"Server error on DSB dashboard: {response.status}"


def test_dsb_mandate_list_renders(auth_page: Page, live_server) -> None:
    auth_page.goto(live_server.url + "/dsb/mandates/")
    auth_page.wait_for_load_state("networkidle")
    expect(auth_page.locator("body")).to_be_visible()


def test_dsb_mandate_list_no_500(auth_page: Page, live_server) -> None:
    response = auth_page.goto(live_server.url + "/dsb/mandates/")
    assert response is not None
    assert response.status < 500


def test_dsb_mandate_create_form_renders(auth_page: Page, live_server) -> None:
    auth_page.goto(live_server.url + "/dsb/mandates/new/")
    auth_page.wait_for_load_state("networkidle")
    expect(auth_page.locator("form")).to_be_visible()


def test_dsb_vvt_list_renders(auth_page: Page, live_server) -> None:
    auth_page.goto(live_server.url + "/dsb/vvt/")
    auth_page.wait_for_load_state("networkidle")
    expect(auth_page.locator("body")).to_be_visible()


def test_dsb_vvt_list_no_500(auth_page: Page, live_server) -> None:
    response = auth_page.goto(live_server.url + "/dsb/vvt/")
    assert response is not None
    assert response.status < 500


def test_dsb_vvt_create_form_renders(auth_page: Page, live_server) -> None:
    auth_page.goto(live_server.url + "/dsb/vvt/new/")
    auth_page.wait_for_load_state("networkidle")
    expect(auth_page.locator("form")).to_be_visible()
