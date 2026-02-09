"""Add LocationSubstanceEntry for TRGS 510 / Seveso III registry."""

import uuid

import django.utils.timezone
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("substances", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="LocationSubstanceEntry",
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
                (
                    "tenant_id",
                    models.UUIDField(db_index=True),
                ),
                (
                    "area_id",
                    models.UUIDField(
                        db_index=True,
                        help_text="Standort/Bereich (Area-ID)",
                    ),
                ),
                (
                    "substance",
                    models.ForeignKey(
                        on_delete=models.PROTECT,
                        related_name="location_entries",
                        to="substances.substance",
                    ),
                ),
                (
                    "substance_name",
                    models.CharField(
                        help_text="Denormalisierter Stoffname",
                        max_length=300,
                    ),
                ),
                (
                    "cas_number",
                    models.CharField(
                        blank=True, default="", max_length=30,
                    ),
                ),
                (
                    "max_quantity_kg",
                    models.DecimalField(
                        decimal_places=2,
                        default=0,
                        help_text="Maximale Lagermenge in kg",
                        max_digits=12,
                    ),
                ),
                (
                    "current_quantity_kg",
                    models.DecimalField(
                        decimal_places=2,
                        default=0,
                        help_text="Aktuelle Lagermenge in kg",
                        max_digits=12,
                    ),
                ),
                (
                    "storage_class",
                    models.CharField(
                        blank=True,
                        choices=[
                            ("1", "LGK 1 – Explosive Stoffe"),
                            ("2A", "LGK 2A – Verdichtete Gase (brennbar)"),
                            ("2B", "LGK 2B – Verdichtete Gase (nicht brennbar)"),
                            ("3", "LGK 3 – Entzündbare Flüssigkeiten"),
                            ("4.1", "LGK 4.1 – Entzündbare feste Stoffe"),
                            ("4.2", "LGK 4.2 – Selbstentzündliche Stoffe"),
                            ("4.3", "LGK 4.3 – Stoffe mit Wasserreaktion"),
                            ("5.1", "LGK 5.1 – Oxidierende Stoffe"),
                            ("5.2", "LGK 5.2 – Organische Peroxide"),
                            ("6.1", "LGK 6.1 – Giftige Stoffe"),
                            ("8", "LGK 8 – Ätzende Stoffe"),
                            ("10", "LGK 10 – Brennbare Flüssigkeiten"),
                            ("11", "LGK 11 – Brennbare Feststoffe"),
                            ("12", "LGK 12 – Nicht brennbare Flüssigkeiten"),
                            ("13", "LGK 13 – Nicht brennbare Feststoffe"),
                        ],
                        db_index=True,
                        default="",
                        max_length=5,
                    ),
                ),
                (
                    "seveso_category",
                    models.CharField(
                        choices=[
                            ("none", "Nicht Seveso-relevant"),
                            ("lower", "Untere Klasse (Grundpflichten)"),
                            ("upper", "Obere Klasse (Erweiterte Pflichten)"),
                        ],
                        db_index=True,
                        default="none",
                        max_length=10,
                    ),
                ),
                (
                    "seveso_threshold_lower_t",
                    models.DecimalField(
                        blank=True,
                        decimal_places=2,
                        help_text="Untere Mengenschwelle (Tonnen)",
                        max_digits=10,
                        null=True,
                    ),
                ),
                (
                    "seveso_threshold_upper_t",
                    models.DecimalField(
                        blank=True,
                        decimal_places=2,
                        help_text="Obere Mengenschwelle (Tonnen)",
                        max_digits=10,
                        null=True,
                    ),
                ),
                (
                    "h_statements",
                    models.TextField(blank=True, default=""),
                ),
                (
                    "ghs_pictograms",
                    models.CharField(
                        blank=True, default="", max_length=200,
                    ),
                ),
                (
                    "notes",
                    models.TextField(blank=True, default=""),
                ),
                (
                    "last_inventory_date",
                    models.DateField(blank=True, null=True),
                ),
                (
                    "created_at",
                    models.DateTimeField(
                        default=django.utils.timezone.now,
                    ),
                ),
                (
                    "updated_at",
                    models.DateTimeField(auto_now=True),
                ),
            ],
            options={
                "db_table": "substances_location_entry",
                "ordering": ["substance_name"],
            },
        ),
        migrations.AddConstraint(
            model_name="locationsubstanceentry",
            constraint=models.UniqueConstraint(
                fields=(
                    "tenant_id", "area_id", "substance_id",
                ),
                name="uq_location_substance",
            ),
        ),
    ]
