"""Add AVV choice to TomCategory.MeasureType."""

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("dsb", "0001_initial"),
    ]

    operations = [
        migrations.AlterField(
            model_name="tomcategory",
            name="measure_type",
            field=models.CharField(
                choices=[
                    ("technical", "Technisch"),
                    ("organizational", "Organisatorisch"),
                    ("avv", "Auftragsverarbeitung (AVV)"),
                ],
                help_text="Art der Maßnahme",
                max_length=20,
            ),
        ),
    ]
