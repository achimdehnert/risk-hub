"""Tests for Hazard API endpoints (Django Ninja).

Tests:
- Service layer: list_hazards, get_hazard
- API endpoint: GET /api/v1/risk/hazards
- Tenant isolation
- Pagination (offset/limit)
- Assessment filter
"""

from __future__ import annotations

import hashlib

import pytest

from common.context import set_tenant, set_user_id
from identity.models import ApiKey
from risk.models import Assessment, Hazard
from risk.services import get_hazard, list_hazards


@pytest.fixture()
def fixture_assessment(db, fixture_tenant, fixture_user):
    """Create a test assessment."""
    return Assessment.objects.create(
        tenant_id=fixture_tenant.tenant_id,
        title="Test Assessment",
        description="Test description",
        category="general",
        status="draft",
        created_by=fixture_user,
    )


@pytest.fixture()
def fixture_hazard(db, fixture_tenant, fixture_assessment):
    """Create a test hazard."""
    return Hazard.objects.create(
        tenant_id=fixture_tenant.tenant_id,
        assessment=fixture_assessment,
        title="Test Hazard",
        description="Falling objects",
        severity=3,
        probability=2,
        mitigation="Wear hard hat",
    )


@pytest.fixture()
def fixture_hazards_batch(db, fixture_tenant, fixture_assessment):
    """Create multiple hazards for pagination tests."""
    hazards = []
    for i in range(5):
        h = Hazard.objects.create(
            tenant_id=fixture_tenant.tenant_id,
            assessment=fixture_assessment,
            title=f"Hazard {i}",
            severity=i % 5 + 1,
            probability=i % 5 + 1,
        )
        hazards.append(h)
    return hazards


@pytest.fixture()
def fixture_api_key(db, fixture_tenant, fixture_user):
    """Create an ApiKey for Ninja API auth."""
    raw_key = "test-api-key-0123456789abcdef"
    key_prefix = raw_key[:16]
    key_hash = hashlib.sha256(raw_key.encode("utf-8")).hexdigest()
    api_key = ApiKey.objects.create(
        tenant_id=fixture_tenant.tenant_id,
        user=fixture_user,
        name="test-key",
        key_prefix=key_prefix,
        key_hash=key_hash,
    )
    return raw_key, api_key


# =============================================================================
# SERVICE LAYER TESTS
# =============================================================================


@pytest.mark.django_db
class TestListHazardsService:
    """Tests for list_hazards service function."""

    def test_should_list_hazards(
        self, fixture_assignment, fixture_hazard,
    ):
        a = fixture_assignment
        set_tenant(a.tenant_id, "test-corp")
        set_user_id(a.user_id)

        result = list_hazards()
        assert len(result) == 1
        assert result[0].title == "Test Hazard"

    def test_should_filter_by_assessment(
        self,
        fixture_assignment,
        fixture_hazard,
        fixture_assessment,
        fixture_tenant,
        fixture_user,
    ):
        a = fixture_assignment
        set_tenant(a.tenant_id, "test-corp")
        set_user_id(a.user_id)

        other_assessment = Assessment.objects.create(
            tenant_id=fixture_tenant.tenant_id,
            title="Other Assessment",
            category="general",
            status="draft",
            created_by=fixture_user,
        )
        Hazard.objects.create(
            tenant_id=fixture_tenant.tenant_id,
            assessment=other_assessment,
            title="Other Hazard",
            severity=1,
            probability=1,
        )

        result = list_hazards(assessment_id=fixture_assessment.id)
        assert len(result) == 1
        assert result[0].title == "Test Hazard"

    def test_should_respect_offset_limit(
        self, fixture_assignment, fixture_hazards_batch,
    ):
        a = fixture_assignment
        set_tenant(a.tenant_id, "test-corp")
        set_user_id(a.user_id)

        result = list_hazards(limit=2, offset=0)
        assert len(result) == 2

        result2 = list_hazards(limit=2, offset=2)
        assert len(result2) == 2

        result3 = list_hazards(limit=2, offset=4)
        assert len(result3) == 1

    def test_should_isolate_tenants(
        self, fixture_assignment, fixture_hazard, fixture_tenant_b,
    ):
        a = fixture_assignment
        set_tenant(fixture_tenant_b.tenant_id, "other-corp")
        set_user_id(a.user_id)

        result = list_hazards()
        assert len(result) == 0


@pytest.mark.django_db
class TestGetHazardService:
    """Tests for get_hazard service function."""

    def test_should_get_hazard(
        self, fixture_assignment, fixture_hazard,
    ):
        a = fixture_assignment
        set_tenant(a.tenant_id, "test-corp")
        set_user_id(a.user_id)

        result = get_hazard(fixture_hazard.id)
        assert result.title == "Test Hazard"
        assert result.risk_score == 6

    def test_should_raise_for_other_tenant(
        self, fixture_assignment, fixture_hazard, fixture_tenant_b,
    ):
        a = fixture_assignment
        set_tenant(fixture_tenant_b.tenant_id, "other-corp")
        set_user_id(a.user_id)

        with pytest.raises(Hazard.DoesNotExist):
            get_hazard(fixture_hazard.id)


# =============================================================================
# API ENDPOINT TESTS
# =============================================================================


@pytest.mark.django_db
class TestHazardAPIEndpoint:
    """Tests for GET /api/v1/risk/hazards via Django Ninja."""

    def test_should_list_hazards_via_api(
        self, client, fixture_api_key, fixture_hazard,
    ):
        raw_key, _ = fixture_api_key
        response = client.get(
            "/api/v1/risk/hazards",
            HTTP_AUTHORIZATION=f"Bearer {raw_key}",
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["title"] == "Test Hazard"
        assert data[0]["risk_score"] == 6

    def test_should_return_401_without_auth(self, client):
        response = client.get("/api/v1/risk/hazards")
        assert response.status_code == 401

    def test_should_get_hazard_detail_via_api(
        self, client, fixture_api_key, fixture_hazard,
    ):
        raw_key, _ = fixture_api_key
        response = client.get(
            f"/api/v1/risk/hazards/{fixture_hazard.id}",
            HTTP_AUTHORIZATION=f"Bearer {raw_key}",
        )
        assert response.status_code == 200
        data = response.json()
        assert data["title"] == "Test Hazard"
        assert data["severity"] == 3
        assert data["probability"] == 2

    def test_should_support_offset_limit(
        self, client, fixture_api_key, fixture_hazards_batch,
    ):
        raw_key, _ = fixture_api_key
        response = client.get(
            "/api/v1/risk/hazards?limit=2&offset=0",
            HTTP_AUTHORIZATION=f"Bearer {raw_key}",
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2

    def test_should_filter_by_assessment(
        self, client, fixture_api_key, fixture_hazard, fixture_assessment,
    ):
        raw_key, _ = fixture_api_key
        response = client.get(
            f"/api/v1/risk/hazards?assessment_id={fixture_assessment.id}",
            HTTP_AUTHORIZATION=f"Bearer {raw_key}",
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
