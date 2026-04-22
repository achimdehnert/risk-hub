# src/explosionsschutz/models/generation_log.py
"""
Forensischer Audit-Log für KI-Calls gegen ExplosionConcept (ADR-018).

Jeder LLM-Call wird gespeichert: Prompt, Response, Tokens, Status,
Accept/Reject — für Compliance (GefStoffV 10 Jahre) und Debugging.
"""

from django.conf import settings
from django.db import models
from django_tenancy.managers import TenantManager


class GenerationChapter(models.TextChoices):
    ZONES = "zones", "Zoneneinteilung"
    IGNITION = "ignition", "Zündquellen"
    MEASURES = "measures", "Schutzmaßnahmen"
    SUMMARY = "summary", "Zusammenfassung"


class GenerationStatus(models.TextChoices):
    RUNNING = "running", "Läuft"
    SUCCESS = "success", "Erfolgreich"
    FAILED = "failed", "Fehlgeschlagen"
    ACCEPTED = "accepted", "Übernommen"
    REJECTED = "rejected", "Verworfen"


class ExplosionConceptGenerationLog(models.Model):
    """Forensischer Audit-Log jedes KI-Calls (ADR-018).

    Unveränderlich nach Erstellung (kein Edit, kein Delete im Normalfall).
    Aufbewahrungsfrist: 10 Jahre (GefStoffV § 6 Abs. 9).
    """

    tenant_id = models.UUIDField(db_index=True)

    concept = models.ForeignKey(
        "explosionsschutz.ExplosionConcept",
        on_delete=models.PROTECT,
        related_name="generation_logs",
        help_text="PROTECT: Log-Zeilen bleiben für Compliance erhalten",
    )

    chapter = models.CharField(
        max_length=32,
        choices=GenerationChapter.choices,
        help_text="Welcher Abschnitt wurde generiert",
    )
    status = models.CharField(
        max_length=16,
        choices=GenerationStatus.choices,
        default=GenerationStatus.RUNNING,
    )

    # iil-aifw Routing-Information
    action_code = models.CharField(
        max_length=100,
        help_text="AIActionType.code aus iil-aifw, z.B. 'ex_concept_zones'",
    )
    model_name = models.CharField(
        max_length=100,
        blank=True,
        help_text="LLMResult.model — befüllt nach API-Call",
    )

    # Prompt-Reproduzierbarkeit
    prompt_hash = models.CharField(
        max_length=64,
        db_index=True,
        help_text="SHA-256 von system+user prompt (Reproduzierbarkeit)",
    )
    prompt_system = models.TextField(help_text="System-Prompt zum Zeitpunkt des Calls")
    prompt_user = models.TextField(help_text="User-Prompt (Kontext-Snapshot)")
    input_context = models.JSONField(
        default=dict,
        help_text="Serialisierter Eingabe-Kontext (Stoff, Bereich, Zonen, ...)",
    )

    # Response
    response_text = models.TextField(blank=True)
    error_message = models.TextField(blank=True)

    # Token-Tracking (getrennt für Kosten-Analytics)
    input_tokens = models.PositiveIntegerField(default=0)
    output_tokens = models.PositiveIntegerField(default=0)

    # Timing
    finished_at = models.DateTimeField(null=True, blank=True)

    # Standard-Audit-Felder
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # Review / Übernahme durch Experten
    accepted_at = models.DateTimeField(null=True, blank=True)
    accepted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
        help_text="Experte der den Vorschlag übernommen / abgelehnt hat",
    )
    changes_on_adoption = models.TextField(
        blank=True,
        help_text="Vom Experten vorgenommene Änderungen am Vorschlag",
    )

    objects = TenantManager()

    class Meta:
        app_label = "explosionsschutz"
        db_table = "ex_concept_generation_log"
        verbose_name = "KI-Generierungslog"
        verbose_name_plural = "KI-Generierungslogs"
        ordering = ["-created_at"]
        indexes = [
            models.Index(
                fields=["concept", "chapter", "-created_at"],
                name="idx_genlog_concept_chapter",
            ),
            models.Index(
                fields=["tenant_id", "status", "-created_at"],
                name="idx_genlog_tenant_status",
            ),
            models.Index(
                fields=["prompt_hash"],
                name="idx_genlog_prompt_hash",
            ),
        ]
        constraints = [
            models.CheckConstraint(
                condition=(
                    ~models.Q(status=GenerationStatus.SUCCESS)
                    | models.Q(response_text__gt="")
                ),
                name="ex_gen_log_success_requires_response",
            ),
        ]

    def __str__(self) -> str:
        return f"GenLog #{self.pk} {self.chapter} ({self.status})"

    @property
    def total_tokens(self) -> int:
        return self.input_tokens + self.output_tokens

    @property
    def was_accepted(self) -> bool:
        return self.status == GenerationStatus.ACCEPTED
