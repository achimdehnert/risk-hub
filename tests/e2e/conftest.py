"""
Playwright E2E Fixtures für risk-hub (ADR-040).

Stellt authentifizierte Browser-Sessions für Risk-Management-Tests bereit.
"""

from __future__ import annotations

import pytest
from django.contrib.auth.models import User
from playwright.sync_api import Page, expect


@pytest.fixture
def risk_user(db):
    """Test-User für risk-hub E2E Tests."""
    return User.objects.create_user(
        username="e2e_risk",
        email="e2e@risktest.local",
        password="testpass123!",
        is_active=True,
        is_staff=True,
    )


@pytest.fixture
def auth_page(page: Page, risk_user, live_server) -> Page:
    """Playwright Page mit eingeloggtem risk-hub User."""
    page.goto(f"{live_server.url}/accounts/login/")
    page.fill("[name=username]", risk_user.username)
    page.fill("[name=password]", "testpass123!")
    page.click("[type=submit]")
    page.wait_for_load_state("networkidle")
    return page


def assert_testid_visible(page: Page, testid: str) -> None:
    expect(page.locator(f"[data-testid='{testid}']")).to_be_visible()
