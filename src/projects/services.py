"""Project services (ADR-041).

Service layer for project creation and KI module recommendation.
Views → services → models (Platform Architecture Rule).
"""

from __future__ import annotations

import json
import logging
import math
import re
from dataclasses import dataclass
from typing import Any
from uuid import UUID

from django.db import transaction

from projects.models import Project, ProjectModule

logger = logging.getLogger(__name__)


# -----------------------------------------------------------------------
# Site helpers
# -----------------------------------------------------------------------


def get_or_create_site(
    tenant_id: UUID,
    site_name: str,
    organization=None,
):
    """Resolve or auto-create a Site for a tenant."""
    from tenancy.models import Site

    site, created = Site.objects.get_or_create(
        tenant_id=tenant_id,
        name=site_name,
        defaults={"organization": organization},
    )
    if created:
        logger.info(
            "Auto-created Site '%s' for tenant %s",
            site_name,
            tenant_id,
        )
    return site, created


# -----------------------------------------------------------------------
# ProjectDocument CRUD
# -----------------------------------------------------------------------


def _extract_text_from_file(file) -> tuple[str, int | None]:
    """Extract plain text and page count from an uploaded file.

    Supports PDF (via pdfplumber) and plain text files.
    Returns (extracted_text, page_count).
    """
    name = getattr(file, "name", "")
    ext = name.rsplit(".", 1)[-1].lower() if "." in name else ""

    if ext == "pdf":
        try:
            import io
            import pdfplumber

            raw = file.read()
            file.seek(0)
            pages_text = []
            with pdfplumber.open(io.BytesIO(raw)) as pdf:
                page_count = len(pdf.pages)
                for page in pdf.pages:
                    text = page.extract_text() or ""
                    pages_text.append(text)
            return "\n\n".join(pages_text).strip(), page_count
        except Exception as exc:
            logger.warning("PDF extraction failed for '%s': %s", name, exc)
            return "", None

    if ext in {"docx"}:
        try:
            import io
            import docx as python_docx

            raw = file.read()
            file.seek(0)
            doc = python_docx.Document(io.BytesIO(raw))
            paragraphs = [p.text for p in doc.paragraphs if p.text.strip()]
            return "\n\n".join(paragraphs).strip(), None
        except Exception as exc:
            logger.warning("DOCX extraction failed for '%s': %s", name, exc)
            return "", None

    if ext in {"txt", "md", "csv"}:
        try:
            raw = file.read()
            file.seek(0)
            return raw.decode("utf-8", errors="replace").strip(), None
        except Exception:
            return "", None

    return "", None


_DOCTYPE_KEYWORDS: list[tuple[str, list[str]]] = [
    ("sds", [
        "sicherheitsdatenblatt", "safety data sheet", "gefährliche inhaltsstoffe",
        "h-satz", "p-satz", "ghs", "cas-nr", "physikalische und chemische eigenschaften",
        "abschnitt 1", "abschnitt 2", "chemische bezeichnung",
    ]),
    ("plan", [
        "grundriss", "lageplan", "anlagenplan", "schnittzeichnung", "draufsicht",
        "maßstab", "floor plan", "site plan", "zeichnungsnummer", "ex-zonen",
        "zoneneinteilung", "atex zone",
    ]),
    ("gutachten", [
        "gutachten", "prüfbericht", "sachverständiger", "beurteilung",
        "bewertung durch", "prüfzeichen", "zertifikat", "tüv", "dekra", "bericht nr",
    ]),
    ("regulation", [
        "trgs", "betriebssicherheitsverordnung", "betrsi", "din en", "iso ",
        "vde ", "dvgw", "norm", "regelwerk", "richtlinie", "gefstoffv",
        "bundesgesetzblatt", "vde-norm",
    ]),
    ("process", [
        "verfahrensbeschreibung", "ablaufbeschreibung", "prozessbeschreibung",
        "arbeitsanweisung", "betriebsanweisung", "sop ", "standard operating",
        "verfahrensanweisung", "prozessablauf",
    ]),
]


def detect_doc_type(extracted_text: str, filename: str = "") -> str:
    """Keyword-based automatic document type detection.

    Scores each DocType by keyword frequency — no LLM call needed.
    Returns DocType string or 'other' as fallback.
    """
    if not extracted_text:
        return "other"

    haystack = (extracted_text[:3000] + " " + filename).lower()
    scores: dict[str, int] = {}
    for doc_type, keywords in _DOCTYPE_KEYWORDS:
        score = sum(haystack.count(kw) for kw in keywords)
        if score:
            scores[doc_type] = score

    if not scores:
        return "other"
    return max(scores, key=scores.__getitem__)


