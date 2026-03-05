# src/dsb/tests/test_workflows.py
"""
Unit-Tests für DSB Workflow-Funktionen.

Tests nach ADR v5:
- advance_breach_workflow: Status-Transitionen, Timestamps, is_overdue
- advance_workflow (deletion): Status-Transitionen, Timestamps
- Breach.is_overdue Property
- DeletionRequest.is_open + next_steps Properties
"""

import uuid
from datetime import date, timedelta
from unittest.mock import patch

import pytest
from django.utils import timezone

from dsb.breach_workflow import advance_breach_workflow
from dsb.deletion_workflow import advance_workflow
from dsb.models import Breach, Mandate
from dsb.models.breach import BreachStatus
from dsb.models.deletion_request import DeletionRequest, DeletionRequestStatus


# =============================================================================
# FIXTURES
# =============================================================================


@pytest.fixture
def fixture_tenant_id():
    return uuid.uuid4()


@pytest.fixture
def fixture_mandate(fixture_tenant_id):
    return Mandate.objects.create(
        tenant_id=fixture_tenant_id,
        name="Test GmbH",
        dsb_appointed_date=date.today(),
        status="active",
    )


@pytest.fixture
def fixture_breach(fixture_tenant_id, fixture_mandate):
    return Breach.objects.create(
        tenant_id=fixture_tenant_id,
        mandate=fixture_mandate,
        discovered_at=timezone.now(),
        severity="high",
        reported_by_email="test@example.com",
        reported_by_name="Max Mustermann",
        title="Test-Datenpanne",
    )


@pytest.fixture
def fixture_deletion_request(fixture_tenant_id, fixture_mandate):
    return DeletionRequest.objects.create(
        tenant_id=fixture_tenant_id,
        mandate=fixture_mandate,
        subject_name="Anna Schmidt",
        subject_email="anna@example.com",
        request_date=date.today(),
        request_description="Bitte alle Daten löschen",
    )


# =============================================================================
# TESTS: Breach.is_overdue Property
# =============================================================================


@pytest.mark.django_db
class TestBreachIsOverdue:
    def test_should_not_be_overdue_if_within_72h(self, fixture_breach):
        """Breach < 72h ist noch nicht overdue"""
        assert fixture_breach.is_overdue is False

    def test_should_be_overdue_after_72h_without_report(self, fixture_tenant_id, fixture_mandate):
        """Breach > 72h ohne Meldung ist overdue"""
        breach = Breach.objects.create(
            tenant_id=fixture_tenant_id,
            mandate=fixture_mandate,
            discovered_at=timezone.now() - timedelta(hours=80),
            severity="critical",
        )
        assert breach.is_overdue is True

    def test_should_not_be_overdue_if_reported(self, fixture_tenant_id, fixture_mandate):
        """Breach > 72h aber gemeldet ist nicht overdue"""
        breach = Breach.objects.create(
            tenant_id=fixture_tenant_id,
            mandate=fixture_mandate,
            discovered_at=timezone.now() - timedelta(hours=80),
            severity="low",
            reported_to_authority_at=timezone.now() - timedelta(hours=5),
        )
        assert breach.is_overdue is False

    def test_should_have_correct_deadline(self, fixture_breach):
        """deadline_72h ist genau 72h nach discovered_at"""
        expected = fixture_breach.discovered_at + timedelta(hours=72)
        assert abs((fixture_breach.deadline_72h - expected).total_seconds()) < 1


# =============================================================================
# TESTS: advance_breach_workflow
# =============================================================================


@pytest.mark.django_db
class TestAdvanceBreachWorkflow:
    def test_should_advance_to_dsb_notified(self, fixture_breach):
        """Workflow-Schritt REPORTED → DSB_NOTIFIED"""
        advance_breach_workflow(
            fixture_breach,
            BreachStatus.DSB_NOTIFIED,
            notes="DSB informiert",
            send_mail=False,
        )
        fixture_breach.refresh_from_db()
        assert fixture_breach.workflow_status == BreachStatus.DSB_NOTIFIED
        assert fixture_breach.dsb_notified_at is not None
        assert fixture_breach.dsb_notes == "DSB informiert"

    def test_should_set_authority_notified_timestamp(self, fixture_breach):
        """AUTHORITY_NOTIFIED setzt reported_to_authority_at"""
        advance_breach_workflow(
            fixture_breach,
            BreachStatus.AUTHORITY_NOTIFIED,
            authority_name="LfDI BW",
            send_mail=False,
        )
        fixture_breach.refresh_from_db()
        assert fixture_breach.workflow_status == BreachStatus.AUTHORITY_NOTIFIED
        assert fixture_breach.authority_notified_at is not None
        assert fixture_breach.reported_to_authority_at is not None
        assert fixture_breach.authority_name == "LfDI BW"

    def test_should_set_resolved_timestamp(self, fixture_breach):
        """RESOLVED setzt resolved_at"""
        advance_breach_workflow(
            fixture_breach,
            BreachStatus.RESOLVED,
            notes="Panne behoben",
            send_mail=False,
        )
        fixture_breach.refresh_from_db()
        assert fixture_breach.resolved_at is not None
        assert fixture_breach.resolution_notes == "Panne behoben"

    def test_should_send_email_when_enabled(self, fixture_breach):
        """E-Mail-Versand wird aufgerufen wenn send_mail=True"""
        with patch("dsb.breach_workflow._send_email") as mock_send:
            advance_breach_workflow(
                fixture_breach,
                BreachStatus.DSB_NOTIFIED,
                send_mail=True,
            )
        mock_send.assert_called_once()

    def test_should_not_send_email_without_address(self, fixture_tenant_id, fixture_mandate):
        """Kein E-Mail wenn reported_by_email leer"""
        breach = Breach.objects.create(
            tenant_id=fixture_tenant_id,
            mandate=fixture_mandate,
            discovered_at=timezone.now(),
            severity="low",
            reported_by_email="",
        )
        with patch("dsb.breach_workflow._send_email") as mock_send:
            advance_breach_workflow(breach, BreachStatus.DSB_NOTIFIED, send_mail=True)
        mock_send.assert_not_called()

    def test_should_set_authority_reference(self, fixture_breach):
        """authority_reference wird gesetzt"""
        advance_breach_workflow(
            fixture_breach,
            BreachStatus.AUTHORITY_NOTIFIED,
            authority_reference="AZ-2024-001",
            send_mail=False,
        )
        fixture_breach.refresh_from_db()
        assert fixture_breach.authority_reference == "AZ-2024-001"


