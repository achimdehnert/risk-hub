"""
Seed-Command: GBU H-Code-Kategorie-Mappings.

Idempotent: get_or_create auf (h_code, category).
Bestehende Mappings werden nicht überschrieben (Admin-Pflege bleibt erhalten).
--force: Annotationen bestehender Einträge aktualisieren.
Quelle: GHS/CLP-VO (EG 1272/2008), TRGS 400 (Stand 2024-09)
"""

import logging

from django.core.management.base import BaseCommand, CommandParser
from django.db import transaction

from gbu.models.reference import HazardCategoryRef, HCodeCategoryMapping

logger = logging.getLogger(__name__)

H_CODE_MAPPINGS: list[tuple[str, str, str]] = [
    # ── Brand / Explosion
    ("H220", "fire_explosion", "Extrem entzündbares Gas — Zone 0/20 prüfen (TRGS 720)"),
    ("H221", "fire_explosion", "Entzündbares Gas"),
    ("H222", "fire_explosion", "Extrem entzündbares Aerosol"),
    ("H223", "fire_explosion", "Entzündbares Aerosol"),
    ("H224", "fire_explosion", "Flammpunkt < 23°C, Siedepunkt ≤ 35°C — Kat. 1"),
    ("H225", "fire_explosion", "Leichtentzündbare Flüssigkeit — Flammpunkt 23–60°C"),
    ("H226", "fire_explosion", "Entzündbare Flüssigkeit — Flammpunkt 60–93°C"),
    ("H228", "fire_explosion", "Entzündbarer Feststoff"),
    ("H240", "fire_explosion", "Explosionsgefährlich bei Erwärmung"),
    ("H241", "fire_explosion", "Entzündbar oder explosionsgefährlich bei Erwärmung"),
    ("H242", "fire_explosion", "Entzündbar bei Erwärmung"),
    ("H250", "fire_explosion", "Entzündet sich in Berührung mit Luft selbst"),
    ("H251", "fire_explosion", "Selbsterhitzungsfähig in großen Mengen"),
    ("H252", "fire_explosion", "Selbsterhitzungsfähig in großen Mengen — Brandgefahr"),
    ("H260", "fire_explosion", "Entzündbares Gas bei Wasserkontakt"),
    ("H261", "fire_explosion", "Entzündbares Gas bei Wasserkontakt"),
    ("H270", "fire_explosion", "Kann Brand verursachen oder verstärken (Oxidationsmittel)"),
    ("H271", "fire_explosion", "Kann Brand oder Explosion verursachen"),
    ("H272", "fire_explosion", "Kann Brand verstärken — Oxidationsmittel"),
    # ── Akute Toxizität
    ("H300", "acute_toxic", "Lebensgefahr bei Verschlucken — Kat. 1/2"),
    ("H301", "acute_toxic", "Giftig bei Verschlucken — Kat. 3"),
    ("H302", "acute_toxic", "Gesundheitsschädlich bei Verschlucken — Kat. 4"),
    ("H304", "acute_toxic", "Kann bei Verschlucken und Eindringen in Atemwege tödlich sein"),
    ("H310", "acute_toxic", "Lebensgefahr bei Hautkontakt — Kat. 1/2"),
    ("H311", "acute_toxic", "Giftig bei Hautkontakt — Kat. 3"),
    ("H312", "acute_toxic", "Gesundheitsschädlich bei Hautkontakt — Kat. 4"),
    ("H330", "acute_toxic", "Lebensgefahr bei Einatmen — Kat. 1/2"),
    ("H331", "acute_toxic", "Giftig bei Einatmen — Kat. 3"),
    ("H332", "acute_toxic", "Gesundheitsschädlich bei Einatmen — Kat. 4"),
    # ── Chronische Toxizität (STOT)
    ("H370", "chronic_toxic", "Schädigt die Organe — STOT SE Kat. 1"),
    ("H371", "chronic_toxic", "Kann die Organe schädigen — STOT SE Kat. 2"),
    ("H372", "chronic_toxic", "Schädigt Organe bei längerer Exposition — STOT RE Kat. 1"),
    ("H373", "chronic_toxic", "Kann Organe schädigen bei längerer Exposition — STOT RE Kat. 2"),
    # ── Haut
    ("H314", "skin_corrosion", "Schwere Verätzungen der Haut und Augenschäden — Kat. 1"),
    ("H315", "skin_corrosion", "Verursacht Hautreizungen — Kat. 2"),
    # ── Augen
    ("H318", "eye_damage", "Verursacht schwere Augenschäden — Kat. 1"),
    ("H319", "eye_damage", "Verursacht schwere Augenreizung — Kat. 2"),
    # ── Atemwegssensibilisierung
    ("H334", "respiratory", "Kann bei Einatmen Allergie/Asthma/Atemnot verursachen"),
    # ── Hautsensibilisierung
    ("H317", "skin_sens", "Kann allergische Hautreaktionen verursachen"),
    # ── CMR
    ("H340", "cmr", "Kann genetische Defekte verursachen — Mutagen Kat. 1"),
    ("H341", "cmr", "Kann vermutlich genetische Defekte verursachen — Kat. 2"),
    ("H350", "cmr", "Kann Krebs erzeugen — Karzinogen Kat. 1A/1B"),
    ("H351", "cmr", "Kann vermutlich Krebs erzeugen — Kat. 2"),
    ("H360", "cmr", "Kann Fruchtbarkeit/ungeborenes Kind schädigen — Kat. 1A/1B"),
    ("H361", "cmr", "Kann vermutlich Fruchtbarkeit beeinträchtigen — Kat. 2"),
    ("H362", "cmr", "Kann Säuglinge über Muttermilch schädigen"),
    # ── Umwelt
    ("H400", "environment", "Sehr giftig für Wasserorganismen — Kat. Akut 1"),
    ("H410", "environment", "Sehr giftig für Wasserorganismen, langfristige Wirkung — Chr. 1"),
    ("H411", "environment", "Giftig für Wasserorganismen, langfristige Wirkung — Chr. 2"),
    ("H412", "environment", "Schädlich für Wasserorganismen, langfristige Wirkung — Chr. 3"),
    ("H413", "environment", "Kann für Wasserorganismen schädlich sein — Chr. 4"),
    # ── Erstickung
    ("H280", "asphyxiant", "Enthält Gas unter Druck — Erwärmen kann Explosion verursachen"),
    ("H281", "asphyxiant", "Enthält tiefgekühltes Gas — Kälteverbrennungen möglich"),
]


