# src/dsb/tests/test_views_documents.py
"""
View-Tests für dsb/views_documents.py.
"""

import uuid
from datetime import date
from unittest.mock import patch

import pytest
from django.contrib.messages.storage.fallback import FallbackStorage
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import RequestFactory

from dsb import views_documents
from dsb.models import Mandate
from dsb.models.document import DsbDocument

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
def fixture_document(db, fixture_tenant_id, fixture_mandate):
    f = SimpleUploadedFile("test.pdf", b"PDF", content_type="application/pdf")
    return DsbDocument.objects.create(
        tenant_id=fixture_tenant_id,
        mandate=fixture_mandate,
        title="Test-Dokument",
        file=f,
        original_filename="test.pdf",
        file_size=3,
        mime_type="application/pdf",
    )


def _req(rf, user, tenant_id, method="GET", path="/dsb/docs/", data=None, files=None):
    if method == "POST":
        post_data = data or {}
        if files:
            post_data = {**post_data, **files}
        r = rf.post(path, post_data)
    else:
        r = rf.get(path, data or {})
    r.user = user
    r.tenant_id = tenant_id
    r.session = {}
    r._messages = FallbackStorage(r)
    return r


# =============================================================================
# TESTS: document_list
# =============================================================================


@pytest.mark.django_db
class TestDocumentListView:
    def test_returns_200_empty(self, rf, fixture_user, fixture_tenant_id):
        with _ALLOW_ALL:
            resp = views_documents.document_list(_req(rf, fixture_user, fixture_tenant_id))
        assert resp.status_code == 200

    def test_returns_200_with_doc(self, rf, fixture_user, fixture_tenant_id, fixture_document):
        with _ALLOW_ALL:
            resp = views_documents.document_list(_req(rf, fixture_user, fixture_tenant_id))
        assert resp.status_code == 200

    def test_filter_by_ref_type(self, rf, fixture_user, fixture_tenant_id, fixture_document):
        with _ALLOW_ALL:
            resp = views_documents.document_list(
                _req(
                    rf,
                    fixture_user,
                    fixture_tenant_id,
                    data={"ref_type": "breach"},
                )
            )
        assert resp.status_code == 200

    def test_isolates_tenant(self, rf, fixture_user, fixture_tenant_id):
        other_tid = uuid.uuid4()
        other_mandate = Mandate.objects.create(
            tenant_id=other_tid,
            name="Fremde GmbH",
            dsb_appointed_date=date.today(),
            status="active",
        )
        f = SimpleUploadedFile("other.pdf", b"X", content_type="application/pdf")
        DsbDocument.objects.create(
            tenant_id=other_tid,
            mandate=other_mandate,
            title="Fremdes Dok",
            file=f,
            original_filename="other.pdf",
        )
        with _ALLOW_ALL:
            resp = views_documents.document_list(_req(rf, fixture_user, fixture_tenant_id))
        assert resp.status_code == 200


# =============================================================================
# TESTS: document_upload
# =============================================================================


@pytest.mark.django_db
class TestDocumentUploadView:
    def test_get_returns_200(self, rf, fixture_user, fixture_tenant_id):
        with _ALLOW_ALL:
            resp = views_documents.document_upload(_req(rf, fixture_user, fixture_tenant_id))
        assert resp.status_code == 200

    def test_post_no_file_redisplays_form(self, rf, fixture_user, fixture_tenant_id):
        with _ALLOW_ALL:
            r = _req(
                rf,
                fixture_user,
                fixture_tenant_id,
                method="POST",
                data={"title": "Kein File"},
            )
            resp = views_documents.document_upload(r)
        assert resp.status_code == 200

    def test_post_no_title_redisplays_form(
        self, rf, fixture_user, fixture_tenant_id, fixture_mandate
    ):
        f = SimpleUploadedFile("x.pdf", b"data", content_type="application/pdf")
        with _ALLOW_ALL:
            r = rf.post("/dsb/docs/upload/", {"mandate": str(fixture_mandate.pk), "file": f})
            r.user = fixture_user
            r.tenant_id = fixture_tenant_id
            r.session = {}
            r._messages = FallbackStorage(r)
            resp = views_documents.document_upload(r)
        assert resp.status_code == 200

    def test_post_valid_redirects(self, rf, fixture_user, fixture_tenant_id, fixture_mandate):
        f = SimpleUploadedFile("doc.pdf", b"pdfdata", content_type="application/pdf")
        with _ALLOW_ALL:
            r = rf.post(
                "/dsb/docs/upload/",
                {
                    "mandate": str(fixture_mandate.pk),
                    "title": "Neues Dok",
                    "ref_type": "general",
                    "file": f,
                },
            )
            r.user = fixture_user
            r.tenant_id = fixture_tenant_id
            r.session = {}
            r._messages = FallbackStorage(r)
            resp = views_documents.document_upload(r)
        assert resp.status_code == 302


# =============================================================================
# TESTS: document_delete
# =============================================================================


@pytest.mark.django_db
class TestDocumentDeleteView:
    def test_get_redirects_to_list(self, rf, fixture_user, fixture_tenant_id, fixture_document):
        """GET auf delete-View → Redirect zur Liste."""
        with _ALLOW_ALL:
            resp = views_documents.document_delete(
                _req(rf, fixture_user, fixture_tenant_id), pk=fixture_document.pk
            )
        assert resp.status_code == 302

    def test_post_deletes_and_redirects(
        self, rf, fixture_user, fixture_tenant_id, fixture_document
    ):
        pk = fixture_document.pk
        with _ALLOW_ALL:
            r = _req(
                rf,
                fixture_user,
                fixture_tenant_id,
                method="POST",
                data={},
            )
            resp = views_documents.document_delete(r, pk=pk)
        assert resp.status_code == 302
        assert not DsbDocument.objects.filter(pk=pk).exists()

    def test_wrong_tenant_returns_404(self, rf, fixture_user, fixture_document):
        from django.http import Http404

        with _ALLOW_ALL:
            with pytest.raises(Http404):
                views_documents.document_delete(
                    _req(rf, fixture_user, uuid.uuid4(), method="POST"),
                    pk=fixture_document.pk,
                )
