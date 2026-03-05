# src/dsb/tests/test_breach_workflow.py
"""
Unit-Tests für dsb/breach_workflow.py.
Kein HTTP — reine Business-Logic.
"""

import uuid
from datetime import date
from unittest.mock import patch

import pytest
from django.utils import timezone

from dsb.breach_workflow import advance_breach_workflow, send_initial_breach_confirmation
from dsb.models import Breach, Mandate
from dsb.models.breach import BreachStatus


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
def fixture_breach(db, fixture_tenant_id, fixture_mandate):
    return Breach.objects.create(
        tenant_id=fixture_tenant_id,
        mandate=fixture_mandate,
        discovered_at=timezone.now(),
        severity="high",
        workflow_status=BreachStatus.REPORTED,
        reported_by_email="reporter@example.com",
        reported_by_name="Max Muster",
    )


# =============================================================================
# TESTS: advance_breach_workflow
# =============================================================================


@pytest.mark.django_db
class TestAdvanceBreachWorkflow:
    def test_status_transition(self, fixture_breach):
        advance_breach_workflow(fixture_breach, BreachStatus.DSB_NOTIFIED, send_mail=False)
        fixture_breach.refresh_from_db()
        assert fixture_breach.workflow_status == BreachStatus.DSB_NOTIFIED

    def test_sets_timestamp(self, fixture_breach):
        advance_breach_workflow(fixture_breach, BreachStatus.DSB_NOTIFIED, send_mail=False)
        fixture_breach.refresh_from_db()
        assert fixture_breach.dsb_notified_at is not None

    def test_sets_dsb_notes(self, fixture_breach):
        advance_breach_workflow(
            fixture_breach, BreachStatus.DSB_NOTIFIED, notes="Notiz DSB", send_mail=False
        )
        fixture_breach.refresh_from_db()
        assert fixture_breach.dsb_notes == "Notiz DSB"

    def test_sets_authority_notes(self, fixture_breach):
        fixture_breach.workflow_status = BreachStatus.DSB_NOTIFIED
        fixture_breach.save()
        advance_breach_workflow(
            fixture_breach,
            BreachStatus.AUTHORITY_NOTIFIED,
            notes="Behörde informiert",
            send_mail=False,
        )
        fixture_breach.refresh_from_db()
        assert fixture_breach.authority_notes == "Behörde informiert"

    def test_sets_remediation_notes(self, fixture_breach):
        fixture_breach.workflow_status = BreachStatus.AUTHORITY_NOTIFIED
        fixture_breach.save()
        advance_breach_workflow(
            fixture_breach,
            BreachStatus.REMEDIATION,
            notes="Behebung läuft",
            send_mail=False,
        )
        fixture_breach.refresh_from_db()
        assert fixture_breach.remediation_notes == "Behebung läuft"

    def test_sets_resolution_notes(self, fixture_breach):
        fixture_breach.workflow_status = BreachStatus.REMEDIATION
        fixture_breach.save()
        advance_breach_workflow(
            fixture_breach,
            BreachStatus.RESOLVED,
            notes="Behoben",
            send_mail=False,
        )
        fixture_breach.refresh_from_db()
        assert fixture_breach.resolution_notes == "Behoben"

    def test_authority_notified_sets_reported_to_authority_at(self, fixture_breach):
        advance_breach_workflow(fixture_breach, BreachStatus.AUTHORITY_NOTIFIED, send_mail=False)
        fixture_breach.refresh_from_db()
        assert fixture_breach.reported_to_authority_at is not None

    def test_sets_authority_name(self, fixture_breach):
        advance_breach_workflow(
            fixture_breach,
            BreachStatus.AUTHORITY_NOTIFIED,
            authority_name="LfDI BW",
            send_mail=False,
        )
        fixture_breach.refresh_from_db()
        assert fixture_breach.authority_name == "LfDI BW"

    def test_sets_authority_reference(self, fixture_breach):
        advance_breach_workflow(
            fixture_breach,
            BreachStatus.AUTHORITY_NOTIFIED,
            authority_reference="AZ-2025-001",
            send_mail=False,
        )
        fixture_breach.refresh_from_db()
        assert fixture_breach.authority_reference == "AZ-2025-001"

    def test_send_mail_true_calls_send(self, fixture_breach, settings):
        """send_mail=True versucht E-Mail — Exception wird geschluckt."""
        settings.EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"
        with patch("dsb.breach_workflow._send_email") as mock_send:
            advance_breach_workflow(fixture_breach, BreachStatus.DSB_NOTIFIED, send_mail=True)
        mock_send.assert_called_once()

    def test_send_mail_no_email_skips(self, db, fixture_tenant_id, fixture_mandate):
        """Kein reported_by_email → kein Mail-Versuch."""
        breach = Breach.objects.create(
            tenant_id=fixture_tenant_id,
            mandate=fixture_mandate,
            discovered_at=timezone.now(),
            severity="low",
            workflow_status=BreachStatus.REPORTED,
            reported_by_email="",
        )
        with patch("dsb.breach_workflow._send_email") as mock_send:
            advance_breach_workflow(breach, BreachStatus.DSB_NOTIFIED, send_mail=True)
        mock_send.assert_not_called()


# =============================================================================
# TESTS: send_initial_breach_confirmation
# =============================================================================


@pytest.mark.django_db
class TestSendInitialBreachConfirmation:
    def test_sends_email(self, fixture_breach):
        with patch("dsb.breach_workflow._send_email") as mock_send:
            send_initial_breach_confirmation(fixture_breach)
        mock_send.assert_called_once()

    def test_skips_if_no_email(self, db, fixture_tenant_id, fixture_mandate):
        breach = Breach.objects.create(
            tenant_id=fixture_tenant_id,
            mandate=fixture_mandate,
            discovered_at=timezone.now(),
            severity="low",
            reported_by_email="",
        )
        with patch("dsb.breach_workflow._send_email") as mock_send:
            send_initial_breach_confirmation(breach)
        mock_send.assert_not_called()