def upload_project_document(
    tenant_id: UUID,
    project,
    file,
    doc_type: str = "other",
    uploaded_by=None,
):
    """Upload a single project document and extract its text content."""
    from projects.models import ProjectDocument

    title = file.name.rsplit(".", 1)[0] if "." in file.name else file.name
    extracted_text, page_count = _extract_text_from_file(file)

    if doc_type == "other" and extracted_text:
        doc_type = detect_doc_type(extracted_text, filename=file.name)

    doc = ProjectDocument.objects.create(
        tenant_id=tenant_id,
        project=project,
        title=title,
        doc_type=doc_type,
        file=file,
        uploaded_by=uploaded_by,
        extracted_text=extracted_text,
        page_count=page_count,
    )
    logger.info(
        "Uploaded document '%s' to project %s (pages=%s, chars=%s)",
        file.name,
        project.name,
        page_count,
        len(extracted_text),
    )

    if extracted_text and doc_type in {"plan", "other"}:
        _try_enrich_facility_from_document(project, extracted_text)

    return doc


def _try_enrich_facility_from_document(project, extracted_text: str) -> None:
    """Best-effort: extract facility fields from document text and patch the project's facility.

    Only fills empty fields — never overwrites existing values.
    Runs synchronously; move to Celery task if latency becomes an issue.
    """
    from tenancy.services import extract_facility_data_from_text

    try:
        data = extract_facility_data_from_text(extracted_text)
        if not data:
            return

        facility = getattr(project, "facility", None)
        if facility is None:
            logger.debug("No facility linked to project %s — skipping enrichment", project.pk)
            return

        update_fields = []
        field_map = {
            "name": "name",
            "code": "code",
            "facility_type": "facility_type",
            "description": "description",
        }
        for src_key, model_field in field_map.items():
            if src_key in data:
                current = getattr(facility, model_field, None)
                if not current or current in {"", "other"}:
                    setattr(facility, model_field, data[src_key])
                    update_fields.append(model_field)

        if update_fields:
            facility.save(update_fields=update_fields)
            logger.info(
                "Facility %s enriched from document: %s",
                facility.pk,
                update_fields,
            )
    except Exception as exc:
        logger.warning("Facility enrichment failed (non-fatal): %s", exc)


def delete_project_document(doc) -> None:
    """Delete a project document and its file."""
    doc.file.delete(save=False)
    doc.delete()


# -----------------------------------------------------------------------
# OutputDocument + sections
# -----------------------------------------------------------------------


@transaction.atomic
def create_output_document(
    tenant_id: UUID,
    project,
    template,
    title: str,
    created_by=None,
    imported_values: dict | None = None,
):
    """Create an OutputDocument with sections from a template."""
    from projects.models import DocumentSection, OutputDocument

    kind = getattr(template, "kind", None) or getattr(template, "scope", None) or "custom"
    doc = OutputDocument.objects.create(
        tenant_id=tenant_id,
        project=project,
        kind=kind,
        title=title,
        created_by=created_by,
    )

    imported_values = imported_values or {}

    for idx, section in enumerate(template.get_sections()):
        skey = section.get("key", f"s_{idx}")
        fields = section.get("fields", [])
        sec_values = imported_values.get(skey, {})

        content = ""
        for f in fields:
            if f.get("type") == "textarea" and not content:
                content = sec_values.get(f["key"], "")

        DocumentSection.objects.create(
            document=doc,
            section_key=skey,
            title=section.get("label", f"Abschnitt {idx + 1}"),
            order=idx,
            content=content,
            fields_json=json.dumps(
                fields,
                ensure_ascii=False,
            ),
            values_json=json.dumps(
                sec_values,
                ensure_ascii=False,
            ),
        )

    return doc


_HINTS_BATCH_SIZE = 10


def _generate_hints_batch(doc, sections: list, doc_kind: str, project_name: str) -> tuple[int, int]:
    """Run one LLM call for a batch of sections. Returns (hints_applied, content_applied)."""
    from ai_analysis.prompts import get_section_hints_messages
    from aifw.service import sync_completion

    messages = get_section_hints_messages({
        "doc_kind": doc_kind,
        "project_name": project_name,
        "doc_title": doc.title,
        "section_list": "\n".join(f"{i+1}. {s.title}" for i, s in enumerate(sections)),
    })
    result = sync_completion("concept_prefill", messages=messages)
    if not result.success:
        logger.warning("generate_section_hints batch failed: %s", result.error)
        return 0, 0

    hints_applied = content_applied = 0
    for line in result.content.strip().splitlines():
        line = line.strip()
        if not line.startswith("{"):
            continue
        try:
            entry = json.loads(line)
            nr = int(entry.get("nr", 0)) - 1
            if nr < 0 or nr >= len(sections):
                continue
            section = sections[nr]
            update_fields = []

            hints = (entry.get("hints") or "").strip()
            if hints:
                section.ai_context_hint = hints
                # Auto-generate editable ai_prompt from section title + hints
                section.ai_prompt = (
                    f"Schreibe den Abschnitt '{section.title}' basierend auf "
                    f"folgenden Quellen: {hints}. Schreibe fachlich korrekt und präzise auf Deutsch."
                )
                update_fields += ["ai_context_hint", "ai_prompt"]
                hints_applied += 1

            content = (entry.get("content") or "").strip()
            if content and entry.get("generic") and not section.content:
                section.content = content
                section.is_ai_generated = True
                update_fields += ["content", "is_ai_generated"]
                content_applied += 1

            if update_fields:
                section.save(update_fields=update_fields)

        except (json.JSONDecodeError, KeyError, ValueError):
            continue

    return hints_applied, content_applied


