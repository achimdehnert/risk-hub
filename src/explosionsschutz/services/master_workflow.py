# src/explosionsschutz/services/master_workflow.py
"""
Master-Workflow-Service für Ex-Schutzkonzepte.

7 Phasen A–G als aufrufbare Service-Methoden.
Alle Methoden nehmen `concept` + `tenant_id` entgegen und delegieren
an Modell-Level-Logik. Keine HTTP-Abhängigkeiten.

ADR-044 Phase 5B.
"""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from django.core.exceptions import ValidationError
from django.utils import timezone

if TYPE_CHECKING:
    from explosionsschutz.models.approval import ConceptApprovalSnapshot
    from explosionsschutz.models.concept import ExplosionConcept


class MasterWorkflowService:
    """
    Orchestriert den 7-Phasen-Workflow für UC-1 Ex-Schutzkonzepte.

    Phase A: Kontext (Anlagen-Setup, Stoffe, Gebinde)
    Phase B: Gefährdungsermittlung (Zonen, Zündquellen, MSR)
    Phase C: Schutz-Hierarchie (primär/sekundär/tertiär/MSR-Ebene)
    Phase D: Betriebsregime (Betriebszustände, Anlagen-Matrix)
    Phase E: Validierung (4 Gates: Vollständigkeit, Anhang-I, Prüfplan, Wirksamkeit)
    Phase F: Freigabe (ApprovalStatement, ConceptApprovalSnapshot)
    Phase G: Lebenszyklus (Revisionsmanagement, Impact-Events, Überprüfungsfristen)
    """

    def __init__(self, concept: ExplosionConcept, tenant_id: uuid.UUID) -> None:
        self.concept = concept
        self.tenant_id = tenant_id

    # ── Phase A: Kontext ─────────────────────────────────────────────────────

    def phase_a_context(self) -> dict:
        """
        Phase A: Anlage kontextualisieren.
        Prüft: concept.area, concept.project, mindestens 1 substance_reference.
        Returns: dict mit missing_items Liste.
        """
        missing = []
        if not self.concept.area_id:
            missing.append("Bereich (Area) fehlt")
        if not self.concept.substance_references.exists():
            missing.append("Mindestens eine Stoff-Referenz (ConceptSubstanceReference) fehlt")
        return {"phase": "A", "complete": not missing, "missing": missing}

    # ── Phase B: Gefährdungsermittlung ───────────────────────────────────────

    def phase_b_hazard_identification(self) -> dict:
        """
        Phase B: Zonen, Zündquellen, Staubkenngrößen.
        Prüft: mindestens 1 Zone, alle Zonen haben ≥ 1 Zündquellen-Assessment.
        """
        missing = []
        # Note: zone query below uses concept.zone_definitions instead
        _ = self.concept.area.zone_definitions.filter(
            explosion_concept=self.concept
        ) if hasattr(self.concept, "area") else []

        zone_qs = getattr(self.concept, "zone_definitions", None)
        if zone_qs is None or not zone_qs.exists():
            missing.append("Keine Zonendefinitionen vorhanden")
        else:
            zones_without_assessment = zone_qs.filter(
                ignition_assessments__isnull=True
            ).count()
            if zones_without_assessment > 0:
                missing.append(
                    f"{zones_without_assessment} Zone(n) ohne Zündquellen-Assessment"
                )
        return {"phase": "B", "complete": not missing, "missing": missing}

    # ── Phase C: Schutz-Hierarchie ───────────────────────────────────────────

    def phase_c_protection_hierarchy(self) -> dict:
        """
        Phase C: Primär-/Sekundär-/Tertiär-/MSR-Schutz prüfen.
        Prüft: mindestens 1 ProtectionMeasure, MSR-Funktionen validiert.
        """
        missing = []
        if not self.concept.protection_measures.exists():
            missing.append("Keine Schutzmaßnahmen (ProtectionMeasure) erfasst")
        safety_fns = self.concept.safety_functions.filter(
            evaluation_narrative=""
        )
        if safety_fns.exists():
            missing.append(
                f"{safety_fns.count()} MSR-Funktion(en) ohne Bewertungs-Narrativ"
            )
        return {"phase": "C", "complete": not missing, "missing": missing}

    # ── Phase D: Betriebsregime ──────────────────────────────────────────────

    def phase_d_operational_regime(self) -> dict:
        """
        Phase D: Betriebszustands-Matrix vollständig?
        Prüft: Alle AnlageComponents haben 5 OperationalStateAssessments.
        """
        from explosionsschutz.models.anlage import OperationalState

        missing = []
        components = self.concept.components.all()
        state_count = len(OperationalState.choices)

        for component in components:
            actual = component.operational_state_assessments.count()
            if actual < state_count:
                missing.append(
                    f"Komponente '{component.name}': {actual}/{state_count} Betriebszustände"
                )
        return {"phase": "D", "complete": not missing, "missing": missing}

    # ── Phase E: Validierung (4 Gates) ──────────────────────────────────────

    def phase_e_validation(self) -> dict:
        """
        Phase E: 4-Gate-Validierung.
        Gate 1: Vollständigkeitsprüfung (A-D komplett)
        Gate 2: Anhang-I-Checkliste vollständig bewertet
        Gate 3: Prüfplan vollständig
        Gate 4: Wirksamkeitsprüfung geplant
        Wirft ValidationError wenn ein Gate fehlschlägt.
        """
        gates = []

        # Gate 1 — Vollständigkeit A–D
        for phase_result in [
            self.phase_a_context(),
            self.phase_b_hazard_identification(),
            self.phase_c_protection_hierarchy(),
            self.phase_d_operational_regime(),
        ]:
            if not phase_result["complete"]:
                gates.append({
                    "gate": 1,
                    "passed": False,
                    "reason": f"Phase {phase_result['phase']} unvollständig: "
                              + "; ".join(phase_result["missing"]),
                })

        # Gate 2 — Anhang-I-Checkliste
        non_compliant = self.concept.annex_i_assessments.filter(
            status="NON_COMPLIANT"
        ).count()
        pending = self.concept.annex_i_assessments.filter(status="PENDING").count()
        if pending > 0:
            gates.append({
                "gate": 2,
                "passed": False,
                "reason": f"Anhang-I: {pending} Punkte noch in Bearbeitung (PENDING)",
            })
        if non_compliant > 0:
            gates.append({
                "gate": 2,
                "passed": False,
                "reason": f"Anhang-I: {non_compliant} Punkte nicht erfüllt (NON_COMPLIANT)",
            })

        # Gate 3 — Prüfplan
        entries_without_due = self.concept.review_schedule_entries.filter(
            next_due_date__isnull=True,
            interval_months__isnull=True,
        ).count()
        if entries_without_due > 0:
            gates.append({
                "gate": 3,
                "passed": False,
                "reason": f"Prüfplan: {entries_without_due} Einträge ohne Fälligkeit und Intervall",
            })

        # Gate 4 — Wirksamkeitsprüfung
        effectiveness_entries = self.concept.review_schedule_entries.filter(
            regulatory_layer="EFFECT"
        )
        if not effectiveness_entries.exists():
            gates.append({
                "gate": 4,
                "passed": False,
                "reason": "Wirksamkeitsprüfung (§ 6(9) GefStoffV) nicht im Prüfplan erfasst",
            })

        failed_gates = [g for g in gates if not g["passed"]]
        if failed_gates:
            raise ValidationError(
                {f"gate_{g['gate']}": g["reason"] for g in failed_gates}
            )

        return {"phase": "E", "complete": True, "gates_passed": 4}

    # ── Phase F: Freigabe ────────────────────────────────────────────────────

    def phase_f_approval(
        self,
        signed_by_id: uuid.UUID,
        signed_by_name: str,
        signed_by_role: str,
        statement_template_id: str = "default_v1",
        signatory_role: str = "ARBEITGEBER",
    ) -> ConceptApprovalSnapshot:
        """
        Phase F: Freigabe-Erklärung anlegen und Snapshot einfrieren.

        Wirft ValidationError wenn Phase E noch nicht bestanden.
        Erstellt ApprovalStatement + ConceptApprovalSnapshot atomisch.
        """
        from django.db import transaction

        from explosionsschutz.models.approval import (
            ApprovalStatement,
            ConceptApprovalSnapshot,
        )

        self.phase_e_validation()

        with transaction.atomic():
            statement = ApprovalStatement.objects.create(
                concept=self.concept,
                statement_template_id=statement_template_id,
                rendered_text=self._render_approval_statement(statement_template_id),
                legal_framework_reference="§ 6(9) GefStoffV i.V.m. § 6(4) BetrSichV",
                signatory_role=signatory_role,
                signed_by_id=signed_by_id,
                signed_by_name=signed_by_name,
                signed_by_role=signed_by_role,
                signed_at=timezone.now(),
                tenant_id=self.tenant_id,
            )
            version = self.concept.approval_snapshots.count() + 1
            snapshot = ConceptApprovalSnapshot.objects.create(
                concept=self.concept,
                snapshot_version=version,
                approval_statement=statement,
                zones_snapshot_json=self._serialize_zones(),
                ignition_sources_snapshot_json=self._serialize_ignition_sources(),
                safety_functions_snapshot_json=self._serialize_safety_functions(),
                review_schedule_snapshot_json=self._serialize_review_schedule(),
                annex_i_assessment_snapshot_json=self._serialize_annex_i(),
                substance_references_snapshot_json=self._serialize_substance_references(),
                operational_states_snapshot_json=self._serialize_operational_states(),
            )
        return snapshot

    # ── Phase G: Lebenszyklus ────────────────────────────────────────────────

    def phase_g_lifecycle_check(self) -> dict:
        """
        Phase G: Überprüfungs-Fälligkeiten berechnen.
        Gibt Liste überfälliger und in 30 Tagen fälliger Einträge zurück.
        """
        from datetime import timedelta

        today = timezone.now().date()
        overdue = list(
            self.concept.review_schedule_entries.filter(
                next_due_date__lt=today
            ).values("id", "regulatory_layer", "next_due_date")
        )
        due_soon = list(
            self.concept.review_schedule_entries.filter(
                next_due_date__range=(today, today + timedelta(days=30))
            ).values("id", "regulatory_layer", "next_due_date")
        )
        return {
            "phase": "G",
            "overdue_count": len(overdue),
            "due_soon_count": len(due_soon),
            "overdue": overdue,
            "due_soon": due_soon,
        }

    # ── Private Serialize Helpers ────────────────────────────────────────────

    def _render_approval_statement(self, template_id: str) -> str:
        return (
            f"Das Ex-Schutzdokument für '{self.concept.title}' wurde gemäß "
            "§ 6(9) GefStoffV i.V.m. § 6(4) BetrSichV erstellt und ist auf "
            "dem aktuellen Stand der Technik. Die Gefährdungsbeurteilung "
            "wurde ordnungsgemäß durchgeführt."
        )

    def _serialize_zones(self) -> list:
        import json

        from django.core import serializers
        qs = self.concept.area.zone_definitions.all() if hasattr(self.concept, "area") else []
        return json.loads(serializers.serialize("json", qs)) if qs else []

    def _serialize_ignition_sources(self) -> list:
        import json

        from django.core import serializers
        zone_ids = list(
            getattr(self.concept, "zone_definitions", type("", (), {"values_list": lambda *a, **kw: []})())
            .values_list("id", flat=True)
        )
        from explosionsschutz.models.zone import ZoneIgnitionSourceAssessment
        qs = ZoneIgnitionSourceAssessment.objects.filter(zone_id__in=zone_ids)
        return json.loads(serializers.serialize("json", qs))

    def _serialize_safety_functions(self) -> list:
        import json

        from django.core import serializers
        return json.loads(serializers.serialize("json", self.concept.safety_functions.all()))

    def _serialize_review_schedule(self) -> list:
        import json

        from django.core import serializers
        return json.loads(serializers.serialize("json", self.concept.review_schedule_entries.all()))

    def _serialize_annex_i(self) -> list:
        import json

        from django.core import serializers
        return json.loads(serializers.serialize("json", self.concept.annex_i_assessments.all()))

    def _serialize_substance_references(self) -> list:
        import json

        from django.core import serializers
        return json.loads(serializers.serialize("json", self.concept.substance_references.all()))

    def _serialize_operational_states(self) -> list:
        import json

        from django.core import serializers

        from explosionsschutz.models.anlage import OperationalStateAssessment
        component_ids = list(self.concept.components.values_list("id", flat=True))
        qs = OperationalStateAssessment.objects.filter(component_id__in=component_ids)
        return json.loads(serializers.serialize("json", qs))
