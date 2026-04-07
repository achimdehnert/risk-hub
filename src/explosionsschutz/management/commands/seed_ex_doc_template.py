# src/explosionsschutz/management/commands/seed_ex_doc_template.py
"""
Idempotentes Seed-Kommando für das Standard-Explosionsschutzdokument-Template.

Erstellt ein ExDocTemplate mit der vollständigen Struktur gemäß
GefStoffV § 6 Abs. 9 / TRGS 720ff. Enthält KI-Unterstützung
(ai_enabled, ai_prompt, ai_sources) für fachliche Abschnitte.

Idempotent: Prüft ob Template mit gleichem Namen + tenant_id=NULL existiert.

Structure loaded from:
  fixtures/ex_doc_template_gefstoffv.json

Shared constants from:
  explosionsschutz.ex_doc_constants

Validation via (optional, graceful fallback):
  concept_templates.schemas.ConceptTemplate
"""

import json
import logging
from pathlib import Path

from django.core.management.base import BaseCommand

logger = logging.getLogger(__name__)

FIXTURE_DIR = Path(__file__).resolve().parent.parent.parent / "fixtures"
FIXTURE_FILE = FIXTURE_DIR / "ex_doc_template_gefstoffv.json"

TEMPLATE_NAME = "Explosionsschutzdokument gemäß GefStoffV § 6 Abs. 9"
TEMPLATE_DESCRIPTION = (
    "Standardvorlage für das Explosionsschutzdokument nach § 6 Abs. 9 GefStoffV "
    "in Verbindung mit TRGS 720ff. Enthält alle Pflichtkapitel sowie "
    "KI-Unterstützung für fachliche Inhalte."
)


def _load_structure() -> dict:
    """Load template structure from JSON fixture file."""
    if not FIXTURE_FILE.exists():
        raise FileNotFoundError(
            f"Fixture nicht gefunden: {FIXTURE_FILE}\nErwartet in: {FIXTURE_DIR}"
        )
    with open(FIXTURE_FILE, encoding="utf-8") as fh:
        data = json.load(fh)
    if "sections" not in data:
        raise ValueError(f"Fixture hat kein 'sections'-Feld: {FIXTURE_FILE}")
    return data


def _validate_structure(structure: dict) -> list[str]:
    """Validate structure against concept_templates schema (optional).

    Returns list of warning strings (empty = OK).
    Uses concept_templates.schemas if installed, else basic checks.
    """
    warnings = []
    from explosionsschutz.ex_doc_constants import (
        AI_SOURCE_TYPES,
        FIELD_TYPES,
    )

    sections = structure.get("sections", [])
    seen_keys = set()
    for si, section in enumerate(sections):
        skey = section.get("key", "")
        if not skey:
            warnings.append(f"Section {si}: fehlender 'key'")
        if skey in seen_keys:
            warnings.append(f"Section {si}: doppelter key '{skey}'")
        seen_keys.add(skey)

        for fi, field in enumerate(section.get("fields", [])):
            ftype = field.get("type", "textarea")
            if ftype not in FIELD_TYPES:
                warnings.append(f"Section '{skey}' Field {fi}: unbekannter Typ '{ftype}'")
            for src in field.get("ai_sources", []):
                if src not in AI_SOURCE_TYPES:
                    warnings.append(
                        f"Section '{skey}' Field '{field.get('key', fi)}': "
                        f"unbekannte AI-Quelle '{src}'"
                    )

    # Try concept_templates schema validation if available
    try:
        from concept_templates.schemas import (
            ConceptTemplate,
            FieldType,
            TemplateField,
            TemplateSection,
        )

        _type_map = {
            "textarea": FieldType.TEXTAREA,
            "text": FieldType.TEXT,
            "table": FieldType.TABLE,
        }
        ct_sections = []
        for i, s in enumerate(sections):
            ct_fields = []
            for f in s.get("fields", []):
                ft = _type_map.get(f.get("type"), FieldType.TEXTAREA)
                ct_fields.append(
                    TemplateField(
                        name=f["key"],
                        label=f.get("label", f["key"]),
                        field_type=ft,
                    )
                )
            ct_sections.append(
                TemplateSection(
                    name=s["key"],
                    title=s.get("label", f"Abschnitt {i + 1}"),
                    order=i + 1,
                    fields=ct_fields,
                )
            )
        ConceptTemplate(
            name=TEMPLATE_NAME,
            scope="explosionsschutz",
            version="1.0",
            sections=ct_sections,
        )
        logger.debug("concept_templates schema validation: OK")
    except ImportError:
        logger.debug("concept_templates not installed — skipping schema validation")
    except Exception as exc:
        warnings.append(f"concept_templates Validierung: {exc}")

    return warnings


