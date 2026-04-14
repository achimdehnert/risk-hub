# tests/test_rls_context.py
"""Tests für Tenant-Context und Service-Account RLS-Integration (ADR-161 §3.2)."""

import uuid

import pytest
from django.db import connection

from common.context import (
    clear_context,
    get_context,
    set_db_service_account,
    set_db_tenant,
    set_tenant,
)


@pytest.fixture(autouse=True)
def _reset_context():
    """Ensure clean context before and after each test."""
    clear_context()
    yield
    clear_context()


class TestSetDbTenant:
    @pytest.mark.django_db
    def test_should_set_tenant_id_session_var(self):
        tid = uuid.uuid4()
        set_db_tenant(tid)
        with connection.cursor() as cursor:
            cursor.execute("SELECT current_setting('app.tenant_id', true)")
            val = cursor.fetchone()[0]
        assert val == str(tid)

    @pytest.mark.django_db
    def test_should_reset_tenant_id_when_none(self):
        tid = uuid.uuid4()
        set_db_tenant(tid)
        set_db_tenant(None)
        with connection.cursor() as cursor:
            cursor.execute("SELECT current_setting('app.tenant_id', true)")
            val = cursor.fetchone()[0]
        assert val in ("", None)

    @pytest.mark.django_db
    def test_should_reset_service_account_flag(self):
        """set_db_tenant always resets is_service_account to false."""
        set_db_service_account(True)
        set_db_tenant(uuid.uuid4())
        with connection.cursor() as cursor:
            cursor.execute("SELECT current_setting('app.is_service_account', true)")
            val = cursor.fetchone()[0]
        assert val == "false"


class TestSetDbServiceAccount:
    @pytest.mark.django_db
    def test_should_enable_service_account(self):
        set_db_service_account(True)
        with connection.cursor() as cursor:
            cursor.execute("SELECT current_setting('app.is_service_account', true)")
            val = cursor.fetchone()[0]
        assert val == "true"

    @pytest.mark.django_db
    def test_should_disable_service_account(self):
        set_db_service_account(True)
        set_db_service_account(False)
        with connection.cursor() as cursor:
            cursor.execute("SELECT current_setting('app.is_service_account', true)")
            val = cursor.fetchone()[0]
        assert val == "false"


class TestContextSetTenant:
    def test_should_set_context_vars(self):  # noqa: no DB needed
        tid = uuid.uuid4()
        set_tenant(tid, "acme")
        ctx = get_context()
        assert ctx.tenant_id == tid
        assert ctx.tenant_slug == "acme"

    def test_should_clear_context(self):  # noqa: no DB needed
        set_tenant(uuid.uuid4(), "acme")
        clear_context()
        ctx = get_context()
        assert ctx.tenant_id is None
        assert ctx.tenant_slug is None
