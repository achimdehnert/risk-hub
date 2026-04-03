"""Project services (ADR-041).

Service layer for project creation and KI module recommendation.
Views → services → models (Platform Architecture Rule).
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
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
    from projects.models import Site

    site, created = Site.objects.get_or_create(
        tenant_id=tenant_id,
        name=site_name,
        defaults={"organization": organization},
    )
    if created:
        logger.info(
            "Auto-created Site '%s' for tenant %s",
            site_name, tenant_id,
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

    title = (
        file.name.rsplit(".", 1)[0]
        if "." in file.name
        else file.name
    )
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
        file.name, project.name,
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

    doc = OutputDocument.objects.create(
        tenant_id=tenant_id,
        project=project,
        template=template,
        kind=template.kind or "custom",
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
                fields, ensure_ascii=False,
            ),
            values_json=json.dumps(
                sec_values, ensure_ascii=False,
            ),
        )

    return doc


# -----------------------------------------------------------------------
# DocumentTemplate CRUD
# -----------------------------------------------------------------------


def create_template(
    tenant_id: UUID,
    name: str,
    kind: str = "",
    description: str = "",
    structure: dict | None = None,
    source_filename: str = "",
    source_text: str = "",
):
    """Create a DocumentTemplate."""
    from projects.models import DocumentTemplate

    structure = structure or {"sections": []}
    tmpl = DocumentTemplate.objects.create(
        tenant_id=tenant_id,
        name=name,
        kind=kind,
        description=description,
        structure_json=json.dumps(
            structure, ensure_ascii=False,
        ),
        source_filename=source_filename,
        source_text=source_text[:50000] if source_text else "",
    )
    return tmpl


def update_template(
    tmpl,
    structure: dict,
    name: str | None = None,
    description: str | None = None,
    status: str | None = None,
) -> None:
    """Update a DocumentTemplate's structure and metadata."""
    from projects.models import DocumentTemplate

    tmpl.structure_json = json.dumps(
        structure, ensure_ascii=False,
    )
    if name is not None:
        tmpl.name = name
    if description is not None:
        tmpl.description = description
    if status and status in dict(DocumentTemplate.Status.choices):
        tmpl.status = status
    tmpl.save()


def delete_template(tmpl) -> None:
    """Delete a DocumentTemplate."""
    tmpl.delete()


# Known modules with display metadata
AVAILABLE_MODULES: dict[str, dict] = {
    "explosionsschutz": {
        "label": "Explosionsschutz",
        "icon": "zap",
        "description": "Zoneneinteilung, Betriebsmittel, Ex-Konzepte, Schutzmaßnahmen",
        "keywords": [
            "explosion", "ex-schutz", "zone", "atex", "lösungsmittel",
            "gas", "dampf", "staub", "zündquelle", "lackier",
            "tank", "abfüll", "chemie", "brennbar", "explosionsfähig",
        ],
    },
    "substances": {
        "label": "Gefahrstoffe & SDS",
        "icon": "flask-conical",
        "description": "Stoffidentifikation, Sicherheitsdatenblätter, H/P-Sätze",
        "keywords": [
            "gefahrstoff", "sds", "sicherheitsdatenblatt", "stoff",
            "chemikalie", "lösungsmittel", "giftig", "ätzend", "h-sätze",
            "ethanol", "toluol", "aceton", "isopropanol", "lackier",
        ],
    },
    "gbu": {
        "label": "Gefährdungsbeurteilung (GBU)",
        "icon": "clipboard-check",
        "description": "Gefährdungsbeurteilung pro Tätigkeit und Arbeitsplatz",
        "keywords": [
            "gefährdung", "gbu", "tätigkeit", "arbeitsplatz", "exposition",
            "gesundheit", "arbeitssicherheit", "schutzausrüstung", "psa",
            "gefahr", "risiko", "unfall",
        ],
    },
    "brandschutz": {
        "label": "Brandschutz",
        "icon": "flame",
        "description": "Feuerlöscher, Fluchtwege, Brandschutznachweis",
        "keywords": [
            "brand", "feuer", "feuerlöscher", "fluchtweg", "rauchmelder",
            "sprinkler", "brandschutz", "evakuierung", "notausgang",
            "brennbar", "entzündlich", "lackier",
        ],
    },
    "risk": {
        "label": "Risikobewertung",
        "icon": "shield-alert",
        "description": "Gesamtrisikobewertung und Maßnahmenplanung",
        "keywords": [
            "risiko", "bewertung", "assessment", "maßnahme",
            "eintrittswahrscheinlichkeit", "schadensausmaß",
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
        matched_keywords = [
            kw for kw in meta["keywords"] if kw in desc_lower
        ]
        recommended = len(matched_keywords) >= 1

        if recommended:
            reason = (
                f"Erkannt: {', '.join(matched_keywords[:3])} "
                f"→ {meta['description']}"
            )
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
        recommendations_by_module = {
            r.module: r for r in cmd.module_recommendations
        }

    for mod_code in (cmd.selected_modules or []):
        rec = recommendations_by_module.get(mod_code)
        ProjectModule.objects.create(
            project=project,
            module=mod_code,
            status=ProjectModule.Status.ACTIVE,
            is_ai_recommended=rec.recommended if rec else False,
            ai_reason=rec.reason if rec else "",
            activated_by_id=cmd.created_by_id,
        )

    for mod_code in (cmd.declined_modules or []):
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
