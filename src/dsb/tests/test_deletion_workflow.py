# src/dsb/tests/test_deletion_workflow.py
"""
Unit-Tests für dsb/deletion_workflow.py.
Kein HTTP — reine Business-Logic.
"""

import uuid
from datetime import date
from unittest.mock import patch

import pytest

from dsb.deletion_workflow import advance_workflow, send_initial_confirmation
from dsb.models import Mandate
from dsb.models.deletion_request import DeletionRequest, DeletionRequestStatus


# =============================================================================
# FIXTURES
# =============================================================================


@pytest.fixture
def fixture_tenant_id():
    return uuid.uuid4()


@pytest.fixture
def fixture_mandate(db, fixture_tenant_id):
    return Mandate.objects.create(
        tenant_id=fixture_tenant_id,
        name="Test GmbH",
        dsb_appointed_date=date.today(),
        status="active",
    )


@pytest.fixture
def fixture_req(db, fixture_tenant_id, fixture_mandate):
    return DeletionRequest.objects.create(
        tenant_id=fixture_tenant_id,
        mandate=fixture_mandate,
        subject_name="Max Mustermann",
        subject_email="max@example.com",
        request_date=date.today(),
        request_description="Alle Daten löschen.",
        status=DeletionRequestStatus.PENDING,
    )


# =============================================================================
# TESTS: advance_workflow
# =============================================================================


@pytest.mark.django_db
class TestAdvanceWorkflow:
    def test_status_transition(self, fixture_req):
        advance_workflow(fixture_req, DeletionRequestStatus.AUTH_SENT, send_mail=False)
        fixture_req.refresh_from_db()
        assert fixture_req.status == DeletionRequestStatus.AUTH_SENT

    def test_sets_auth_sent_timestamp(self, fixture_req):
        advance_workflow(fixture_req, DeletionRequestStatus.AUTH_SENT, send_mail=False)
        fixture_req.refresh_from_db()
        assert fixture_req.auth_sent_at is not None

    def test_sets_auth_notes(self, fixture_req):
        advance_workflow(
            fixture_req,
            DeletionRequestStatus.AUTH_SENT,
            notes="Bitte Ausweis senden",
            send_mail=False,
        )
        fixture_req.refresh_from_db()
        assert fixture_req.auth_notes == "Bitte Ausweis senden"

    def test_sets_deletion_notes(self, fixture_req):
        fixture_req.status = DeletionRequestStatus.AUTH_RECEIVED
        fixture_req.save()
        advance_workflow(
            fixture_req,
            DeletionRequestStatus.DELETION_ORDERED,
            notes="Löschung beauftragt",
            send_mail=False,
        )
        fixture_req.refresh_from_db()
        assert fixture_req.deletion_notes == "Löschung beauftragt"

    def test_sets_rejection_reason(self, fixture_req):
        advance_workflow(
            fixture_req,
            DeletionRequestStatus.REJECTED,
            notes="Nicht identifizierbar",
            send_mail=False,
        )
        fixture_req.refresh_from_db()
        assert fixture_req.rejection_reason == "Nicht identifizierbar"

    def test_closed_sets_closed_at(self, fixture_req):
        fixture_req.status = DeletionRequestStatus.NOTIFIED
        fixture_req.save()
        advance_workflow(fixture_req, DeletionRequestStatus.CLOSED, send_mail=False)
        fixture_req.refresh_from_db()
        assert fixture_req.closed_at is not None

    def test_send_mail_true_calls_send(self, fixture_req):
        with patch("dsb.deletion_workflow._send_email") as mock_send:
            advance_workflow(fixture_req, DeletionRequestStatus.AUTH_SENT, send_mail=True)
        mock_send.assert_called_once()

    def test_send_mail_skipped_for_status_without_template(self, fixture_req):
        """REJECTED hat kein Email-Template → kein Mail."""
        with patch("dsb.deletion_workflow._send_email") as mock_send:
            advance_workflow(
                fixture_req, DeletionRequestStatus.REJECTED, send_mail=True
            )
        mock_send.assert_not_called()

    def test_deletion_confirmed_timestamp(self, fixture_req):
        fixture_req.status = DeletionRequestStatus.DELETION_ORDERED
        fixture_req.save()
        advance_workflow(
            fixture_req, DeletionRequestStatus.DELETION_CONFIRMED, send_mail=False
        )
        fixture_req.refresh_from_db()
        assert fixture_req.deletion_confirmed_at is not None


# =============================================================================
# TESTS: send_initial_confirmation
# =============================================================================


@pytest.mark.django_db
class TestSendInitialConfirmation:
    def test_sends_email(self, fixture_req):
        with patch("dsb.deletion_workflow._send_email") as mock_send:
            send_initial_confirmation(fixture_req)
        mock_send.assert_called_once()

    def test_send_call_contains_subject_email(self, fixture_req):
        with patch("dsb.deletion_workflow._send_email") as mock_send:
            send_initial_confirmation(fixture_req)
        call_args = mock_send.call_args
        assert call_args[0][0] == "max@example.com"
