"""
Brandschutz-Modul — Datenmodelle.

FireProtectionConcept  — Brandschutzkonzept (Kern-Entity, tenant-gebunden)
FireSection            — Brandabschnitt (Bereich innerhalb eines Konzepts)
EscapeRoute            — Flucht- und Rettungsweg
FireExtinguisher       — Feuerlöscher-Inventar
FireProtectionMeasure  — Brandschutzmaßnahme (baulich/technisch/organisatorisch)
"""

import uuid

from django.db import models


class FireProtectionConcept(models.Model):
    """Brandschutzkonzept für einen Standort/Bereich."""

    class Status(models.TextChoices):
        DRAFT = "draft", "Entwurf"
        IN_REVIEW = "in_review", "In Prüfung"
        APPROVED = "approved", "Freigegeben"
        OUTDATED = "outdated", "Veraltet"

    class ConceptType(models.TextChoices):
        BASIC = "basic", "Basiskonzept (§14 MBO)"
        FULL = "full", "Vollständiges Brandschutzkonzept"
        OPERATIONAL = "operational", "Betrieblicher Brandschutz"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant_id = models.UUIDField(db_index=True)
    site = models.ForeignKey(
        "tenancy.Site",
        on_delete=models.PROTECT,
        related_name="fire_protection_concepts",
    )
    title = models.CharField(max_length=240)
    concept_type = models.CharField(
        max_length=20,
        choices=ConceptType.choices,
        default=ConceptType.BASIC,
    )
    status = models.CharField(
        max_length=15,
        choices=Status.choices,
        default=Status.DRAFT,
        db_index=True,
    )
    description = models.TextField(blank=True, default="")
    valid_from = models.DateField(null=True, blank=True)
    valid_until = models.DateField(
        null=True,
        blank=True,
        help_text="Nächste Überprüfung / Ablaufdatum",
    )
    responsible_user_id = models.UUIDField(
        null=True,
        blank=True,
        help_text="Verantwortlicher Brandschutzbeauftragter",
    )
    approved_by_id = models.UUIDField(null=True, blank=True)
    approved_at = models.DateTimeField(null=True, blank=True)
    created_by_id = models.UUIDField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "brandschutz_concept"
        verbose_name = "Brandschutzkonzept"
        verbose_name_plural = "Brandschutzkonzepte"
        ordering = ["-created_at"]
        indexes = [
            models.Index(
                fields=["tenant_id", "status"],
                name="ix_bs_concept_tenant_status",
            ),
        ]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(status__in=["draft", "in_review", "approved", "outdated"]),
                name="ck_brandschutz_concept_status",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.title} ({self.get_status_display()})"

    @property
    def is_approved(self) -> bool:
        return self.status == self.Status.APPROVED

    @property
    def is_valid(self) -> bool:
        """True wenn freigegeben und gültig (valid_until nicht abgelaufen)."""
        from django.utils import timezone

        if self.status != self.Status.APPROVED:
            return False
        if self.valid_until and self.valid_until < timezone.now().date():
            return False
        return True


