"""DSB Module Models — Datenschutzbeauftragter (ADR-038)."""

import uuid
from datetime import timedelta

from django.db import models
from django.utils import timezone


# ---------------------------------------------------------------------------
# Mandate (betreutes Unternehmen)
# ---------------------------------------------------------------------------


class Mandate(models.Model):
    """Betreutes Unternehmen des DSB. KEIN Tenant — Subentität."""

    class Status(models.TextChoices):
        ACTIVE = "active", "Aktiv"
        PAUSED = "paused", "Pausiert"
        TERMINATED = "terminated", "Beendet"

    class Industry(models.TextChoices):
        HEALTHCARE = "healthcare", "Gesundheitswesen"
        FINANCE = "finance", "Finanzwesen"
        PUBLIC_SECTOR = "public_sector", "Öffentlicher Dienst"
        EDUCATION = "education", "Bildung"
        IT_TELECOM = "it_telecom", "IT & Telekommunikation"
        MANUFACTURING = "manufacturing", "Produzierendes Gewerbe"
        RETAIL = "retail", "Handel"
        LOGISTICS = "logistics", "Logistik"
        ENERGY = "energy", "Energie"
        OTHER = "other", "Sonstige"

    id = models.UUIDField(
        primary_key=True, default=uuid.uuid4, editable=False,
    )
    tenant_id = models.UUIDField(db_index=True)
    name = models.CharField(max_length=200)
    industry = models.CharField(
        max_length=20,
        choices=Industry.choices,
        blank=True,
        default="",
        help_text="Branche des betreuten Unternehmens",
    )
    employee_count = models.IntegerField(
        null=True,
        blank=True,
        help_text="Anzahl Beschäftigte (für Meldepflichten relevant)",
    )
    dsb_appointed_date = models.DateField(
        help_text="Datum der DSB-Bestellung",
    )
    contract_end_date = models.DateField(
        null=True,
        blank=True,
        help_text="Vertragsende (NULL = unbefristet)",
    )
    supervisory_authority = models.CharField(
        max_length=200,
        blank=True,
        default="",
        help_text="Zuständige Aufsichtsbehörde (z.B. LfDI Baden-Württemberg)",
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.ACTIVE,
    )
    created_by_id = models.UUIDField(null=True, blank=True)
    updated_by_id = models.UUIDField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "dsb_mandate"
        verbose_name = "Mandat"
        verbose_name_plural = "Mandate"
        ordering = ["name"]
        constraints = [
            models.UniqueConstraint(
                fields=["tenant_id", "name"],
                name="uq_dsb_mandate_tenant_name",
            ),
            models.CheckConstraint(
                check=models.Q(
                    status__in=["active", "paused", "terminated"],
                ),
                name="ck_dsb_mandate_status",
            ),
        ]
        indexes = [
            models.Index(
                fields=["tenant_id", "status"],
                name="idx_dsb_mandate_tenant_status",
            ),
        ]

    def __str__(self) -> str:
        return self.name


# ---------------------------------------------------------------------------
# Lookups — Globale Referenzdaten (kein tenant_id, ADR-038 R2-F13)
# ---------------------------------------------------------------------------

class Category(models.Model):
    """Datenkategorie (Art. 9 DSGVO). Global, nicht tenant-spezifisch."""

    id = models.UUIDField(
        primary_key=True, default=uuid.uuid4, editable=False,
    )
    key = models.CharField(max_length=50, unique=True)
    label = models.CharField(max_length=200)
    is_special_category = models.BooleanField(
        default=False,
        help_text="Art. 9 besondere Kategorie (Gesundheit, Religion, etc.)",
    )

    class Meta:
        db_table = "dsb_category"
        verbose_name = "Datenkategorie"
        verbose_name_plural = "Datenkategorien"
        ordering = ["key"]

    def __str__(self) -> str:
        return self.label


class SubjectGroup(models.Model):
    """Lookup: Betroffenengruppe (z.B. Beschäftigte, Kunden, Patienten)."""

    id = models.UUIDField(
        primary_key=True, default=uuid.uuid4, editable=False,
    )
    key = models.CharField(max_length=50, unique=True)
    label = models.CharField(max_length=200)

    class Meta:
        db_table = "dsb_subject_group"
        verbose_name = "Betroffenengruppe"
        verbose_name_plural = "Betroffenengruppen"
        ordering = ["key"]

    def __str__(self) -> str:
        return self.label


