"""Project services (ADR-041).

Service layer for project creation and KI module recommendation.
Views → services → models (Platform Architecture Rule).
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

from django.db import transaction

from projects.models import Project, ProjectModule

logger = logging.getLogger(__name__)

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