class FireSection(models.Model):
    """
    Brandabschnitt innerhalb eines Brandschutzkonzepts.

    Entspricht einem Bereich, der durch Brandschutzbauteile (Wände, Türen)
    von angrenzenden Bereichen abgetrennt ist.
    """

    class ConstructionClass(models.TextChoices):
        GK1 = "GK1", "GK1 — Freistehend, eingeschossig"
        GK2 = "GK2", "GK2 — bis 7 m, max. 2 Vollgeschosse"
        GK3 = "GK3", "GK3 — bis 7 m, mehr als 2 Vollgeschosse"
        GK4 = "GK4", "GK4 — bis 13 m Höhe"
        GK5 = "GK5", "GK5 — Hochhaus (>13 m)"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant_id = models.UUIDField(db_index=True)
    concept = models.ForeignKey(
        FireProtectionConcept,
        on_delete=models.CASCADE,
        related_name="sections",
    )
    name = models.CharField(max_length=200)
    floor = models.CharField(
        max_length=50,
        blank=True,
        default="",
        help_text="Stockwerk/Etage (z.B. 'EG', '1.OG', 'UG')",
    )
    area_sqm = models.FloatField(
        null=True,
        blank=True,
        help_text="Fläche in m²",
    )
    construction_class = models.CharField(
        max_length=5,
        choices=ConstructionClass.choices,
        blank=True,
        default="",
    )
    max_occupancy = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text="Maximale Personenanzahl (für Fluchtwegberechnung)",
    )
    fire_load_mj_m2 = models.FloatField(
        null=True,
        blank=True,
        help_text="Brandlast in MJ/m² (nach DIN 18230)",
    )
    has_sprinkler = models.BooleanField(default=False)
    has_smoke_detector = models.BooleanField(default=False)
    notes = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "brandschutz_section"
        verbose_name = "Brandabschnitt"
        verbose_name_plural = "Brandabschnitte"
        ordering = ["concept", "floor", "name"]
        constraints = [
            models.UniqueConstraint(
                fields=["concept", "name"],
                name="uq_bs_section_name_concept",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.name} ({self.floor})" if self.floor else self.name


class EscapeRoute(models.Model):
    """Flucht- und Rettungsweg innerhalb eines Brandabschnitts."""

    class RouteType(models.TextChoices):
        PRIMARY = "primary", "Erster Fluchtweg"
        SECONDARY = "secondary", "Zweiter Fluchtweg"
        EMERGENCY_EXIT = "emergency_exit", "Notausgang"
        RESCUE_ACCESS = "rescue_access", "Rettungszugang (Feuerwehr)"

    class Status(models.TextChoices):
        OK = "ok", "In Ordnung"
        DEFICIENT = "deficient", "Mängel vorhanden"
        BLOCKED = "blocked", "Blockiert"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant_id = models.UUIDField(db_index=True)
    section = models.ForeignKey(
        FireSection,
        on_delete=models.CASCADE,
        related_name="escape_routes",
    )
    route_type = models.CharField(
        max_length=20,
        choices=RouteType.choices,
    )
    description = models.TextField(
        help_text="Wegbeschreibung (z.B. 'Treppenhaus Nord → Ausgang Hof')",
    )
    length_m = models.FloatField(
        null=True,
        blank=True,
        help_text="Länge des Fluchtwegs in Metern",
    )
    width_m = models.FloatField(
        null=True,
        blank=True,
        help_text="Lichte Breite in Metern (Mindestanforderung: 0,9 m)",
    )
    door_width_m = models.FloatField(
        null=True,
        blank=True,
        help_text="Türbreite in Metern",
    )
    is_signposted = models.BooleanField(
        default=False,
        help_text="Rettungszeichenleuchten vorhanden",
    )
    status = models.CharField(
        max_length=15,
        choices=Status.choices,
        default=Status.OK,
        db_index=True,
    )
    last_inspection_date = models.DateField(null=True, blank=True)
    deficiency_notes = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "brandschutz_escape_route"
        verbose_name = "Flucht- und Rettungsweg"
        verbose_name_plural = "Flucht- und Rettungswege"
        ordering = ["section", "route_type"]

    def __str__(self) -> str:
        return f"{self.get_route_type_display()}: {self.description[:60]}"

    @property
    def meets_minimum_width(self) -> bool | None:
        """Prüft ob Mindestbreite 0,9 m eingehalten wird."""
        if self.width_m is None:
            return None
        return self.width_m >= 0.9


class FireExtinguisher(models.Model):
    """Feuerlöscher-Inventar."""

    class ExtinguisherType(models.TextChoices):
        WATER = "water", "Wasserlöscher"
        FOAM = "foam", "Schaumlöscher"
        CO2 = "co2", "CO₂-Löscher"
        DRY_POWDER = "dry_powder", "Pulverlöscher"
        WET_CHEMICAL = "wet_chemical", "Fettbrandlöscher"
        ABC_POWDER = "abc_powder", "ABC-Pulverlöscher"

    class Status(models.TextChoices):
        OPERATIONAL = "operational", "Betriebsbereit"
        INSPECTION_DUE = "inspection_due", "Prüfung fällig"
        DEFECTIVE = "defective", "Defekt"
        RETIRED = "retired", "Ausgemustert"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant_id = models.UUIDField(db_index=True)
    section = models.ForeignKey(
        FireSection,
        on_delete=models.CASCADE,
        related_name="fire_extinguishers",
    )
    serial_number = models.CharField(max_length=100, blank=True, default="")
    extinguisher_type = models.CharField(
        max_length=20,
        choices=ExtinguisherType.choices,
    )
    capacity_kg = models.FloatField(
        help_text="Füllmenge in kg (z.B. 6 kg für ABC-Löscher)",
    )
    fire_class = models.CharField(
        max_length=20,
        blank=True,
        default="",
        help_text="Brandklassen (z.B. 'A, B, C' oder 'F')",
    )
    location_description = models.CharField(
        max_length=300,
        help_text="Standortbeschreibung (z.B. 'Wand neben Notausgang Ost')",
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.OPERATIONAL,
        db_index=True,
    )
    last_inspection_date = models.DateField(null=True, blank=True)
    next_inspection_date = models.DateField(
        null=True,
        blank=True,
        help_text="Nächste Prüfung (BGV A3 / DGUV V3, alle 2 Jahre)",
    )
    installed_at = models.DateField(null=True, blank=True)
    notes = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "brandschutz_extinguisher"
        verbose_name = "Feuerlöscher"
        verbose_name_plural = "Feuerlöscher"
        ordering = ["section", "extinguisher_type"]
        indexes = [
            models.Index(
                fields=["tenant_id", "status"],
                name="ix_bs_ext_tenant_status",
            ),
            models.Index(
                fields=["tenant_id", "next_inspection_date"],
                name="ix_bs_ext_inspection",
            ),
        ]

    def __str__(self) -> str:
        return (
            f"{self.get_extinguisher_type_display()} {self.capacity_kg} kg"
            f" — {self.location_description[:50]}"
        )

    @property
    def is_inspection_due(self) -> bool:
        """True wenn Prüfdatum überschritten oder Prüfung fällig."""
        from django.utils import timezone

        if self.status == self.Status.INSPECTION_DUE:
            return True
        if self.next_inspection_date:
            return self.next_inspection_date <= timezone.now().date()
        return False


class FireProtectionMeasure(models.Model):
    """
    Brandschutzmaßnahme innerhalb eines Konzepts.

    Unterscheidet baulichen, anlagentechnischen und organisatorischen Brandschutz.
    """

    class Category(models.TextChoices):
        STRUCTURAL = "structural", "Baulicher Brandschutz"
        TECHNICAL = "technical", "Anlagentechnischer Brandschutz"
        ORGANIZATIONAL = "organizational", "Organisatorischer Brandschutz"

    class Status(models.TextChoices):
        OPEN = "open", "Offen"
        IN_PROGRESS = "in_progress", "In Bearbeitung"
        IMPLEMENTED = "implemented", "Umgesetzt"
        ACCEPTED = "accepted", "Akzeptiertes Risiko"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant_id = models.UUIDField(db_index=True)
    concept = models.ForeignKey(
        FireProtectionConcept,
        on_delete=models.CASCADE,
        related_name="measures",
    )
    section = models.ForeignKey(
        FireSection,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="measures",
        help_text="Optional: Zugeordneter Brandabschnitt",
    )
    category = models.CharField(
        max_length=20,
        choices=Category.choices,
        db_index=True,
    )
    title = models.CharField(max_length=300)
    description = models.TextField(blank=True, default="")
    legal_basis = models.CharField(
        max_length=200,
        blank=True,
        default="",
        help_text="z.B. 'MBO §14', 'ASR A2.3', 'DGUV R 215-220'",
    )
    status = models.CharField(
        max_length=15,
        choices=Status.choices,
        default=Status.OPEN,
        db_index=True,
    )
    responsible_user_id = models.UUIDField(null=True, blank=True)
    due_date = models.DateField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    sort_order = models.PositiveSmallIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "brandschutz_measure"
        verbose_name = "Brandschutzmaßnahme"
        verbose_name_plural = "Brandschutzmaßnahmen"
        ordering = ["category", "sort_order", "title"]
        indexes = [
            models.Index(
                fields=["tenant_id", "status"],
                name="ix_bs_measure_tenant_status",
            ),
        ]

    def __str__(self) -> str:
        return f"[{self.get_category_display()}] {self.title}"

    @property
    def is_overdue(self) -> bool:
        from django.utils import timezone

        if not self.due_date:
            return False
        return (
            self.status not in (self.Status.IMPLEMENTED, self.Status.ACCEPTED)
            and self.due_date < timezone.now().date()
        )


class ConceptDocument(models.Model):
    """Unterlage zu einem Brandschutzkonzept (ADR-147 Phase B).

    Speichert hochgeladene Dokumente mit Extraktionsergebnis und
    optionalem Template-JSON aus LLM-Analyse.
    """

    class DocStatus(models.TextChoices):
        UPLOADED = "uploaded", "Hochgeladen"
        EXTRACTING = "extracting", "Wird extrahiert"
        EXTRACTED = "extracted", "Text extrahiert"
        ANALYZING = "analyzing", "Wird analysiert"
        ANALYZED = "analyzed", "Analysiert"
        FAILED = "failed", "Fehlgeschlagen"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant_id = models.UUIDField(db_index=True)
    concept = models.ForeignKey(
        FireProtectionConcept,
        on_delete=models.CASCADE,
        related_name="concept_documents",
    )
    title = models.CharField(max_length=240)
    scope = models.CharField(
        max_length=30,
        blank=True,
        default="brandschutz",
    )
    source_filename = models.CharField(max_length=255, blank=True, default="")
    content_type = models.CharField(max_length=120, blank=True, default="")
    extracted_text = models.TextField(blank=True, default="")
    extraction_warnings = models.TextField(
        blank=True,
        default="",
        help_text="JSON-Liste von Warnungen aus der Extraktion",
    )
    page_count = models.IntegerField(null=True, blank=True)
    template_json = models.TextField(
        blank=True,
        default="",
        help_text="Serialisiertes ConceptTemplate nach LLM-Analyse",
    )
    analysis_confidence = models.FloatField(
        null=True,
        blank=True,
        help_text="0.0-1.0, Konfidenz der LLM-Strukturanalyse",
    )
    status = models.CharField(
        max_length=20,
        choices=DocStatus.choices,
        default=DocStatus.UPLOADED,
        db_index=True,
    )
    error_message = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    deleted_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "brandschutz_concept_document"
        verbose_name = "Konzept-Unterlage"
        verbose_name_plural = "Konzept-Unterlagen"
        ordering = ["-created_at"]
        indexes = [
            models.Index(
                fields=["tenant_id", "status"],
                name="ix_bs_cdoc_tenant_status",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.title} ({self.get_status_display()})"

    @property
    def is_deleted(self) -> bool:
        return self.deleted_at is not None

    @property
    def has_extracted_text(self) -> bool:
        return bool(self.extracted_text)

    @property
    def has_template(self) -> bool:
        return bool(self.template_json)


class ConceptTemplateStore(models.Model):
    """Persistiertes Konzept-Template (ADR-147 Phase E).

    Wird erstellt aus:
    - LLM-Analyse eines ConceptDocument (template_json → hier persistiert)
    - Built-in Frameworks (brandschutz_mbo, exschutz_trgs720)
    - Manueller Merge mehrerer Analysen
    """

    class TemplateSource(models.TextChoices):
        ANALYZED = "analyzed", "Aus Dokumentanalyse"
        BUILTIN = "builtin", "Framework-Vorlage"
        MERGED = "merged", "Zusammengeführt"
        MANUAL = "manual", "Manuell erstellt"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant_id = models.UUIDField(db_index=True)
    name = models.CharField(max_length=200)
    scope = models.CharField(max_length=30, default="brandschutz")
    version = models.CharField(max_length=20, default="1.0")
    is_master = models.BooleanField(default=False)
    framework = models.CharField(max_length=100, blank=True, default="")
    source = models.CharField(
        max_length=20,
        choices=TemplateSource.choices,
        default=TemplateSource.ANALYZED,
    )
    source_document = models.ForeignKey(
        ConceptDocument,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="generated_templates",
    )
    template_json = models.TextField(
        help_text="Serialisiertes ConceptTemplate (Pydantic JSON)",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "brandschutz_concept_template_store"
        verbose_name = "Konzept-Template"
        verbose_name_plural = "Konzept-Templates"
        ordering = ["-updated_at"]
        indexes = [
            models.Index(
                fields=["tenant_id", "scope"],
                name="ix_bs_ctmpl_tenant_scope",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.name} v{self.version} ({self.get_source_display()})"


class FilledTemplate(models.Model):
    """Ausgefülltes Template für ein Brandschutzkonzept (ADR-147 Phase E).

    Enthält die vom Benutzer (und optional KI) eingetragenen Werte
    für ein ConceptTemplateStore. Daraus wird das finale Dokument generiert.
    """

    class FillStatus(models.TextChoices):
        DRAFT = "draft", "Entwurf"
        REVIEW = "review", "In Prüfung"
        APPROVED = "approved", "Freigegeben"
        EXPORTED = "exported", "Exportiert"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant_id = models.UUIDField(db_index=True)
    concept = models.ForeignKey(
        FireProtectionConcept,
        on_delete=models.CASCADE,
        related_name="filled_templates",
    )
    template = models.ForeignKey(
        ConceptTemplateStore,
        on_delete=models.PROTECT,
        related_name="filled_instances",
    )
    name = models.CharField(max_length=240)
    values_json = models.TextField(
        default="{}",
        help_text="JSON: {section_name: {field_name: value}}",
    )
    status = models.CharField(
        max_length=20,
        choices=FillStatus.choices,
        default=FillStatus.DRAFT,
        db_index=True,
    )
    generated_pdf_key = models.CharField(
        max_length=500,
        blank=True,
        default="",
        help_text="S3-Pfad des generierten PDFs",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "brandschutz_filled_template"
        verbose_name = "Ausgefülltes Template"
        verbose_name_plural = "Ausgefüllte Templates"
        ordering = ["-updated_at"]
        indexes = [
            models.Index(
                fields=["tenant_id", "status"],
                name="ix_bs_ftmpl_tenant_status",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.name} ({self.get_status_display()})"
