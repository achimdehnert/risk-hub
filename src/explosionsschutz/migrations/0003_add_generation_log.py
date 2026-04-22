# src/explosionsschutz/migrations/0003_add_generation_log.py
"""
Migration: ExplosionConceptGenerationLog (ADR-018 KI-Augmentierung).

Erstellt forensischen Audit-Log für alle LLM-Calls gegen ExplosionConcept.
"""

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("explosionsschutz", "0002_initial"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="ExplosionConceptGenerationLog",
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
                ("tenant_id", models.UUIDField(db_index=True)),
                (
                    "chapter",
                    models.CharField(
                        choices=[
                            ("zones", "Zoneneinteilung"),
                            ("ignition", "Zündquellen"),
                            ("measures", "Schutzmaßnahmen"),
                            ("summary", "Zusammenfassung"),
                        ],
                        help_text="Welcher Abschnitt wurde generiert",
                        max_length=32,
                    ),
                ),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("running", "Läuft"),
                            ("success", "Erfolgreich"),
                            ("failed", "Fehlgeschlagen"),
                            ("accepted", "Übernommen"),
                            ("rejected", "Verworfen"),
                        ],
                        default="running",
                        max_length=16,
                    ),
                ),
                (
                    "action_code",
                    models.CharField(
                        help_text="AIActionType.code aus iil-aifw, z.B. 'ex_concept_zones'",
                        max_length=100,
                    ),
                ),
                (
                    "model_name",
                    models.CharField(
                        blank=True,
                        help_text="LLMResult.model — befüllt nach API-Call",
                        max_length=100,
                    ),
                ),
                (
                    "prompt_hash",
                    models.CharField(
                        db_index=True,
                        help_text="SHA-256 von system+user prompt (Reproduzierbarkeit)",
                        max_length=64,
                    ),
                ),
                (
                    "prompt_system",
                    models.TextField(
                        help_text="System-Prompt zum Zeitpunkt des Calls"
                    ),
                ),
                (
                    "prompt_user",
                    models.TextField(
                        help_text="User-Prompt (Kontext-Snapshot)"
                    ),
                ),
                (
                    "input_context",
                    models.JSONField(
                        default=dict,
                        help_text="Serialisierter Eingabe-Kontext (Stoff, Bereich, Zonen, ...)",
                    ),
                ),
                ("response_text", models.TextField(blank=True)),
                ("error_message", models.TextField(blank=True)),
                ("input_tokens", models.PositiveIntegerField(default=0)),
                ("output_tokens", models.PositiveIntegerField(default=0)),
                ("finished_at", models.DateTimeField(blank=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("accepted_at", models.DateTimeField(blank=True, null=True)),
                (
                    "changes_on_adoption",
                    models.TextField(
                        blank=True,
                        help_text="Vom Experten vorgenommene Änderungen am Vorschlag",
                    ),
                ),
                (
                    "concept",
                    models.ForeignKey(
                        help_text="PROTECT: Log-Zeilen bleiben für Compliance erhalten",
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="generation_logs",
                        to="explosionsschutz.explosionconcept",
                    ),
                ),
                (
                    "accepted_by",
                    models.ForeignKey(
                        blank=True,
                        help_text="Experte der den Vorschlag übernommen / abgelehnt hat",
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="+",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "verbose_name": "KI-Generierungslog",
                "verbose_name_plural": "KI-Generierungslogs",
                "db_table": "ex_concept_generation_log",
                "ordering": ["-created_at"],
            },
        ),
        migrations.AddIndex(
            model_name="explosionconceptgenerationlog",
            index=models.Index(
                fields=["concept", "chapter", "-created_at"],
                name="idx_genlog_concept_chapter",
            ),
        ),
        migrations.AddIndex(
            model_name="explosionconceptgenerationlog",
            index=models.Index(
                fields=["tenant_id", "status", "-created_at"],
                name="idx_genlog_tenant_status",
            ),
        ),
        migrations.AddIndex(
            model_name="explosionconceptgenerationlog",
            index=models.Index(
                fields=["prompt_hash"],
                name="idx_genlog_prompt_hash",
            ),
        ),
        migrations.AddConstraint(
            model_name="explosionconceptgenerationlog",
            constraint=models.CheckConstraint(
                condition=(
                    ~models.Q(status="success") | models.Q(response_text__gt="")
                ),
                name="ex_gen_log_success_requires_response",
            ),
        ),
    ]
