# src/global_sds/tests/factories.py
"""Factories for Global SDS Library tests (ADR-012)."""

import uuid

import factory

from global_sds.models import (
    GlobalSdsComponent,
    GlobalSdsExposureLimit,
    GlobalSdsRevision,
    GlobalSubstance,
    SdsRevisionDiffRecord,
    ImpactLevel,
)
from global_sds.sds_usage import SdsUsage, SdsUsageStatus


class GlobalSubstanceFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = GlobalSubstance

    cas_number = factory.Sequence(lambda n: f"{100 + n}-00-{n % 10}")
    name = factory.Sequence(lambda n: f"Substance {n}")
    ec_number = factory.Sequence(lambda n: f"200-{n:03d}-{n % 10}")
    synonyms = factory.LazyFunction(list)


class GlobalSdsRevisionFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = GlobalSdsRevision

    substance = factory.SubFactory(GlobalSubstanceFactory)
    source_hash = factory.LazyFunction(lambda: uuid.uuid4().hex + uuid.uuid4().hex[:32])
    status = GlobalSdsRevision.Status.VERIFIED
    uploaded_by_tenant_id = factory.LazyFunction(uuid.uuid4)
    product_name = factory.LazyAttribute(lambda obj: f"Product {obj.substance.name}")
    manufacturer_name = "Test Manufacturer GmbH"
    revision_date = factory.LazyFunction(lambda: __import__("datetime").date(2025, 1, 1))
    version_number = "1.0"
    parse_confidence = 0.95


class GlobalSdsComponentFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = GlobalSdsComponent

    sds_revision = factory.SubFactory(GlobalSdsRevisionFactory)
    chemical_name = factory.Sequence(lambda n: f"Component {n}")
    cas_number = factory.Sequence(lambda n: f"{200 + n}-00-{n % 10}")


class GlobalSdsExposureLimitFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = GlobalSdsExposureLimit

    sds_revision = factory.SubFactory(GlobalSdsRevisionFactory)
    limit_type = GlobalSdsExposureLimit.LimitType.AGW
    route = GlobalSdsExposureLimit.ExposureRoute.INHALATION
    value = factory.LazyFunction(lambda: __import__("decimal").Decimal("10.0"))
    unit = "mg/m³"


class SdsRevisionDiffRecordFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = SdsRevisionDiffRecord

    old_revision = factory.SubFactory(GlobalSdsRevisionFactory)
    new_revision = factory.SubFactory(GlobalSdsRevisionFactory)
    overall_impact = ImpactLevel.INFORMATIONAL
    field_diffs = factory.LazyFunction(list)
    added_h_codes = factory.LazyFunction(list)
    removed_h_codes = factory.LazyFunction(list)
    changed_components = factory.LazyFunction(list)


class SdsUsageFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = SdsUsage

    tenant_id = factory.LazyFunction(uuid.uuid4)
    sds_revision = factory.SubFactory(GlobalSdsRevisionFactory)
    status = SdsUsageStatus.ACTIVE
