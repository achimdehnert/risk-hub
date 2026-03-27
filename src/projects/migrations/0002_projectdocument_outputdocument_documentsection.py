"""Add ProjectDocument, OutputDocument, DocumentSection (ADR-041 Phase 2+4)."""

import uuid

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("projects", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="ProjectDocument",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "uuid",
                    models.UUIDField(
                        default=uuid.uuid4,
                        editable=False,
                        unique=True,
                    ),
                ),
                ("tenant_id", models.UUIDField(db_index=True)),
                ("title", models.CharField(max_length=255)),
                (
                    "doc_type",
                    models.CharField(
                        choices=[
                            ("sds", "Sicherheitsdatenblatt"),
                            ("plan", "Grundriss/Anlagenplan"),
                            ("gutachten", "Bestehendes Gutachten"),
                            ("regulation", "Regelwerk/Norm"),
                            ("process", "Verfahrensbeschreibung"),
                            ("other", "Sonstiges"),
                        ],
                        default="other",
                        max_length=20,
                    ),
                ),
                (
                    "file",
                    models.FileField(upload_to="projects/docs/%Y/%m/"),
                ),
                (
                    "extracted_text",
                    models.TextField(blank=True, default=""),
                ),
                (
                    "page_count",
                    models.IntegerField(blank=True, null=True),
                ),
                (
                    "ai_summary",
                    models.TextField(blank=True, default=""),
                ),
                (
                    "created_at",
                    models.DateTimeField(auto_now_add=True),
                ),
                (
                    "project",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="documents",
                        to="projects.project",
                    ),
                ),
                (
                    "uploaded_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "verbose_name": "Projektunterlage",
                "verbose_name_plural": "Projektunterlagen",
                "db_table": "project_document",
                "ordering": ["-created_at"],
            },
        ),
        migrations.CreateModel(
            name="OutputDocument",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "uuid",
                    models.UUIDField(
                        default=uuid.uuid4,
                        editable=False,
                        unique=True,
                    ),
                ),
                ("tenant_id", models.UUIDField(db_index=True)),
                (
                    "kind",
                    models.CharField(
                        help_text="Dokumenttyp, z.B. ex_schutz, gbu, brandschutz",
                        max_length=50,
                    ),
                ),
                ("title", models.CharField(max_length=255)),
                (
                    "version",
                    models.PositiveIntegerField(default=1),
                ),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("draft", "Entwurf"),
                            ("review", "In Prüfung"),
                            ("approved", "Freigegeben"),
                        ],
                        default="draft",
                        max_length=20,
                    ),
                ),
                (
                    "created_at",
                    models.DateTimeField(auto_now_add=True),
                ),
                (
                    "updated_at",
                    models.DateTimeField(auto_now=True),
                ),
                (
                    "project",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="output_documents",
                        to="projects.project",
                    ),
                ),
                (
                    "created_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "verbose_name": "Ausgabedokument",
                "verbose_name_plural": "Ausgabedokumente",
                "db_table": "project_output_document",
                "ordering": ["-updated_at"],
            },
        ),
        migrations.CreateModel(
            name="DocumentSection",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("section_key", models.CharField(max_length=50)),
                ("title", models.CharField(max_length=255)),
                (
                    "order",
                    models.PositiveIntegerField(default=0),
                ),
                (
                    "content",
                    models.TextField(blank=True, default=""),
                ),
                (
                    "is_ai_generated",
                    models.BooleanField(default=False),
                ),
                (
                    "created_at",
                    models.DateTimeField(auto_now_add=True),
                ),
                (
                    "updated_at",
                    models.DateTimeField(auto_now=True),
                ),
                (
                    "document",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="sections",
                        to="projects.outputdocument",
                    ),
                ),
            ],
            options={
                "verbose_name": "Dokumentabschnitt",
                "verbose_name_plural": "Dokumentabschnitte",
                "db_table": "project_document_section",
                "ordering": ["order"],
            },
        ),
    ]
