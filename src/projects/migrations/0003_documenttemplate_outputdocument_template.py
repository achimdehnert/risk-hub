"""Add DocumentTemplate model and OutputDocument.template FK."""

import uuid

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("projects", "0002_projectdocument_outputdocument_documentsection"),
    ]

    operations = [
        migrations.CreateModel(
            name="DocumentTemplate",
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
                ("name", models.CharField(max_length=255)),
                (
                    "description",
                    models.TextField(blank=True, default=""),
                ),
                (
                    "kind",
                    models.CharField(
                        blank=True,
                        default="",
                        help_text="Dokumenttyp, z.B. ex_schutz, gbu",
                        max_length=50,
                    ),
                ),
                (
                    "structure_json",
                    models.TextField(
                        default='{"sections": []}',
                        help_text="Template-Struktur als JSON",
                    ),
                ),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("draft", "Entwurf"),
                            ("accepted", "Akzeptiert"),
                            ("archived", "Archiviert"),
                        ],
                        default="draft",
                        max_length=20,
                    ),
                ),
                (
                    "source_filename",
                    models.CharField(
                        blank=True, default="", max_length=255,
                    ),
                ),
                (
                    "source_text",
                    models.TextField(blank=True, default=""),
                ),
                (
                    "created_at",
                    models.DateTimeField(auto_now_add=True),
                ),
                (
                    "updated_at",
                    models.DateTimeField(auto_now=True),
                ),
            ],
            options={
                "verbose_name": "Dokumentvorlage",
                "verbose_name_plural": "Dokumentvorlagen",
                "db_table": "project_doc_template",
                "ordering": ["-updated_at"],
                "indexes": [
                    models.Index(
                        fields=["tenant_id", "status"],
                        name="ix_doctmpl_tenant_status",
                    ),
                ],
            },
        ),
        migrations.AddField(
            model_name="outputdocument",
            name="template",
            field=models.ForeignKey(
                blank=True,
                help_text="Verwendete Dokumentvorlage",
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="output_documents",
                to="projects.documenttemplate",
            ),
        ),
    ]
