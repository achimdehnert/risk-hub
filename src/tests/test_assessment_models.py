# tests/test_assessment_models.py — ADR-057 Phase 2: Model Tests
import uuid
import pytest

from tests.factories import AssessmentFactory, HazardFactory
from risk.models import Assessment, Hazard


@pytest.mark.django_db
class TestAssessmentModel:
    def test_should_create_assessment_with_uuid_pk(self):
        a = AssessmentFactory()
        assert isinstance(a.pk, uuid.UUID)

    def test_should_default_status_to_draft(self):
        a = AssessmentFactory()
        assert a.status == Assessment.Status.DRAFT

    def test_should_default_category_to_general(self):
        a = AssessmentFactory()
        assert a.category == Assessment.Category.GENERAL

    def test_should_str_return_title(self):
        a = AssessmentFactory(title="Brandschutz 2025")
        assert str(a) == "Brandschutz 2025"

    def test_should_enforce_unique_title_per_tenant(self):
        tid = uuid.uuid4()
        AssessmentFactory(tenant_id=tid, title="Unique Title")
        with pytest.raises(Exception):
            AssessmentFactory(tenant_id=tid, title="Unique Title")

    def test_should_allow_same_title_for_different_tenants(self):
        a1 = AssessmentFactory(title="Same Title")
        a2 = AssessmentFactory(title="Same Title")
        assert a1.tenant_id != a2.tenant_id


@pytest.mark.django_db
class TestHazardModel:
    def test_should_calculate_risk_score_as_severity_times_probability(self):
        hazard = HazardFactory(
            severity=Hazard.Severity.HIGH,
            probability=Hazard.Probability.PROBABLE,
        )
        assert hazard.risk_score == 3 * 4

    def test_should_cascade_delete_hazards_with_assessment(self):
        assessment = AssessmentFactory()
        HazardFactory(assessment=assessment)
        HazardFactory(assessment=assessment)
        assessment_pk = assessment.pk
        assessment.delete()
        assert Hazard.objects.filter(assessment_id=assessment_pk).count() == 0

    def test_should_str_return_title(self):
        h = HazardFactory(title="Brandgefahr")
        assert str(h) == "Brandgefahr"

    def test_should_risk_score_be_max_for_critical_frequent(self):
        h = HazardFactory(
            severity=Hazard.Severity.CRITICAL,
            probability=Hazard.Probability.FREQUENT,
        )
        assert h.risk_score == 25

    def test_should_share_tenant_id_with_assessment(self):
        assessment = AssessmentFactory()
        hazard = HazardFactory(assessment=assessment)
        assert hazard.tenant_id == assessment.tenant_id
