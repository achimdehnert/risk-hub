# src/explosionsschutz/management/commands/assign_auto_projects.py
"""
ADR-044 Phase 7: Auto-Projekt-Zuweisung für bestehende Konzepte ohne Projekt-FK.

Erstellt für jedes Konzept ohne project-FK ein automatisches Projekt
mit dem Naming-Schema: 'Auto-ExSchutz-{area.name}-{created_at.date()}'.

Läuft idempotent — bereits zugewiesene Konzepte werden übersprungen.

Usage:
    python manage.py assign_auto_projects [--dry-run] [--tenant-id <uuid>]
"""

import uuid

from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = "ADR-044 Phase 7: Konzepte ohne Project-FK einem Auto-Projekt zuweisen"

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Zeigt an was passieren würde, ohne Änderungen zu speichern",
        )
        parser.add_argument(
            "--tenant-id",
            type=str,
            default=None,
            help="Nur einen Tenant migrieren (UUID)",
        )

    def handle(self, *args, **options):
        from explosionsschutz.models import ExplosionConcept
        from projects.models import Project

        dry_run = options["dry_run"]
        tenant_filter = options.get("tenant_id")

        qs = ExplosionConcept.objects.filter(project__isnull=True).select_related("area")
        if tenant_filter:
            try:
                tenant_uuid = uuid.UUID(tenant_filter)
            except ValueError as err:
                raise CommandError(f"Ungültige UUID: {tenant_filter}") from err
            qs = qs.filter(tenant_id=tenant_uuid)

        total = qs.count()
        if total == 0:
            self.stdout.write(self.style.SUCCESS("Keine Konzepte ohne Projekt-FK gefunden."))
            return

        self.stdout.write(f"{total} Konzepte ohne Projekt-FK gefunden.")
        if dry_run:
            self.stdout.write(self.style.WARNING("DRY-RUN — keine Änderungen werden gespeichert"))

        assigned = 0
        for concept in qs.iterator(chunk_size=100):
            project_name = (
                f"Auto-ExSchutz-{concept.area.name}-{concept.created_at.date()}"
            )
            if not dry_run:
                project, created = Project.objects.get_or_create(
                    name=project_name,
                    tenant_id=concept.tenant_id,
                    defaults={"description": "Automatisch erstellt via assign_auto_projects (ADR-044 Phase 7)"},
                )
                concept.project = project
                concept.save(update_fields=["project"])
                action = "Neu" if created else "Existiert"
                self.stdout.write(
                    f"  [{action}] Projekt '{project_name}' → Konzept '{concept.title}'"
                )
            else:
                self.stdout.write(
                    f"  [DRY] Würde Projekt '{project_name}' erstellen → '{concept.title}'"
                )
            assigned += 1

        verb = "würden zugewiesen" if dry_run else "wurden zugewiesen"
        self.stdout.write(
            self.style.SUCCESS(f"{assigned} Konzepte {verb}.")
        )
