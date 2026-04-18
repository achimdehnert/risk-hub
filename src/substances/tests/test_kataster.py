# substances/tests/test_kataster.py
"""Tests für das Gefahrstoffkataster (UC-004): Services und Views."""

import uuid

import pytest

from substances.models import (
    ImportBatch,
    Party,
    Product,
    SubstanceUsage,
)
from substances.services.kataster_service import (
    KatasterDashboardService,
    KatasterImportService,
    ProductService,
    UsageService,
)
from tenancy.models import Department, Organization, Site


@pytest.fixture
def tenant_id():
    return uuid.uuid4()


@pytest.fixture
def user_id():
    return uuid.uuid4()


@pytest.fixture
def org(tenant_id):
    return Organization.objects.create(
        tenant_id=tenant_id,
        name="Test GmbH",
        slug="test-gmbh",
    )


@pytest.fixture
def site(tenant_id, org):
    return Site.objects.create(
        tenant_id=tenant_id,
        organization=org,
        name="Hauptwerk",
        code="HW",
        site_type="production",
        is_active=True,
    )


@pytest.fixture
def department(tenant_id, org, site):
    return Department.objects.create(
        tenant_id=tenant_id,
        organization=org,
        site=site,
        name="Lackierung",
        code="LACK",
    )


@pytest.fixture
def manufacturer(tenant_id, user_id):
    return Party.objects.create(
        tenant_id=tenant_id,
        created_by=user_id,
        name="BASF SE",
        party_type="manufacturer",
    )


@pytest.fixture
def product(tenant_id, user_id, manufacturer):
    return Product.objects.create(
        tenant_id=tenant_id,
        created_by=user_id,
        trade_name="Verdünner V100",
        manufacturer=manufacturer,
        material_number="MAT-001",
        status=Product.Status.ACTIVE,
    )


@pytest.fixture
def usage(tenant_id, user_id, product, site, department):
    return SubstanceUsage.objects.create(
        tenant_id=tenant_id,
        created_by=user_id,
        product=product,
        site=site,
        department=department,
        usage_description="Verdünnung von Lacken",
        storage_location="Gefahrstofflager Halle 3",
        storage_class="3",
        status=SubstanceUsage.Status.ACTIVE,
    )


# =========================================================================
# ProductService Tests
# =========================================================================


@pytest.mark.django_db
class TestProductService:
    """Tests für ProductService."""

    def test_should_list_products_for_tenant(self, product, tenant_id):
        results = ProductService.list_products(tenant_id)
        assert len(results) == 1
        assert results[0].trade_name == "Verdünner V100"

    def test_should_not_list_products_for_wrong_tenant(self, product):
        results = ProductService.list_products(uuid.uuid4())
        assert len(results) == 0

    def test_should_filter_by_search(self, product, tenant_id):
        results = ProductService.list_products(tenant_id, search="Verdünner")
        assert len(results) == 1
        results = ProductService.list_products(tenant_id, search="xyz-not-exist")
        assert len(results) == 0

    def test_should_filter_by_status(self, product, tenant_id):
        results = ProductService.list_products(tenant_id, status="active")
        assert len(results) == 1
        results = ProductService.list_products(tenant_id, status="archived")
        assert len(results) == 0

    def test_should_filter_by_site(self, usage, tenant_id, site):
        results = ProductService.list_products(tenant_id, site_id=site.pk)
        assert len(results) == 1

    def test_should_get_product(self, product, tenant_id):
        result = ProductService.get_product(product.pk, tenant_id)
        assert result.trade_name == "Verdünner V100"

    def test_should_raise_404_for_wrong_tenant(self, product):
        from django.http import Http404

        with pytest.raises(Http404):
            ProductService.get_product(product.pk, uuid.uuid4())


# =========================================================================
# UsageService Tests
# =========================================================================


@pytest.mark.django_db
class TestUsageService:
    """Tests für UsageService."""

    def test_should_list_usages_for_tenant(self, usage, tenant_id):
        results = UsageService.list_usages(tenant_id)
        assert len(results) == 1

    def test_should_filter_by_site(self, usage, tenant_id, site):
        results = UsageService.list_usages(tenant_id, site_id=site.pk)
        assert len(results) == 1

    def test_should_filter_by_department(self, usage, tenant_id, department):
        results = UsageService.list_usages(tenant_id, department_id=department.pk)
        assert len(results) == 1

    def test_should_filter_by_status(self, usage, tenant_id):
        results = UsageService.list_usages(tenant_id, status="active")
        assert len(results) == 1
        results = UsageService.list_usages(tenant_id, status="inactive")
        assert len(results) == 0

    def test_should_filter_by_search(self, usage, tenant_id):
        results = UsageService.list_usages(tenant_id, search="Lacken")
        assert len(results) == 1

    def test_should_get_usage(self, usage, tenant_id):
        result = UsageService.get_usage(usage.pk, tenant_id)
        assert result.product.trade_name == "Verdünner V100"


# =========================================================================
# KatasterDashboardService Tests
# =========================================================================


@pytest.mark.django_db
class TestKatasterDashboardService:
    """Tests für KatasterDashboardService."""

    def test_should_return_stats(self, product, usage, tenant_id):
        stats = KatasterDashboardService.get_stats(tenant_id)
        assert stats["total_products"] == 1
        assert stats["active_products"] == 1
        assert stats["total_usages"] == 1
        assert stats["active_usages"] == 1

    def test_should_return_empty_stats_for_empty_tenant(self):
        stats = KatasterDashboardService.get_stats(uuid.uuid4())
        assert stats["total_products"] == 0
        assert stats["total_usages"] == 0

    def test_should_return_site_summary(self, usage, tenant_id):
        sites = KatasterDashboardService.get_site_summary(tenant_id)
        assert len(sites) == 1
        assert sites[0].usage_count == 1
        assert sites[0].department_count == 1

    def test_should_return_recent_products(self, product, tenant_id):
        recent = KatasterDashboardService.get_recent_products(tenant_id)
        assert len(recent) == 1
        assert recent[0].trade_name == "Verdünner V100"


# =========================================================================
# KatasterImportService Tests
# =========================================================================


@pytest.mark.django_db
class TestKatasterImportService:
    """Tests für KatasterImportService."""

    def test_should_create_batch(self, tenant_id, user_id, site):
        service = KatasterImportService(tenant_id=tenant_id, user_id=user_id)
        batch, is_dup = service.create_batch("test.xlsx", b"fake-content", site.pk)
        assert batch is not None
        assert is_dup is False
        assert batch.file_name == "test.xlsx"
        assert batch.status == ImportBatch.Status.PENDING

    def test_should_detect_duplicate_batch(self, tenant_id, user_id, site):
        service = KatasterImportService(tenant_id=tenant_id, user_id=user_id)
        batch1, dup1 = service.create_batch("test.xlsx", b"same-content", site.pk)
        batch2, dup2 = service.create_batch("test2.xlsx", b"same-content", site.pk)
        assert dup1 is False
        assert dup2 is True
        assert batch1.pk == batch2.pk

    def test_should_map_fields(self):
        row = {"Produkt": "Aceton", "Nummer": "MAT-01"}
        mapping = {"trade_name": "Produkt", "material_number": "Nummer"}
        result = KatasterImportService._map_field(row, mapping, "trade_name")
        assert result == "Aceton"

    def test_should_return_empty_for_unmapped_field(self):
        row = {"Produkt": "Aceton"}
        mapping = {}
        result = KatasterImportService._map_field(row, mapping, "trade_name")
        assert result == ""
