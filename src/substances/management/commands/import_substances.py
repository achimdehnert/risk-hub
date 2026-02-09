# substances/management/commands/import_substances.py
"""
Management Command: Importiert Gefahrstoffe aus JSON-Datendateien.

Usage:
    python manage.py import_substances --tenant-slug demo
    python manage.py import_substances --tenant-slug demo --file custom.json
    python manage.py import_substances --tenant-slug demo --dry-run
    python manage.py import_substances --tenant-slug demo --with-ghs
"""

from pathlib import Path

from django.core.management import call_command
from django.core.management.base import BaseCommand, CommandError

from substances.services.substance_import import (
    SubstanceImportService,
)


class Command(BaseCommand):
    """Importiert reale Gefahrstoffe in die Datenbank."""

    help = (
        "Importiert Gefahrstoffe aus JSON-Datendateien "
        "für einen bestimmten Tenant"
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--tenant-slug",
            required=True,
            help="Slug des Ziel-Tenants (z.B. 'demo')",
        )
        parser.add_argument(
            "--file",
            type=str,
            default=None,
            help="Pfad zur JSON-Datendatei (Standard: "
                 "eingebaute common_substances.json)",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Nur validieren, nicht importieren",
        )
        parser.add_argument(
            "--with-ghs",
            action="store_true",
            help="Vorher GHS-Referenzdaten laden "
                 "(load_ghs_data)",
        )
        parser.add_argument(
            "--user",
            type=str,
            default=None,
            help="Username für created_by (optional)",
        )

    def handle(self, *args, **options):
        from identity.models import User
        from tenancy.models import Organization

        slug = options["tenant_slug"]
        try:
            org = Organization.objects.get(slug=slug)
        except Organization.DoesNotExist:
            raise CommandError(
                f"Tenant '{slug}' nicht gefunden"
            )

        user_id = None
        if options["user"]:
            try:
                user = User.objects.get(
                    username=options["user"]
                )
                user_id = user.id
            except User.DoesNotExist:
                raise CommandError(
                    f"User '{options['user']}' nicht gefunden"
                )

        if options["with_ghs"]:
            self.stdout.write(
                "Lade GHS-Referenzdaten..."
            )
            call_command("load_ghs_data")
            self.stdout.write("")

        file_path = None
        if options["file"]:
            file_path = Path(options["file"])
            if not file_path.exists():
                raise CommandError(
                    f"Datei nicht gefunden: {file_path}"
                )

        dry_run = options["dry_run"]
        if dry_run:
            self.stdout.write(self.style.WARNING(
                "DRY-RUN: Keine Daten werden geschrieben"
            ))

        self.stdout.write(
            f"Importiere Gefahrstoffe für Tenant "
            f"'{org.name}' ({org.id})..."
        )

        service = SubstanceImportService(
            tenant_id=org.id,
            user_id=user_id,
        )
        stats = service.import_from_file(
            path=file_path, dry_run=dry_run,
        )

        self.stdout.write("")
        self.stdout.write(stats.summary())

        if stats.errors:
            self.stdout.write(self.style.WARNING(
                f"\n⚠ {len(stats.errors)} Fehler aufgetreten"
            ))
        else:
            self.stdout.write(self.style.SUCCESS(
                f"\n✓ Import abgeschlossen: "
                f"{stats.created} neu, "
                f"{stats.updated} aktualisiert"
            ))