class Recipient(models.Model):
    """Lookup: Empfängerkategorie (Art. 30 Abs. 1 lit. d DSGVO)."""

    id = models.UUIDField(
        primary_key=True, default=uuid.uuid4, editable=False,
    )
    key = models.CharField(max_length=50, unique=True)
    label = models.CharField(max_length=200)

    class Meta:
        db_table = "dsb_recipient"
        verbose_name = "Empfängerkategorie"
        verbose_name_plural = "Empfängerkategorien"
        ordering = ["key"]

    def __str__(self) -> str:
        return self.label


class Purpose(models.Model):
    """Lookup: Verarbeitungszweck (Art. 30 Abs. 1 lit. b DSGVO)."""

    id = models.UUIDField(
        primary_key=True, default=uuid.uuid4, editable=False,
    )
    key = models.CharField(max_length=80, unique=True)
    label = models.CharField(max_length=300)

    class Meta:
        db_table = "dsb_purpose"
        verbose_name = "Verarbeitungszweck"
        verbose_name_plural = "Verarbeitungszwecke"
        ordering = ["key"]

    def __str__(self) -> str:
        return self.label


class TomCategory(models.Model):
    """Stammdaten-Katalog für TOM (Art. 32 DSGVO).

    Globale Vorlagen, z.B. 'Verschlüsselung', 'Zugriffsbeschränkung',
    'Schulung'. Tenant-spezifische Instanzen verweisen hierauf.
    """

    class MeasureType(models.TextChoices):
        TECHNICAL = "technical", "Technisch"
        ORGANIZATIONAL = "organizational", "Organisatorisch"

    id = models.UUIDField(
        primary_key=True, default=uuid.uuid4, editable=False,
    )
    key = models.CharField(max_length=80, unique=True)
    label = models.CharField(max_length=300)
    measure_type = models.CharField(
        max_length=20,
        choices=MeasureType.choices,
        help_text="Art der Maßnahme",
    )
    description = models.TextField(
        blank=True,
        default="",
        help_text="Beschreibung / Best Practice",
    )

    class Meta:
        db_table = "dsb_tom_category"
        verbose_name = "TOM-Katalog (Stammdaten)"
        verbose_name_plural = "TOM-Katalog (Stammdaten)"
        ordering = ["measure_type", "key"]

    def __str__(self) -> str:
        return f"[{self.get_measure_type_display()}] {self.label}"


class StandardRetentionPeriod(models.Model):
    """Stammdaten: Gesetzliche Aufbewahrungsfristen.

    Globaler Katalog wiederverwendbarer Löschfristen,
    z.B. '§ 257 HGB — 10 Jahre', '§ 147 AO — 10 Jahre'.
    """

    id = models.UUIDField(
        primary_key=True, default=uuid.uuid4, editable=False,
    )
    key = models.CharField(max_length=80, unique=True)
    label = models.CharField(max_length=300)
    legal_reference = models.CharField(
        max_length=200,
        help_text="Gesetzliche Grundlage (z.B. '§ 257 HGB')",
    )
    period = models.CharField(
        max_length=100,
        help_text="Frist (z.B. '10 Jahre', 'unverzüglich')",
    )
    notes = models.TextField(
        blank=True,
        default="",
    )

    class Meta:
        db_table = "dsb_standard_retention"
        verbose_name = "Löschfrist (Stammdaten)"
        verbose_name_plural = "Löschfristen (Stammdaten)"
        ordering = ["key"]

    def __str__(self) -> str:
        return f"{self.label} ({self.period})"


# ---------------------------------------------------------------------------
# VVT — Verarbeitungsverzeichnis (Art. 30 DSGVO)
# ---------------------------------------------------------------------------


