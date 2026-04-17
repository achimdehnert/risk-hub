# src/global_sds/services/upload_pipeline.py
"""
SdsUploadPipeline — Orchestriert Stufen 1-3 (ADR-012 §5).

PDF Upload → SHA-256 Deduplizierung → Identitätsauflösung →
Versionserkennung → optional Supersession.
"""

import contextlib
import hashlib
import logging
from dataclasses import dataclass
from enum import StrEnum

from django.conf import settings
from django.db import transaction

from global_sds.models import GlobalSdsRevision, GlobalSubstance
from global_sds.services.diff_service import SdsRevisionDiffService
from global_sds.services.enrichment_service import (
    SdsEnrichmentService,
)
from global_sds.services.identity_resolver import (
    SdsIdentityResolver,
)
from global_sds.services.supersession_service import (
    SdsSupersessionService,
)
from global_sds.services.version_detector import (
    SdsVersionDetector,
    VersionOutcome,
)

logger = logging.getLogger(__name__)

GLOBAL_PROMOTION_THRESHOLD = getattr(
    settings,
    "SDS_PARSER_GLOBAL_PROMOTION_THRESHOLD",
    0.90,
)


class UploadOutcome(StrEnum):
    """Ergebnis des Upload-Vorgangs."""

    DUPLICATE = "DUPLICATE"
    NEW_SUBSTANCE = "NEW_SUBSTANCE"
    NEW_REVISION = "NEW_REVISION"
    CONFLICT = "CONFLICT"
    IDENTITY_REVIEW = "IDENTITY_REVIEW"


@dataclass
class UploadResult:
    """Ergebnis der Upload-Pipeline."""

    outcome: UploadOutcome
    revision: GlobalSdsRevision | None = None
    substance: GlobalSubstance | None = None
    message: str = ""
    superseded_count: int = 0


