"""
Seed-Command: GBU Gefährdungskategorien (HazardCategoryRef).

Idempotent: update_or_create auf natürlichem Schlüssel 'code'.
Mehrfaches Ausführen ist sicher (CI, Post-Deploy, lokale Einrichtung).
Quelle: TRGS 400 (Stand 2024-09)
"""

import logging

from django.core.management.base import BaseCommand
from django.db import transaction

from gbu.models.reference import HazardCategoryRef, HazardCategoryType

logger = logging.getLogger(__name__)

HAZARD_CATEGORIES: list[dict] = [
    {
        "code": "fire_explosion",
        "name": "Brand und Explosion",
        "category_type": HazardCategoryType.FIRE_EXPLOSION,
        "trgs_reference": "TRGS 400 Abschnitt 5.3",
        "description": "Entzündbare Flüssigkeiten, Gase, Feststoffe (H220–H228, H240–H242)",
        "sort_order": 10,
    },
    {
        "code": "acute_toxic",
        "name": "Akute Toxizität",
        "category_type": HazardCategoryType.ACUTE_TOXIC,
        "trgs_reference": "TRGS 400 Abschnitt 5.4",
        "description": "Akut giftig bei Einatmen, Hautkontakt oder Verschlucken (H300–H332)",
        "sort_order": 20,
    },
    {
        "code": "chronic_toxic",
        "name": "Chronische Toxizität (STOT)",
        "category_type": HazardCategoryType.CHRONIC_TOXIC,
        "trgs_reference": "TRGS 400 Abschnitt 5.5",
        "description": "Schädigung bei wiederholter Exposition (H370–H373)",
        "sort_order": 30,
    },
    {
        "code": "skin_corrosion",
        "name": "Ätz-/Reizwirkung Haut",
        "category_type": HazardCategoryType.SKIN_CORROSION,
        "trgs_reference": "TRGS 401",
        "description": "Verätzung (H314) oder Reizung (H315) der Haut",
        "sort_order": 40,
    },
    {
        "code": "eye_damage",
        "name": "Augenschäden",
        "category_type": HazardCategoryType.EYE_DAMAGE,
        "trgs_reference": "TRGS 400 Abschnitt 5.6",
        "description": "Schwere Augenschäden (H318) oder Augenreizung (H319)",
        "sort_order": 50,
    },
    {
        "code": "respiratory",
        "name": "Atemwegssensibilisierung",
        "category_type": HazardCategoryType.RESPIRATORY,
        "trgs_reference": "TRGS 406",
        "description": "Sensibilisierung der Atemwege (H334) — Berufsasthma",
        "sort_order": 60,
    },
    {
        "code": "skin_sens",
        "name": "Hautsensibilisierung",
        "category_type": HazardCategoryType.SKIN_SENS,
        "trgs_reference": "TRGS 401",
        "description": "Allergische Kontaktdermatitis (H317)",
        "sort_order": 70,
    },
    {
        "code": "cmr",
        "name": "CMR-Stoff (Karzinogen/Mutagen/Reproduktionstoxisch)",
        "category_type": HazardCategoryType.CMR,
        "trgs_reference": "TRGS 905, TRGS 906",
        "description": "Krebserzeugend (H350/H351), mutagen (H340/H341), repr.tox. (H360/H361)",
        "sort_order": 80,
    },
    {
        "code": "environment",
        "name": "Umweltgefährlichkeit",
        "category_type": HazardCategoryType.ENVIRONMENT,
        "trgs_reference": "TRGS 400 Abschnitt 5.9",
        "description": "Aquatische oder terrestrische Toxizität (H400–H413)",
        "sort_order": 90,
    },
    {
        "code": "asphyxiant",
        "name": "Erstickungsgefahr",
        "category_type": HazardCategoryType.ASPHYXIANT,
        "trgs_reference": "TRGS 400 Abschnitt 5.10",
        "description": "Sauerstoffverdrängung oder chemische Erstickung (H280, H281)",
        "sort_order": 100,
    },
]


class Command(BaseCommand):
    help = "Seed GBU Gefährdungskategorien — idempotent via update_or_create(code)"

    @transaction.atomic
    def handle(self, *args, **options) -> None:
        created_count = 0
        updated_count = 0

        for data in HAZARD_CATEGORIES:
            code = data["code"]
            defaults = {k: v for k, v in data.items() if k != "code"}
            _, created = HazardCategoryRef.objects.update_or_create(
                code=code,
                defaults=defaults,
            )
            if created:
                created_count += 1
                logger.info("[seed_hazard_categories] Erstellt: %s", code)
            else:
                updated_count += 1

        total = HazardCategoryRef.objects.count()
        self.stdout.write(
            self.style.SUCCESS(
                f"OK: {created_count} erstellt, {updated_count} aktualisiert "
                f"— {total} Kategorien gesamt"
            )
        )
