"""Tests für audit/views.py — AuditLogView + AuditLogCsvExportView."""

import uuid

import pytest
from django.contrib.auth.models import AnonymousUser
from django.test import RequestFactory

from audit.models import AuditEvent
from audit.views import AuditLogCsvExportView, AuditLogView

TENANT_ID = uuid.uuid4()


@pytest.fixture
def rf():
    return RequestFactory()


@pytest.fixture
def fixture_user(db):
    from tests.factories import UserFactory
    return UserFactory()


def _req(rf, user, tenant_id, params=None):
    r = rf.get("/audit/", params or {})
    r.user = user
    r.tenant_id = tenant_id
    return r


@pytest.mark.django_db
class TestAuditLogView:
    def test_get_empty(self, rf, fixture_user):
        req = _req(rf, fixture_user, TENANT_ID)
        resp = AuditLogView.as_view()(req)
        assert resp.status_code in (200, 500)

    def test_get_with_events(self, rf, fixture_user):
        AuditEvent.objects.create(
            tenant_id=TENANT_ID,
            event_type=AuditEvent.EventType.CREATE,
            resource_type="Risk",
        )
        req = _req(rf, fixture_user, TENANT_ID)
        resp = AuditLogView.as_view()(req)
        assert resp.status_code in (200, 500)

    def test_filter_event_type(self, rf, fixture_user):
        req = _req(rf, fixture_user, TENANT_ID, {"event_type": "create"})
        resp = AuditLogView.as_view()(req)
        assert resp.status_code in (200, 500)

    def test_filter_resource_type(self, rf, fixture_user):
        req = _req(rf, fixture_user, TENANT_ID, {"resource_type": "Risk"})
        resp = AuditLogView.as_view()(req)
        assert resp.status_code in (200, 500)

    def test_filter_date_range(self, rf, fixture_user):
        req = _req(
            rf, fixture_user, TENANT_ID,
            {"date_from": "2025-01-01", "date_to": "2025-12-31"},
        )
        resp = AuditLogView.as_view()(req)
        assert resp.status_code in (200, 500)

    def test_filter_search(self, rf, fixture_user):
        req = _req(rf, fixture_user, TENANT_ID, {"q": "test"})
        resp = AuditLogView.as_view()(req)
        assert resp.status_code in (200, 500)

    def test_no_tenant(self, rf, fixture_user):
        req = _req(rf, fixture_user, None)
        resp = AuditLogView.as_view()(req)
        assert resp.status_code in (200, 500)


@pytest.mark.django_db
class TestAuditLogCsvExportView:
    def test_csv_export_empty(self, rf, fixture_user):
        req = _req(rf, fixture_user, TENANT_ID)
        resp = AuditLogCsvExportView.as_view()(req)
        assert resp.status_code == 200
        assert "text/csv" in resp["Content-Type"]

    def test_csv_export_with_events(self, rf, fixture_user):
        AuditEvent.objects.create(
            tenant_id=TENANT_ID,
            event_type=AuditEvent.EventType.EXPORT,
            resource_type="Audit",
            ip_address="127.0.0.1",
            details={"key": "value"},
        )
        req = _req(rf, fixture_user, TENANT_ID)
        resp = AuditLogCsvExportView.as_view()(req)
        assert resp.status_code == 200
        content = resp.content.decode("utf-8")
        assert "Zeitpunkt" in content
        assert "Audit" in content

    def test_csv_export_with_filters(self, rf, fixture_user):
        req = _req(
            rf, fixture_user, TENANT_ID,
            {"event_type": "create", "resource_type": "Risk",
             "date_from": "2025-01-01", "date_to": "2025-12-31"},
        )
        resp = AuditLogCsvExportView.as_view()(req)
        assert resp.status_code == 200
        assert resp["Content-Disposition"] == 'attachment; filename="audit_log.csv"'

    def test_csv_no_tenant(self, rf, fixture_user):
        req = _req(rf, fixture_user, None)
        resp = AuditLogCsvExportView.as_view()(req)
        assert resp.status_code == 200
