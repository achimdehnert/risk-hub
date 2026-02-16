"""DSB Module Models — Datenschutzbeauftragter (ADR-038)."""

import uuid
from datetime import timedelta

from django.conf import settings
from django.db import models


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
        on_delete=models.CASCADE,
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
        ordering = ["name"]
        constraints = [
            models.UniqueConstraint(
                fields=["tenant_id", "mandate", "name"],
                name="uq_dsb_vvt_name_per_mandate",
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
    processing_activity = models.ForeignKey(
        ProcessingActivity,
        on_delete=models.CASCADE,
        related_name="retention_rules",
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
        on_delete=models.CASCADE,
        related_name="technical_measures",
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
        on_delete=models.CASCADE,
        related_name="organizational_measures",
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
        on_delete=models.CASCADE,
        related_name="audits",
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
        return f"{self.get_audit_type_display()} @ {self.scheduled_date}"


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
        on_delete=models.CASCADE,
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
    confirmed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
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
        on_delete=models.CASCADE,
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
        from django.utils import timezone

        return (
            self.reported_to_authority_at is None
            and timezone.now() > self.deadline_72h
        )
