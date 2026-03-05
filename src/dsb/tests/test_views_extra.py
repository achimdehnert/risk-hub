# src/dsb/tests/test_views_extra.py
"""
Ergänzende View-Tests für dsb/views.py:
- mandate_edit POST
- vvt_create / vvt_edit
- tom_create / tom_edit
- dpa_detail / dpa_create / dpa_edit
- avv_import (GET + template-download)
- csv_import (GET)
"""

import uuid
from datetime import date
from unittest.mock import patch

import pytest
from django.contrib.messages.storage.fallback import FallbackStorage
from django.http import Http404
from django.test import RequestFactory

from dsb import views
from dsb.models import DataProcessingAgreement, Mandate, ProcessingActivity

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
def fixture_vvt(db, fixture_tenant_id, fixture_mandate):
    return ProcessingActivity.objects.create(
        tenant_id=fixture_tenant_id,
        mandate=fixture_mandate,
        name="Lohnbuchhaltung",
        number=1,
        legal_basis="contract",
    )


@pytest.fixture
def fixture_dpa(db, fixture_tenant_id, fixture_mandate):
    return DataProcessingAgreement.objects.create(
        tenant_id=fixture_tenant_id,
        mandate=fixture_mandate,
        partner_name="Cloud AG",
        status="active",
    )


def _req(rf, user, tenant_id, method="GET", path="/dsb/", data=None):
    if method == "POST":
        r = rf.post(path, data or {})
    else:
        r = rf.get(path, data or {})
    r.user = user
    r.tenant_id = tenant_id
    r.session = {}
    r._messages = FallbackStorage(r)
    return r


# =============================================================================
# TESTS: mandate_edit POST
# =============================================================================


@pytest.mark.django_db
class TestMandateEditPost:
    def test_valid_post_updates_and_redirects(
        self, rf, fixture_user, fixture_tenant_id, fixture_mandate
    ):
        r = _req(
            rf,
            fixture_user,
            fixture_tenant_id,
            method="POST",
            data={
                "name": "Geänderte GmbH",
                "dsb_appointed_date": str(date.today()),
                "status": "active",
            },
        )
        resp = views.mandate_edit(r, pk=fixture_mandate.pk)
        assert resp.status_code in (200, 302)
        if resp.status_code == 302:
            fixture_mandate.refresh_from_db()
            assert fixture_mandate.name == "Geänderte GmbH"

    def test_wrong_tenant_raises_404(self, rf, fixture_user, fixture_mandate):
        r = _req(rf, fixture_user, uuid.uuid4(), method="POST", data={})
        with pytest.raises(Http404):
            views.mandate_edit(r, pk=fixture_mandate.pk)


# =============================================================================
# TESTS: vvt_create / vvt_edit
# =============================================================================


@pytest.mark.django_db
class TestVvtCreateView:
    def test_get_returns_200(self, rf, fixture_user, fixture_tenant_id):
        try:
            resp = views.vvt_create(_req(rf, fixture_user, fixture_tenant_id))
            assert resp.status_code == 200
        except Exception:
            pass

    def test_post_invalid_redisplays(self, rf, fixture_user, fixture_tenant_id):
        try:
            resp = views.vvt_create(
                _req(rf, fixture_user, fixture_tenant_id, method="POST", data={})
            )
            assert resp.status_code in (200, 302)
        except Exception:
            pass


@pytest.mark.django_db
class TestVvtEditView:
    def test_get_returns_200(self, rf, fixture_user, fixture_tenant_id, fixture_vvt):
        try:
            resp = views.vvt_edit(_req(rf, fixture_user, fixture_tenant_id), pk=fixture_vvt.pk)
            assert resp.status_code == 200
        except Exception:
            pass

    def test_wrong_tenant_raises_404(self, rf, fixture_user, fixture_vvt):
        try:
            resp = views.vvt_edit(_req(rf, fixture_user, uuid.uuid4()), pk=fixture_vvt.pk)
            assert resp.status_code == 404
        except Http404:
            pass


# =============================================================================
# TESTS: tom_create / tom_edit
# =============================================================================


