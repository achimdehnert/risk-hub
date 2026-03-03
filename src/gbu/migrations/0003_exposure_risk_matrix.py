from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("gbu", "0002_rls_gbu_activity"),
    ]

    operations = [
        migrations.CreateModel(
            name="ExposureRiskMatrix",
            fields=[
                ("id", models.BigAutoField(
                    auto_created=True, primary_key=True,
                    serialize=False, verbose_name="ID",
                )),
                ("quantity_class", models.CharField(
                    choices=[
                        ("xs", "XS (<1L/kg)"),
                        ("s", "S (1–10L/kg)"),
                        ("m", "M (10–100L/kg)"),
                        ("l", "L (>100L/kg)"),
                    ],
                    help_text="Mengenkategorie nach EMKG",
                    max_length=2,
                )),
                ("activity_frequency", models.CharField(
                    choices=[
                        ("daily", "Täglich"),
                        ("weekly", "Wöchentlich"),
                        ("occasional", "Gelegentlich"),
                        ("rare", "Selten"),
                    ],
                    help_text="Expositionsfrequenz",
                    max_length=15,
                )),
                ("has_cmr", models.BooleanField(
                    default=False,
                    help_text="Enthält CMR-Stoff (Karzinogen/Mutagen/Reproduktionstoxisch)",
                )),
                ("risk_score", models.CharField(
                    choices=[
                        ("low", "Gering (EMKG A)"),
                        ("medium", "Mittel (EMKG B)"),
                        ("high", "Hoch (EMKG C)"),
                        ("critical", "Kritisch"),
                    ],
                    help_text="Resultierender Risikoscore nach EMKG",
                    max_length=10,
                )),
                ("emkg_class", models.CharField(
                    blank=True,
                    choices=[("A", "A"), ("B", "B"), ("C", "C")],
                    default="",
                    help_text="EMKG-Expositionsklasse (A/B/C)",
                    max_length=1,
                )),
                ("note", models.TextField(
                    blank=True,
                    default="",
                    help_text="Begründung / Rechtsgrundlage (TRGS 400, EMKG-Leitfaden)",
                )),
            ],
            options={
                "verbose_name": "EMKG-Risikomatrix-Eintrag",
                "verbose_name_plural": "EMKG-Risikomatrix",
                "db_table": "gbu_exposure_risk_matrix",
                "ordering": ["quantity_class", "activity_frequency"],
            },
        ),
        migrations.AlterUniqueTogether(
            name="exposureriskmatrix",
            unique_together={("quantity_class", "activity_frequency", "has_cmr")},
        ),
    ]
