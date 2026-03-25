"""
URL-Konfiguration: explosionsschutz

HTML-Views: /ex/
HTMX-Partials: /ex/…/htmx/…
"""
from django.urls import path

from . import views

app_name = "explosionsschutz"

urlpatterns = [
    # ── Dashboard & Listen ──────────────────────────────────────────────────
    path("", views.concept_list, name="concept-list"),

    # ── Wizard (5 Schritte) ─────────────────────────────────────────────────
    path("wizard/new/", views.wizard_create, name="wizard-create"),
    path("wizard/<uuid:pk>/step2/", views.wizard_step2, name="wizard-step2"),
    path("wizard/<uuid:pk>/step3/", views.wizard_step3, name="wizard-step3"),
    path("wizard/<uuid:pk>/step4/", views.wizard_step4, name="wizard-step4"),
    path("wizard/<uuid:pk>/step5/", views.wizard_step5, name="wizard-step5"),

    # ── Konzept Detail & Workflow ───────────────────────────────────────────
    path("concept/<uuid:pk>/", views.concept_detail, name="concept-detail"),
    path("concept/<uuid:pk>/approve/", views.concept_approve, name="concept-approve"),
    path("concept/<uuid:pk>/archive/", views.concept_archive, name="concept-archive"),
    path("concept/<uuid:pk>/progress/", views.concept_progress, name="concept-progress"),

    # ── HTMX: Zonen ────────────────────────────────────────────────────────
    path("concept/<uuid:pk>/zones/add/", views.zone_add, name="zone-add"),
    path(
        "concept/<uuid:pk>/zones/proposal/",
        views.zone_proposal_htmx,
        name="zone-proposal",
    ),

    # ── HTMX: Zündquellen ──────────────────────────────────────────────────
    path(
        "zone/<uuid:zone_pk>/ignition/",
        views.ignition_assessment,
        name="ignition-assessment",
    ),

    # ── HTMX: Maßnahmen ────────────────────────────────────────────────────
    path("concept/<uuid:pk>/measures/add/", views.measure_add, name="measure-add"),

    # ── Equipment ──────────────────────────────────────────────────────────
    path("equipment/", views.equipment_list, name="equipment-list"),
    path("equipment/<uuid:pk>/", views.equipment_detail, name="equipment-detail"),
    path(
        "equipment/<uuid:equipment_pk>/inspections/add/",
        views.inspection_record,
        name="inspection-record",
    ),
]
