# src/explosionsschutz/migrations/0010_data_substance_id_to_concept_substance_reference.py
"""
ADR-044 Phase 2 Datenmigration: substance_id → ConceptSubstanceReference

Für jedes ExplosionConcept mit gesetztem substance_id wird eine
ConceptSubstanceReference mit role=PRIMARY angelegt.

Ablauf:
1. Alle Konzepte mit substance_id != NULL ermitteln
2. Prüfen ob bereits eine ConceptSubstanceReference für dieses Konzept existiert
3. Falls nicht: ConceptSubstanceReference(role=PRIMARY, sds_revision=None) anlegen
   sds_revision bleibt NULL — manuell per Admin oder SDS-Upload-Flow nachzufüllen.

Reverse: Keine Rückwärtsmigration (additive Datenmigration, lossless).
"""

from django.db import migrations


def migrate_substance_id_forward(apps, schema_editor):
    ExplosionConcept = apps.get_model("explosionsschutz", "ExplosionConcept")
    ConceptSubstanceReference = apps.get_model(
        "explosionsschutz", "ConceptSubstanceReference"
    )

    concepts = ExplosionConcept.objects.filter(
        substance_id__isnull=False
    ).exclude(substance_id="").select_related()

    migrated = 0
    skipped = 0

    for concept in concepts.iterator(chunk_size=200):
        already_exists = ConceptSubstanceReference.objects.filter(
            concept=concept,
            role="PRIMARY",
        ).exists()

        if already_exists:
            skipped += 1
            continue

        ConceptSubstanceReference.objects.create(
            concept=concept,
            sds_revision=None,
            role="PRIMARY",
            release_rate_text=(
                f"Migriert aus substance_id={concept.substance_id} "
                f"(substance_name='{concept.substance_name}'). "
                "SDS-Revision bitte manuell verknüpfen."
            ),
            tenant_id=concept.tenant_id,
        )
        migrated += 1

    print(
        f"\n[0010] substance_id → ConceptSubstanceReference: "
        f"{migrated} migriert, {skipped} übersprungen (existierten bereits)"
    )


class Migration(migrations.Migration):

    dependencies = [
        ("explosionsschutz", "0009_phase2_sds_revision_nullable"),
    ]

    operations = [
        migrations.RunPython(
            migrate_substance_id_forward,
            reverse_code=migrations.RunPython.noop,
        ),
    ]
