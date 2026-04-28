"""Project services (ADR-041).

Service layer for project creation and KI module recommendation.
Views → services → models (Platform Architecture Rule).
"""

from __future__ import annotations

import json
import logging
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


def upload_project_document(
    tenant_id: UUID,
    project,
    file,
    doc_type: str = "other",
    uploaded_by=None,
):
    """Upload a single project document."""
    from projects.models import ProjectDocument

    title = file.name.rsplit(".", 1)[0] if "." in file.name else file.name
    doc = ProjectDocument.objects.create(
        tenant_id=tenant_id,
        project=project,
        title=title,
        doc_type=doc_type,
        file=file,
        uploaded_by=uploaded_by,
    )
    logger.info(
        "Uploaded document '%s' to project %s",
        file.name,
        project.name,
    )
    return doc


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
            "values_json",
            "is_ai_generated",
            "updated_at",
        ],
    )


# -----------------------------------------------------------------------
# LLM section content generation
# -----------------------------------------------------------------------


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

    prompt_parts = [
        f"Du bist ein Experte für {doc.kind or 'Arbeitsschutz'}-Dokumentation.",
        f"Projekt: {project.name}.",
        f"Dokument: {doc.title}.",
        f"Abschnitt: {section.title}.",
    ]
    if concept_context:
        prompt_parts.append(concept_context)
    prompt_parts.append(
        f"Aufgabe: {llm_hint or section.title}. "
        f"Schreibe einen fachlich korrekten, professionellen Text für diesen Abschnitt auf Deutsch. "
        f"Nutze die obigen Konzeptdaten wenn sie zum Abschnitt passen."
    )
    prompt = "\n".join(prompt_parts)

    try:
        from aifw.service import sync_completion

        result = sync_completion(
            "concept_prefill",
            messages=[{"role": "user", "content": prompt}],
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
