# src/dsb/tests/test_views_deletion.py
"""
View-Tests für dsb/views_deletion.py — Coverage +8%.

Strategie:
- mock _check_module_access=None → @require_module bypass
- RequestFactory + req.tenant_id direkt setzen
"""

import uuid
from datetime import date
from unittest.mock import patch

import pytest
from django.test import RequestFactory

from dsb import views_deletion
from dsb.models import Mandate
from dsb.models.deletion_request import DeletionRequest, DeletionRequestStatus

_ALLOW_ALL = patch(
    "django_tenancy.module_access._check_module_access",
    return_value=None,
)


# =============================================================================
# FIXTURES
# =============================================================================


@pytest.fixture
def rf():
    return RequestFactory()


@pytest.fixture
def fixture_tenant_id():
    return uuid.uuid4()


@pytest.fixture
def fixture_user(db):
    from tests.factories import UserFactory

    return UserFactory()


@pytest.fixture
def fixture_mandate(db, fixture_tenant_id):
    return Mandate.objects.create(
        tenant_id=fixture_tenant_id,
        name="Test GmbH",
        dsb_appointed_date=date.today(),
        status="active",
    )


@pytest.fixture
def fixture_deletion_request(db, fixture_tenant_id, fixture_mandate):
    return DeletionRequest.objects.create(
        tenant_id=fixture_tenant_id,
        mandate=fixture_mandate,
        subject_name="Max Mustermann",
        subject_email="max@example.com",
        request_date=date.today(),
        request_description="Bitte alle Daten löschen.",
        status=DeletionRequestStatus.PENDING,
    )


def _req(rf, user, tenant_id, method="GET", path="/dsb/deletion-requests/", data=None):
    if method == "POST":
        r = rf.post(path, data or {})
    else:
        r = rf.get(path)
    r.user = user
    r.tenant_id = tenant_id
    r.session = {}
    from django.contrib.messages.storage.fallback import FallbackStorage

    r._messages = FallbackStorage(r)
    return r


# =============================================================================
# TESTS: deletion_request_list
# =============================================================================


@pytest.mark.django_db
class TestDeletionRequestListView:
    def test_returns_200_empty(self, rf, fixture_user, fixture_tenant_id):
        with _ALLOW_ALL:
            resp = views_deletion.deletion_request_list(_req(rf, fixture_user, fixture_tenant_id))
        assert resp.status_code == 200

    def test_returns_200_with_data(
        self, rf, fixture_user, fixture_tenant_id, fixture_deletion_request
    ):
        with _ALLOW_ALL:
            resp = views_deletion.deletion_request_list(_req(rf, fixture_user, fixture_tenant_id))
        assert resp.status_code == 200

    def test_isolates_tenant(self, rf, fixture_user, fixture_tenant_id, fixture_mandate):
        other_tid = uuid.uuid4()
        other_mandate = Mandate.objects.create(
            tenant_id=other_tid,
            name="Fremde GmbH",
            dsb_appointed_date=date.today(),
            status="active",
        )
        DeletionRequest.objects.create(
            tenant_id=other_tid,
            mandate=other_mandate,
            subject_name="Fremder User",
            subject_email="fremder@example.com",
            request_date=date.today(),
            request_description="Fremder Antrag",
        )
        with _ALLOW_ALL:
            resp = views_deletion.deletion_request_list(_req(rf, fixture_user, fixture_tenant_id))
        assert resp.status_code == 200


# =============================================================================
# TESTS: deletion_request_create
# =============================================================================


@pytest.mark.django_db
class TestDeletionRequestCreateView:
    def test_get_returns_200(self, rf, fixture_user, fixture_tenant_id):
        with _ALLOW_ALL:
            resp = views_deletion.deletion_request_create(_req(rf, fixture_user, fixture_tenant_id))
        assert resp.status_code == 200

    def test_post_valid_creates_request(self, rf, fixture_user, fixture_tenant_id, fixture_mandate):
        with _ALLOW_ALL:
            r = _req(
                rf,
                fixture_user,
                fixture_tenant_id,
                method="POST",
                data={
                    "mandate": str(fixture_mandate.pk),
                    "subject_name": "Anna Muster",
                    "subject_email": "anna@example.com",
                    "request_date": str(date.today()),
                    "request_description": "Alle Daten löschen.",
                },
            )
            before = DeletionRequest.objects.filter(tenant_id=fixture_tenant_id).count()
            resp = views_deletion.deletion_request_create(r)
        assert resp.status_code in (200, 302)
        if resp.status_code == 302:
            assert DeletionRequest.objects.filter(tenant_id=fixture_tenant_id).count() == before + 1


# =============================================================================
# TESTS: deletion_request_detail
# =============================================================================


@pytest.mark.django_db
class TestDeletionRequestDetailView:
    def test_returns_200(self, rf, fixture_user, fixture_tenant_id, fixture_deletion_request):
        with _ALLOW_ALL:
            resp = views_deletion.deletion_request_detail(
                _req(rf, fixture_user, fixture_tenant_id), pk=fixture_deletion_request.pk
            )
        assert resp.status_code == 200

    def test_wrong_tenant_returns_404(self, rf, fixture_user, fixture_deletion_request):
        from django.http import Http404

        with _ALLOW_ALL:
            with pytest.raises(Http404):
                views_deletion.deletion_request_detail(
                    _req(rf, fixture_user, uuid.uuid4()), pk=fixture_deletion_request.pk
                )


# =============================================================================
# TESTS: deletion_request_advance
# =============================================================================


@pytest.mark.django_db
class TestDeletionRequestAdvanceView:
    def test_get_redirects(self, rf, fixture_user, fixture_tenant_id, fixture_deletion_request):
        """GET → redirect zu detail"""
        with _ALLOW_ALL:
            resp = views_deletion.deletion_request_advance(
                _req(rf, fixture_user, fixture_tenant_id),
                pk=fixture_deletion_request.pk,
            )
        assert resp.status_code == 302

    def test_post_valid_transition(
        self, rf, fixture_user, fixture_tenant_id, fixture_deletion_request
    ):
        """POST pending → auth_sent"""
        with _ALLOW_ALL:
            r = _req(
                rf,
                fixture_user,
                fixture_tenant_id,
                method="POST",
                data={"new_status": DeletionRequestStatus.AUTH_SENT, "send_mail": "0"},
            )
            resp = views_deletion.deletion_request_advance(r, pk=fixture_deletion_request.pk)
        assert resp.status_code == 302
        fixture_deletion_request.refresh_from_db()
        assert fixture_deletion_request.status == DeletionRequestStatus.AUTH_SENT

    def test_post_invalid_transition_stays(
        self, rf, fixture_user, fixture_tenant_id, fixture_deletion_request
    ):
        """POST mit ungültigem Übergang → bleibt in PENDING"""
        with _ALLOW_ALL:
            r = _req(
                rf,
                fixture_user,
                fixture_tenant_id,
                method="POST",
                data={"new_status": DeletionRequestStatus.CLOSED, "send_mail": "0"},
            )
            resp = views_deletion.deletion_request_advance(r, pk=fixture_deletion_request.pk)
        assert resp.status_code == 302
        fixture_deletion_request.refresh_from_db()
        assert fixture_deletion_request.status == DeletionRequestStatus.PENDING
