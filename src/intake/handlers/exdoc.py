from __future__ import annotations

import logging

logger = logging.getLogger(__name__)

EXDOC_DOC_TYPES = {"EXDOC", "EX_SCHUTZKONZEPT", "EXPLOSIONSSCHUTZDOKUMENT", "UNKNOWN"}


class ExDocIntakeHandler:
    target_code = "exdoc"
    label = "Ex-Schutzdokument anlegen/befüllen"
    icon = "file-text"

    def can_handle(self, doc_type: str) -> bool:
        return doc_type.upper() in EXDOC_DOC_TYPES

    def run(self, upload):  # type: ignore[override]
        from intake.models import IntakeResult
        from projects.models import OutputDocument

        # Find active output documents for this facility
        docs = OutputDocument.objects.filter(
            project__facility=upload.facility,
            status__in=["draft", "in_progress"],
        ).order_by("-created_at")

        if not docs.exists():
            return IntakeResult.objects.create(
                upload=upload,
                target_code=self.target_code,
                status=IntakeResult.STATUS_SKIPPED,
                error_message="Kein aktives Ex-Schutzdokument für diesen Betrieb gefunden.",
            )

        doc = docs.first()

        # Add uploaded file as project document source
        from projects.models import ProjectDocument
        proj_doc, _ = ProjectDocument.objects.get_or_create(
            project=doc.project,
            original_filename=upload.original_filename,
            defaults={
                "extracted_text": upload.extracted_text,
                "file": upload.file,
            },
        )
        if not proj_doc.extracted_text and upload.extracted_text:
            proj_doc.extracted_text = upload.extracted_text
            proj_doc.save(update_fields=["extracted_text"])

        return IntakeResult.objects.create(
            upload=upload,
            target_code=self.target_code,
            status=IntakeResult.STATUS_OK,
            result_id=doc.pk,
            result_url=f"/projects/output-documents/{doc.pk}/edit/",
        )
