"""Tests for reporting models."""

import uuid

import pytest

from reporting.models import ExportJob, RetentionPolicy

TENANT_ID = uuid.uuid4()


@pytest.mark.django_db
class TestRetentionPolicy:
    def test_should_create_policy(self):
        policy = RetentionPolicy.objects.create(
            name="DSGVO Standard",
            category="documents",
            retention_days=730,
        )
        assert policy.pk is not None
        assert policy.delete_mode == RetentionPolicy.DeleteMode.SOFT
        assert policy.legal_hold_allowed is True

    def test_should_display_days(self):
        policy = RetentionPolicy.objects.create(
            name="Kurz",
            category="temp",
            retention_days=30,
        )
        assert "30" in str(policy)

    def test_should_support_hard_delete_mode(self):
        policy = RetentionPolicy.objects.create(
            name="Hard Delete",
            category="logs",
            retention_days=90,
            delete_mode=RetentionPolicy.DeleteMode.HARD,
        )
        assert policy.delete_mode == "hard"

    def test_should_support_never_delete(self):
        policy = RetentionPolicy.objects.create(
            name="Legal Hold",
            category="legal",
            retention_days=3650,
            delete_mode=RetentionPolicy.DeleteMode.NEVER,
        )
        assert policy.delete_mode == "never"


@pytest.mark.django_db
class TestExportJob:
    @pytest.fixture()
    def fixture_policy(self):
        return RetentionPolicy.objects.create(
            name="Standard",
            category="export",
            retention_days=90,
        )

    def test_should_create_queued_job(self, fixture_policy):
        job = ExportJob.objects.create(
            tenant_id=TENANT_ID,
            requested_by_user_id=uuid.uuid4(),
            export_type="pdf.risk_assessment",
            params_json={"assessment_id": str(uuid.uuid4())},
            params_hash="abc123",
            retention_policy=fixture_policy,
        )
        assert job.pk is not None
        assert job.status == ExportJob.Status.QUEUED
        assert job.started_at is None
        assert job.finished_at is None

    def test_should_display_export_type(self):
        job = ExportJob.objects.create(
            tenant_id=TENANT_ID,
            requested_by_user_id=uuid.uuid4(),
            export_type="excel.dsb_vvt",
            params_json={},
            params_hash="xyz",
        )
        assert "excel.dsb_vvt" in str(job)

    def test_should_transition_to_done(self):
        from django.utils import timezone

        job = ExportJob.objects.create(
            tenant_id=TENANT_ID,
            requested_by_user_id=uuid.uuid4(),
            export_type="pdf.test",
            params_json={},
            params_hash="h1",
        )
        now = timezone.now()
        job.status = ExportJob.Status.DONE
        job.finished_at = now
        job.save(update_fields=["status", "finished_at"])

        reloaded = ExportJob.objects.get(pk=job.pk)
        assert reloaded.status == "done"
        assert reloaded.finished_at is not None

    def test_should_record_failure(self):
        job = ExportJob.objects.create(
            tenant_id=TENANT_ID,
            requested_by_user_id=uuid.uuid4(),
            export_type="pdf.fail",
            params_json={},
            params_hash="h2",
        )
        job.status = ExportJob.Status.FAILED
        job.error = "Template not found"
        job.save(update_fields=["status", "error"])

        reloaded = ExportJob.objects.get(pk=job.pk)
        assert reloaded.status == "failed"
        assert "Template" in reloaded.error