class ProcessingActivity(models.Model):
    """Verarbeitungstätigkeit gemäß Art. 30 DSGVO (VVT)."""

    class LegalBasis(models.TextChoices):
        CONSENT = "consent", "Art. 6(1)(a) Einwilligung"
        CONTRACT = "contract", "Art. 6(1)(b) Vertragserfüllung"
        LEGAL_OBLIGATION = (
            "legal_obligation",
            "Art. 6(1)(c) Rechtl. Verpflichtung",
        )
        VITAL_INTEREST = (
            "vital_interest",
            "Art. 6(1)(d) Lebenswichtige Interessen",
        )
        PUBLIC_INTEREST = (
            "public_interest",
            "Art. 6(1)(e) Öffentliches Interesse",
        )
        LEGITIMATE_INTEREST = (
            "legitimate_interest",
            "Art. 6(1)(f) Berechtigtes Interesse",
        )

    class RiskLevel(models.TextChoices):
        LOW = "low", "Gering"
        MEDIUM = "medium", "Mittel"
        HIGH = "high", "Hoch"
        VERY_HIGH = "very_high", "Sehr hoch"

    id = models.UUIDField(
        primary_key=True, default=uuid.uuid4, editable=False,
    )
    tenant_id = models.UUIDField(db_index=True)
    mandate = models.ForeignKey(
        Mandate,
        on_delete=models.PROTECT,
        related_name="processing_activities",
    )
    number = models.PositiveIntegerField(
        help_text="Laufende Nummer im Mandat (z.B. 1, 2, 3)",
    )
    name = models.CharField(max_length=300)
    purposes = models.ManyToManyField(
        Purpose,
        blank=True,
        help_text="Zwecke der Verarbeitung (Art. 30 Abs. 1 lit. b)",
    )
    description = models.TextField(
        blank=True,
        default="",
        help_text="Ergänzende Beschreibung der Verarbeitung",
    )
    legal_basis = models.CharField(
        max_length=30,
        choices=LegalBasis.choices,
        help_text="Rechtsgrundlage nach Art. 6 Abs. 1 DSGVO",
    )
    data_categories = models.ManyToManyField(
        Category,
        blank=True,
        help_text="Kategorien personenbezogener Daten",
    )
    data_subjects = models.ManyToManyField(
        SubjectGroup,
        blank=True,
        help_text="Kategorien betroffener Personen",
    )
    recipients = models.ManyToManyField(
        Recipient,
        blank=True,
        help_text="Empfängerkategorien (Art. 30 Abs. 1 lit. d)",
    )
    technical_measures = models.ManyToManyField(
        "TechnicalMeasure",
        blank=True,
        help_text="Zugeordnete technische Maßnahmen",
    )
    organizational_measures = models.ManyToManyField(
        "OrganizationalMeasure",
        blank=True,
        help_text="Zugeordnete organisatorische Maßnahmen",
    )
    risk_level = models.CharField(
        max_length=20,
        choices=RiskLevel.choices,
        default=RiskLevel.LOW,
    )
    dsfa_required = models.BooleanField(
        default=False,
        help_text="DSFA erforderlich (Art. 35 DSGVO)",
    )
    created_by_id = models.UUIDField(null=True, blank=True)
    updated_by_id = models.UUIDField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "dsb_processing_activity"
        verbose_name = "Verarbeitungstätigkeit"
        verbose_name_plural = "Verarbeitungstätigkeiten"
        ordering = ["mandate", "number"]
        constraints = [
            models.UniqueConstraint(
                fields=["tenant_id", "mandate", "name"],
                name="uq_dsb_vvt_name_per_mandate",
            ),
            models.UniqueConstraint(
                fields=["tenant_id", "mandate", "number"],
                name="uq_dsb_vvt_num_per_mandate",
            ),
        ]
        indexes = [
            models.Index(
                fields=["tenant_id", "mandate"],
                name="idx_dsb_vvt_tenant_mandate",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.number}. {self.name}"


class ThirdCountryTransfer(models.Model):
    """Drittlandübermittlung zu einer Verarbeitungstätigkeit (Art. 44ff)."""

    class Safeguard(models.TextChoices):
        SCC = "scc", "Standardvertragsklauseln (SCC)"
        DPF = "dpf", "Data Privacy Framework (DPF)"
        BCR = "bcr", "Binding Corporate Rules (BCR)"
        ADEQUACY = "adequacy", "Angemessenheitsbeschluss"
        CONSENT = "consent", "Einwilligung (Art. 49)"
        OTHER = "other", "Sonstige"

    id = models.UUIDField(
        primary_key=True, default=uuid.uuid4, editable=False,
    )
    tenant_id = models.UUIDField(db_index=True)
    processing_activity = models.ForeignKey(
        ProcessingActivity,
        on_delete=models.CASCADE,
        related_name="third_country_transfers",
    )
    country = models.CharField(
        max_length=100,
        help_text="Zielland (z.B. USA, Indien)",
    )
    recipient_entity = models.CharField(
        max_length=200,
        blank=True,
        default="",
        help_text="Empfänger im Drittland (z.B. LinkedIn)",
    )
    safeguard = models.CharField(
        max_length=20,
        choices=Safeguard.choices,
        help_text="Absicherungsmechanismus (Art. 46 DSGVO)",
    )
    notes = models.TextField(
        blank=True,
        default="",
        help_text="Ergänzende Hinweise",
    )

    class Meta:
        db_table = "dsb_third_country_transfer"
        verbose_name = "Drittlandübermittlung"
        verbose_name_plural = "Drittlandübermittlungen"
        ordering = ["country"]

    def __str__(self) -> str:
        entity = f" ({self.recipient_entity})" if self.recipient_entity else ""
        return f"{self.country}{entity}"


class RetentionRule(models.Model):
    """Löschfrist/Aufbewahrungsregel einer Verarbeitungstätigkeit."""

    id = models.UUIDField(
        primary_key=True, default=uuid.uuid4, editable=False,
    )
    tenant_id = models.UUIDField(db_index=True)
    processing_activity = models.ForeignKey(
        ProcessingActivity,
        on_delete=models.CASCADE,
        related_name="retention_rules",
    )
    standard_period = models.ForeignKey(
        StandardRetentionPeriod,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="usages",
        help_text="Referenz auf Löschfristen-Stammdaten",
    )
    condition = models.CharField(
        max_length=200,
        help_text="Bedingung (z.B. 'bei fehlender Reaktion')",
    )
    period = models.CharField(
        max_length=100,
        help_text="Frist (z.B. '6-12 Monate', 'unverzüglich')",
    )
    legal_reference = models.CharField(
        max_length=200,
        blank=True,
        default="",
        help_text="Gesetzliche Grundlage (z.B. '§ 257 HGB')",
    )

    class Meta:
        db_table = "dsb_retention_rule"
        verbose_name = "Löschfrist"
        verbose_name_plural = "Löschfristen"
        ordering = ["condition"]

    def __str__(self) -> str:
        return f"{self.condition}: {self.period}"


# ---------------------------------------------------------------------------
# TOM — Technische und organisatorische Maßnahmen (Art. 32 DSGVO)
# ---------------------------------------------------------------------------


class TechnicalMeasure(models.Model):
    """Technische Maßnahme gemäß Art. 32 DSGVO."""

    class Status(models.TextChoices):
        PLANNED = "planned", "Geplant"
        IMPLEMENTED = "implemented", "Umgesetzt"
        VERIFIED = "verified", "Verifiziert"
        OBSOLETE = "obsolete", "Obsolet"

    id = models.UUIDField(
        primary_key=True, default=uuid.uuid4, editable=False,
    )
    tenant_id = models.UUIDField(db_index=True)
    mandate = models.ForeignKey(
        Mandate,
        on_delete=models.PROTECT,
        related_name="technical_measures",
    )
    category = models.ForeignKey(
        TomCategory,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="technical_instances",
        help_text="Referenz auf TOM-Katalog (Stammdaten)",
    )
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True, default="")
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PLANNED,
    )
    responsible_user_id = models.UUIDField(
        null=True,
        blank=True,
        help_text="Verantwortliche Person (User-ID)",
    )
    review_date = models.DateField(
        null=True,
        blank=True,
        help_text="Nächster Überprüfungstermin",
    )
    created_by_id = models.UUIDField(null=True, blank=True)
    updated_by_id = models.UUIDField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "dsb_technical_measure"
        verbose_name = "Technische Maßnahme"
        verbose_name_plural = "Technische Maßnahmen"
        ordering = ["title"]
        constraints = [
            models.UniqueConstraint(
                fields=["tenant_id", "mandate", "title"],
                name="uq_dsb_tech_meas_mandate",
            ),
        ]
        indexes = [
            models.Index(
                fields=["tenant_id", "status"],
                name="idx_dsb_tech_measure_status",
            ),
        ]

    def __str__(self) -> str:
        return self.title


