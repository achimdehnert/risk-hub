"""Add ConceptDocument model for concept-template integration (ADR-147 Phase B)."""

import uuid

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("brandschutz", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="ConceptDocument",
            fields=[
                (
                    "id",
                    models.UUIDField(
                        default=uuid.uuid4,
                        editable=False,
                        primary_key=True,
                        serialize=False,
                    ),
                ),
                ("tenant_id", models.UUIDField(db_index=True)),
                ("title", models.CharField(max_length=240)),
                (
                    "scope",
                    models.CharField(
                        blank=True, default="brandschutz", max_length=30
                    ),
                ),
                (
                    "source_filename",
                    models.CharField(blank=True, default="", max_length=255),
                ),
                (
                    "content_type",
                    models.CharField(blank=True, default="", max_length=120),
                ),
                (
                    "extracted_text",
                    models.TextField(blank=True, default=""),
                ),
                (
                    "extraction_warnings",
                    models.TextField(
                        blank=True,
                        default="",
                        help_text="JSON-Liste von Warnungen aus der Extraktion",
                    ),
                ),
                (
                    "page_count",
                    models.IntegerField(blank=True, null=True),
                ),
                (
                    "template_json",
                    models.TextField(
                        blank=True,
                        default="",
                        help_text="Serialisiertes ConceptTemplate nach LLM-Analyse",
                    ),
                ),
                (
                    "analysis_confidence",
                    models.FloatField(
                        blank=True,
                        help_text="0.0-1.0, Konfidenz der LLM-Strukturanalyse",
                        null=True,
                    ),
                ),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("uploaded", "Hochgeladen"),
                            ("extracting", "Wird extrahiert"),
                            ("extracted", "Text extrahiert"),
                            ("analyzing", "Wird analysiert"),
                            ("analyzed", "Analysiert"),
                            ("failed", "Fehlgeschlagen"),
                        ],
                        db_index=True,
                        default="uploaded",
                        max_length=20,
                    ),
                ),
                (
                    "error_message",
                    models.TextField(blank=True, default=""),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "deleted_at",
                    models.DateTimeField(blank=True, null=True),
                ),
                (
                    "concept",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="concept_documents",
                        to="brandschutz.fireprotectionconcept",
                    ),
                ),
            ],
            options={
                "verbose_name": "Konzept-Unterlage",
                "verbose_name_plural": "Konzept-Unterlagen",
                "db_table": "brandschutz_concept_document",
                "ordering": ["-created_at"],
                "indexes": [
                    models.Index(
                        fields=["tenant_id", "status"],
                        name="ix_bs_cdoc_tenant_status",
                    ),
                ],
            },
        ),
    ]