class Command(BaseCommand):
    help = (
        "Seed GBU H-Code-Mappings — idempotent via get_or_create(h_code, category).\n"
        "Nutze --force um Annotationen bestehender Einträge zu überschreiben."
    )

    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument(
            "--force",
            action="store_true",
            default=False,
            help="Annotationen bestehender Mappings überschreiben",
        )

    @transaction.atomic
    def handle(self, *args, **options) -> None:
        force = options["force"]
        created_count = 0
        skipped_count = 0
        error_count = 0

        for h_code, category_code, annotation in H_CODE_MAPPINGS:
            try:
                category = HazardCategoryRef.objects.get(code=category_code)
            except HazardCategoryRef.DoesNotExist:
                self.stderr.write(
                    self.style.ERROR(
                        f"  ERROR: Kategorie '{category_code}' nicht gefunden "
                        f"(H-Code: {h_code}). seed_hazard_categories zuerst ausführen."
                    )
                )
                error_count += 1
                continue

            if force:
                _, created = HCodeCategoryMapping.objects.update_or_create(
                    h_code=h_code,
                    category=category,
                    defaults={"annotation": annotation},
                )
            else:
                _, created = HCodeCategoryMapping.objects.get_or_create(
                    h_code=h_code,
                    category=category,
                    defaults={"annotation": annotation},
                )

            if created:
                created_count += 1
            else:
                skipped_count += 1

        if error_count > 0:
            self.stderr.write(
                self.style.ERROR(f"FEHLER: {error_count} Mappings konnten nicht angelegt werden.")
            )
            raise SystemExit(1)

        total = HCodeCategoryMapping.objects.count()
        self.stdout.write(
            self.style.SUCCESS(
                f"OK: {created_count} erstellt, {skipped_count} übersprungen "
                f"— {total} Mappings gesamt"
            )
        )