class OrganizationalMeasure(models.Model):
    """Organisatorische Maßnahme gemäß Art. 32 DSGVO."""

    class Status(models.TextChoices):
        PLANNED = "planned", "Geplant"
        IMPLEMENTED = "implemented", "Umgesetzt"
        VERIFIED = "verified", "Verifiziert"
        OBSOLETE = "obsolete", "Obsolet"

    id = models.UUIDField(
        primary_key=True, default=uuid.uuid4, editable=False,
    )
    tenant_id = models.UUIDField(db_index=True)
    mandate = models.ForeignKey(
        Mandate,
        on_delete=models.PROTECT,
        related_name="organizational_measures",
    )
    category = models.ForeignKey(
        TomCategory,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="organizational_instances",
        help_text="Referenz auf TOM-Katalog (Stammdaten)",
    )
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True, default="")
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PLANNED,
    )
    responsible_user_id = models.UUIDField(
        null=True,
        blank=True,
        help_text="Verantwortliche Person (User-ID)",
    )
    review_date = models.DateField(
        null=True,
        blank=True,
        help_text="Nächster Überprüfungstermin",
    )
    created_by_id = models.UUIDField(null=True, blank=True)
    updated_by_id = models.UUIDField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "dsb_organizational_measure"
        verbose_name = "Organisatorische Maßnahme"
        verbose_name_plural = "Organisatorische Maßnahmen"
        ordering = ["title"]
        constraints = [
            models.UniqueConstraint(
                fields=["tenant_id", "mandate", "title"],
                name="uq_dsb_org_meas_mandate",
            ),
        ]
        indexes = [
            models.Index(
                fields=["tenant_id", "status"],
                name="idx_dsb_org_measure_status",
            ),
        ]

    def __str__(self) -> str:
        return self.title


