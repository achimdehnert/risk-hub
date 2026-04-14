# src/explosionsschutz/services/progress.py
"""
ExProgressService — 7-Schritt Fortschritts-Tracking für Ex-Schutzkonzepte.

Prüft Vollständigkeit nach TRGS 720ff, EN 1127-1, BetrSichV, ATEX 1999/92/EG.
Nutzt BaseProgressService aus common/progress.
"""

from __future__ import annotations

from typing import Any

from common.progress.base import BaseProgressService, StepDef, StepState, StepStatus

# ATEX-Kategorie vs. Zone Validierungsmatrix (ATEX 1999/92/EG Anhang II)
ATEX_ZONE_MATRIX: dict[str, set[str]] = {
    "1G": {"0", "1", "2"},
    "2G": {"1", "2"},
    "3G": {"2"},
    "1D": {"20", "21", "22"},
    "2D": {"21", "22"},
    "3D": {"22"},
}


class ExProgressService(BaseProgressService):
    """
    7-Schritt Ex-Schutzkonzept-Fortschritt nach TRGS 720ff.

    Schritte:
        1. Anlage & Stoff          — Area + Gefahrstoff zugewiesen
        2. Zoneneinteilung         — ATEX-Zonen definiert + begründet
        3. Zündquellenbewertung    — 13 Zündquellen nach EN 1127-1
        4. Schutzmaßnahmen         — Primär/Sekundär/Tertiär (TRGS 722)
        5. Betriebsmittel          — ATEX-Kategorie vs. Zone validiert
        6. Prüfpläne               — BetrSichV: jedes Betriebsmittel hat Prüfplan
        7. Freigabe                — Validierung durch befähigte Person
    """

    STEP_DEFS = [
        StepDef(1, "Anlage & Stoff", "_check_area_substance", "TRGS 720 §4"),
        StepDef(2, "Zoneneinteilung", "_check_zones", "TRGS 720 §5"),
        StepDef(3, "Zündquellenbewertung", "_check_ignition_sources", "EN 1127-1 §6"),
        StepDef(4, "Schutzmaßnahmen", "_check_measures", "TRGS 722"),
        StepDef(5, "Betriebsmittel", "_check_equipment", "ATEX 1999/92/EG"),
        StepDef(6, "Prüfpläne", "_check_inspections", "BetrSichV §15"),
        StepDef(7, "Freigabe", "_check_approval", "BetrSichV §3"),
    ]

    # ── Step 1: Anlage & Stoff ────────────────────────────────────────────

    def _check_area_substance(self, concept: Any, ctx: dict) -> StepStatus:
        has_area = getattr(concept, "area_id", None) is not None
        has_substance = bool(getattr(concept, "substance_id", None))

        if not has_area and not has_substance:
            return self._empty("Anlage und Gefahrstoff nicht zugewiesen")
        if not has_area:
            return self._partial(["Betriebsbereich fehlt"], pct=50)
        if not has_substance:
            return self._partial(["Gefahrstoff fehlt"], pct=50)
        return self._complete()

    # ── Step 2: Zoneneinteilung ───────────────────────────────────────────

    def _check_zones(self, concept: Any, ctx: dict) -> StepStatus:
        zones = list(concept.zones.all()) if hasattr(concept, "zones") else []
        if not zones:
            return self._empty("Keine Zonen definiert")

        incomplete = []
        for zone in zones:
            rationale = getattr(zone, "classification_rationale", "") or ""
            if not rationale.strip():
                zone_type = getattr(zone, "zone_type", "?")
                incomplete.append(f"Zone {zone_type}: Begründung fehlt")

        if incomplete:
            return self._partial(
                incomplete,
                pct=round((len(zones) - len(incomplete)) / len(zones) * 100),
                item_count=len(zones),
            )
        return self._complete(
            info=[f"{len(zones)} Zone(n) definiert"],
            item_count=len(zones),
        )

    # ── Step 3: Zündquellenbewertung ──────────────────────────────────────

    def _check_ignition_sources(self, concept: Any, ctx: dict) -> StepStatus:
        # EN 1127-1 defines 13 ignition sources
        total_sources = 13

        assessed = set()
        if hasattr(concept, "ignition_source_assessments"):
            assessed = set(
                concept.ignition_source_assessments.values_list(
                    "source_type", flat=True
                )
            )

        done = len(assessed)
        if done == 0:
            return self._empty(
                f"Alle {total_sources} Zündquellen (EN 1127-1) müssen bewertet werden"
            )

        if done < total_sources:
            return self._partial(
                [f"{total_sources - done} Zündquellen noch nicht bewertet"],
                pct=round(done / total_sources * 100),
                item_count=done,
            )

        return self._complete(
            info=["Alle 13 Zündquellen bewertet"],
            item_count=total_sources,
        )

    # ── Step 4: Schutzmaßnahmen ───────────────────────────────────────────

    def _check_measures(self, concept: Any, ctx: dict) -> StepStatus:
        measures = list(concept.measures.all()) if hasattr(concept, "measures") else []
        if not measures:
            return self._empty("Keine Schutzmaßnahmen erfasst")

        has_primary = any(
            getattr(m, "category", "") == "primary" for m in measures
        )
        issues = []
        if not has_primary:
            issues.append("Keine primäre Maßnahme vorhanden (TRGS 722 Pflicht)")

        open_measures = [
            m for m in measures if getattr(m, "status", "") == "open"
        ]
        if open_measures:
            issues.append(f"{len(open_measures)} Maßnahme(n) noch offen")

        by_cat = {}
        for m in measures:
            cat = getattr(m, "category", "other")
            by_cat[cat] = by_cat.get(cat, 0) + 1
        summary = " · ".join(f"{k}: {v}" for k, v in sorted(by_cat.items()))

        if issues:
            state = StepState.PARTIAL if has_primary else StepState.ERROR
            return StepStatus(
                step=0, label="", state=state,
                issues=issues, info=[summary] if summary else [],
                item_count=len(measures),
                completion_percent=70 if has_primary else 30,
            )
        return self._complete(info=[summary], item_count=len(measures))

    # ── Step 5: Betriebsmittel ────────────────────────────────────────────

    def _check_equipment(self, concept: Any, ctx: dict) -> StepStatus:
        equipment = list(concept.equipment.all()) if hasattr(concept, "equipment") else []
        if not equipment:
            return self._empty("Keine Ex-Betriebsmittel erfasst")

        errors = []
        for eq in equipment:
            eq_zone = getattr(eq, "zone", None)
            if not eq_zone:
                continue
            zone_type = getattr(eq_zone, "zone_type", "")
            eq_type = getattr(eq, "equipment_type", None)
            if eq_type:
                atex_cat = getattr(eq_type, "atex_category", "")
                if atex_cat and zone_type:
                    allowed_zones = ATEX_ZONE_MATRIX.get(atex_cat, set())
                    if zone_type not in allowed_zones:
                        eq_name = getattr(eq, "name", str(eq))
                        errors.append(
                            f"{eq_name}: Kat {atex_cat} "
                            f"nicht zulässig in Zone {zone_type}"
                        )

        if errors:
            return self._error(errors, item_count=len(equipment))
        return self._complete(
            info=[f"{len(equipment)} Betriebsmittel geprüft"],
            item_count=len(equipment),
        )

    # ── Step 6: Prüfpläne ────────────────────────────────────────────────

    def _check_inspections(self, concept: Any, ctx: dict) -> StepStatus:
        equipment = (
            list(concept.equipment.prefetch_related("inspections").all())
            if hasattr(concept, "equipment")
            else []
        )
        if not equipment:
            return self._complete(info=["Keine Betriebsmittel — Schritt entfällt"])

        without_plan = [
            eq for eq in equipment if not eq.inspections.exists()
        ]
        if without_plan:
            names = ", ".join(
                getattr(eq, "name", str(eq)) for eq in without_plan[:3]
            )
            return self._partial(
                [f"{len(without_plan)} Betriebsmittel ohne Prüfplan: {names}"],
                pct=round(
                    (len(equipment) - len(without_plan)) / len(equipment) * 100
                ),
                item_count=len(equipment) - len(without_plan),
            )
        return self._complete(
            info=[f"Prüfpläne für alle {len(equipment)} Betriebsmittel"],
            item_count=len(equipment),
        )

    # ── Step 7: Freigabe ──────────────────────────────────────────────────

    def _check_approval(self, concept: Any, ctx: dict) -> StepStatus:
        is_validated = getattr(concept, "is_validated", False)
        validated_by = getattr(concept, "validated_by", None)

        if not is_validated:
            return self._empty("Konzept muss durch befähigte Person validiert werden")

        name = str(validated_by) if validated_by else "unbekannt"
        return self._complete(info=[f"Validiert durch {name}"])
