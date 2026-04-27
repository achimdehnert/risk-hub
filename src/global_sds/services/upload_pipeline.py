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
from django.core.files.base import ContentFile
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

        # ── Stufe 1b: PubChem-Anreicherung ──
        try:
            from global_sds.services.pubchem_service import PubChemEnrichmentService

            pubchem_svc = PubChemEnrichmentService()
            pubchem_result = pubchem_svc.enrich(parse_result)
            if pubchem_result.enriched:
                parse_result = pubchem_svc.merge_into_parse_result(parse_result, pubchem_result)
                logger.info(
                    "PubChem enriched CID=%s formula=%s",
                    pubchem_result.cid,
                    pubchem_result.molecular_formula,
                )
        except Exception as exc:
            logger.warning("PubChem enrichment skipped: %s", exc)

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
                pdf_bytes=pdf_bytes,
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
            pdf_bytes=pdf_bytes,
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
        pdf_bytes: bytes | None = None,
        initial: bool = False,
    ) -> GlobalSdsRevision:
        """Revision erstellen — Felder via sync_fields_from_raw_data() befüllen."""
        confidence = parse_result.get("parse_confidence", 0.0)

        # Status basierend auf Konfidenz
        if initial and confidence >= GLOBAL_PROMOTION_THRESHOLD:
            status = GlobalSdsRevision.Status.VERIFIED
        else:
            status = GlobalSdsRevision.Status.PENDING

        # Nur Pflichtfelder + Metadaten beim create() — restliche Felder via sync
        revision = GlobalSdsRevision(
            substance=substance,
            source_hash=source_hash,
            status=status,
            uploaded_by_tenant_id=tenant_id,
            pdf_file=ContentFile(pdf_bytes, name=f"{source_hash[:16]}.pdf") if pdf_bytes else None,
            raw_data=parse_result,
            llm_corrections=parse_result.get("llm_corrections", []),
            product_name=parse_result.get("product_name", "") or "",
        )

        # Alle raw_data-Felder typkonform in Modell-Spalten schreiben
        revision.sync_fields_from_raw_data(parse_result)
        revision.save()

        self._populate_ghs_relations(revision, parse_result)

        logger.info(
            "Created revision %s for %s (status=%s, h=%d, p=%d)",
            revision.pk,
            substance.name,
            status,
            revision.hazard_statements.count(),
            revision.precautionary_statements.count(),
        )
        return revision

    @staticmethod
    def _populate_ghs_relations(revision: GlobalSdsRevision, parse_result: dict) -> None:
        """Populate H/P-Statement and GHS pictogram M2M relations from parse_result.

        Uses get_or_create so the pipeline works even without pre-loaded CLP fixtures.
        The text_de placeholder will be overwritten once real fixtures are loaded.
        """
        from substances.models import (
            HazardStatementRef,
            PictogramRef,
            PrecautionaryStatementRef,
        )

        h_codes = parse_result.get("h_statements") or []
        p_codes = parse_result.get("p_statements") or []
        ghs_codes = parse_result.get("pictograms") or []

        h_refs = []
        for code in h_codes:
            ref, _ = HazardStatementRef.objects.get_or_create(
                code=code,
                defaults={"text_de": code, "text_en": ""},
            )
            h_refs.append(ref)
        if h_refs:
            revision.hazard_statements.set(h_refs)

        p_refs = []
        for code in p_codes:
            ref, _ = PrecautionaryStatementRef.objects.get_or_create(
                code=code,
                defaults={"text_de": code, "text_en": ""},
            )
            p_refs.append(ref)
        if p_refs:
            revision.precautionary_statements.set(p_refs)

        ghs_refs = []
        for code in ghs_codes:
            ref, _ = PictogramRef.objects.get_or_create(
                code=code,
                defaults={"name_de": code, "name_en": ""},
            )
            ghs_refs.append(ref)
        if ghs_refs:
            revision.pictograms.set(ghs_refs)
