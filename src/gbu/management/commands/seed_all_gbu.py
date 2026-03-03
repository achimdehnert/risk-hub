"""
Wrapper-Command: Führt alle GBU-Seed-Commands in korrekter Reihenfolge aus.

Reihenfolge (Abhängigkeiten beachten):
  1. seed_hazard_categories   — HazardCategoryRef (Basis)
  2. seed_h_code_mappings     — H-Code → Kategorie (benötigt Kategorien)
  3. seed_exposure_risk_matrix — EMKG-Matrix (unabhängig)
  4. seed_measure_templates   — TOPS-Vorlagen (benötigt Kategorien)

Idempotent: alle Unter-Commands sind idempotent.
Nutzung in CI/CD und lokalem Setup: python manage.py seed_all_gbu
"""
import logging

from django.core.management import call_command
from django.core.management.base import BaseCommand

logger = logging.getLogger(__name__)

_GBU_SEED_COMMANDS: list[tuple[str, dict]] = [
    ("seed_hazard_categories", {}),
    ("seed_h_code_mappings",   {}),
    ("seed_exposure_risk_matrix", {}),
    ("seed_measure_templates", {}),
]


class Command(BaseCommand):
    help = "Führt alle GBU-Seed-Commands in korrekter Reihenfolge aus (idempotent)"

    def handle(self, *args, **options) -> None:
        self.stdout.write(self.style.MIGRATE_HEADING("GBU Seed-Daten:"))

        for cmd_name, cmd_kwargs in _GBU_SEED_COMMANDS:
            self.stdout.write(f"  → {cmd_name}...")
            try:
                call_command(cmd_name, **cmd_kwargs, stdout=self.stdout, stderr=self.stderr)
            except SystemExit:
                self.stderr.write(
                    self.style.ERROR(f"  FEHLER bei {cmd_name} — Abbruch.")
                )
                raise

        self.stdout.write(self.style.SUCCESS("GBU Seed-Daten vollständig."))
