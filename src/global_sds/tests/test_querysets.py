# src/global_sds/tests/test_querysets.py
"""Tests for SdsRevisionQuerySet (ADR-012 §3.2 Tenant-Visibility)."""

import uuid

import pytest

from global_sds.models import GlobalSdsRevision
from global_sds.tests.factories import GlobalSdsRevisionFactory, GlobalSubstanceFactory

pytestmark = pytest.mark.django_db


class TestVisibleForTenant:
    """visible_for_tenant() — VERIFIED/SUPERSEDED global, PENDING only for uploader."""

    def test_should_show_verified_to_any_tenant(self, db):
        tenant_a = uuid.uuid4()
        tenant_b = uuid.uuid4()
        rev = GlobalSdsRevisionFactory(
            status="VERIFIED",
            uploaded_by_tenant_id=tenant_a,
        )

        qs = GlobalSdsRevision.objects.visible_for_tenant(tenant_b)
        assert rev in qs

    def test_should_show_pending_only_to_uploader(self, db):
        tenant_a = uuid.uuid4()
        tenant_b = uuid.uuid4()
        rev = GlobalSdsRevisionFactory(
            status="PENDING",
            uploaded_by_tenant_id=tenant_a,
        )

        assert rev in GlobalSdsRevision.objects.visible_for_tenant(tenant_a)
        assert rev not in GlobalSdsRevision.objects.visible_for_tenant(tenant_b)

    def test_should_show_superseded_to_any_tenant(self, db):
        tenant_a = uuid.uuid4()
        tenant_b = uuid.uuid4()
        rev = GlobalSdsRevisionFactory(
            status="SUPERSEDED",
            uploaded_by_tenant_id=tenant_a,
        )

        qs = GlobalSdsRevision.objects.visible_for_tenant(tenant_b)
        assert rev in qs

    def test_should_hide_rejected_from_other_tenants(self, db):
        tenant_a = uuid.uuid4()
        tenant_b = uuid.uuid4()
        rev = GlobalSdsRevisionFactory(
            status="REJECTED",
            uploaded_by_tenant_id=tenant_a,
        )

        assert rev not in GlobalSdsRevision.objects.visible_for_tenant(tenant_b)


class TestVerified:
    """verified() — only VERIFIED status."""

    def test_should_filter_verified_only(self, db):
        v = GlobalSdsRevisionFactory(status="VERIFIED")
        GlobalSdsRevisionFactory(status="PENDING")
        GlobalSdsRevisionFactory(status="REJECTED")

        qs = GlobalSdsRevision.objects.verified()
        assert list(qs) == [v]


class TestCurrent:
    """current() — VERIFIED and not superseded."""

    def test_should_exclude_superseded_revisions(self, db):
        substance = GlobalSubstanceFactory()
        old = GlobalSdsRevisionFactory(
            substance=substance,
            status="VERIFIED",
            source_hash="o" * 64,
        )
        new = GlobalSdsRevisionFactory(
            substance=substance,
            status="VERIFIED",
            source_hash="n" * 64,
        )
        old.superseded_by = new
        old.save(update_fields=["superseded_by"])

        qs = GlobalSdsRevision.objects.current()
        assert new in qs
        assert old not in qs
