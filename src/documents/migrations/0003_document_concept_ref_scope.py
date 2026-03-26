"""Add concept_ref_id and scope to Document for concept-template integration (ADR-147)."""

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("documents", "0002_add_document_categories"),
    ]

    operations = [
        migrations.AddField(
            model_name="document",
            name="concept_ref_id",
            field=models.UUIDField(
                blank=True,
                db_index=True,
                help_text="Optional: Verknüpfung zu Brandschutz-/Explosionsschutzkonzept",
                null=True,
            ),
        ),
        migrations.AddField(
            model_name="document",
            name="scope",
            field=models.CharField(
                blank=True,
                default="",
                help_text="Fachbereich: brandschutz, explosionsschutz, etc.",
                max_length=30,
            ),
        ),
    ]
