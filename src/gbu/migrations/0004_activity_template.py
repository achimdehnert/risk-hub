# Generated manually — adds ActivityTemplate model to gbu app

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("gbu", "0003_exposure_risk_matrix"),
    ]

    operations = [
        migrations.CreateModel(
            name="ActivityTemplate",
            fields=[
                (
                    "id",
                    models.AutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "name",
                    models.CharField(
                        help_text="Bezeichnung der Tätigkeitsvorlage",
                        max_length=200,
                    ),
                ),
                (
                    "scope",
                    models.CharField(
                        choices=[
                            ("system", "Systemvorlage (global)"),
                            ("tenant", "Mandanten-Vorlage"),
                        ],
                        db_index=True,
                        default="system",
                        max_length=10,
                    ),
                ),
                (
                    "tenant_id",
                    models.UUIDField(
                        blank=True,
                        db_index=True,
                        help_text="Nur bei scope=tenant gesetzt; NULL = systemweite Vorlage",
                        null=True,
                    ),
                ),
                (
                    "activity_description",
                    models.TextField(
                        help_text="Vorausgefüllte Tätigkeitsbeschreibung",
                    ),
                ),
                (
                    "activity_frequency",
                    models.CharField(
                        blank=True,
                        choices=[
                            ("daily", "Täglich"),
                            ("weekly", "Wöchentlich"),
                            ("occasional", "Gelegentlich"),
                            ("rare", "Selten"),
                        ],
                        default="",
                        max_length=15,
                    ),
                ),
                (
                    "quantity_class",
                    models.CharField(
                        blank=True,
                        choices=[
                            ("xs", "XS"),
                            ("s", "S"),
                            ("m", "M"),
                            ("l", "L"),
                        ],
                        default="",
                        max_length=2,
                    ),
                ),
                (
                    "duration_minutes",
                    models.PositiveSmallIntegerField(
                        blank=True,
                        help_text="Typische Expositionsdauer in Minuten",
                        null=True,
                    ),
                ),
                (
                    "default_hazard_categories",
                    models.ManyToManyField(
                        blank=True,
                        help_text="Voreingestellte Gefährdungskategorien",
                        related_name="activity_templates",
                        to="gbu.hazardcategoryref",
                    ),
                ),
                ("is_active", models.BooleanField(default=True)),
                ("sort_order", models.PositiveSmallIntegerField(default=0)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={
                "verbose_name": "Tätigkeitsvorlage",
                "verbose_name_plural": "Tätigkeitsvorlagen",
                "db_table": "gbu_activity_template",
                "ordering": ["scope", "sort_order", "name"],
                "constraints": [
                    models.UniqueConstraint(
                        condition=models.Q(scope="tenant"),
                        fields=("tenant_id", "name"),
                        name="uq_gbu_activity_template_tenant_name",
                    ),
                ],
            },
        ),
    ]