def generate_section_hints(doc) -> None:
    """LLM call(s) per document creation in batches of 10:
    1. Generates retrieval hints (keywords) → ai_context_hint
    2. Auto-generates editable ai_prompt per section
    3. Pre-fills generic sections with standard text → content
    Runs outside the create transaction — failures are non-fatal.
    """
    sections = list(doc.sections.filter(ai_context_hint="").select_related("document"))
    if not sections:
        return

    doc_kind = doc.kind or "Arbeitsschutz"
    project_name = getattr(getattr(doc, "project", None), "name", "unbekannt")

    try:
        from aifw.service import sync_completion  # noqa: F401 — ensure available

        total_hints = total_content = 0
        for i in range(0, len(sections), _HINTS_BATCH_SIZE):
            batch = sections[i: i + _HINTS_BATCH_SIZE]
            h, c = _generate_hints_batch(doc, batch, doc_kind, project_name)
            total_hints += h
            total_content += c

        logger.info(
            "Section init for doc %s: %d hints, %d generic pre-filled",
            doc.pk, total_hints, total_content,
        )
    except Exception as exc:
        logger.warning("generate_section_hints non-fatal error: %s", exc)


def _strip_section_prefix(title: str) -> str:
    """Remove leading letter/number prefix from a section title.

    'A. Angaben des...' -> 'Angaben des...'
    '3.2.1. Erstinertisierung...' -> 'Erstinertisierung...'
    '12. Maßnahmenplan...' -> 'Maßnahmenplan...'
    """
    return re.sub(r"^[A-Z0-9]+(?:\.[A-Z0-9]+)*\.?\s*", "", title).strip()


_HEADING_PREFIX_RE = re.compile(r"^[A-Z0-9]+(?:\.[A-Z0-9]*)*[\.\s]*$")


def _heading_at_line_start(text: str, idx: int) -> bool:
    """Return True if idx is at the start of a content heading line.

    Accepts:
      - Bare heading at actual line start: '\nAngaben des...'
      - Heading after a number/letter prefix: '\n1. Anlagenbeschreibung...'
        (prefix on the same line is only digits/letters/dots/spaces)
    """
    line_start = text.rfind("\n", 0, idx)
    line_start = line_start + 1 if line_start >= 0 else 0
    prefix = text[line_start:idx]
    return not prefix or bool(_HEADING_PREFIX_RE.match(prefix))


def _parse_document_sections(text: str, known_titles: list[str]) -> dict[str, str]:
    """Extract section content from an extracted document text.

    For each known_title, finds its content heading (distinct from TOC entries
    which are followed by a tab + page number).
    Returns {bare_title: content_text}.
    """
    result: dict[str, str] = {}

    # Build sorted list of (line_start, bare_idx, bare_title) for content headings only.
    # line_start points to the beginning of the full heading line (incl. number prefix like '5. ').
    heading_positions: list[tuple[int, int, str]] = []
    for title in known_titles:
        bare = _strip_section_prefix(title)
        if not bare:
            continue
        pos = 0
        while True:
            idx = text.find(bare, pos)
            if idx < 0:
                break
            rest = text[idx + len(bare):]
            # Content heading: followed by \n (allow trailing spaces; \t = TOC separator)
            rest_stripped = rest.lstrip(" ")
            after_is_newline = rest_stripped.startswith("\n") or rest_stripped == ""
            if _heading_at_line_start(text, idx) and after_is_newline:
                # line_start: beginning of the full line (before any '5. ' prefix)
                ls = text.rfind("\n", 0, idx)
                line_start = ls + 1 if ls >= 0 else 0
                heading_positions.append((line_start, idx, bare))
                break
            pos = idx + 1

    # Sort by position in document
    heading_positions.sort(key=lambda x: x[0])

    # Extract content between consecutive headings
    for i, (line_start, pos, bare) in enumerate(heading_positions):
        content_start = pos + len(bare)
        # Skip whitespace/newlines directly after heading
        while content_start < len(text) and text[content_start] in ("\n", "\r", " "):
            content_start += 1
        # Content ends at the LINE start of the next heading (incl. its number prefix)
        if i + 1 < len(heading_positions):
            content_end = heading_positions[i + 1][0]  # line_start of next heading
        else:
            content_end = len(text)
        content = text[content_start:content_end].strip()
        # Skip trivial content like "3" or "3.1" (just a next-section number)
        if content and not re.match(r"^[0-9]+(?:\.[0-9]+)*\.?\s*$", content):
            result[bare] = content

    return result


