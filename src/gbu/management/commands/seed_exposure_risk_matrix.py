"""
Seed-Command: GBU EMKG-Risikomatrix (ExposureRiskMatrix).

Idempotent: update_or_create auf (quantity_class, activity_frequency, has_cmr).
Quelle: EMKG-Leitfaden BAuA (Stand 2024), Tabelle Expositionsklassen A/B/C.
"""
import logging

from django.core.management.base import BaseCommand
from django.db import transaction

from gbu.models.reference import ExposureRiskMatrix

logger = logging.getLogger(__name__)

# Format: (quantity_class, activity_frequency, has_cmr, risk_score, emkg_class, note)
MATRIX_DATA: list[tuple] = [
    # ── Selten
    ("xs", "rare",       False, "low",      "A", "EMKG A: Geringe Exposition — Grundschutz ausreichend"),
    ("s",  "rare",       False, "low",      "A", "EMKG A: Geringe Exposition"),
    ("m",  "rare",       False, "medium",   "B", "EMKG B: Mittlere Exposition — Technische Maßnahmen prüfen"),
    ("l",  "rare",       False, "medium",   "B", "EMKG B: Mittlere Exposition"),
    # ── Gelegentlich
    ("xs", "occasional", False, "low",      "A", "EMKG A: Geringe Exposition"),
    ("s",  "occasional", False, "medium",   "B", "EMKG B: Mittlere Exposition"),
    ("m",  "occasional", False, "high",     "C", "EMKG C: Hohe Exposition — Sofortmaßnahmen erforderlich"),
    ("l",  "occasional", False, "high",     "C", "EMKG C: Hohe Exposition"),
    # ── Wöchentlich
    ("xs", "weekly",     False, "low",      "A", "EMKG A: Geringe Exposition"),
    ("s",  "weekly",     False, "medium",   "B", "EMKG B: Mittlere Exposition"),
    ("m",  "weekly",     False, "high",     "C", "EMKG C: Hohe Exposition"),
    ("l",  "weekly",     False, "high",     "C", "EMKG C: Hohe Exposition — Schutzlüftung prüfen"),
    # ── Täglich
    ("xs", "daily",      False, "medium",   "B", "EMKG B: Tägliche Exposition erhöht Risikostufe"),
    ("s",  "daily",      False, "high",     "C", "EMKG C: Täglich mittlere Menge — kritisch"),
    ("m",  "daily",      False, "high",     "C", "EMKG C: Hohe Exposition"),
    ("l",  "daily",      False, "critical", "C", "Kritisch: Sofortmaßnahmen + Grenzwertprüfung (TRGS 900)"),
    # ── CMR-Stoffe
    ("xs", "rare",       True, "high",      "C", "CMR-Stoff: Immer mind. EMKG C (TRGS 905/906)"),
    ("s",  "rare",       True, "high",      "C", "CMR-Stoff: Substitutionsprüfung Pflicht (§7 GefStoffV)"),
    ("m",  "rare",       True, "critical",  "C", "CMR-Stoff: Kritisch — Schutzmaßnahmen der höchsten Stufe"),
    ("l",  "rare",       True, "critical",  "C", "CMR-Stoff: Kritisch"),
    ("xs", "occasional", True, "high",      "C", "CMR-Stoff: Immer mind. EMKG C"),
    ("s",  "occasional", True, "high",      "C", "CMR-Stoff: Substitutionsprüfung Pflicht"),
    ("m",  "occasional", True, "critical",  "C", "CMR-Stoff: Kritisch"),
    ("l",  "occasional", True, "critical",  "C", "CMR-Stoff: Kritisch"),
    ("xs", "weekly",     True, "high",      "C", "CMR-Stoff: Immer mind. EMKG C"),
    ("s",  "weekly",     True, "critical",  "C", "CMR-Stoff: Wöchentlich → Kritisch"),
    ("m",  "weekly",     True, "critical",  "C", "CMR-Stoff: Kritisch"),
    ("l",  "weekly",     True, "critical",  "C", "CMR-Stoff: Kritisch"),
    ("xs", "daily",      True, "critical",  "C", "CMR-Stoff täglich: Sofortmaßnahmen zwingend"),
    ("s",  "daily",      True, "critical",  "C", "CMR-Stoff täglich: Sofortmaßnahmen zwingend"),
    ("m",  "daily",      True, "critical",  "C", "CMR-Stoff täglich: Sofortmaßnahmen zwingend"),
    ("l",  "daily",      True, "critical",  "C", "CMR-Stoff täglich: Sofortmaßnahmen zwingend"),
]


class Command(BaseCommand):
    help = (
        "Seed GBU EMKG-Risikomatrix — idempotent via "
        "update_or_create(quantity_class, activity_frequency, has_cmr)"
    )

    @transaction.atomic
    def handle(self, *args, **options) -> None:
        created_count = 0
        updated_count = 0

        for qty, freq, cmr, score, emkg, note in MATRIX_DATA:
            _, created = ExposureRiskMatrix.objects.update_or_create(
                quantity_class=qty,
                activity_frequency=freq,
                has_cmr=cmr,
                defaults={
                    "risk_score": score,
                    "emkg_class": emkg,
                    "note": note,
                },
            )
            if created:
                created_count += 1
            else:
                updated_count += 1

        total = ExposureRiskMatrix.objects.count()
        self.stdout.write(
            self.style.SUCCESS(
                f"OK: {created_count} erstellt, {updated_count} aktualisiert "
                f"— {total} Einträge gesamt"
            )
        )