class SdsUploadPipeline:
    """
    Orchestriert den dreistufigen Upload-Prozess.

    Stufe 1: SHA-256 Deduplizierung
    Stufe 2: Identitätsauflösung (SdsIdentityResolver)
    Stufe 3: Versionserkennung (SdsVersionDetector)
    """

    def __init__(self):
        self.enrichment_service = SdsEnrichmentService()
        self.identity_resolver = SdsIdentityResolver()
        self.version_detector = SdsVersionDetector()
        self.diff_service = SdsRevisionDiffService()
        self.supersession_service = SdsSupersessionService()

    @transaction.atomic
    def process(
        self,
        pdf_bytes: bytes,
        parse_result: dict,
        tenant_id: str,
    ) -> UploadResult:
        """
        PDF durch die Pipeline verarbeiten.

        Args:
            pdf_bytes: Raw PDF content.
            parse_result: Extrahierte Daten (von SdsParserService).
            tenant_id: Hochladender Tenant.

        Returns:
            UploadResult mit Outcome und ggf. erstellter Revision.
        """
        # ── Stufe 1: SHA-256 Deduplizierung ──
        source_hash = hashlib.sha256(pdf_bytes).hexdigest()

        existing = GlobalSdsRevision.objects.filter(
            source_hash=source_hash,
        ).first()
        if existing:
            logger.info(
                "Duplicate: hash %s already exists (rev %s)",
                source_hash[:12],
                existing.pk,
            )
            return UploadResult(
                outcome=UploadOutcome.DUPLICATE,
                revision=existing,
                message="PDF bereits importiert (SHA-256 Match)",
            )

        # ── Stufe 1b: Web-Enrichment (CAS/GHS aus PubChem) ──
        enrichment = self.enrichment_service.enrich(parse_result)
        if enrichment.enriched:
            parse_result = self.enrichment_service.merge_into_parse_result(
                parse_result,
                enrichment,
            )
            logger.info(
                "Enriched parse_result (source=%s, CAS=%s)",
                enrichment.source,
                enrichment.cas_number or "—",
            )

        # ── Stufe 2: Identitätsauflösung ──
        cas_number = parse_result.get("cas_number", "")
        product_name = parse_result.get("product_name", "")
        manufacturer = parse_result.get("manufacturer_name", "")

        identity = self.identity_resolver.resolve(
            cas_number=cas_number or None,
            product_name=product_name,
            manufacturer_name=manufacturer,
        )

        if identity.needs_user_confirmation:
            return UploadResult(
                outcome=UploadOutcome.IDENTITY_REVIEW,
                substance=identity.substance,
                message=(
                    f"Match unsicher (conf={identity.confidence:.2f}). "
                    f"Nutzerbestätigung erforderlich."
                ),
            )

        # Substanz bestimmen oder neu anlegen
        if identity.is_new_substance:
            substance = GlobalSubstance.objects.create(
                cas_number=cas_number or None,
                name=product_name,
            )
            revision = self._create_revision(
                substance=substance,
                source_hash=source_hash,
                parse_result=parse_result,
                tenant_id=tenant_id,
                initial=True,
            )
            return UploadResult(
                outcome=UploadOutcome.NEW_SUBSTANCE,
                revision=revision,
                substance=substance,
                message=f"Neue Substanz: {substance.name}",
            )

        substance = identity.substance

        # ── Stufe 3: Versionserkennung ──
        from datetime import date

        revision_date_str = parse_result.get("revision_date")
        revision_date = None
        if revision_date_str:
            with contextlib.suppress(ValueError, TypeError):
                revision_date = date.fromisoformat(
                    revision_date_str,
                )

        version = self.version_detector.detect(
            substance=substance,
            revision_date=revision_date,
            version_number=parse_result.get(
                "version_number",
                "",
            ),
        )

        if version.outcome == VersionOutcome.CONFLICT:
            return UploadResult(
                outcome=UploadOutcome.CONFLICT,
                substance=substance,
                message=f"Versionskonflikt: {version.reason}",
            )

        # Neue Revision erstellen
        is_first = version.outcome == VersionOutcome.FIRST_REVISION
        revision = self._create_revision(
            substance=substance,
            source_hash=source_hash,
            parse_result=parse_result,
            tenant_id=tenant_id,
            initial=is_first,
        )

        # Supersession durchführen
        superseded_count = 0
        if version.outcome == VersionOutcome.NEW_REVISION and version.previous_revision:
            diff = self.diff_service.compute_diff(
                version.previous_revision,
                revision,
            )
            diff_record = self.diff_service.persist_diff(
                version.previous_revision,
                revision,
                diff,
            )
            superseded_count = self.supersession_service.supersede(
                version.previous_revision,
                revision,
                diff_record,
            )

        return UploadResult(
            outcome=UploadOutcome.NEW_REVISION,
            revision=revision,
            substance=substance,
            message=(f"Neue Revision für {substance.name}"),
            superseded_count=superseded_count,
        )

    def _create_revision(
        self,
        substance: GlobalSubstance,
        source_hash: str,
        parse_result: dict,
        tenant_id: str,
        initial: bool = False,
    ) -> GlobalSdsRevision:
        """Revision erstellen."""
        from datetime import date

        confidence = parse_result.get(
            "parse_confidence",
            0.0,
        )

        # Status basierend auf Konfidenz
        if initial and confidence >= GLOBAL_PROMOTION_THRESHOLD:
            status = GlobalSdsRevision.Status.VERIFIED
        else:
            status = GlobalSdsRevision.Status.PENDING

        revision_date = None
        rd_str = parse_result.get("revision_date")
        if rd_str:
            with contextlib.suppress(ValueError, TypeError):
                revision_date = date.fromisoformat(rd_str)

        revision = GlobalSdsRevision.objects.create(
            substance=substance,
            source_hash=source_hash,
            status=status,
            uploaded_by_tenant_id=tenant_id,
            manufacturer_name=parse_result.get(
                "manufacturer_name",
                "",
            ),
            product_name=parse_result.get(
                "product_name",
                "",
            ),
            revision_date=revision_date,
            version_number=parse_result.get(
                "version_number",
                "",
            ),
            signal_word=parse_result.get(
                "signal_word",
                "",
            ),
            flash_point_c=parse_result.get("flash_point_c"),
            ignition_temperature_c=parse_result.get(
                "ignition_temperature_c",
            ),
            lower_explosion_limit=parse_result.get(
                "lower_explosion_limit",
            ),
            upper_explosion_limit=parse_result.get(
                "upper_explosion_limit",
            ),
            parse_confidence=confidence,
            llm_corrections=parse_result.get(
                "llm_corrections",
                [],
            ),
        )

        logger.info(
            "Created revision %s for %s (status=%s)",
            revision.pk,
            substance.name,
            status,
        )
        return revision
