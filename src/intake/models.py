from django.db import models
from django.utils.translation import gettext_lazy as _


class IntakeUpload(models.Model):
    STATUS_PENDING = "pending"
    STATUS_PROCESSING = "processing"
    STATUS_DONE = "done"
    STATUS_ERROR = "error"
    STATUS_CHOICES = [
        (STATUS_PENDING, _("Ausstehend")),
        (STATUS_PROCESSING, _("Wird verarbeitet")),
        (STATUS_DONE, _("Fertig")),
        (STATUS_ERROR, _("Fehler")),
    ]

    facility = models.ForeignKey(
        "tenancy.Facility",
        on_delete=models.PROTECT,
        related_name="intake_uploads",
        verbose_name=_("Betrieb"),
    )
    original_filename = models.CharField(max_length=255, verbose_name=_("Dateiname"))
    file = models.FileField(upload_to="intake/%Y/%m/", verbose_name=_("Datei"))

    doc_type = models.CharField(max_length=100, blank=True, verbose_name=_("Erkannter Typ"))
    doc_type_confidence = models.CharField(
        max_length=10, blank=True, verbose_name=_("Konfidenz")
    )
    extracted_text = models.TextField(blank=True, verbose_name=_("Extrahierter Text"))

    suggested_targets = models.JSONField(default=list, verbose_name=_("Vorgeschlagene Ziele"))
    selected_targets = models.JSONField(default=list, verbose_name=_("Ausgewählte Ziele"))

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default=STATUS_PENDING,
        verbose_name=_("Status"),
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = _("Intake Upload")
        verbose_name_plural = _("Intake Uploads")

    def __str__(self) -> str:
        return f"{self.original_filename} ({self.get_status_display()})"


class IntakeResult(models.Model):
    STATUS_OK = "ok"
    STATUS_ERROR = "error"
    STATUS_SKIPPED = "skipped"
    STATUS_CHOICES = [
        (STATUS_OK, _("OK")),
        (STATUS_ERROR, _("Fehler")),
        (STATUS_SKIPPED, _("Übersprungen")),
    ]

    upload = models.ForeignKey(
        IntakeUpload,
        on_delete=models.CASCADE,
        related_name="results",
        verbose_name=_("Upload"),
    )
    target_code = models.CharField(max_length=50, verbose_name=_("Ziel"))
    status = models.CharField(
        max_length=10,
        choices=STATUS_CHOICES,
        verbose_name=_("Status"),
    )
    result_id = models.IntegerField(null=True, blank=True, verbose_name=_("Ergebnis-ID"))
    result_url = models.CharField(max_length=500, blank=True, verbose_name=_("Ergebnis-URL"))
    error_message = models.TextField(blank=True, verbose_name=_("Fehlermeldung"))
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = [("upload", "target_code")]
        verbose_name = _("Intake Result")
        verbose_name_plural = _("Intake Results")

    def __str__(self) -> str:
        return f"{self.upload} → {self.target_code} [{self.status}]"