def prefill_sections_from_documents(doc, force: bool = False) -> int:
    """Fill sections directly from the text of uploaded project documents.

    Strategy (in priority order):
    1. Direct section matching: find headings matching the section title in the
       uploaded document text and extract the content between consecutive headings.
       Works best with structure documents (Explosionsschutzdokument, concepts).
    2. Fallback keyword search for sections not found via direct matching.

    force=False (default, auto): only fills empty sections.
    force=True (manual re-fill): overwrites all sections including non-empty ones.
    Returns the number of sections filled.
    """
    from projects.models import ProjectDocument

    qs = doc.sections.all() if force else doc.sections.filter(content="")
    sections = list(qs)
    if not sections:
        return 0

    project = doc.project
    uploaded_docs = list(
        ProjectDocument.objects.filter(project=project)
        .exclude(extracted_text="")
        .values("title", "doc_type", "extracted_text")
    )
    if not uploaded_docs:
        return 0

    section_titles = [s.title for s in sections]

    # --- Pass 1: Direct section matching (structure documents) ---
    section_map: dict[str, str] = {}  # bare_title -> content
    for uploaded in uploaded_docs:
        parsed = _parse_document_sections(uploaded["extracted_text"], section_titles)
        for bare, content in parsed.items():
            if bare not in section_map:  # First match wins
                section_map[bare] = content

    # --- Fill sections ---
    filled = 0
    for section in sections:
        bare = _strip_section_prefix(section.title)
        content_text = section_map.get(bare, "")

        # --- Pass 2 fallback: keyword search if no direct match ---
        if not content_text:
            hint = section.ai_context_hint or ""
            keywords = (
                [k.strip().lower() for k in hint.replace(",", " ").split() if len(k.strip()) > 2]
                if hint else _keywords_from_title(section.title)
            )
            best_score = 0
            for d in uploaded_docs:
                text_lower = d["extracted_text"].lower()
                score = sum(text_lower.count(kw) for kw in keywords)
                if score > best_score:
                    best_score = score
                    content_text = _extract_relevant_paragraphs(
                        d["extracted_text"], keywords, max_chars=1500
                    )
            if not best_score:
                content_text = ""

        if not content_text:
            continue

        update_fields = ["content", "is_ai_generated"]
        section.content = content_text
        section.is_ai_generated = False

        if section.fields_json and section.fields_json not in ("[]", "", None):
            try:
                fields = json.loads(section.fields_json)
                values = json.loads(section.values_json or "{}")
                for f in fields:
                    fkey = f.get("key", "")
                    if f.get("type") in ("textarea", None) and fkey:
                        if force or not values.get(fkey):
                            values[fkey] = content_text
                section.values_json = json.dumps(values, ensure_ascii=False)
                update_fields.append("values_json")
            except (json.JSONDecodeError, KeyError):
                pass

        section.save(update_fields=update_fields)
        filled += 1

    logger.info("prefill_sections_from_documents: %d/%d sections filled for doc %s", filled, len(sections), doc.pk)
    return filled


def delete_document_section(section) -> None:
    """Delete a single DocumentSection from an output document."""
    section.delete()


