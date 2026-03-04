# Generated manually — adds DXF upload + analysis fields to Area

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("explosionsschutz", "0002_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="area",
            name="dxf_file",
            field=models.FileField(
                blank=True,
                null=True,
                upload_to="areas/dxf/",
                help_text="Grundriss-DXF für Zonengeometrie und Brandschutz-Analyse",
            ),
        ),
        migrations.AddField(
            model_name="area",
            name="dxf_analysis_json",
            field=models.JSONField(
                blank=True,
                null=True,
                help_text=("Ergebnis der nl2cad-core/areas DXF-Analyse (Räume, Flächen)"),
            ),
        ),
        migrations.AddField(
            model_name="area",
            name="brandschutz_analysis_json",
            field=models.JSONField(
                blank=True,
                null=True,
                help_text=("Ergebnis der nl2cad-brandschutz Analyse (Fluchtwege, Mängel)"),
            ),
        ),
    ]