# =============================================================================
# TESTS: Breach.is_open + next_steps
# =============================================================================


@pytest.mark.django_db
class TestBreachProperties:
    def test_should_be_open_when_reported(self, fixture_breach):
        assert fixture_breach.is_open is True

    def test_should_not_be_open_when_closed(self, fixture_breach):
        fixture_breach.workflow_status = BreachStatus.CLOSED
        fixture_breach.save()
        assert fixture_breach.is_open is False

    def test_should_have_next_steps_from_reported(self, fixture_breach):
        assert BreachStatus.DSB_NOTIFIED in fixture_breach.next_steps

    def test_should_have_no_next_steps_when_closed(self, fixture_breach):
        fixture_breach.workflow_status = BreachStatus.CLOSED
        assert fixture_breach.next_steps == []


# =============================================================================
# TESTS: DeletionRequest advance_workflow
# =============================================================================


@pytest.mark.django_db
class TestAdvanceDeletionWorkflow:
    def test_should_advance_to_auth_sent(self, fixture_deletion_request):
        """PENDING → AUTH_SENT"""
        advance_workflow(
            fixture_deletion_request,
            DeletionRequestStatus.AUTH_SENT,
            send_mail=False,
        )
        fixture_deletion_request.refresh_from_db()
        assert fixture_deletion_request.status == DeletionRequestStatus.AUTH_SENT
        assert fixture_deletion_request.auth_sent_at is not None

    def test_should_advance_to_deletion_ordered(self, fixture_deletion_request):
        """→ DELETION_ORDERED mit Notes"""
        advance_workflow(
            fixture_deletion_request,
            DeletionRequestStatus.DELETION_ORDERED,
            notes="Löschung beauftragt",
            send_mail=False,
        )
        fixture_deletion_request.refresh_from_db()
        assert fixture_deletion_request.deletion_notes == "Löschung beauftragt"
        assert fixture_deletion_request.deletion_ordered_at is not None

    def test_should_advance_to_closed(self, fixture_deletion_request):
        """→ CLOSED setzt closed_at"""
        advance_workflow(
            fixture_deletion_request,
            DeletionRequestStatus.CLOSED,
            send_mail=False,
        )
        fixture_deletion_request.refresh_from_db()
        assert fixture_deletion_request.status == DeletionRequestStatus.CLOSED
        assert fixture_deletion_request.closed_at is not None

    def test_should_advance_to_rejected_with_reason(self, fixture_deletion_request):
        """→ REJECTED setzt rejection_reason"""
        advance_workflow(
            fixture_deletion_request,
            DeletionRequestStatus.REJECTED,
            notes="Keine Berechtigung",
            send_mail=False,
        )
        fixture_deletion_request.refresh_from_db()
        assert fixture_deletion_request.status == DeletionRequestStatus.REJECTED
        assert fixture_deletion_request.rejection_reason == "Keine Berechtigung"

    def test_should_send_email_on_advance(self, fixture_deletion_request):
        """E-Mail-Versand bei gültigem Status"""
        with patch("dsb.deletion_workflow._send_email") as mock_send:
            advance_workflow(
                fixture_deletion_request,
                DeletionRequestStatus.AUTH_SENT,
                send_mail=True,
            )
        mock_send.assert_called_once()


# =============================================================================
# TESTS: DeletionRequest Properties
# =============================================================================


@pytest.mark.django_db
class TestDeletionRequestProperties:
    def test_should_be_open_when_pending(self, fixture_deletion_request):
        assert fixture_deletion_request.is_open is True

    def test_should_not_be_open_when_closed(self, fixture_deletion_request):
        fixture_deletion_request.status = DeletionRequestStatus.CLOSED
        fixture_deletion_request.save()
        assert fixture_deletion_request.is_open is False

    def test_should_not_be_open_when_rejected(self, fixture_deletion_request):
        fixture_deletion_request.status = DeletionRequestStatus.REJECTED
        fixture_deletion_request.save()
        assert fixture_deletion_request.is_open is False

    def test_should_have_next_steps_from_pending(self, fixture_deletion_request):
        steps = fixture_deletion_request.next_steps
        assert DeletionRequestStatus.AUTH_SENT in steps

    def test_should_have_step_number(self, fixture_deletion_request):
        assert fixture_deletion_request.step_number == "1"

    def test_should_str_contain_subject_name(self, fixture_deletion_request):
        assert "Anna Schmidt" in str(fixture_deletion_request)