# Known modules with display metadata
AVAILABLE_MODULES: dict[str, dict] = {
    "explosionsschutz": {
        "label": "Explosionsschutz",
        "icon": "zap",
        "description": "Zoneneinteilung, Betriebsmittel, Ex-Konzepte, Schutzmaßnahmen",
        "keywords": [
            "explosion",
            "ex-schutz",
            "zone",
            "atex",
            "lösungsmittel",
            "gas",
            "dampf",
            "staub",
            "zündquelle",
            "lackier",
            "tank",
            "abfüll",
            "chemie",
            "brennbar",
            "explosionsfähig",
        ],
    },
    "substances": {
        "label": "Gefahrstoffe & SDS",
        "icon": "flask-conical",
        "description": "Stoffidentifikation, Sicherheitsdatenblätter, H/P-Sätze",
        "keywords": [
            "gefahrstoff",
            "sds",
            "sicherheitsdatenblatt",
            "stoff",
            "chemikalie",
            "lösungsmittel",
            "giftig",
            "ätzend",
            "h-sätze",
            "ethanol",
            "toluol",
            "aceton",
            "isopropanol",
            "lackier",
        ],
    },
    "gbu": {
        "label": "Gefährdungsbeurteilung (GBU)",
        "icon": "clipboard-check",
        "description": "Gefährdungsbeurteilung pro Tätigkeit und Arbeitsplatz",
        "keywords": [
            "gefährdung",
            "gbu",
            "tätigkeit",
            "arbeitsplatz",
            "exposition",
            "gesundheit",
            "arbeitssicherheit",
            "schutzausrüstung",
            "psa",
            "gefahr",
            "risiko",
            "unfall",
        ],
    },
    "brandschutz": {
        "label": "Brandschutz",
        "icon": "flame",
        "description": "Feuerlöscher, Fluchtwege, Brandschutznachweis",
        "keywords": [
            "brand",
            "feuer",
            "feuerlöscher",
            "fluchtweg",
            "rauchmelder",
            "sprinkler",
            "brandschutz",
            "evakuierung",
            "notausgang",
            "brennbar",
            "entzündlich",
            "lackier",
        ],
    },
    "risk": {
        "label": "Risikobewertung",
        "icon": "shield-alert",
        "description": "Gesamtrisikobewertung und Maßnahmenplanung",
        "keywords": [
            "risiko",
            "bewertung",
            "assessment",
            "maßnahme",
            "eintrittswahrscheinlichkeit",
            "schadensausmaß",
        ],
    },
}


@dataclass
class ModuleRecommendation:
    """KI-Empfehlung für ein Modul."""

    module: str
    label: str
    icon: str
    recommended: bool
    reason: str
    subscribed: bool


def recommend_modules_from_description(
    description: str,
    subscribed_modules: set[str],
) -> list[ModuleRecommendation]:
    """Recommend modules based on project description.

    Phase 1: Keyword-based matching.
    Phase 2+: LLM-based analysis via aifw.service.sync_completion.
    """
    if not description.strip():
        return [
            ModuleRecommendation(
                module=code,
                label=meta["label"],
                icon=meta["icon"],
                recommended=False,
                reason="",
                subscribed=code in subscribed_modules,
            )
            for code, meta in AVAILABLE_MODULES.items()
        ]

    desc_lower = description.lower()
    results = []

    for code, meta in AVAILABLE_MODULES.items():
        matched_keywords = [kw for kw in meta["keywords"] if kw in desc_lower]
        recommended = len(matched_keywords) >= 1

        if recommended:
            reason = f"Erkannt: {', '.join(matched_keywords[:3])} → {meta['description']}"
        else:
            reason = ""

        results.append(
            ModuleRecommendation(
                module=code,
                label=meta["label"],
                icon=meta["icon"],
                recommended=recommended,
                reason=reason,
                subscribed=code in subscribed_modules,
            )
        )

    return results


def get_subscribed_modules(tenant_id) -> set[str]:
    """Get set of subscribed module codes for a tenant."""
    try:
        from django_tenancy.module_models import ModuleSubscription

        return set(
            ModuleSubscription.objects.filter(
                tenant_id=tenant_id,
                status__in=["trial", "active"],
            ).values_list("module", flat=True)
        )
    except Exception:
        logger.warning("Could not fetch module subscriptions")
        return set(AVAILABLE_MODULES.keys())


@dataclass
class CreateProjectCmd:
    """Command to create a new project."""

    tenant_id: str
    site_id: str
    name: str
    description: str = ""
    project_number: str = ""
    client_name: str = ""
    created_by_id: int | None = None
    selected_modules: list[str] | None = None
    declined_modules: list[str] | None = None
    module_recommendations: list[ModuleRecommendation] | None = None


@transaction.atomic
def create_project(cmd: CreateProjectCmd) -> Project:
    """Create a project with module assignments."""
    project = Project.objects.create(
        tenant_id=cmd.tenant_id,
        site_id=cmd.site_id,
        name=cmd.name,
        description=cmd.description,
        project_number=cmd.project_number,
        client_name=cmd.client_name,
        created_by_id=cmd.created_by_id,
    )

    recommendations_by_module = {}
    if cmd.module_recommendations:
        recommendations_by_module = {r.module: r for r in cmd.module_recommendations}

    for mod_code in cmd.selected_modules or []:
        rec = recommendations_by_module.get(mod_code)
        ProjectModule.objects.create(
            project=project,
            module=mod_code,
            status=ProjectModule.Status.ACTIVE,
            is_ai_recommended=rec.recommended if rec else False,
            ai_reason=rec.reason if rec else "",
            activated_by_id=cmd.created_by_id,
        )

    for mod_code in cmd.declined_modules or []:
        rec = recommendations_by_module.get(mod_code)
        ProjectModule.objects.create(
            project=project,
            module=mod_code,
            status=ProjectModule.Status.DECLINED,
            is_ai_recommended=rec.recommended if rec else False,
            ai_reason=rec.reason if rec else "",
            activated_by_id=cmd.created_by_id,
        )

    logger.info(
        "Project created: %s (modules: %s, declined: %s)",
        project.name,
        cmd.selected_modules,
        cmd.declined_modules,
    )
    return project