# ---------------------------------------------------------------------------
# AVV — Auftragsverarbeitungsvertrag (Art. 28 DSGVO)
# ---------------------------------------------------------------------------


class DataProcessingAgreement(models.Model):
    """Auftragsverarbeitungsvertrag (AVV) gemäß Art. 28 DSGVO."""

    class Status(models.TextChoices):
        DRAFT = "draft", "Entwurf"
        ACTIVE = "active", "Aktiv"
        EXPIRED = "expired", "Abgelaufen"
        TERMINATED = "terminated", "Gekündigt"

    class Role(models.TextChoices):
        CONTROLLER = "controller", "Verantwortlicher"
        PROCESSOR = "processor", "Auftragsverarbeiter"
        JOINT_CONTROLLER = "joint", "Gemeinsam Verantwortliche"

    id = models.UUIDField(
        primary_key=True, default=uuid.uuid4, editable=False,
    )
    tenant_id = models.UUIDField(db_index=True)
    mandate = models.ForeignKey(
        Mandate,
        on_delete=models.PROTECT,
        related_name="dpa_agreements",
    )
    partner_name = models.CharField(
        max_length=300,
        help_text="Name des Vertragspartners",
    )
    partner_role = models.CharField(
        max_length=20,
        choices=Role.choices,
        default=Role.PROCESSOR,
        help_text="Rolle des Partners im Vertrag",
    )
    subject_matter = models.TextField(
        help_text="Gegenstand der Auftragsverarbeitung",
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.DRAFT,
    )
    effective_date = models.DateField(
        null=True,
        blank=True,
        help_text="Inkrafttreten",
    )
    expiry_date = models.DateField(
        null=True,
        blank=True,
        help_text="Ablaufdatum / Kündigungstermin",
    )
    data_categories = models.ManyToManyField(
        Category,
        blank=True,
        help_text="Verarbeitete Datenkategorien",
    )
    data_subjects = models.ManyToManyField(
        SubjectGroup,
        blank=True,
        help_text="Betroffene Personengruppen",
    )
    processing_activities = models.ManyToManyField(
        ProcessingActivity,
        blank=True,
        related_name="dpa_agreements",
        help_text="Zugeordnete Verarbeitungstätigkeiten",
    )
    technical_measures = models.ManyToManyField(
        "TechnicalMeasure",
        blank=True,
        help_text="Vereinbarte technische Maßnahmen",
    )
    organizational_measures = models.ManyToManyField(
        "OrganizationalMeasure",
        blank=True,
        help_text="Vereinbarte organisatorische Maßnahmen",
    )
    subprocessors_allowed = models.BooleanField(
        default=False,
        help_text="Unterauftragsverarbeitung zulässig",
    )
    subprocessors_notes = models.TextField(
        blank=True,
        default="",
        help_text="Hinweise zu Unterauftragsverarbeitern",
    )
    document_id = models.UUIDField(
        null=True,
        blank=True,
        db_index=True,
        help_text="FK zu documents.Document (lose Kopplung)",
    )
    notes = models.TextField(blank=True, default="")
    created_by_id = models.UUIDField(null=True, blank=True)
    updated_by_id = models.UUIDField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "dsb_dpa"
        verbose_name = "Auftragsverarbeitungsvertrag"
        verbose_name_plural = "Auftragsverarbeitungsverträge"
        ordering = ["partner_name"]
        indexes = [
            models.Index(
                fields=["tenant_id", "status"],
                name="idx_dsb_dpa_tenant_status",
            ),
        ]

    def __str__(self) -> str:
        return f"AVV: {self.partner_name} ({self.get_status_display()})"


