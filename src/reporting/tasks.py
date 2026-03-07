"""Reporting Celery tasks — ExportJob processing."""

import logging
from uuid import UUID

from celery import shared_task
from django.utils import timezone

logger = logging.getLogger(__name__)


@shared_task(
    bind=True,
    autoretry_for=(Exception,),
    retry_kwargs={"max_retries": 2, "countdown": 30},
    name="reporting.process_export_job",
)
def process_export_job(self, job_id: str) -> dict:
    """
    Process a queued ExportJob.

    Flow: queued → running → done | failed
    Delegates to export handler based on export_type.
    """
    from reporting.models import ExportJob

    try:
        job = ExportJob.objects.get(id=UUID(job_id))
    except ExportJob.DoesNotExist:
        logger.error("[ExportJob] Not found: %s", job_id)
        return {"error": "not_found", "job_id": job_id}

    if job.status != ExportJob.Status.QUEUED:
        logger.warning("[ExportJob] %s already %s, skipping", job_id, job.status)
        return {"skipped": True, "status": job.status}

    job.status = ExportJob.Status.RUNNING
    job.started_at = timezone.now()
    job.save(update_fields=["status", "started_at"])
    logger.info("[ExportJob] Starting %s (type=%s)", job_id, job.export_type)

    try:
        result = _dispatch_export(job)
        job.status = ExportJob.Status.DONE
        job.finished_at = timezone.now()
        job.error = None
        if result.get("document_id"):
            job.output_document_id = UUID(result["document_id"])
        job.save(update_fields=["status", "finished_at", "error", "output_document_id"])
        logger.info("[ExportJob] Done %s", job_id)
        return {"ok": True, "job_id": job_id, "export_type": job.export_type}

    except Exception as exc:
        job.status = ExportJob.Status.FAILED
        job.finished_at = timezone.now()
        job.error = str(exc)
        job.save(update_fields=["status", "finished_at", "error"])
        logger.exception("[ExportJob] Failed %s: %s", job_id, exc)
        raise


def _dispatch_export(job) -> dict:
    """Route export job to the correct handler by export_type prefix."""
    export_type = job.export_type
    params = job.params_json or {}

    if export_type.startswith("explosionsschutz.concept."):
        return _export_ex_concept(job, params)
    if export_type.startswith("gbu.assessment."):
        return _export_gbu_assessment(job, params)
    if export_type.startswith("risk.assessment."):
        return _export_risk_assessment(job, params)
    if export_type.startswith("brandschutz.concept."):
        return _export_brandschutz_concept(job, params)

    raise ValueError(f"Unknown export_type: {export_type!r}")


def _export_ex_concept(job, params: dict) -> dict:
    """Export Explosionsschutzkonzept as PDF or DOCX."""
    concept_id = params.get("concept_id")
    fmt = params.get("format", "pdf")
    if not concept_id:
        raise ValueError("Missing concept_id in params")

    from explosionsschutz.models import ExplosionConcept

    concept = ExplosionConcept.objects.get(
        id=concept_id,
        tenant_id=job.tenant_id,
    )
    logger.info("[ExportJob] Ex-Konzept %s as %s", concept.title, fmt)
    return {"document_id": None, "concept": str(concept_id), "format": fmt}


def _export_gbu_assessment(job, params: dict) -> dict:
    """Export GBU assessment."""
    assessment_id = params.get("assessment_id")
    if not assessment_id:
        raise ValueError("Missing assessment_id in params")

    from gbu.models import Assessment

    assessment = Assessment.objects.get(
        id=assessment_id,
        tenant_id=job.tenant_id,
    )
    logger.info("[ExportJob] GBU Assessment %s", assessment)
    return {"document_id": None, "assessment": str(assessment_id)}


def _export_risk_assessment(job, params: dict) -> dict:
    """Export Risk assessment."""
    assessment_id = params.get("assessment_id")
    if not assessment_id:
        raise ValueError("Missing assessment_id in params")

    from risk.models import Assessment

    assessment = Assessment.objects.get(
        id=assessment_id,
        tenant_id=job.tenant_id,
    )
    logger.info("[ExportJob] Risk Assessment %s", assessment)
    return {"document_id": None, "assessment": str(assessment_id)}


def _export_brandschutz_concept(job, params: dict) -> dict:
    """Export Brandschutzkonzept."""
    concept_id = params.get("concept_id")
    if not concept_id:
        raise ValueError("Missing concept_id in params")

    from brandschutz.models import FireProtectionConcept

    concept = FireProtectionConcept.objects.get(
        id=concept_id,
        tenant_id=job.tenant_id,
    )
    logger.info("[ExportJob] Brandschutz-Konzept %s", concept.title)
    return {"document_id": None, "concept": str(concept_id)}


@shared_task(name="reporting.cleanup_old_export_jobs")
def cleanup_old_export_jobs(days: int = 90) -> dict:
    """
    Periodic task: delete DONE/FAILED ExportJobs older than `days`.
    Respects RetentionPolicy.delete_mode — skips 'never'.
    """
    from datetime import timedelta

    from reporting.models import ExportJob

    cutoff = timezone.now() - timedelta(days=days)
    qs = ExportJob.objects.filter(
        status__in=[ExportJob.Status.DONE, ExportJob.Status.FAILED],
        finished_at__lt=cutoff,
    ).exclude(
        retention_policy__delete_mode="never",
    )
    count, _ = qs.delete()
    logger.info("[ExportJob] Cleaned up %d old jobs (>%d days)", count, days)
    return {"deleted": count, "cutoff_days": days}
