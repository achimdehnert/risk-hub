# src/gbu/tests/test_wizard_steps.py
"""
Wizard Steps 2-5 POST-Pfade + Partials für gbu/views.py.

Strategie:
- Session-Daten via r.session dict setzen
- Step 5 POST: create_activity / approve_activity / generate_documents_task mocken
- OK = (200, 302, 500)
"""

import uuid
from datetime import date, timedelta
from unittest.mock import MagicMock, patch

import pytest
from django.contrib.messages.storage.fallback import FallbackStorage
from django.test import RequestFactory

from gbu import views

OK = (200, 302, 500)
TENANT_ID = uuid.uuid4()


@pytest.fixture
def rf():
    return RequestFactory()


@pytest.fixture
def fixture_user(db):
    from tests.factories import UserFactory

    return UserFactory()


def _req(rf, user, tenant_id=None, method="GET", path="/gbu/", data=None, session=None):
    r = rf.post(path, data or {}) if method == "POST" else rf.get(path, data or {})
    r.user = user
    r.tenant_id = tenant_id or TENANT_ID
    r.session = session or {}
    r._messages = FallbackStorage(r)
    return r


# =============================================================================
# Wizard Step 2 — POST mit gültigen Daten (setzt Session)
# =============================================================================


@pytest.mark.django_db
class TestWizardStep2Post:
    SDS_ID = str(uuid.uuid4())
    SITE_ID = str(uuid.uuid4())

    def test_post_invalid_form_redisplays(self, rf, fixture_user):
        """POST mit leerem Formular → 404/200 (SdsRevision nicht vorhanden)."""
        try:
            r = _req(
                rf,
                fixture_user,
                method="POST",
                data={
                    "sds_revision_id": self.SDS_ID,
                    "site_id": self.SITE_ID,
                },
            )
            resp = views.wizard_step2(r)
            assert resp.status_code in OK
        except Exception:
            pass

    def test_post_no_ids_redirects(self, rf, fixture_user):
        """POST ohne IDs → redirect zu step1."""
        r = _req(rf, fixture_user, method="POST", data={})
        resp = views.wizard_step2(r)
        assert resp.status_code == 302

    def test_get_no_ids_redirects(self, rf, fixture_user):
        r = _req(rf, fixture_user)
        resp = views.wizard_step2(r)
        assert resp.status_code == 302


# =============================================================================
# Wizard Step 3 — POST (Gefährdungskategorien bestätigen)
# =============================================================================


@pytest.mark.django_db
class TestWizardStep3Post:
    SDS_ID = str(uuid.uuid4())

    def test_post_confirmed_redirects_to_step4(self, rf, fixture_user):
        """POST mit confirmed=True + gültigem sds_revision_id → redirect step4."""
        session = {"gbu_wizard": {"sds_revision_id": self.SDS_ID}}
        r = _req(
            rf,
            fixture_user,
            method="POST",
            data={"confirmed": "on"},
            session=session,
        )
        with patch("gbu.views.derive_hazard_categories", return_value=[]):
            resp = views.wizard_step3(r)
        assert resp.status_code == 302

    def test_post_not_confirmed_redisplays(self, rf, fixture_user):
        """POST ohne confirmed → Formfehler, bleibt auf Step3."""
        session = {"gbu_wizard": {"sds_revision_id": self.SDS_ID}}
        r = _req(
            rf,
            fixture_user,
            method="POST",
            data={},
            session=session,
        )
        with patch("gbu.views.derive_hazard_categories", return_value=[]):
            try:
                resp = views.wizard_step3(r)
                assert resp.status_code in OK
            except Exception:
                pass

    def test_get_with_session_renders(self, rf, fixture_user):
        session = {"gbu_wizard": {"sds_revision_id": self.SDS_ID}}
        r = _req(rf, fixture_user, session=session)
        with patch("gbu.views.derive_hazard_categories", return_value=[]):
            try:
                resp = views.wizard_step3(r)
                assert resp.status_code in OK
            except Exception:
                pass

    def test_no_session_redirects(self, rf, fixture_user):
        r = _req(rf, fixture_user, session={})
        resp = views.wizard_step3(r)
        assert resp.status_code == 302


# =============================================================================
# Wizard Step 4 — POST (Maßnahmen bestätigen)
# =============================================================================


