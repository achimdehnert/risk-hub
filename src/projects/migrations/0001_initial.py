"""Initial migration for projects app (ADR-041).

Creates Project and ProjectModule tables with BigAutoField PKs.
"""

import uuid

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("tenancy", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="Project",
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
                (
                    "tenant_id",
                    models.UUIDField(db_index=True),
                ),
                ("name", models.CharField(max_length=255)),
                (
                    "project_number",
                    models.CharField(
                        blank=True,
                        default="",
                        max_length=50,
                    ),
                ),
                (
                    "client_name",
                    models.CharField(
                        blank=True,
                        default="",
                        help_text="Auftraggeber",
                        max_length=255,
                    ),
                ),
                (
                    "description",
                    models.TextField(
                        blank=True,
                        default="",
                        help_text="Freitext-Beschreibung für KI-Modulempfehlung",
                    ),
                ),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("active", "Aktiv"),
                            ("on_hold", "Pausiert"),
                            ("completed", "Abgeschlossen"),
                            ("archived", "Archiviert"),
                        ],
                        default="active",
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
                    "completed_at",
                    models.DateTimeField(
                        blank=True,
                        null=True,
                    ),
                ),
                (
                    "created_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="created_projects",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "site",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="projects",
                        to="tenancy.site",
                    ),
                ),
            ],
            options={
                "verbose_name": "Projekt",
                "verbose_name_plural": "Projekte",
                "db_table": "project",
                "ordering": ["-created_at"],
                "indexes": [
                    models.Index(
                        fields=["tenant_id", "status"],
                        name="ix_project_tenant_status",
                    ),
                ],
            },
        ),
        migrations.CreateModel(
            name="ProjectModule",
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
                    "module",
                    models.CharField(
                        db_index=True,
                        help_text="Modul-Code z.B. 'explosionsschutz', 'gbu'",
                        max_length=50,
                    ),
                ),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("active", "Aktiv"),
                            ("declined", "Bewusst abgelehnt"),
                            ("deactivated", "Nachträglich deaktiviert"),
                        ],
                        default="active",
                        max_length=20,
                    ),
                ),
                (
                    "is_ai_recommended",
                    models.BooleanField(default=False),
                ),
                (
                    "ai_reason",
                    models.TextField(
                        blank=True,
                        default="",
                        help_text="KI-Begründung für Empfehlung",
                    ),
                ),
                (
                    "activated_at",
                    models.DateTimeField(auto_now_add=True),
                ),
                (
                    "activated_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "project",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="modules",
                        to="projects.project",
                    ),
                ),
            ],
            options={
                "verbose_name": "Projekt-Modul",
                "verbose_name_plural": "Projekt-Module",
                "db_table": "project_module",
                "constraints": [
                    models.UniqueConstraint(
                        fields=("project", "module"),
                        name="uq_project_module",
                    ),
                ],
            },
        ),
    ]
