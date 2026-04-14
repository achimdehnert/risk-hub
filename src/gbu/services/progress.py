# src/gbu/services/progress.py
"""
GbuProgressService — 8-Schritt Fortschritts-Tracking für GBU-Tätigkeiten.

Prüft Vollständigkeit nach GefStoffV §6, TRGS 400, TRGS 500, ArbSchG §3.
Nutzt BaseProgressService aus common/progress.
"""

from __future__ import annotations

from typing import Any

from common.progress.base import BaseProgressService, StepDef, StepState, StepStatus


class GbuProgressService(BaseProgressService):
    """
    8-Schritt GBU-Fortschritt nach GefStoffV §6.

    Schritte:
        1. Stoff & Standort        — SDS-Revision zugewiesen, Standort gesetzt
        2. Tätigkeitsdaten         — Beschreibung, Frequenz, Menge, Dauer
        3. Gefährdungskategorien   — H-Codes → DGUV-Kategorien abgeleitet
        4. Substitutionsprüfung    — GefStoffV §7 (CMR-Gate: blockiert wenn CMR + nicht geprüft)
        5. Schutzmaßnahmen         — TOPS-Hierarchie (TRGS 500 §4)
        6. PSA-Festlegung          — P-Sätze aus SDB (nur wenn Expositionsprofil es erfordert)
        7. Wirksamkeitsprüfung     — Review-Intervall festgelegt (ArbSchG §3(1))
        8. Freigabe                — Freigeber + Datum (CMR → Betriebsarzt-Hinweis)
    """

    STEP_DEFS = [
        StepDef(1, "Stoff & Standort", "_check_substance_site", "GefStoffV §6(1)"),
        StepDef(2, "Tätigkeitsdaten", "_check_activity_data", "GefStoffV §6(1)"),
        StepDef(3, "Gefährdungskategorien", "_check_hazard_categories", "TRGS 400"),
        StepDef(4, "Substitutionsprüfung", "_check_substitution", "GefStoffV §7"),
        StepDef(5, "Schutzmaßnahmen", "_check_measures", "TRGS 500 §4"),
        StepDef(6, "PSA-Festlegung", "_check_ppe", "PSA-BV"),
        StepDef(7, "Wirksamkeitsprüfung", "_check_effectiveness", "ArbSchG §3(1)"),
        StepDef(8, "Freigabe", "_check_approval", "GefStoffV §6(3)"),
    ]

    def _build_context(self, activity: Any) -> dict[str, Any]:
        """Derive hazard categories and CMR flag for all checkers."""
        cats = (
            list(activity.derived_hazard_categories.values_list("category_type", flat=True))
            if hasattr(activity, "derived_hazard_categories")
            else []
        )
        return {
            "cats": cats,
            "has_cmr": "CMR" in cats,
        }

    # ── Step 1: Stoff & Standort ──────────────────────────────────────────

    def _check_substance_site(self, a: Any, ctx: dict) -> StepStatus:
        has_sds = getattr(a, "sds_revision_id", None) is not None
        has_site = getattr(a, "site_id", None) is not None

        if not has_sds and not has_site:
            return self._empty("SDS-Revision und Standort nicht zugewiesen")
        if not has_sds:
            return self._partial(["SDS-Revision fehlt"], pct=50)
        if not has_site:
            return self._partial(["Standort fehlt"], pct=50)
        return self._complete()

    # ── Step 2: Tätigkeitsdaten ───────────────────────────────────────────

    def _check_activity_data(self, a: Any, ctx: dict) -> StepStatus:
        issues = []
        desc = getattr(a, "activity_description", "") or ""
        if not desc.strip():
            issues.append("Tätigkeitsbeschreibung fehlt")
        if not getattr(a, "activity_frequency", ""):
            issues.append("Expositionsfrequenz fehlt")
        if not getattr(a, "duration_minutes", 0):
            issues.append("Expositionsdauer fehlt")
        if not getattr(a, "quantity_class", ""):
            issues.append("Mengenkategorie fehlt")

        if len(issues) == 4:
            return self._empty("Keine Tätigkeitsdaten erfasst")
        if issues:
            return self._partial(issues, pct=round((4 - len(issues)) / 4 * 100))
        return self._complete()

    # ── Step 3: Gefährdungskategorien ─────────────────────────────────────

    def _check_hazard_categories(self, a: Any, ctx: dict) -> StepStatus:
        cats = ctx.get("cats", [])
        if not cats:
            return self._empty("Keine Gefährdungskategorien abgeleitet (H-Codes prüfen)")
        return self._complete(
            info=[f"{len(cats)} Kategorie(n): {', '.join(cats)}"],
            item_count=len(cats),
        )

    # ── Step 4: Substitutionsprüfung (CMR-Gate) ──────────────────────────

    def _check_substitution(self, a: Any, ctx: dict) -> StepStatus:
        has_cmr = ctx.get("has_cmr", False)
        checked = getattr(a, "substitution_checked", False)
        notes = (getattr(a, "substitution_notes", "") or "").strip()

        if not has_cmr and not checked:
            return self._complete(info=["Kein CMR-Stoff — Substitutionsprüfung optional"])

        if has_cmr and not checked:
            return self._blocked("CMR-Stoff: Substitutionsprüfung ist Pflicht (GefStoffV §7)")

        if checked and not notes:
            return self._partial(["Ergebnis der Substitutionsprüfung fehlt"], pct=60)

        return self._complete(info=["Substitutionsprüfung dokumentiert"])

    # ── Step 5: Schutzmaßnahmen (TOPS) ───────────────────────────────────

    def _check_measures(self, a: Any, ctx: dict) -> StepStatus:
        measures = list(a.measures.all()) if hasattr(a, "measures") else []
        if not measures:
            return self._empty("Keine Schutzmaßnahmen erfasst (T-O-P-S)")

        by_type = {"T": 0, "O": 0, "P": 0, "S": 0}
        for m in measures:
            t = getattr(m, "tops_type", "")
            if t in by_type:
                by_type[t] += 1

        issues = []
        if by_type["P"] > 0 and by_type["T"] == 0 and by_type["O"] == 0:
            issues.append(
                "PSA allein ist unzureichend — technische/organisatorische "
                "Maßnahmen müssen vorrangig sein (TRGS 500 §4)"
            )

        summary = " · ".join(f"{k}: {v}" for k, v in by_type.items() if v > 0)

        if issues:
            return self._error(issues, item_count=len(measures))
        return self._complete(info=[summary], item_count=len(measures))

    # ── Step 6: PSA-Festlegung ────────────────────────────────────────────

    def _check_ppe(self, a: Any, ctx: dict) -> StepStatus:
        cats = ctx.get("cats", [])
        needs_ppe = bool(
            {"DERMAL", "HAUT_REIZ", "HAUT_SENSIB", "INHALATION", "HAUT_AEZT", "AUGE"} & set(cats)
        )

        if not needs_ppe:
            return self._complete(info=["Keine PSA erforderlich (Gefährdungsprofil)"])

        # Check if S-type (Schutzausrüstung) measures exist
        measures = list(a.measures.all()) if hasattr(a, "measures") else []
        has_ppe = any(getattr(m, "tops_type", "") == "S" for m in measures)

        if not has_ppe:
            return self._partial(
                ["PSA-Festlegung fehlt (aus P-Sätzen ableiten)"],
                warnings=["P-Sätze aus SDB als Ausgangspunkt nutzen"],
            )
        return self._complete(info=["PSA dokumentiert"])

    # ── Step 7: Wirksamkeitsprüfung ───────────────────────────────────────

    def _check_effectiveness(self, a: Any, ctx: dict) -> StepStatus:
        review_date = getattr(a, "next_review_date", None)
        if not review_date:
            return self._empty("Wiederholungstermin nicht festgelegt (ArbSchG §3(1))")

        import datetime

        if review_date < datetime.date.today():
            return self._error([f"Wirksamkeitsprüfung überfällig seit {review_date}"])
        return self._complete(info=[f"Nächste Überprüfung: {review_date}"])

    # ── Step 8: Freigabe ──────────────────────────────────────────────────

    def _check_approval(self, a: Any, ctx: dict) -> StepStatus:
        approved_by = getattr(a, "approved_by_name", "") or ""
        if not approved_by:
            issues = ["GBU muss freigegeben werden (GefStoffV §6(3))"]
            warnings = []
            if ctx.get("has_cmr"):
                warnings.append("CMR-Stoff: Betriebsarzt muss eingebunden sein")
            return StepStatus(
                step=0,
                label="",
                state=StepState.EMPTY,
                issues=issues,
                warnings=warnings,
            )
        return self._complete(info=[f"Freigegeben durch {approved_by}"])
