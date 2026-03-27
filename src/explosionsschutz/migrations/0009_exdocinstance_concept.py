# Generated manually — register ExDocTemplate/ExDocInstance
# in migration state (tables already exist) + add concept FK.

import uuid

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("explosionsschutz", "0008_concept_templates"),
    ]

    operations = [
        # 1. Register ExDocTemplate in state (table exists)
        migrations.SeparateDatabaseAndState(
            state_operations=[
                migrations.CreateModel(
                    name="ExDocTemplate",
                    fields=[
                        ("id", models.BigAutoField(
                            auto_created=True,
                            primary_key=True,
                            serialize=False,
                            verbose_name="ID",
                        )),
                        ("uuid", models.UUIDField(
                            default=uuid.uuid4,
                            editable=False,
                            unique=True,
                        )),
                        ("tenant_id", models.UUIDField(
                            db_index=True,
                        )),
                        ("name", models.CharField(
                            max_length=255,
                        )),
                        ("description", models.TextField(
                            blank=True, default="",
                        )),
                        ("structure_json", models.TextField(
                            default='{"sections": []}',
                        )),
                        ("status", models.CharField(
                            choices=[
                                ("draft", "Entwurf"),
                                ("accepted", "Akzeptiert"),
                                ("archived", "Archiviert"),
                            ],
                            default="draft",
                            max_length=20,
                        )),
                        ("source_filename", models.CharField(
                            blank=True, default="",
                            max_length=255,
                        )),
                        ("source_text", models.TextField(
                            blank=True, default="",
                        )),
                        ("created_at", models.DateTimeField(
                            auto_now_add=True,
                        )),
                        ("updated_at", models.DateTimeField(
                            auto_now=True,
                        )),
                    ],
                    options={
                        "db_table": "ex_doc_template",
                    },
                ),
            ],
            database_operations=[],
        ),
        # 2. Register ExDocInstance in state (table exists)
        migrations.SeparateDatabaseAndState(
            state_operations=[
                migrations.CreateModel(
                    name="ExDocInstance",
                    fields=[
                        ("id", models.BigAutoField(
                            auto_created=True,
                            primary_key=True,
                            serialize=False,
                            verbose_name="ID",
                        )),
                        ("uuid", models.UUIDField(
                            default=uuid.uuid4,
                            editable=False,
                            unique=True,
                        )),
                        ("tenant_id", models.UUIDField(
                            db_index=True,
                        )),
                        ("template", models.ForeignKey(
                            on_delete=django.db.models.deletion.PROTECT,
                            related_name="instances",
                            to="explosionsschutz.exdoctemplate",
                        )),
                        ("name", models.CharField(
                            max_length=255,
                        )),
                        ("values_json", models.TextField(
                            default="{}",
                        )),
                        ("status", models.CharField(
                            choices=[
                                ("draft", "Entwurf"),
                                ("review", "In Prüfung"),
                                ("approved", "Freigegeben"),
                            ],
                            default="draft",
                            max_length=20,
                        )),
                        ("source_filename", models.CharField(
                            blank=True, default="",
                            max_length=255,
                        )),
                        ("created_at", models.DateTimeField(
                            auto_now_add=True,
                        )),
                        ("updated_at", models.DateTimeField(
                            auto_now=True,
                        )),
                    ],
                    options={
                        "db_table": "ex_doc_instance",
                    },
                ),
            ],
            database_operations=[],
        ),
        # 3. Add concept FK (both state + DB)
        migrations.AddField(
            model_name="exdocinstance",
            name="concept",
            field=models.ForeignKey(
                blank=True,
                help_text="Verknüpftes Ex-Konzept (optional)",
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="doc_instances",
                to="explosionsschutz.explosionconcept",
            ),
        ),
    ]
