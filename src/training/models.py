"""Training models for hazardous substance instruction management (UC-009).

Enthält:
- TrainingTopic (Unterweisungsthema)
- TrainingSession (Durchgeführte Unterweisung)
- TrainingAttendance (Teilnahme-Nachweis pro Person)
"""

from django.db import models
from django_tenancy.managers import TenantManager

# =============================================================================
# TRAINING TOPIC (Unterweisungsthema)
# =============================================================================


class TrainingTopic(models.Model):
    """Unterweisungsthema mit Bezug zu Gefahrstoff/Standort/Abteilung.

    Definiert WAS unterwiesen wird und in welchem Intervall.
    """

    class Interval(models.TextChoices):
        ANNUAL = "annual", "Jährlich"
        SEMI_ANNUAL = "semi_annual", "Halbjährlich"
        QUARTERLY = "quarterly", "Vierteljährlich"
        ON_CHANGE = "on_change", "Bei Änderung"

    tenant_id = models.UUIDField(db_index=True)
    title = models.CharField(max_length=300)
    description = models.TextField(blank=True, default="")
    interval = models.CharField(
        max_length=20,
        choices=Interval.choices,
        default=Interval.ANNUAL,
    )

    site = models.ForeignKey(
        "tenancy.Site",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="training_topics",
    )
    department = models.ForeignKey(
        "tenancy.Department",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="training_topics",
    )
    products = models.ManyToManyField(
        "substances.Product",
        blank=True,
        related_name="training_topics",
        help_text="Verknüpfte Gefahrstoffe/Produkte",
    )

    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = TenantManager()

    class Meta:
        db_table = "training_topic"
        verbose_name = "Unterweisungsthema"
        verbose_name_plural = "Unterweisungsthemen"
        ordering = ["title"]
        indexes = [
            models.Index(
                fields=["tenant_id", "is_active"],
                name="ix_training_topic_active",
            ),
        ]

    def __str__(self) -> str:
        return self.title


# =============================================================================
# TRAINING SESSION (Durchgeführte Unterweisung)
# =============================================================================


class TrainingSession(models.Model):
    """Durchgeführte Unterweisungs-Veranstaltung.

    Eine Session hat genau ein Topic, einen Trainer, ein Datum
    und beliebig viele Teilnehmer (über TrainingAttendance).
    """

    class Status(models.TextChoices):
        PLANNED = "planned", "Geplant"
        COMPLETED = "completed", "Durchgeführt"
        CANCELLED = "cancelled", "Abgesagt"

    tenant_id = models.UUIDField(db_index=True)
    topic = models.ForeignKey(
        TrainingTopic,
        on_delete=models.CASCADE,
        related_name="sessions",
    )
    trainer_id = models.UUIDField(
        db_index=True,
        help_text="User-ID des Unterweisenden",
    )
    session_date = models.DateField(help_text="Datum der Unterweisung")
    status = models.CharField(
        max_length=15,
        choices=Status.choices,
        default=Status.PLANNED,
    )
    document = models.ForeignKey(
        "documents.Document",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="training_sessions",
        help_text="Unterweisungsnachweis (PDF/Scan)",
    )
    notes = models.TextField(blank=True, default="")

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = TenantManager()

    class Meta:
        db_table = "training_session"
        verbose_name = "Unterweisungs-Veranstaltung"
        verbose_name_plural = "Unterweisungs-Veranstaltungen"
        ordering = ["-session_date"]
        indexes = [
            models.Index(
                fields=["tenant_id", "session_date"],
                name="ix_training_session_date",
            ),
            models.Index(
                fields=["tenant_id", "status"],
                name="ix_training_session_status",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.topic.title} — {self.session_date}"


# =============================================================================
# TRAINING ATTENDANCE (Teilnahme-Nachweis)
# =============================================================================


class TrainingAttendance(models.Model):
    """Teilnahme-Nachweis einer Person an einer Unterweisungs-Session.

    Bildet die N:M-Beziehung Session↔Person ab, mit individuellem
    Status und optional unterschriebener Bestätigung.
    """

    class AttendanceStatus(models.TextChoices):
        PRESENT = "present", "Anwesend"
        ABSENT = "absent", "Abwesend"
        EXCUSED = "excused", "Entschuldigt"
        MAKEUP = "makeup", "Nachschulung"

    tenant_id = models.UUIDField(db_index=True)
    session = models.ForeignKey(
        TrainingSession,
        on_delete=models.CASCADE,
        related_name="attendances",
    )
    user_id = models.PositiveBigIntegerField(
        db_index=True,
        help_text="User-ID des Teilnehmers (FK zu identity.User.pk)",
    )
    status = models.CharField(
        max_length=10,
        choices=AttendanceStatus.choices,
        default=AttendanceStatus.PRESENT,
    )
    signed_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Zeitpunkt der digitalen Unterschrift / Bestätigung",
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = TenantManager()

    class Meta:
        db_table = "training_attendance"
        verbose_name = "Teilnahme-Nachweis"
        verbose_name_plural = "Teilnahme-Nachweise"
        constraints = [
            models.UniqueConstraint(
                fields=["session", "user_id"],
                name="uq_attendance_session_user",
            ),
        ]
        indexes = [
            models.Index(
                fields=["tenant_id", "user_id"],
                name="ix_attendance_tenant_user",
            ),
        ]

    def __str__(self) -> str:
        return f"Teilnahme {self.user_id} @ {self.session}"
