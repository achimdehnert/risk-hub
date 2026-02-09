"""Tests for approval workflow models."""

import uuid

import pytest

from approvals.models import (
    ApprovalDecision,
    ApprovalRequest,
    ApprovalStep,
    ApprovalWorkflow,
)


TENANT_ID = uuid.uuid4()


@pytest.mark.django_db
class TestApprovalWorkflow:
    """Test ApprovalWorkflow model."""

    def test_should_create_workflow(self):
        wf = ApprovalWorkflow.objects.create(
            tenant_id=TENANT_ID,
            workflow_type=ApprovalWorkflow.WorkflowType.EX_CONCEPT,
            name="Ex-Konzept Freigabe",
        )
        assert wf.pk is not None
        assert wf.is_active is True

    def test_should_display_type(self):
        wf = ApprovalWorkflow.objects.create(
            tenant_id=TENANT_ID,
            workflow_type=ApprovalWorkflow.WorkflowType.EX_CONCEPT,
            name="Test",
        )
        assert "Ex-Schutz-Konzept" in str(wf)


@pytest.mark.django_db
class TestApprovalStep:
    """Test ApprovalStep model."""

    @pytest.fixture()
    def fixture_workflow(self):
        return ApprovalWorkflow.objects.create(
            tenant_id=TENANT_ID,
            workflow_type=ApprovalWorkflow.WorkflowType.EX_CONCEPT,
            name="Test WF",
        )

    def test_should_create_step(self, fixture_workflow):
        step = ApprovalStep.objects.create(
            workflow=fixture_workflow,
            order=1,
            name="Fachliche Prüfung",
        )
        assert step.pk is not None
        assert step.require_comment is False

    def test_should_enforce_unique_order(self, fixture_workflow):
        ApprovalStep.objects.create(
            workflow=fixture_workflow, order=1, name="Step 1",
        )
        from django.db import IntegrityError
        with pytest.raises(IntegrityError):
            ApprovalStep.objects.create(
                workflow=fixture_workflow, order=1, name="Dup",
            )

    def test_should_order_by_step_number(self, fixture_workflow):
        ApprovalStep.objects.create(
            workflow=fixture_workflow, order=2, name="B",
        )
        ApprovalStep.objects.create(
            workflow=fixture_workflow, order=1, name="A",
        )
        steps = list(fixture_workflow.steps.all())
        assert steps[0].name == "A"
        assert steps[1].name == "B"


@pytest.mark.django_db
class TestApprovalRequest:
    """Test ApprovalRequest model."""

    @pytest.fixture()
    def fixture_workflow(self):
        return ApprovalWorkflow.objects.create(
            tenant_id=TENANT_ID,
            workflow_type=ApprovalWorkflow.WorkflowType.RISK_ASSESSMENT,
            name="RA Freigabe",
        )

    def test_should_create_request(self, fixture_workflow):
        req = ApprovalRequest.objects.create(
            tenant_id=TENANT_ID,
            workflow=fixture_workflow,
            entity_type="risk.RiskAssessment",
            entity_id=uuid.uuid4(),
        )
        assert req.status == ApprovalRequest.Status.PENDING
        assert req.current_step == 1

    def test_should_display_status(self, fixture_workflow):
        req = ApprovalRequest.objects.create(
            tenant_id=TENANT_ID,
            workflow=fixture_workflow,
            entity_type="test.Entity",
            entity_id=uuid.uuid4(),
        )
        assert "Ausstehend" in str(req)


@pytest.mark.django_db
class TestApprovalDecision:
    """Test ApprovalDecision model."""

    @pytest.fixture()
    def fixture_request_with_step(self):
        wf = ApprovalWorkflow.objects.create(
            tenant_id=TENANT_ID,
            workflow_type=ApprovalWorkflow.WorkflowType.EX_CONCEPT,
            name="WF",
        )
        step = ApprovalStep.objects.create(
            workflow=wf, order=1, name="Step 1",
        )
        req = ApprovalRequest.objects.create(
            tenant_id=TENANT_ID,
            workflow=wf,
            entity_type="test.Entity",
            entity_id=uuid.uuid4(),
        )
        return req, step

    def test_should_create_decision(self, fixture_request_with_step):
        req, step = fixture_request_with_step
        dec = ApprovalDecision.objects.create(
            request=req,
            step=step,
            outcome=ApprovalDecision.Outcome.APPROVED,
            comment="Sieht gut aus",
        )
        assert dec.pk is not None
        assert dec.outcome == "approved"

    def test_should_record_rejection(self, fixture_request_with_step):
        req, step = fixture_request_with_step
        dec = ApprovalDecision.objects.create(
            request=req,
            step=step,
            outcome=ApprovalDecision.Outcome.REJECTED,
            comment="Nachbesserung nötig",
        )
        assert dec.outcome == "rejected"