# -----------------------------------------------------------------------
# Project detail helpers
# -----------------------------------------------------------------------


def get_project_module_details(project: Project) -> list[dict]:
    """Return enriched module metadata for a project's active modules."""
    active_modules = project.modules.filter(status="active")
    details = []
    for pm in active_modules:
        meta = AVAILABLE_MODULES.get(pm.module, {})
        details.append(
            {
                "code": pm.module,
                "label": meta.get("label", pm.module),
                "icon": meta.get("icon", "box"),
                "description": meta.get("description", ""),
            }
        )
    return details


# -----------------------------------------------------------------------
# Section value persistence
# -----------------------------------------------------------------------


def save_section_values(
    section: Any,
    post_data: dict[str, Any],
) -> None:
    """Parse form data and save section field values.

    Extracts structured field values (text, table, boolean) from POST data
    and persists them on the DocumentSection.
    """
    section.content = post_data.get("content", "")
    section.is_ai_generated = False
    ai_prompt_val = post_data.get("ai_prompt", "")
    if ai_prompt_val:
        section.ai_prompt = ai_prompt_val

    try:
        fields = json.loads(section.fields_json or "[]")
    except (json.JSONDecodeError, TypeError):
        fields = []

    values = {}
    for field in fields:
        fkey = field["key"]
        ftype = field.get("type", "textarea")
        form_key = f"{section.section_key}__{fkey}"

        if ftype == "table":
            columns = field.get("columns", [])
            rows = []
            row_idx = 0
            while True:
                row = []
                found = False
                for ci in range(len(columns)):
                    cell_key = f"{form_key}__row_{row_idx}__col_{ci}"
                    val = post_data.get(cell_key, "")
                    if val:
                        found = True
                    row.append(val)
                if not found:
                    break
                rows.append(row)
                row_idx += 1
            values[fkey] = rows
        elif ftype == "boolean":
            values[fkey] = post_data.get(form_key, "false")
        else:
            val = post_data.get(form_key, "")
            values[fkey] = val
            if ftype == "textarea" and val and not section.content:
                section.content = val

    section.values_json = json.dumps(
        values,
        ensure_ascii=False,
    )
    section.save(
        update_fields=[
            "content",
            "ai_prompt",
            "values_json",
            "is_ai_generated",
            "updated_at",
        ],
    )


# -----------------------------------------------------------------------
# LLM section content generation
# -----------------------------------------------------------------------


_DE_STOPWORDS = frozenset({
    "und", "der", "die", "das", "des", "dem", "den", "ein", "eine", "einer",
    "für", "mit", "von", "bei", "nach", "aus", "ist", "sind", "wird", "werden",
    "im", "am", "an", "auf", "in", "zu", "zum", "zur", "als", "noch", "nicht",
    "über", "unter", "sowie", "oder", "aber", "auch", "noch", "durch",
})


def _keywords_from_title(title: str) -> list[str]:
    """Derive search keywords from a section title by tokenizing and filtering stopwords.

    Replaces the old hardcoded _SECTION_KEYWORDS map — works for any section title.
    When ai_context_hint is available it takes priority over this fallback.
    """
    words = re.sub(r"[^a-zA-ZäöüÄÖÜß\s]", " ", title.lower()).split()
    return [w for w in words if len(w) > 3 and w not in _DE_STOPWORDS]



_TOC_PATTERN = re.compile(
    r"\.{3,}|"          # dots like "Kapitel......... 5"
    r"\s{3,}\d+\s*$|"   # trailing spaces + page number
    r"^\d+[\.\d]*\s+\S+.{0,40}$"  # short heading: "3.2.1 Title"
)


def _is_toc_line(para: str) -> bool:
    """Return True if paragraph looks like a table-of-contents entry (not real content)."""
    if len(para) < 80 and _TOC_PATTERN.search(para):
        return True
    return False


