"""GBU services package — re-exports + query helpers (ADR-041)."""

from __future__ import annotations


def get_hazard_assessment_activities(tenant_id):
    """Return HazardAssessmentActivities for a tenant."""
    from gbu.models.activity import HazardAssessmentActivity

    return HazardAssessmentActivity.objects.filter(tenant_id=tenant_id)


def get_activities_with_relations(tenant_id):
    """Return HazardAssessmentActivities with site/sds_revision related data."""
    from gbu.models.activity import HazardAssessmentActivity

    return (
        HazardAssessmentActivity.objects.filter(tenant_id=tenant_id)
        .select_related("site", "sds_revision")
        .prefetch_related("measures")
    )


def get_sds_revisions(tenant_id):
    """Return SdsRevisions for a tenant."""
    from substances.models import SdsRevision

    return SdsRevision.objects.filter(tenant_id=tenant_id)


def get_sites(tenant_id):
    """Return Sites for a tenant ordered by name."""
    from tenancy.models import Site

    return Site.objects.filter(tenant_id=tenant_id).order_by("name")


def get_measure_templates(category_ids):
    """Return MeasureTemplates for the given category IDs."""
    from gbu.models.reference import MeasureTemplate

    return MeasureTemplate.objects.filter(category_id__in=category_ids).order_by(
        "tops_type", "sort_order"
    )