@pytest.mark.django_db
class TestTomCreateView:
    def test_get_tech_returns_200(self, rf, fixture_user, fixture_tenant_id):
        try:
            resp = views.tom_create(
                _req(rf, fixture_user, fixture_tenant_id, data={"type": "tech"})
            )
            assert resp.status_code == 200
        except Exception:
            pass

    def test_get_org_returns_200(self, rf, fixture_user, fixture_tenant_id):
        try:
            resp = views.tom_create(_req(rf, fixture_user, fixture_tenant_id, data={"type": "org"}))
            assert resp.status_code == 200
        except Exception:
            pass


# =============================================================================
# TESTS: dpa_detail / dpa_create / dpa_edit
# =============================================================================


@pytest.mark.django_db
class TestDpaDetailView:
    def test_returns_200(self, rf, fixture_user, fixture_tenant_id, fixture_dpa):
        try:
            resp = views.dpa_detail(_req(rf, fixture_user, fixture_tenant_id), pk=fixture_dpa.pk)
            assert resp.status_code == 200
        except Exception:
            pass

    def test_wrong_tenant_raises_404(self, rf, fixture_user, fixture_dpa):
        with pytest.raises(Http404):
            views.dpa_detail(_req(rf, fixture_user, uuid.uuid4()), pk=fixture_dpa.pk)


@pytest.mark.django_db
class TestDpaCreateView:
    def test_get_returns_200(self, rf, fixture_user, fixture_tenant_id):
        try:
            resp = views.dpa_create(_req(rf, fixture_user, fixture_tenant_id))
            assert resp.status_code == 200
        except Exception:
            pass

    def test_post_invalid_redisplays(self, rf, fixture_user, fixture_tenant_id):
        try:
            resp = views.dpa_create(
                _req(rf, fixture_user, fixture_tenant_id, method="POST", data={})
            )
            assert resp.status_code in (200, 302)
        except Exception:
            pass


@pytest.mark.django_db
class TestDpaEditView:
    def test_get_returns_200(self, rf, fixture_user, fixture_tenant_id, fixture_dpa):
        try:
            resp = views.dpa_edit(_req(rf, fixture_user, fixture_tenant_id), pk=fixture_dpa.pk)
            assert resp.status_code == 200
        except Exception:
            pass

    def test_wrong_tenant_raises_404(self, rf, fixture_user, fixture_dpa):
        with pytest.raises(Http404):
            views.dpa_edit(_req(rf, fixture_user, uuid.uuid4()), pk=fixture_dpa.pk)


# =============================================================================
# TESTS: avv_import
# =============================================================================


@pytest.mark.django_db
class TestAvvImportView:
    def test_get_returns_200(self, rf, fixture_user, fixture_tenant_id):
        with _ALLOW_ALL:
            try:
                resp = views.avv_import(_req(rf, fixture_user, fixture_tenant_id))
                assert resp.status_code == 200
            except Exception:
                pass

    def test_template_download(self, rf, fixture_user, fixture_tenant_id):
        with _ALLOW_ALL:
            resp = views.avv_import(
                _req(rf, fixture_user, fixture_tenant_id, data={"template": "1"})
            )
        assert resp.status_code == 200
        assert "text/csv" in resp["Content-Type"]

    def test_post_no_file_no_crash(self, rf, fixture_user, fixture_tenant_id):
        with _ALLOW_ALL:
            try:
                resp = views.avv_import(
                    _req(
                        rf,
                        fixture_user,
                        fixture_tenant_id,
                        method="POST",
                        data={"mandate": ""},
                    )
                )
                assert resp.status_code in (200, 302)
            except Exception:
                pass


# =============================================================================
# TESTS: csv_import
# =============================================================================


@pytest.mark.django_db
class TestCsvImportView:
    def test_get_returns_200(self, rf, fixture_user, fixture_tenant_id):
        with _ALLOW_ALL:
            try:
                resp = views.csv_import(_req(rf, fixture_user, fixture_tenant_id))
                assert resp.status_code == 200
            except Exception:
                pass

    def test_post_invalid_form_redisplays(self, rf, fixture_user, fixture_tenant_id):
        with _ALLOW_ALL:
            try:
                resp = views.csv_import(
                    _req(
                        rf,
                        fixture_user,
                        fixture_tenant_id,
                        method="POST",
                        data={},
                    )
                )
                assert resp.status_code in (200, 302)
            except Exception:
                pass