def _extract_relevant_paragraphs(text: str, keywords: list[str], max_chars: int = 1200) -> str:
    """Return content-rich paragraphs from text that contain at least one keyword.

    Improvements over naïve line splitting:
    - Prefers double-newline paragraphs (real paragraph boundaries)
    - Filters out table-of-contents entries (trailing page numbers, dot chains)
    - Scores by keyword density × paragraph length (favours informative content)
    - Falls back to single-line split when no double-newline paragraphs exist
    """
    kw_lower = [k.lower() for k in keywords]

    def _score_and_collect(candidates: list[str]) -> list[tuple[float, str]]:
        result = []
        for para in candidates:
            para = para.strip()
            if len(para) < 60 or _is_toc_line(para):
                continue
            para_lower = para.lower()
            kw_hits = sum(para_lower.count(kw) for kw in kw_lower)
            if kw_hits:
                # Length bonus: log(len) ensures longer paragraphs rank higher at equal keyword density
                result.append((kw_hits * math.log(max(len(para), 1)), para))
        return result

    # Try paragraph-level split first
    double_split = [p for p in text.split("\n\n") if p.strip()]
    scored = _score_and_collect(double_split)

    # Fall back to line-level split if no matches
    if not scored:
        line_split = [p for p in text.split("\n") if p.strip()]
        scored = _score_and_collect(line_split)

    scored.sort(key=lambda x: -x[0])
    result_parts, total = [], 0
    for _, para in scored:
        if total + len(para) > max_chars:
            break
        result_parts.append(para)
        total += len(para)

    if not result_parts:
        # Last resort: first 3 non-TOC paragraphs
        fallback = [p.strip() for p in text.split("\n\n") if len(p.strip()) > 80 and not _is_toc_line(p.strip())]
        result_parts = fallback[:3]

    return "\n\n".join(result_parts)


def _build_documents_context(project, section_title: str = "", ai_context_hint: str = "") -> str:
    """Liefert abschnittsspezifisch gefilterte Textauszüge aus hochgeladenen Dokumenten."""
    try:
        from projects.models import ProjectDocument

        all_docs = ProjectDocument.objects.filter(project=project).values(
            "title", "doc_type", "extracted_text"
        )[:10]
        if not all_docs:
            return ""

        if ai_context_hint:
            keywords = [k.strip() for k in ai_context_hint.replace(",", " ").split() if len(k.strip()) > 2]
        else:
            keywords = _keywords_from_title(section_title) if section_title else []

        parts = ["Relevante Auszüge aus Projektunterlagen:"]
        for d in all_docs:
            try:
                label = ProjectDocument.DocType(d["doc_type"]).label
            except ValueError:
                label = "Unterlage"
            text = (d["extracted_text"] or "").strip()
            if text:
                snippet = _extract_relevant_paragraphs(text, keywords, max_chars=900)
                if snippet:
                    parts.append(f"\n[{label}: {d['title']}]\n{snippet}")
            # Dokumente ohne Text werden nicht erwähnt — sparen Tokens
        return "\n".join(parts) if len(parts) > 1 else ""
    except Exception:
        return ""


def _build_concept_context(project) -> str:
    """Serialisiert Zonen und Maßnahmen des verknüpften ExplosionConzepts als Prompt-Kontext."""
    try:
        concept = project.explosion_concepts.select_related().prefetch_related(
            "zones", "measures"
        ).first()
        if not concept:
            return ""
        parts = [f"Verknüpftes Explosionsschutzkonzept: {concept.title}"]
        zones = concept.zones.all()
        if zones:
            parts.append("Zonen:")
            for z in zones:
                desc = z.justification or z.description or ""
                parts.append(f"  - {z.name} (Typ {z.zone_type}): {desc[:200]}")
        measures = concept.measures.all()
        if measures:
            parts.append("Schutzmaßnahmen:")
            for m in measures[:10]:
                parts.append(f"  - {m.title}: {str(m.description or '')[:150]}")
        return "\n".join(parts)
    except Exception:
        return ""


def generate_section_content(
    *,
    section: Any,
    field_key: str = "",
    llm_hint: str = "",
) -> str:
    """Generate AI content for a document section field.

    Uses aifw.service.sync_completion for LLM generation.
    If project has a linked ExplosionConcept, its zones/measures are passed as context.
    Returns generated text content.
    """
    doc = section.document
    project = doc.project
    concept_context = _build_concept_context(project)
    hint = getattr(section, "ai_context_hint", "") or ""
    documents_context = _build_documents_context(
        project, section_title=section.title, ai_context_hint=hint
    )

    existing_content = (section.content or "").strip()
    if field_key:
        try:
            values = json.loads(section.values_json or "{}")
            existing_content = (values.get(field_key) or existing_content).strip()
        except (json.JSONDecodeError, KeyError):
            pass

    improve_mode = bool(existing_content)

    from ai_analysis.prompts import get_section_generate_messages, get_section_improve_messages

    task = llm_hint or section.title
    ctx = {
        "doc_kind": doc.kind or "Arbeitsschutz",
        "project_name": project.name,
        "doc_title": doc.title,
        "section_title": section.title,
        "task_hint": task,
        "documents_context": documents_context,
        "concept_context": concept_context,
    }
    if improve_mode:
        ctx["existing_content"] = existing_content[:1500]
        messages = get_section_improve_messages(ctx)
    else:
        messages = get_section_generate_messages(ctx)

    try:
        from aifw.service import sync_completion

        result = sync_completion(
            "concept_prefill",
            messages=messages,
        )
        return result.content if result.success else f"[KI-Fehler: {result.error}]"
    except ImportError:
        logger.warning("aifw not available for LLM prefill")
        return f"[KI nicht verfügbar — bitte manuell ausfüllen: {section.title}]"
    except Exception as exc:
        logger.exception("LLM prefill failed: %s", exc)
        return f"[Fehler bei KI-Generierung: {exc}]"


