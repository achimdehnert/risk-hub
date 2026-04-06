# src/explosionsschutz/ex_doc_constants.py
"""
Shared constants for the Ex-Dokument template system.

Single source of truth for:
- AI context source types and labels
- Field type definitions
- System tenant ID

Used by: seed command, doc_template_views, edit.html (via context).
"""

from django.conf import settings

# ── System Tenant ────────────────────────────────────────────
SYSTEM_TENANT_ID = getattr(
    settings, "EX_DOC_SYSTEM_TENANT_ID",
    "00000000-0000-0000-0000-000000000000",
)

# ── AI Context Source Types ──────────────────────────────────
# key → (short_label, full_label)
AI_SOURCE_TYPES: dict[str, tuple[str, str]] = {
    "sds": ("SDS", "Sicherheitsdatenblätter (SDS)"),
    "bedienungsanleitung": ("Bedienungsanl.", "Bedienungsanleitungen"),
    "standortdaten": ("Standortdaten", "Standort- und Gebäudedaten"),
    "cad": ("CAD", "CAD-Zeichnungen / Anlagenpläne"),
    "zonenplan": ("Zonenpläne", "Zonenpläne / Ex-Zonen"),
    "gefaehrdungsbeurteilung": ("GBU", "Gefährdungsbeurteilungen"),
    "betriebsanweisung": ("Betriebsanw.", "Betriebsanweisungen"),
    "pruefbericht": ("Prüfberichte", "Prüfberichte / Protokolle"),
    "rechtliche_grundlagen": ("Normen", "Rechtliche Grundlagen / Normen"),
    "wartungsplan": ("Wartungsplan", "Wartungs- und Instandhaltungspläne"),
    "risikobewertung": ("Risikobew.", "Risikobewertungen"),
    "brandschutz": ("Brandschutz", "Brandschutzkonzepte"),
}

# ── Field Type Definitions ───────────────────────────────────
# key → (label, icon)
FIELD_TYPES: dict[str, tuple[str, str]] = {
    "textarea": ("Freitext", "\U0001f4dd"),
    "table": ("Tabelle", "\U0001f4ca"),
    "text": ("Kurztext", "\u270f\ufe0f"),
    "number": ("Zahl", "#"),
    "date": ("Datum", "\U0001f4c5"),
    "boolean": ("Ja/Nein", "\u2611"),
}


# ── Helper functions ─────────────────────────────────────────

def ai_source_short_labels() -> dict[str, str]:
    """key → short label (for template rendering)."""
    return {k: v[0] for k, v in AI_SOURCE_TYPES.items()}


def ai_source_full_labels() -> dict[str, str]:
    """key → full label (for LLM prompts)."""
    return {k: v[1] for k, v in AI_SOURCE_TYPES.items()}


def ai_source_choices_for_js() -> list[dict[str, str]]:
    """List of {value, label} dicts for JavaScript template editor."""
    return [
        {"value": k, "label": v[1]}
        for k, v in AI_SOURCE_TYPES.items()
    ]


def field_type_choices_for_js() -> list[dict[str, str]]:
    """List of {value, label, icon} dicts for JavaScript template editor."""
    return [
        {"value": k, "label": v[0], "icon": v[1]}
        for k, v in FIELD_TYPES.items()
    ]
