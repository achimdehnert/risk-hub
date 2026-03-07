# Generated manually — adds mitigation_status, responsible_user_id, due_date, substance_id to Hazard

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("risk", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="hazard",
            name="mitigation_status",
            field=models.CharField(
                choices=[
                    ("open", "Offen"),
                    ("in_progress", "In Bearbeitung"),
                    ("mitigated", "Gemindert"),
                    ("accepted", "Akzeptiert"),
                ],
                db_index=True,
                default="open",
                max_length=15,
            ),
        ),
        migrations.AddField(
            model_name="hazard",
            name="responsible_user_id",
            field=models.UUIDField(
                blank=True,
                db_index=True,
                help_text="UUID der verantwortlichen Person für die Maßnahme",
                null=True,
            ),
        ),
        migrations.AddField(
            model_name="hazard",
            name="due_date",
            field=models.DateField(
                blank=True,
                help_text="Fälligkeitsdatum der Maßnahme",
                null=True,
            ),
        ),
        migrations.AddField(
            model_name="hazard",
            name="substance_id",
            field=models.UUIDField(
                blank=True,
                db_index=True,
                help_text="Verknüpfter Gefahrstoff (substances.Substance, optional)",
                null=True,
            ),
        ),
        migrations.AddIndex(
            model_name="hazard",
            index=models.Index(
                fields=["tenant_id", "mitigation_status"],
                name="idx_hazard_tenant_status",
            ),
        ),
        migrations.AddIndex(
            model_name="hazard",
            index=models.Index(
                fields=["tenant_id", "due_date"],
                name="idx_hazard_tenant_due_date",
            ),
        ),
    ]
