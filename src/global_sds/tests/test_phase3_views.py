# global_sds/tests/test_phase3_views.py
"""Tests für Phase 3: Progress Rail View, SDS Datacard View, Dashboard (ADR-017 §8)."""

import uuid
from datetime import date, timedelta
from unittest.mock import MagicMock, patch

import pytest
from django.test import RequestFactory

from common.progress.base import DocumentProgress, StepState, StepStatus
from common.progress.views import progress_rail_partial
from global_sds.views import compliance_dashboard
from global_sds.views_partials import sds_datacard_partial

pytestmark = pytest.mark.django_db


# ── Fixtures ──────────────────────────────────────────────────────────


@pytest.fixture
def rf():
    return RequestFactory()


@pytest.fixture
def tenant_id():
    return uuid.UUID("aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee")


@pytest.fixture
def auth_request(rf, tenant_id):
    """Authenticated GET request with tenant context."""
    from tests.factories import UserFactory

    user = UserFactory()
    request = rf.get("/")
    request.user = user
    request.tenant_id = tenant_id
    return request


# ── Progress Rail View ────────────────────────────────────────────────


class TestProgressRailView:
    def test_should_return_404_for_unknown_doc_type(self, auth_request):
        from django.http import Http404

        with pytest.raises(Http404):
            progress_rail_partial(auth_request, "unknown", str(uuid.uuid4()))

    def test_should_return_404_for_invalid_uuid(self, auth_request):
        from django.http import Http404

        with pytest.raises(Http404):
            progress_rail_partial(auth_request, "gbu", "not-a-uuid")

    @patch("common.progress.views._import_class")
    def test_should_render_progress_rail(self, mock_import, auth_request, tenant_id):
        doc_id = uuid.uuid4()

        mock_model = MagicMock()
        mock_doc = MagicMock()
        mock_model.objects.get.return_value = mock_doc
        mock_model.DoesNotExist = type("DoesNotExist", (Exception,), {})

        mock_service_cls = MagicMock()
        mock_service = MagicMock()
        mock_service.get_progress.return_value = DocumentProgress(
            steps=[
                StepStatus(step=1, label="Step A", state=StepState.COMPLETE),
                StepStatus(step=2, label="Step B", state=StepState.EMPTY),
            ],
            can_approve=False,
            blocking_reasons=["Step B not done"],
            overall_percent=50,
        )
        mock_service_cls.return_value = mock_service

        mock_import.side_effect = [mock_model, mock_service_cls]

        response = progress_rail_partial(auth_request, "gbu", str(doc_id))

        assert response.status_code == 200
        content = response.content.decode()
        assert "Step A" in content
        assert "Step B" in content
        assert "50%" in content

    @patch("common.progress.views._import_class")
    def test_should_return_404_for_missing_document(self, mock_import, auth_request, tenant_id):
        from django.http import Http404

        doc_id = uuid.uuid4()

        mock_model = MagicMock()
        exc_cls = type("DoesNotExist", (Exception,), {})
        mock_model.DoesNotExist = exc_cls
        mock_model.objects.get.side_effect = exc_cls("not found")

        mock_service_cls = MagicMock()
        mock_import.side_effect = [mock_model, mock_service_cls]

        with pytest.raises(Http404):
            progress_rail_partial(auth_request, "gbu", str(doc_id))


# ── SDS Datacard View ────────────────────────────────────────────────


class TestSdsDatacardView:
    def test_should_render_datacard_for_revision(self, auth_request, tenant_id):
        from global_sds.tests.factories import (
            GlobalSdsRevisionFactory,
            GlobalSubstanceFactory,
        )

        substance = GlobalSubstanceFactory(cas_number="67-64-1", name="Aceton")
        revision = GlobalSdsRevisionFactory(
            substance=substance,
            product_name="Aceton technisch",
            manufacturer_name="Merck KGaA",
            flash_point_c=-20,
            status="VERIFIED",
            uploaded_by_tenant_id=tenant_id,
        )

        response = sds_datacard_partial(auth_request, pk=revision.pk)
        assert response.status_code == 200
        content = response.content.decode()
        assert "Aceton technisch" in content
        assert "Merck KGaA" in content
        assert "67-64-1" in content
        assert "sds-datacard" in content

    def test_should_return_404_for_nonexistent_revision(self, auth_request):
        from django.http import Http404

        with pytest.raises(Http404):
            sds_datacard_partial(auth_request, pk=999999)

    def test_should_show_ex_data_when_present(self, auth_request, tenant_id):
        from global_sds.tests.factories import (
            GlobalSdsRevisionFactory,
            GlobalSubstanceFactory,
        )

        substance = GlobalSubstanceFactory(cas_number="110-54-3", name="n-Hexan")
        revision = GlobalSdsRevisionFactory(
            substance=substance,
            product_name="n-Hexan reinst",
            flash_point_c=-22,
            ignition_temperature_c=233,
            lower_explosion_limit=1.1,
            upper_explosion_limit=7.5,
            status="VERIFIED",
            uploaded_by_tenant_id=tenant_id,
        )

        response = sds_datacard_partial(auth_request, pk=revision.pk)
        content = response.content.decode()
        assert "-22" in content
        assert "233" in content
        assert "1.1" in content


# ── Compliance Dashboard View ─────────────────────────────────────────


class TestComplianceDashboardView:
    def test_should_render_dashboard_empty(self, auth_request):
        response = compliance_dashboard(auth_request)
        assert response.status_code == 200
        content = response.content.decode()
        assert "SDS Compliance-Dashboard" in content

    def test_should_show_kpi_counts(self, auth_request, tenant_id):
        from global_sds.sds_usage import SdsUsageStatus
        from global_sds.tests.factories import (
            GlobalSdsRevisionFactory,
            GlobalSubstanceFactory,
            SdsUsageFactory,
        )
        from tests.factories import UserFactory

        substance = GlobalSubstanceFactory(cas_number="67-64-1")
        rev = GlobalSdsRevisionFactory(
            substance=substance,
            status="VERIFIED",
            uploaded_by_tenant_id=tenant_id,
        )
        user = UserFactory()
        SdsUsageFactory(
            tenant_id=tenant_id,
            sds_revision=rev,
            status=SdsUsageStatus.REVIEW_REQUIRED,
            review_deadline=date.today() - timedelta(days=7),
            approved_by=user,
        )

        response = compliance_dashboard(auth_request)
        assert response.status_code == 200
        content = response.content.decode()
        assert "Safety-Critical" in content


# ── Progress Rail Registry ────────────────────────────────────────────


class TestProgressRegistry:
    def test_should_have_gbu_and_ex_registered(self):
        from common.progress.views import _PROGRESS_REGISTRY

        assert "gbu" in _PROGRESS_REGISTRY
        assert "ex" in _PROGRESS_REGISTRY

    def test_should_have_valid_import_paths(self):
        from common.progress.views import _PROGRESS_REGISTRY, _import_class

        for _doc_type, (model_path, service_path) in _PROGRESS_REGISTRY.items():
            # Should not raise ImportError
            model_cls = _import_class(model_path)
            service_cls = _import_class(service_path)
            assert model_cls is not None
            assert service_cls is not None