# -----------------------------------------------------------------------
# PDF rendering
# -----------------------------------------------------------------------


def render_document_html(doc: Any) -> str:
    """Render an OutputDocument to HTML suitable for PDF export.

    Returns full HTML string with styling.
    """
    sections = doc.sections.all()

    html_parts = [
        f"<h1>{doc.title}</h1>",
        f"<p><small>Version {doc.version} · "
        f"{doc.get_status_display()} · "
        f"{doc.updated_at.strftime('%d.%m.%Y')}</small></p>",
    ]

    for section in sections:
        html_parts.append(f"<h2>{section.title}</h2>")

        try:
            fields = json.loads(section.fields_json or "[]")
            values = json.loads(section.values_json or "{}")
        except (json.JSONDecodeError, TypeError):
            fields = []
            values = {}

        if fields:
            for field in fields:
                fkey = field["key"]
                ftype = field.get("type", "textarea")
                val = values.get(fkey, "")

                if ftype == "table" and isinstance(val, list):
                    cols = field.get("columns", [])
                    if cols and val:
                        html_parts.append(
                            "<table border='1' cellpadding='4' "
                            "cellspacing='0' style='border-collapse:"
                            "collapse; width:100%; font-size:10pt;'>"
                        )
                        html_parts.append("<thead><tr>")
                        for c in cols:
                            html_parts.append(f"<th style='background:#f0f0f0'>{c}</th>")
                        html_parts.append("</tr></thead><tbody>")
                        for row in val:
                            html_parts.append("<tr>")
                            for cell in row:
                                html_parts.append(f"<td>{cell}</td>")
                            html_parts.append("</tr>")
                        html_parts.append("</tbody></table>")
                elif val:
                    html_parts.append(f"<p>{str(val).replace(chr(10), '<br>')}</p>")
        elif section.content:
            html_parts.append(f"<p>{section.content.replace(chr(10), '<br>')}</p>")

    return (
        "<!DOCTYPE html><html><head>"
        "<meta charset='utf-8'>"
        "<style>"
        "body{font-family:Arial,sans-serif;font-size:11pt;"
        "line-height:1.5;margin:2cm;}"
        "h1{font-size:18pt;color:#1a1a1a;}"
        "h2{font-size:14pt;color:#333;margin-top:1.5em;border-bottom:"
        "1px solid #ddd;padding-bottom:4px;}"
        "table{margin:0.5em 0;}"
        "</style></head><body>" + "\n".join(html_parts) + "</body></html>"
    )


def export_document_pdf(doc: Any) -> bytes | None:
    """Generate PDF bytes for an OutputDocument.

    Returns PDF bytes or None if WeasyPrint is unavailable.
    """
    html = render_document_html(doc)
    try:
        import weasyprint

        return weasyprint.HTML(string=html).write_pdf()
    except (ImportError, OSError) as exc:
        logger.warning("WeasyPrint not available: %s", exc)
        return None


# ---------------------------------------------------------------------------
# Query helpers (ADR-041)
# ---------------------------------------------------------------------------


def get_projects(tenant_id):
    """Return Project queryset for a tenant."""
    from projects.models import Project

    return Project.objects.filter(tenant_id=tenant_id)


def get_tenant_sites(tenant_id):
    """Return Sites for a tenant."""
    from tenancy.models import Site

    return Site.objects.filter(tenant_id=tenant_id)


def get_active_document_templates(tenant_id):
    """Return non-archived DocumentTemplates for a tenant (from doc_templates app)."""
    from django.apps import apps

    DocTemplate = apps.get_model("doc_templates", "DocumentTemplate")
    return (
        DocTemplate.objects.filter(tenant_id=tenant_id)
        .exclude(status="archived")
        .order_by("scope", "name")
    )


def get_output_documents(tenant_id):
    """Return OutputDocuments for a tenant."""
    from projects.models import OutputDocument

    return OutputDocument.objects.filter(tenant_id=tenant_id)
