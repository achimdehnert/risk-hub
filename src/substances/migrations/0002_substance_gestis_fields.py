"""Add GESTIS data fields to Substance model."""

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("substances", "0001_initial"),
    ]

    operations = [
        # Physical properties
        migrations.AddField(
            model_name="substance",
            name="boiling_point_c",
            field=models.FloatField(
                blank=True, null=True,
                help_text="Siedepunkt in °C",
            ),
        ),
        migrations.AddField(
            model_name="substance",
            name="melting_point_c",
            field=models.FloatField(
                blank=True, null=True,
                help_text="Schmelzpunkt in °C",
            ),
        ),
        migrations.AddField(
            model_name="substance",
            name="density",
            field=models.CharField(
                blank=True, default="", max_length=50,
                help_text="Dichte (z.B. 0,79 g/cm³)",
            ),
        ),
        migrations.AddField(
            model_name="substance",
            name="molecular_formula",
            field=models.CharField(
                blank=True, default="", max_length=100,
                help_text="Summenformel",
            ),
        ),
        migrations.AddField(
            model_name="substance",
            name="molecular_weight",
            field=models.CharField(
                blank=True, default="", max_length=50,
                help_text="Molare Masse",
            ),
        ),
        # Workplace limits
        migrations.AddField(
            model_name="substance",
            name="agw",
            field=models.TextField(
                blank=True, default="",
                help_text="Arbeitsplatzgrenzwert (TRGS 900)",
            ),
        ),
        migrations.AddField(
            model_name="substance",
            name="wgk",
            field=models.CharField(
                blank=True, default="", max_length=200,
                help_text="Wassergefährdungsklasse",
            ),
        ),
        # Protective measures
        migrations.AddField(
            model_name="substance",
            name="first_aid",
            field=models.TextField(
                blank=True, default="",
                help_text="Erste Hilfe",
            ),
        ),
        migrations.AddField(
            model_name="substance",
            name="protective_measures",
            field=models.TextField(
                blank=True, default="",
                help_text="Technische + persönliche Schutzmaßnahmen",
            ),
        ),
        migrations.AddField(
            model_name="substance",
            name="storage_info",
            field=models.TextField(
                blank=True, default="",
                help_text="Lagerung (GESTIS)",
            ),
        ),
        migrations.AddField(
            model_name="substance",
            name="fire_protection",
            field=models.TextField(
                blank=True, default="",
                help_text="Brand- und Explosionsschutz",
            ),
        ),
        migrations.AddField(
            model_name="substance",
            name="disposal",
            field=models.TextField(
                blank=True, default="",
                help_text="Entsorgung",
            ),
        ),
        migrations.AddField(
            model_name="substance",
            name="spill_response",
            field=models.TextField(
                blank=True, default="",
                help_text="Maßnahmen bei Freisetzung",
            ),
        ),
        # Regulations
        migrations.AddField(
            model_name="substance",
            name="regulations",
            field=models.TextField(
                blank=True, default="",
                help_text="Vorschriften/Regelwerke (JSON-Liste)",
            ),
        ),
        # GESTIS reference
        migrations.AddField(
            model_name="substance",
            name="gestis_zvg",
            field=models.CharField(
                blank=True, default="", max_length=20,
                help_text="GESTIS ZVG-Nummer",
            ),
        ),
        migrations.AddField(
            model_name="substance",
            name="gestis_url",
            field=models.URLField(
                blank=True, default="",
                help_text="GESTIS Volltext-Link",
            ),
        ),
    ]
