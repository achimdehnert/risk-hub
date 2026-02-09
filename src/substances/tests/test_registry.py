"""Tests for LocationSubstanceEntry (TRGS 510 / Seveso III)."""

import uuid
from decimal import Decimal

import pytest

from substances.models import (
    LocationSubstanceEntry,
    SevesoCategory,
    StorageClass,
    Substance,
)


TENANT_ID = uuid.uuid4()


@pytest.fixture()
def fixture_substance(db):
    """Create a base substance for testing."""
    return Substance.objects.create(
        tenant_id=TENANT_ID,
        name="Ethanol",
    )


@pytest.mark.django_db
class TestLocationSubstanceEntry:
    """Test hazardous substance registry entries."""

    def test_should_create_entry(self, fixture_substance):
        entry = LocationSubstanceEntry.objects.create(
            tenant_id=TENANT_ID,
            area_id=uuid.uuid4(),
            substance=fixture_substance,
            substance_name="Ethanol",
            max_quantity_kg=Decimal("5000.00"),
            current_quantity_kg=Decimal("2500.00"),
            storage_class=StorageClass.LGK_3,
        )
        assert entry.pk is not None
        assert entry.storage_class == "3"

    def test_should_default_seveso_none(self, fixture_substance):
        entry = LocationSubstanceEntry.objects.create(
            tenant_id=TENANT_ID,
            area_id=uuid.uuid4(),
            substance=fixture_substance,
            substance_name="Ethanol",
        )
        assert entry.seveso_category == SevesoCategory.NONE

    def test_should_calculate_seveso_utilization(
        self, fixture_substance,
    ):
        entry = LocationSubstanceEntry(
            tenant_id=TENANT_ID,
            area_id=uuid.uuid4(),
            substance=fixture_substance,
            substance_name="Ethanol",
            current_quantity_kg=Decimal("500.00"),
            seveso_threshold_lower_t=Decimal("10.00"),
            seveso_category=SevesoCategory.LOWER,
        )
        assert entry.seveso_utilization_pct == 5.0

    def test_should_return_none_utilization_without_threshold(
        self, fixture_substance,
    ):
        entry = LocationSubstanceEntry(
            tenant_id=TENANT_ID,
            area_id=uuid.uuid4(),
            substance=fixture_substance,
            substance_name="Ethanol",
            current_quantity_kg=Decimal("100.00"),
        )
        assert entry.seveso_utilization_pct is None

    def test_should_enforce_unique_per_area(
        self, fixture_substance,
    ):
        area_id = uuid.uuid4()
        LocationSubstanceEntry.objects.create(
            tenant_id=TENANT_ID,
            area_id=area_id,
            substance=fixture_substance,
            substance_name="Ethanol",
        )
        from django.db import IntegrityError
        with pytest.raises(IntegrityError):
            LocationSubstanceEntry.objects.create(
                tenant_id=TENANT_ID,
                area_id=area_id,
                substance=fixture_substance,
                substance_name="Ethanol Dup",
            )

    def test_should_display_string(self, fixture_substance):
        entry = LocationSubstanceEntry(
            substance_name="Aceton",
            current_quantity_kg=Decimal("42.50"),
        )
        s = str(entry)
        assert "Aceton" in s
        assert "42.50" in s
