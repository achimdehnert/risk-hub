"""Unit-Tests für GBU-Models (Phase 2A)."""

import pytest

from gbu.models.activity import (
    ActivityFrequency,
    ActivityMeasure,
    ActivityStatus,
    HazardAssessmentActivity,
    QuantityClass,
    RiskScore,
)
from gbu.models.reference import (
    HazardCategoryRef,
    HazardCategoryType,
    HCodeCategoryMapping,
    MeasureTemplate,
    TOPSType,
)

# ── StrEnum-Tests ──────────────────────────────────────────────────────────────


def test_should_hazard_category_type_be_str_compatible():
    assert HazardCategoryType.FIRE_EXPLOSION == "fire_explosion"
    assert isinstance(HazardCategoryType.CMR, str)


def test_should_tops_type_be_str_compatible():
    assert TOPSType.SUBSTITUTION == "S"
    assert TOPSType.PERSONAL == "P"


def test_should_activity_status_be_str_compatible():
    assert ActivityStatus.DRAFT == "draft"
    assert ActivityStatus.APPROVED == "approved"


def test_should_risk_score_cover_all_emkg_classes():
    assert RiskScore.LOW == "low"
    assert RiskScore.CRITICAL == "critical"


def test_should_quantity_class_be_str_compatible():
    assert QuantityClass.XS == "xs"
    assert QuantityClass.L == "l"


def test_should_activity_frequency_be_str_compatible():
    assert ActivityFrequency.DAILY == "daily"
    assert ActivityFrequency.RARE == "rare"


# ── Model-Meta-Tests ──────────────────────────────────────────────────────────


def test_should_activity_have_no_delete_permission():
    perms = HazardAssessmentActivity._meta.default_permissions
    assert "delete" not in perms
    assert "add" in perms
    assert "view" in perms
    assert "change" in perms


def test_should_models_have_correct_db_tables():
    assert HazardCategoryRef._meta.db_table == "gbu_hazard_category_ref"
    assert HCodeCategoryMapping._meta.db_table == "gbu_h_code_category_mapping"
    assert HazardAssessmentActivity._meta.db_table == "gbu_hazard_assessment_activity"
    assert ActivityMeasure._meta.db_table == "gbu_activity_measure"


def test_should_activity_measure_have_tenant_id_field():
    """K4: ActivityMeasure muss tenant_id haben (RLS-Schutz ohne JOIN)."""
    field_names = [f.name for f in ActivityMeasure._meta.get_fields()]
    assert "tenant_id" in field_names


def test_should_activity_not_have_approved_by_fk():
    """H4: approved_by ist UUID-Snapshot, kein FK (verhindert Compliance-Datenverlust)."""
    field_names = [f.name for f in HazardAssessmentActivity._meta.get_fields()]
    assert "approved_by_id" in field_names
    assert "approved_by_name" in field_names
    fk_to_user = [
        f
        for f in HazardAssessmentActivity._meta.get_fields()
        if hasattr(f, "related_model")
        and f.related_model is not None
        and "user" in str(f.related_model).lower()
        and getattr(f, "column", None) == "approved_by_id"
    ]
    assert len(fk_to_user) == 0


# ── DB-Tests ──────────────────────────────────────────────────────────────────


@pytest.mark.django_db
def test_should_create_hazard_category_ref():
    cat = HazardCategoryRef.objects.create(
        code="TEST-FIRE",
        name="Test Brand",
        category_type=HazardCategoryType.FIRE_EXPLOSION,
        trgs_reference="TRGS 400 Test",
    )
    assert cat.pk is not None
    assert str(cat) == "TEST-FIRE — Test Brand"


@pytest.mark.django_db
def test_should_create_h_code_mapping():
    cat = HazardCategoryRef.objects.create(
        code="TEST-CMR",
        name="CMR Test",
        category_type=HazardCategoryType.CMR,
    )
    m = HCodeCategoryMapping.objects.create(
        h_code="H350", category=cat, annotation="Karzinogen Kat 1"
    )
    assert str(m) == "H350 → TEST-CMR"


@pytest.mark.django_db
def test_should_enforce_unique_h_code_per_category():
    from django.db import IntegrityError

    cat = HazardCategoryRef.objects.create(
        code="TEST-U",
        name="Unique Test",
        category_type=HazardCategoryType.ACUTE_TOXIC,
    )
    HCodeCategoryMapping.objects.create(h_code="H300", category=cat)
    with pytest.raises(IntegrityError):
        HCodeCategoryMapping.objects.create(h_code="H300", category=cat)


@pytest.mark.django_db
def test_should_create_measure_template():
    cat = HazardCategoryRef.objects.create(
        code="TEST-PSA",
        name="PSA Test",
        category_type=HazardCategoryType.SKIN_CORROSION,
    )
    t = MeasureTemplate.objects.create(
        category=cat,
        tops_type=TOPSType.PERSONAL,
        title="Schutzhandschuhe Typ III",
        is_mandatory=True,
    )
    assert t.is_mandatory is True
    assert "[P]" in str(t)
