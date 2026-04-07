"""
Kernmodelle: Betriebsbereich und Explosionsschutzkonzept.
Entspricht Kapitel 1–4 des Explosionsschutzdokuments.
"""
from __future__ import annotations

import uuid
from enum import StrEnum

from django.db import models


class SubstituteCheckStatus(StrEnum):
    """Ergebnis der Substitutionsprüfung gem. GefStoffV §6(2)."""
    NOT_CHECKED = "not_checked"
    NOT_POSSIBLE = "not_possible"             # Verfahrenstechnisch nicht möglich
    IN_PLANNING = "in_planning"               # Umstellung in Planung
    SUBSTITUTED = "substituted"              # Substitution erfolgt
    PARTIALLY_SUBSTITUTED = "partially_substituted"


class ReleaseSource(StrEnum):
    """Art des Stoffaustritts gem. TRGS 721 Abschnitt 4."""
    GAS = "gas"
    VAPOR = "vapor"
    MIST = "mist"
    DUST = "dust"


class Area(models.Model):
    """
    Betriebsbereich / Betrachtungsraum.

    Ein Bereich kann mehrere Ex-Konzepte über die Zeit haben
    (Versionierung via ExplosionConcept.is_current).
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant_id = models.UUIDField(db_index=True)

    site_id = models.UUIDField(
        db_index=True,
        help_text="FK zu tenancy.Site (denormalisiert für RLS-Performance)",
    )
    code = models.CharField(
        max_length=50,
        help_text="Internes Kürzel (z.B. 'E2-50.01', 'OF-5')",
    )
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    location_description = models.CharField(
        max_length=500,
        blank=True,
        help_text="Gebäude, Raum, Adresse",
    )
    floor_plan = models.ForeignKey(
        "documents.Document",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="area_floor_plans",
        help_text="Grundriss / Lageplan (für Zonendarstellung)",
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "ex_area"
        constraints = [
            models.UniqueConstraint(
                fields=["tenant_id", "code"],
                name="uq_ex_area_code_per_tenant",
            ),
        ]
        ordering = ["code"]

    def __str__(self) -> str:
        return f"{self.code} – {self.name}"

    @property
    def has_explosion_hazard(self) -> bool:
        """
        Dynamisch geprüft: Hat dieser Bereich ein aktives Ex-Konzept?
        Kein DB-Feld – immer aktuell.
        """
        return self.concepts.filter(
            is_current=True,
            status__in=[
                ExplosionConcept.Status.APPROVED,
                ExplosionConcept.Status.REVIEW,
                ExplosionConcept.Status.DRAFT,
            ],
        ).exists()

    @property
    def current_concept(self) -> ExplosionConcept | None:
        return self.concepts.filter(is_current=True).first()


class ExplosionConcept(models.Model):
    """
    Explosionsschutzkonzept für einen Betriebsbereich.

    Entspricht dem vollständigen Explosionsschutzdokument nach §6 GefStoffV
    und §5 ArbSchG. Enthält alle Kapitel als Sub-Modelle (Zonen, Maßnahmen,
    Zündquellen, Betriebsmittel).

    Status-Workflow: draft → review → approved → archived
    """

    class Status(models.TextChoices):
        DRAFT = "draft", "Entwurf"
        REVIEW = "review", "In Prüfung"
        APPROVED = "approved", "Freigegeben"
        ARCHIVED = "archived", "Archiviert"

    class AtmosphereType(models.TextChoices):
        GAS_VAPOR = "gas", "Gas/Dampf (Zone 0/1/2)"
        DUST = "dust", "Staub (Zone 20/21/22)"
        MIXED = "mixed", "Gas/Dampf + Staub"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant_id = models.UUIDField(db_index=True)

    area = models.ForeignKey(
        Area,
        on_delete=models.PROTECT,  # Compliance: Bereich nicht löschbar solange Konzept existiert
        related_name="concepts",
    )
    # FK zur Substanz aus substances-Modul (maßgeblicher Stoff)
    substance_id = models.UUIDField(
        null=True,
        blank=True,
        db_index=True,
        help_text="UUID der maßgeblichen Substanz aus substances.Substance",
    )

    # Dokument-Metadaten
    title = models.CharField(max_length=300)
    version = models.CharField(
        max_length=20,
        default="1.0",
        help_text="Dokumentenversion (z.B. '1.0', 'Rev.03')",
    )
    document_number = models.CharField(
        max_length=100,
        blank=True,
        help_text="Interne Dokumentennummer",
    )
    is_current = models.BooleanField(
        default=True,
        help_text="Aktuell gültiges Konzept für diesen Bereich",
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.DRAFT,
    )
    atmosphere_type = models.CharField(
        max_length=10,
        choices=AtmosphereType.choices,
        default=AtmosphereType.GAS_VAPOR,
    )

    # Verfahrensbeschreibung (Kapitel 1)
    process_description = models.TextField(
        blank=True,
        help_text="Anlagenbeschreibung / Verfahrensbeschreibung",
    )

    # Substitutionsprüfung (Kapitel 5.1 gem. Dokument)
    substitute_check_status = models.CharField(
        max_length=30,
        choices=[(s.value, s.value) for s in SubstituteCheckStatus],
        default=SubstituteCheckStatus.NOT_CHECKED,
        help_text="Ergebnis der Substitutionsprüfung (GefStoffV §6(2))",
    )
    substitute_check_notes = models.TextField(
        blank=True,
        help_text="Begründung wenn Substitution nicht möglich",
    )

    # Freisetzungsquellen (Kapitel 6.1)
    release_source_type = models.CharField(
        max_length=10,
        choices=[(s.value, s.value) for s in ReleaseSource],
        default=ReleaseSource.VAPOR,
    )
    release_grade = models.CharField(
        max_length=20,
        choices=[
            ("continuous", "Ständig (kontinuierlich)"),
            ("primary", "Gelegentlich im Normalbetrieb (primär)"),
            ("secondary", "Selten und kurzzeitig (sekundär)"),
        ],
        blank=True,
        help_text="Freisetzungsgrad gem. TRGS 721",
    )
    release_description = models.TextField(
        blank=True,
        help_text="Beschreibung der Freisetzungsquellen und -raten",
    )

    # Beschränkung Explosionsauswirkungen (Kapitel 6.3)
    explosion_impact_mitigation = models.TextField(
        blank=True,
        help_text="Maßnahmen zur Beschränkung von Explosionsauswirkungen",
    )

    # Verantwortlichkeiten
    responsible_id = models.UUIDField(
        null=True,
        blank=True,
        help_text="UUID des Verantwortlichen (Kostenstellenleiter)",
    )
    responsible_name = models.CharField(
        max_length=200,
        blank=True,
        help_text="Name des Verantwortlichen (Snapshot)",
    )
    author_id = models.UUIDField(
        null=True,
        blank=True,
        help_text="UUID des Erstellers/Verfassers",
    )
    author_name = models.CharField(max_length=200, blank=True)

    # Freigabe (immutable nach Approval)
    approved_by_id = models.UUIDField(
        null=True,
        blank=True,
        help_text="UUID der freigebenden Person (unveränderlich nach Freigabe)",
    )
    approved_by_name = models.CharField(
        max_length=200,
        blank=True,
        help_text="Vollname der freigebenden Person (Snapshot, immutable)",
    )
    approved_at = models.DateTimeField(null=True, blank=True)
    approval_notes = models.TextField(blank=True)

    # Nächste Überprüfung
    next_review_date = models.DateField(
        null=True,
        blank=True,
        help_text="Nächste Überprüfung (§6(9) GefStoffV, i.d.R. alle 3 Jahre)",
    )

    # Generiertes PDF
    pdf_document = models.ForeignKey(
        "documents.Document",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="explosion_concept_pdfs",
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "ex_concept"
        constraints = [
            models.CheckConstraint(
                check=models.Q(status__in=["draft", "review", "approved", "archived"]),
                name="ck_ex_concept_status_valid",
            ),
        ]
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"{self.title} ({self.version}) – {self.get_status_display()}"

    @property
    def can_transition_to_review(self) -> bool:
        """Alle Pflichtabschnitte ausgefüllt?"""
        return (
            self.status == self.Status.DRAFT
            and bool(self.process_description)
            and bool(self.release_grade)
            and self.zones.exists()
            and self.measures.filter(
                category=self.MeasureCategory if hasattr(self, "MeasureCategory") else "primary"
            ).exists()
        )

    @property
    def completion_percentage(self) -> int:
        """Fortschrittsindikator für Wizard (0–100)."""
        checks = [
            bool(self.process_description),
            bool(self.substitute_check_status) and self.substitute_check_status != "not_checked",
            bool(self.release_grade),
            self.zones.exists(),
            self.zones.filter(ignition_assessments__isnull=False).exists(),
            self.measures.filter(category="primary").exists(),
            self.measures.filter(category="secondary").exists(),
            bool(self.responsible_id),
        ]
        return int(sum(checks) / len(checks) * 100)
