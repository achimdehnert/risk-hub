# src/global_sds/tests/conftest.py
"""Shared fixtures for Global SDS Library tests."""

import uuid
from datetime import date

import pytest

from global_sds.tests.factories import (
    GlobalSdsRevisionFactory,
    GlobalSubstanceFactory,
    SdsUsageFactory,
)
from global_sds.sds_usage import SdsUsageStatus


@pytest.fixture
def tenant_id():
    """Fixed tenant UUID for multi-tenant tests."""
    return uuid.UUID("aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee")


@pytest.fixture
def tenant_id_b():
    """Second tenant UUID for isolation tests."""
    return uuid.UUID("11111111-2222-3333-4444-555555555555")


@pytest.fixture
def user(db):
    """Standard test user."""
    from tests.factories import UserFactory
    return UserFactory()


@pytest.fixture
def substance_acetone(db):
    """Acetone — well-known substance with CAS."""
    return GlobalSubstanceFactory(
        cas_number="67-64-1",
        name="Aceton",
        synonyms=["Acetone", "2-Propanon", "Dimethylketon"],
    )


@pytest.fixture
def substance_toluene(db):
    """Toluene — second substance for multi-substance tests."""
    return GlobalSubstanceFactory(
        cas_number="108-88-3",
        name="Toluol",
        synonyms=["Toluene", "Methylbenzol"],
    )


@pytest.fixture
def revision_acetone_v1(db, substance_acetone, tenant_id):
    """Verified v1 revision for Acetone."""
    return GlobalSdsRevisionFactory(
        substance=substance_acetone,
        source_hash="a" * 64,
        status="VERIFIED",
        uploaded_by_tenant_id=tenant_id,
        product_name="Aceton technisch",
        manufacturer_name="Merck KGaA",
        revision_date=date(2024, 6, 15),
        version_number="1.0",
        flash_point_c=-20,
        wgk=1,
        parse_confidence=0.95,
    )


@pytest.fixture
def revision_acetone_v2(db, substance_acetone, tenant_id):
    """Verified v2 revision for Acetone (newer)."""
    return GlobalSdsRevisionFactory(
        substance=substance_acetone,
        source_hash="b" * 64,
        status="VERIFIED",
        uploaded_by_tenant_id=tenant_id,
        product_name="Aceton technisch",
        manufacturer_name="Merck KGaA",
        revision_date=date(2025, 3, 1),
        version_number="2.0",
        flash_point_c=-18,
        wgk=1,
        parse_confidence=0.97,
    )


@pytest.fixture
def usage_active(db, revision_acetone_v1, tenant_id, user):
    """Active SdsUsage for tenant A using Acetone v1."""
    return SdsUsageFactory(
        tenant_id=tenant_id,
        sds_revision=revision_acetone_v1,
        status=SdsUsageStatus.ACTIVE,
        approved_by=user,
    )
