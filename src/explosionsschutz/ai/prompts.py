# src/explosionsschutz/ai/prompts.py
"""
Prompt-Builder für KI-Generierung (ADR-018).

Baut chapter-spezifische User-Prompts aus dem ExplosionConcept-Kontext.
Gibt (prompt_text, input_context_dict) zurück.
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from explosionsschutz.models import ExplosionConcept

CHAPTER_BUILDERS = {}


def _register(chapter: str):
    def decorator(fn):
        CHAPTER_BUILDERS[chapter] = fn
        return fn
    return decorator


def build_prompt_for_chapter(
    chapter: str,
    concept: ExplosionConcept,
    user_notes: str = "",
) -> tuple[str, dict]:
    """Dispatcht an den kapitelspezifischen Prompt-Builder.

    Returns:
        (user_prompt, input_context) — input_context wird im GenerationLog gespeichert.
    """
    builder = CHAPTER_BUILDERS.get(chapter)
    if builder is None:
        raise ValueError(f"Kein Prompt-Builder für chapter '{chapter}' registriert.")
    return builder(concept=concept, user_notes=user_notes)


def _base_context(concept: ExplosionConcept) -> dict:
    """Gemeinsamer Kontext-Snapshot für alle Kapitel."""
    return {
        "concept_id": concept.pk,
        "title": concept.title,
        "substance_name": concept.substance_name or "unbekannt",
        "substance_id": str(concept.substance_id) if concept.substance_id else None,
        "area_name": concept.area.name if concept.area_id else "unbekannt",
        "area_code": getattr(concept.area, "code", "") if concept.area_id else "",
        "area_description": getattr(concept.area, "description", "") if concept.area_id else "",
    }


def _zones_summary(concept: ExplosionConcept) -> list[dict]:
    return [
        {
            "name": z.name,
            "zone_type": z.zone_type,
            "description": z.description,
            "justification": z.justification,
        }
        for z in concept.zones.all()
    ]


def _measures_summary(concept: ExplosionConcept) -> list[dict]:
    return [
        {"category": m.category, "title": m.title, "description": m.description}
        for m in concept.measures.select_related("catalog_reference")
    ]


@_register("zones")
def _build_zones_prompt(concept: ExplosionConcept, user_notes: str = "") -> tuple[str, dict]:
    ctx = _base_context(concept)
    prompt_parts = [
        "## Aufgabe: Zonenklassifizierung nach TRGS 721 / EN 60079-10",
        "",
        f"**Anlage/Bereich:** {ctx['area_name']} ({ctx['area_code']})",
        f"**Beschreibung:** {ctx['area_description'] or 'keine'}",
        f"**Gefährlicher Stoff:** {ctx['substance_name']}",
        "",
        "Erstelle eine Zonenklassifizierung mit:",
        "- Zonenbezeichnung (Zone 0 / Zone 1 / Zone 2)",
        "- Begründung (Freisetzungsquelle, -grad, -häufigkeit nach TRGS 722)",
        "- Hinweis auf TRBS 2152 / EN 60079-10-1 Anwendbarkeit",
        "- Ausdehnung des Ex-Bereichs (schätzend, mit Norm-Verweis)",
        "",
        "Fehlende Angaben als `[KLÄRUNGSBEDARF: Grund]` markieren.",
    ]
    if user_notes:
        prompt_parts += ["", f"**Hinweise des Experten:** {user_notes}"]

    return "\n".join(prompt_parts), ctx


@_register("ignition")
def _build_ignition_prompt(concept: ExplosionConcept, user_notes: str = "") -> tuple[str, dict]:
    ctx = _base_context(concept)
    zones = _zones_summary(concept)
    ctx["existing_zones"] = zones

    prompt_parts = [
        "## Aufgabe: Zündquellen-Bewertung nach EN 1127-1",
        "",
        f"**Anlage:** {ctx['area_name']}  |  **Stoff:** {ctx['substance_name']}",
    ]
    if zones:
        prompt_parts += [
            "",
            "**Klassifizierte Zonen:**",
            json.dumps(zones, ensure_ascii=False, indent=2),
        ]
    prompt_parts += [
        "",
        "Bewerte die 13 Zündquellen nach EN 1127-1 Abschnitt 6:",
        "Für jede Zündquelle: wirksam (ja/nein/bedingt) + Begründung + ggf. Schutzmaßnahme.",
        "Fehlende Angaben als `[KLÄRUNGSBEDARF: Grund]` markieren.",
    ]
    if user_notes:
        prompt_parts += ["", f"**Hinweise des Experten:** {user_notes}"]

    return "\n".join(prompt_parts), ctx


@_register("measures")
def _build_measures_prompt(concept: ExplosionConcept, user_notes: str = "") -> tuple[str, dict]:
    ctx = _base_context(concept)
    zones = _zones_summary(concept)
    ctx["existing_zones"] = zones

    prompt_parts = [
        "## Aufgabe: Schutzmaßnahmen nach TRGS 722 / BetrSichV",
        "",
        f"**Anlage:** {ctx['area_name']}  |  **Stoff:** {ctx['substance_name']}",
    ]
    if zones:
        prompt_parts += [
            "",
            "**Klassifizierte Zonen:**",
            json.dumps(zones, ensure_ascii=False, indent=2),
        ]
    prompt_parts += [
        "",
        "Schlage Schutzmaßnahmen in drei Kategorien vor (§ 6 TRBS 2152):",
        "1. Primär (Vermeidung expl. Atmosphäre) — technische Maßnahmen",
        "2. Sekundär (Zündquellenvermeidung) — ATEX-Betriebsmittel, Erdung, ...",
        "3. Tertiär (Auswirkungsbegrenzung) — Druckentlastung, Löschanlagen, ...",
        "4. Organisatorisch — Freigabeschein, Unterweisung, ...",
        "",
        "Pro Maßnahme: Kategorie, Bezeichnung, Norm-Verweis, Priorität (hoch/mittel/niedrig).",
        "Fehlende Angaben als `[KLÄRUNGSBEDARF: Grund]` markieren.",
    ]
    if user_notes:
        prompt_parts += ["", f"**Hinweise des Experten:** {user_notes}"]

    return "\n".join(prompt_parts), ctx


@_register("summary")
def _build_summary_prompt(concept: ExplosionConcept, user_notes: str = "") -> tuple[str, dict]:
    ctx = _base_context(concept)
    zones = _zones_summary(concept)
    measures = _measures_summary(concept)
    ctx["existing_zones"] = zones
    ctx["existing_measures"] = measures

    prompt_parts = [
        "## Aufgabe: Zusammenfassung Explosionsschutzdokument",
        "",
        f"**Konzept:** {ctx['title']}",
        f"**Anlage:** {ctx['area_name']}  |  **Stoff:** {ctx['substance_name']}",
    ]
    if zones:
        prompt_parts += ["", "**Zonen:**", json.dumps(zones, ensure_ascii=False, indent=2)]
    if measures:
        prompt_parts += ["", "**Maßnahmen:**", json.dumps(measures, ensure_ascii=False, indent=2)]
    prompt_parts += [
        "",
        "Schreibe eine Zusammenfassung für das Explosionsschutzdokument:",
        "- Geltungsbereich und Anlagenbeschreibung",
        "- Ergebnis der Zoneneinteilung",
        "- Wesentliche Schutzmaßnahmen",
        "- Hinweis auf Prüfpflichten (§ 14 BetrSichV) und Aktualisierungsanlass",
        "Fehlende Angaben als `[KLÄRUNGSBEDARF: Grund]` markieren.",
    ]
    if user_notes:
        prompt_parts += ["", f"**Hinweise des Experten:** {user_notes}"]

    return "\n".join(prompt_parts), ctx