class Command(BaseCommand):
    help = "Seed Standard-Explosionsschutzdokument-Template (GefStoffV § 6 Abs. 9, idempotent)"

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Nur anzeigen, was erstellt würde",
        )
        parser.add_argument(
            "--tenant-id",
            type=str,
            default=None,
            help=("Tenant-ID für das Template (default: settings.EX_DOC_SYSTEM_TENANT_ID)"),
        )
        parser.add_argument(
            "--skip-validation",
            action="store_true",
            help="Validierung überspringen",
        )

    def handle(self, *args, **options):
        from explosionsschutz.ex_doc_constants import SYSTEM_TENANT_ID
        from explosionsschutz.models import ExDocTemplate

        dry_run = options["dry_run"]
        tenant_id = options["tenant_id"] or SYSTEM_TENANT_ID
        prefix = "[DRY-RUN] " if dry_run else ""

        # Load structure from fixture
        try:
            structure = _load_structure()
        except (FileNotFoundError, ValueError, json.JSONDecodeError) as exc:
            self.stderr.write(self.style.ERROR(str(exc)))
            return

        # Validate
        if not options["skip_validation"]:
            warnings = _validate_structure(structure)
            for w in warnings:
                self.stderr.write(self.style.WARNING(f"  ⚠ {w}"))
            if warnings:
                self.stderr.write(
                    self.style.WARNING(
                        f"{len(warnings)} Validierungswarnung(en). "
                        f"Nutze --skip-validation zum Überspringen."
                    )
                )

        # Check idempotency
        existing = ExDocTemplate.objects.filter(
            tenant_id=tenant_id,
            name=TEMPLATE_NAME,
        ).first()

        if existing:
            self.stdout.write(
                self.style.WARNING(
                    f"{prefix}Template '{TEMPLATE_NAME}' existiert bereits "
                    f"(PK={existing.pk}, Status={existing.status}). "
                    f"Übersprungen."
                )
            )
            return

        sections = structure["sections"]
        total_fields = sum(len(s.get("fields", [])) for s in sections)
        ai_fields = sum(1 for s in sections for f in s.get("fields", []) if f.get("ai_enabled"))

        if dry_run:
            self.stdout.write(
                self.style.SUCCESS(
                    f"{prefix}Würde Template erstellen:\n"
                    f"  Name: {TEMPLATE_NAME}\n"
                    f"  Fixture: {FIXTURE_FILE.name}\n"
                    f"  Abschnitte: {len(sections)}\n"
                    f"  Felder: {total_fields}\n"
                    f"  KI-Felder: {ai_fields}\n"
                    f"  Tenant: {tenant_id}"
                )
            )
            return

        tmpl = ExDocTemplate.objects.create(
            tenant_id=tenant_id,
            name=TEMPLATE_NAME,
            description=TEMPLATE_DESCRIPTION,
            structure_json=json.dumps(
                structure,
                ensure_ascii=False,
            ),
            status=ExDocTemplate.Status.ACCEPTED,
        )

        logger.info(
            "Created Ex-Doc Template: %s (PK=%s)",
            TEMPLATE_NAME,
            tmpl.pk,
        )
        self.stdout.write(
            self.style.SUCCESS(
                f"Template '{TEMPLATE_NAME}' erstellt "
                f"(PK={tmpl.pk}, {tmpl.section_count} Abschnitte, "
                f"{tmpl.field_count} Felder)."
            )
        )
