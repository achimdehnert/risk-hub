# src/global_sds/services/__init__.py
"""Global SDS Services (ADR-012 §14)."""

from global_sds.services.diff_service import SdsRevisionDiffService
from global_sds.services.dtos import ParsedSdsData
from global_sds.services.enrichment_service import SdsEnrichmentService
from global_sds.services.identity_resolver import SdsIdentityResolver
from global_sds.services.supersession_service import SdsSupersessionService
from global_sds.services.upload_pipeline import SdsUploadPipeline
from global_sds.services.usage_service import SdsUsageService
from global_sds.services.version_detector import SdsVersionDetector

__all__ = [
    "ParsedSdsData",
    "SdsEnrichmentService",
    "SdsIdentityResolver",
    "SdsVersionDetector",
    "SdsRevisionDiffService",
    "SdsSupersessionService",
    "SdsUploadPipeline",
    "SdsUsageService",
]


# ---------------------------------------------------------------------------
# Query helpers (ADR-041)
# ---------------------------------------------------------------------------


def get_sds_usages(tenant_id):
    """Return SdsUsage queryset for a tenant."""
    from global_sds.sds_usage import SdsUsage

    return SdsUsage.objects.filter(tenant_id=tenant_id)


def get_visible_revisions(tenant_id):
    """Return GlobalSdsRevisions visible for a tenant (custom manager)."""
    from global_sds.models import GlobalSdsRevision

    return GlobalSdsRevision.objects.visible_for_tenant(tenant_id)


def get_tenant_revisions(tenant_id):
    """Return GlobalSdsRevisions uploaded by a tenant (for delete gate)."""
    from global_sds.models import GlobalSdsRevision

    return GlobalSdsRevision.objects.filter(uploaded_by_tenant_id=str(tenant_id))


def get_sds_usage_for_revision(tenant_id, revision):
    """Return SdsUsage for a specific revision, or None."""
    from global_sds.sds_usage import SdsUsage

    return SdsUsage.objects.filter(tenant_id=tenant_id, sds_revision=revision).first()


def get_diff_record(old_revision, new_revision):
    """Return SdsRevisionDiffRecord for old/new revision pair, or None."""
    from global_sds.models import SdsRevisionDiffRecord

    return SdsRevisionDiffRecord.objects.filter(
        old_revision=old_revision,
        new_revision=new_revision,
    ).first()


def get_substance_revisions(substance):
    """Return all GlobalSdsRevisions for a substance, newest first.

    Used for revision history panels (GefStoffV §14 Archivierungspflicht).
    """
    from global_sds.models import GlobalSdsRevision

    return (
        GlobalSdsRevision.objects.filter(substance=substance)
        .order_by("-created_at")
        .select_related("substance")
    )