# ---------------------------------------------------------------------------
# Audit — Datenschutz-Audits
# ---------------------------------------------------------------------------


class PrivacyAudit(models.Model):
    """Datenschutz-Audit."""

    class AuditType(models.TextChoices):
        INTERNAL = "internal", "Intern"
        EXTERNAL = "external", "Extern"
        SPOT_CHECK = "spot_check", "Stichprobe"

    class Status(models.TextChoices):
        PLANNED = "planned", "Geplant"
        IN_PROGRESS = "in_progress", "In Durchführung"
        COMPLETED = "completed", "Abgeschlossen"
        CANCELLED = "cancelled", "Abgebrochen"

    id = models.UUIDField(
        primary_key=True, default=uuid.uuid4, editable=False,
    )
    tenant_id = models.UUIDField(db_index=True)
    mandate = models.ForeignKey(
        Mandate,
        on_delete=models.PROTECT,
        related_name="audits",
    )
    title = models.CharField(
        max_length=300,
        help_text="Titel / Gegenstand des Audits",
    )
    audit_type = models.CharField(
        max_length=20,
        choices=AuditType.choices,
    )
    scheduled_date = models.DateField()
    completed_date = models.DateField(null=True, blank=True)
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PLANNED,
    )
    report_document_id = models.UUIDField(
        null=True,
        blank=True,
        db_index=True,
        help_text="FK zu documents.Document (lose Kopplung)",
    )
    created_by_id = models.UUIDField(null=True, blank=True)
    updated_by_id = models.UUIDField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "dsb_privacy_audit"
        verbose_name = "Datenschutz-Audit"
        verbose_name_plural = "Datenschutz-Audits"
        ordering = ["-scheduled_date"]
        indexes = [
            models.Index(
                fields=["tenant_id", "status"],
                name="idx_dsb_audit_tenant_status",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.title} ({self.get_audit_type_display()})"


class AuditFinding(models.Model):
    """Einzelbefund eines Audits."""

    class Severity(models.TextChoices):
        LOW = "low", "Gering"
        MEDIUM = "medium", "Mittel"
        HIGH = "high", "Hoch"
        CRITICAL = "critical", "Kritisch"

    class Status(models.TextChoices):
        OPEN = "open", "Offen"
        IN_PROGRESS = "in_progress", "In Bearbeitung"
        RESOLVED = "resolved", "Behoben"
        ACCEPTED = "accepted", "Akzeptiert"

    id = models.UUIDField(
        primary_key=True, default=uuid.uuid4, editable=False,
    )
    tenant_id = models.UUIDField(db_index=True)
    audit = models.ForeignKey(
        PrivacyAudit,
        on_delete=models.CASCADE,
        related_name="findings",
    )
    title = models.CharField(max_length=240)
    description = models.TextField(blank=True, default="")
    severity = models.CharField(
        max_length=20,
        choices=Severity.choices,
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.OPEN,
    )
    action_item_id = models.UUIDField(
        null=True,
        blank=True,
        db_index=True,
        help_text="FK zu actions.ActionItem (lose Kopplung)",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "dsb_audit_finding"
        verbose_name = "Audit-Befund"
        verbose_name_plural = "Audit-Befunde"
        ordering = ["-created_at"]
        indexes = [
            models.Index(
                fields=["tenant_id", "status"],
                name="idx_dsb_finding_tenant_status",
            ),
        ]

    def __str__(self) -> str:
        return self.title


# ---------------------------------------------------------------------------
# Deletion — Löschprotokolle (Art. 17 DSGVO)
# ---------------------------------------------------------------------------


class DeletionLog(models.Model):
    """Löschprotokoll gemäß Art. 17 DSGVO."""

    id = models.UUIDField(
        primary_key=True, default=uuid.uuid4, editable=False,
    )
    tenant_id = models.UUIDField(db_index=True)
    mandate = models.ForeignKey(
        Mandate,
        on_delete=models.PROTECT,
        related_name="deletion_logs",
    )
    processing_activity = models.ForeignKey(
        ProcessingActivity,
        on_delete=models.PROTECT,
        related_name="deletion_logs",
    )
    requested_at = models.DateTimeField()
    executed_at = models.DateTimeField(null=True, blank=True)
    data_category = models.ForeignKey(
        Category,
        on_delete=models.PROTECT,
        help_text="Gelöschte Datenkategorie",
    )
    record_count = models.IntegerField(
        null=True,
        blank=True,
        help_text="Anzahl gelöschter Datensätze",
    )
    method = models.CharField(
        max_length=100,
        help_text="Löschmethode (z.B. 'DB DELETE', 'Aktenvernichtung')",
    )
    confirmed_by_id = models.UUIDField(
        null=True,
        blank=True,
        help_text="User-ID des Bestätigenden (lose Kopplung)",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "dsb_deletion_log"
        verbose_name = "Löschprotokoll"
        verbose_name_plural = "Löschprotokolle"
        ordering = ["-requested_at"]
        indexes = [
            models.Index(
                fields=["tenant_id", "mandate"],
                name="idx_dsb_del_tenant_mandate",
            ),
        ]

    def __str__(self) -> str:
        return (
            f"Löschung {self.data_category}"
            f" @ {self.requested_at:%Y-%m-%d}"
        )


# ---------------------------------------------------------------------------
# Breach — Datenpannen (Art. 33 DSGVO)
# ---------------------------------------------------------------------------


class Breach(models.Model):
    """Datenpanne gemäß Art. 33 DSGVO."""

    class Severity(models.TextChoices):
        LOW = "low", "Gering"
        MEDIUM = "medium", "Mittel"
        HIGH = "high", "Hoch"
        CRITICAL = "critical", "Kritisch"

    id = models.UUIDField(
        primary_key=True, default=uuid.uuid4, editable=False,
    )
    tenant_id = models.UUIDField(db_index=True)
    mandate = models.ForeignKey(
        Mandate,
        on_delete=models.PROTECT,
        related_name="breaches",
    )
    discovered_at = models.DateTimeField()
    reported_to_authority_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Meldezeitpunkt an Aufsichtsbehörde",
    )
    severity = models.CharField(
        max_length=20,
        choices=Severity.choices,
    )
    affected_categories = models.ManyToManyField(
        Category,
        blank=True,
        help_text="Betroffene Datenkategorien (Art. 33 Abs. 3 lit. a)",
    )
    affected_count = models.IntegerField(
        null=True,
        blank=True,
        help_text="Ungefähre Anzahl betroffener Personen",
    )
    root_cause = models.TextField(blank=True, default="")
    measures_taken = models.TextField(
        blank=True,
        default="",
        help_text="Ergriffene Abhilfemaßnahmen (Art. 33 Abs. 3 lit. d)",
    )
    notified_subjects = models.BooleanField(
        default=False,
        help_text="Betroffene benachrichtigt (Art. 34 DSGVO)",
    )
    created_by_id = models.UUIDField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "dsb_breach"
        verbose_name = "Datenpanne"
        verbose_name_plural = "Datenpannen"
        ordering = ["-discovered_at"]
        indexes = [
            models.Index(
                fields=["tenant_id", "severity"],
                name="idx_dsb_breach_tenant_sev",
            ),
        ]

    def __str__(self) -> str:
        return (
            f"Datenpanne {self.discovered_at:%Y-%m-%d}"
            f" ({self.get_severity_display()})"
        )

    @property
    def deadline_72h(self):
        """72h-Meldefrist (Art. 33)."""
        return self.discovered_at + timedelta(hours=72)

    @property
    def is_overdue(self) -> bool:
        """Prüft ob 72h-Frist überschritten und noch nicht gemeldet."""
        return (
            self.reported_to_authority_at is None
            and timezone.now() > self.deadline_72h
        )
