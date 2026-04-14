# src/global_sds/tests/test_upload_pipeline.py
"""Tests for SdsUploadPipeline (ADR-012 §5)."""

import hashlib

import pytest

from global_sds.models import GlobalSdsRevision, GlobalSubstance
from global_sds.services.upload_pipeline import SdsUploadPipeline, UploadOutcome
from global_sds.tests.factories import GlobalSdsRevisionFactory, GlobalSubstanceFactory


pytestmark = pytest.mark.django_db


def _make_pdf(content: str = "dummy") -> bytes:
    """Create deterministic fake PDF bytes."""
    return content.encode("utf-8")


def _make_parse_result(**overrides) -> dict:
    """Minimal parse result dict."""
    base = {
        "cas_number": "",
        "product_name": "Test Product",
        "manufacturer_name": "Test GmbH",
        "revision_date": "2025-06-01",
        "version_number": "1.0",
        "parse_confidence": 0.95,
        "signal_word": "Gefahr",
        "flash_point_c": None,
        "ignition_temperature_c": None,
        "lower_explosion_limit": None,
        "upper_explosion_limit": None,
        "llm_corrections": [],
    }
    base.update(overrides)
    return base


class TestSha256Deduplication:
    """Stufe 1: SHA-256 check for duplicate PDFs."""

    def test_should_detect_duplicate_pdf(self, db, tenant_id):
        pdf = _make_pdf("unique-pdf-content")
        source_hash = hashlib.sha256(pdf).hexdigest()
        existing = GlobalSdsRevisionFactory(source_hash=source_hash)

        pipeline = SdsUploadPipeline()
        result = pipeline.process(pdf, _make_parse_result(), str(tenant_id))

        assert result.outcome == UploadOutcome.DUPLICATE
        assert result.revision == existing

    def test_should_pass_new_pdf(self, db, tenant_id):
        pdf = _make_pdf("brand-new-content")
        pipeline = SdsUploadPipeline()
        result = pipeline.process(
            pdf,
            _make_parse_result(cas_number="", product_name="Totally New Chemical"),
            str(tenant_id),
        )
        assert result.outcome != UploadOutcome.DUPLICATE


class TestNewSubstance:
    """No identity match → create new substance."""

    def test_should_create_new_substance_for_unknown(self, db, tenant_id):
        pdf = _make_pdf("new-substance-pdf")
        parse = _make_parse_result(
            cas_number="",
            product_name="Xylenol-9000 Spezial Reiniger",
        )

        pipeline = SdsUploadPipeline()
        result = pipeline.process(pdf, parse, str(tenant_id))

        assert result.outcome == UploadOutcome.NEW_SUBSTANCE
        assert result.substance is not None
        assert result.substance.name == "Xylenol-9000 Spezial Reiniger"
        assert GlobalSubstance.objects.count() == 1
        assert GlobalSdsRevision.objects.count() == 1


class TestIdentityResolution:
    """Stufe 2: CAS match or fuzzy match."""

    def test_should_match_known_cas(self, substance_acetone, tenant_id):
        pdf = _make_pdf("acetone-v2-pdf")
        parse = _make_parse_result(
            cas_number="67-64-1",
            product_name="Aceton rein",
            revision_date="2026-01-01",
            version_number="3.0",
        )

        pipeline = SdsUploadPipeline()
        result = pipeline.process(pdf, parse, str(tenant_id))

        # Should match existing substance and create new revision
        assert result.outcome == UploadOutcome.NEW_REVISION
        assert result.substance == substance_acetone


class TestVersionConflict:
    """Stufe 3: Retrograde date or ambiguous version → CONFLICT."""

    def test_should_detect_version_conflict(
        self, substance_acetone, revision_acetone_v1, tenant_id,
    ):
        pdf = _make_pdf("conflict-pdf")
        parse = _make_parse_result(
            cas_number="67-64-1",
            product_name="Aceton",
            revision_date="2023-01-01",  # older than v1 (2024-06-15)
            version_number="0.5",
        )

        pipeline = SdsUploadPipeline()
        result = pipeline.process(pdf, parse, str(tenant_id))

        assert result.outcome == UploadOutcome.CONFLICT


class TestEndToEnd:
    """Full pipeline integration."""

    def test_should_process_new_substance_end_to_end(self, db, tenant_id):
        pdf = _make_pdf("e2e-test-pdf")
        parse = _make_parse_result(
            cas_number="110-82-7",
            product_name="Cyclohexan",
            manufacturer_name="Sigma-Aldrich",
            revision_date="2025-06-15",
            version_number="2.0",
            parse_confidence=0.92,
            flash_point_c=-20,
        )

        pipeline = SdsUploadPipeline()
        result = pipeline.process(pdf, parse, str(tenant_id))

        assert result.outcome == UploadOutcome.NEW_SUBSTANCE
        assert result.revision is not None
        assert result.revision.product_name == "Cyclohexan"
        assert result.revision.flash_point_c == -20
        assert result.revision.uploaded_by_tenant_id == str(tenant_id)
