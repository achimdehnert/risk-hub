"""Add fields_json and values_json to DocumentSection."""

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("projects", "0003_documenttemplate_outputdocument_template"),
    ]

    operations = [
        migrations.AddField(
            model_name="documentsection",
            name="fields_json",
            field=models.TextField(
                blank=True,
                default="[]",
                help_text="Felddefinitionen als JSON (aus Template-Struktur)",
            ),
        ),
        migrations.AddField(
            model_name="documentsection",
            name="values_json",
            field=models.TextField(
                blank=True,
                default="{}",
                help_text="Feldwerte als JSON {field_key: value}",
            ),
        ),
    ]
