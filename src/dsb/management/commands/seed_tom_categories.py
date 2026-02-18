"""Seed TomCategory Stammdaten (DB-driven TOM classification)."""

from django.core.management.base import BaseCommand
from django.utils.text import slugify

from dsb.models.lookups import TomCategory

# (label, measure_type)
DEFAULT_CATEGORIES: list[tuple[str, str]] = [
    # Technisch
    ("Zutrittskontrolle", "technical"),
    ("Zugangskontrolle", "technical"),
    ("Zugriffskontrolle", "technical"),
    ("Weitergabekontrolle", "technical"),
    ("Eingabekontrolle", "technical"),
    ("Verfügbarkeitskontrolle", "technical"),
    ("Trennungsgebot", "technical"),
    # Organisatorisch
    ("Organisatorische Maßnahmen", "organizational"),
    # AVV (Auftragsverarbeitung)
    ("Auftragskontrolle", "avv"),
]


class Command(BaseCommand):
    help = "Seed TomCategory Stammdaten for CSV import"

    def handle(self, *args, **options):
        created = 0
        for label, mtype in DEFAULT_CATEGORIES:
            key = slugify(label)[:80]
            _, is_new = TomCategory.objects.get_or_create(
                key=key,
                defaults={
                    "label": label,
                    "measure_type": mtype,
                },
            )
            if is_new:
                created += 1
                self.stdout.write(f"  + {label} ({mtype})")
            else:
                self.stdout.write(f"  = {label} (exists)")

        self.stdout.write(
            self.style.SUCCESS(
                f"Done. {created} new categories created.",
            ),
        )
