# src/explosionsschutz/migrations/0011_data_project_assignment_and_harden.py
"""
ADR-044 Phase 3 Datenmigration: project FK Härtung

Schritt 1 (RunPython): Konzepte ohne project FK werden einem Auto-Projekt zugeordnet.
  - Naming: 'Auto-ExSchutz-{area.name}-{created_at.date()}'
  - get_or_create pro Tenant + Name → idempotent

Schritt 2 (AlterField): project.null → False (Schema-Härtung)

Voraussetzung: assign_auto_projects.py Command (oder dieser Migration) muss
laufen BEVOR AlterField angewendet wird. Daher beide in einer Migration.

Reverse: AlterField null=True + kein Rück-Unassign (additive Datenmigration).
"""

from django.db import migrations, models


def assign_auto_projects(apps, schema_editor):
    ExplosionConcept = apps.get_model("explosionsschutz", "ExplosionConcept")
    Project = apps.get_model("projects", "Project")

    concepts_without_project = ExplosionConcept.objects.filter(
        project__isnull=True
    ).select_related("area")

    assigned = 0
    Site = apps.get_model("tenancy", "Site")

    for concept in concepts_without_project.iterator(chunk_size=100):
        site = Site.objects.filter(tenant_id=concept.tenant_id).first()
        if site is None:
            continue

        project_name = (
            f"Auto-ExSchutz-{concept.area.name}-{concept.created_at.date()}"
        )
        project, _ = Project.objects.get_or_create(
            name=project_name,
            tenant_id=concept.tenant_id,
            defaults={
                "site": site,
                "description": "Automatisch erstellt via Datenmigration 0011 (ADR-044 Phase 3)",
            },
        )
        concept.project = project
        concept.save(update_fields=["project"])
        assigned += 1

    print(f"\n[0011] Auto-Projekt-Zuweisung: {assigned} Konzepte zugewiesen")


class Migration(migrations.Migration):

    atomic = False  # AlterField nach RunPython erfordert separaten Transaktionskontext

    dependencies = [
        ("explosionsschutz", "0010_data_substance_id_to_concept_substance_reference"),
        ("projects", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(
            assign_auto_projects,
            reverse_code=migrations.RunPython.noop,
        ),
        migrations.AlterField(
            model_name="explosionconcept",
            name="project",
            field=models.ForeignKey(
                help_text="ADR-041 Container. Nach Phase 3 der Datenmigration: null=False.",
                on_delete=models.deletion.PROTECT,
                related_name="explosion_concepts",
                to="projects.project",
            ),
        ),
    ]