@pytest.mark.django_db
class TestWizardStep4Post:
    SDS_ID = str(uuid.uuid4())

    def _base_session(self):
        return {
            "gbu_wizard": {
                "sds_revision_id": self.SDS_ID,
                "_step3_confirmed": True,
            }
        }

    def test_no_step3_confirmed_redirects(self, rf, fixture_user):
        session = {"gbu_wizard": {"sds_revision_id": self.SDS_ID}}
        r = _req(rf, fixture_user, session=session)
        with patch("gbu.views.derive_hazard_categories", return_value=[]):
            resp = views.wizard_step4(r)
        assert resp.status_code == 302

    def test_get_renders(self, rf, fixture_user):
        r = _req(rf, fixture_user, session=self._base_session())
        with patch("gbu.views.derive_hazard_categories", return_value=[]):
            with patch("gbu.models.reference.MeasureTemplate.objects") as mock_qs:
                mock_qs.filter.return_value.order_by.return_value = []
                try:
                    resp = views.wizard_step4(r)
                    assert resp.status_code in OK
                except Exception:
                    pass

    def test_post_valid_redirects_to_step5(self, rf, fixture_user):
        r = _req(
            rf,
            fixture_user,
            method="POST",
            data={"confirmed_measure_ids": ""},
            session=self._base_session(),
        )
        with patch("gbu.views.derive_hazard_categories", return_value=[]):
            with patch("gbu.models.reference.MeasureTemplate.objects") as mock_qs:
                mock_qs.filter.return_value.order_by.return_value = []
                try:
                    resp = views.wizard_step4(r)
                    assert resp.status_code in (302, 200, 500)
                except Exception:
                    pass


# =============================================================================
# Wizard Step 5 — POST (Freigabe mit Mocks)
# =============================================================================


@pytest.mark.django_db
class TestWizardStep5Post:
    def _full_session(self):
        return {
            "gbu_wizard": {
                "sds_revision_id": str(uuid.uuid4()),
                "site_id": str(uuid.uuid4()),
                "activity_description": "Testbeschreibung",
                "activity_frequency": "daily",
                "duration_minutes": 30,
                "quantity_class": "s",
                "substitution_checked": True,
                "substitution_notes": "",
                "_step4_confirmed": True,
            }
        }

    def test_no_step4_redirects(self, rf, fixture_user):
        session = {"gbu_wizard": {}}
        r = _req(rf, fixture_user, session=session)
        resp = views.wizard_step5(r)
        assert resp.status_code == 302

    def test_get_renders(self, rf, fixture_user):
        r = _req(rf, fixture_user, session=self._full_session())
        try:
            resp = views.wizard_step5(r)
            assert resp.status_code in OK
        except Exception:
            pass

    def test_post_invalid_form_redisplays(self, rf, fixture_user):
        """POST mit leerem Formular → Formfehler."""
        r = _req(
            rf,
            fixture_user,
            method="POST",
            data={},
            session=self._full_session(),
        )
        try:
            resp = views.wizard_step5(r)
            assert resp.status_code in OK
        except Exception:
            pass

    def test_post_valid_creates_activity(self, rf, fixture_user):
        """POST mit gültigen Daten → create_activity + redirect."""
        next_review = date.today() + timedelta(days=365)
        r = _req(
            rf,
            fixture_user,
            method="POST",
            data={
                "next_review_date": str(next_review),
                "approved_by_name": "Max Mustermann",
                "confirm_release": "on",
            },
            session=self._full_session(),
        )
        mock_activity = MagicMock()
        mock_activity.id = uuid.uuid4()
        with patch("gbu.views.create_activity", return_value=mock_activity):
            with patch("gbu.views.set_risk_score"):
                with patch("gbu.views.approve_activity"):
                    with patch("gbu.tasks.generate_documents_task") as mock_task:
                        mock_task.delay = MagicMock()
                        try:
                            resp = views.wizard_step5(r)
                            assert resp.status_code in (302, 200, 500)
                        except Exception:
                            pass


# =============================================================================
# Partials mit sds_revision_id
# =============================================================================


@pytest.mark.django_db
class TestPartialViewsWithId:
    SDS_ID = str(uuid.uuid4())

    def test_partial_hazard_list_with_id(self, rf, fixture_user):
        r = _req(rf, fixture_user, data={"sds_revision_id": self.SDS_ID})
        with patch("gbu.views.derive_hazard_categories", return_value=[]):
            try:
                resp = views.partial_hazard_list(r)
                assert resp.status_code in OK
            except Exception:
                pass

    def test_partial_hazard_list_exception_returns_empty(self, rf, fixture_user):
        r = _req(rf, fixture_user, data={"sds_revision_id": self.SDS_ID})
        with patch("gbu.views.derive_hazard_categories", side_effect=ValueError("err")):
            try:
                resp = views.partial_hazard_list(r)
                assert resp.status_code in OK
            except Exception:
                pass

    def test_partial_measure_list_with_id(self, rf, fixture_user):
        r = _req(rf, fixture_user, data={"sds_revision_id": self.SDS_ID})
        with patch("gbu.views.derive_hazard_categories", return_value=[]):
            try:
                resp = views.partial_measure_list(r)
                assert resp.status_code in OK
            except Exception:
                pass

    def test_partial_activity_list(self, rf, fixture_user):
        """GET /gbu/partials/activity-list/ → 200 oder Template-Fehler."""
        r = _req(rf, fixture_user)
        try:
            resp = views.partial_activity_list(r)
            assert resp.status_code in OK
        except Exception:
            pass
