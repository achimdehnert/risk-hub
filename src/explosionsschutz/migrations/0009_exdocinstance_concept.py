# Generated manually — add concept FK to ExDocInstance

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("explosionsschutz", "0008_concept_templates"),
    ]

    operations = [
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
