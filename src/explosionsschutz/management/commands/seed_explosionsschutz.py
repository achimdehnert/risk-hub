# src/explosionsschutz/management/commands/seed_explosionsschutz.py
"""
Idempotentes Seed-Kommando für Explosionsschutz-Stammdaten.

Erstellt globale (tenant_id=NULL, is_system=True) Einträge für:
- ReferenceStandard: TRGS, IEC, EN Normen
- MeasureCatalog: Vorlagen für Schutzmaßnahmen
- SafetyFunction: MSR-Sicherheitsfunktionen
- EquipmentType: Gängige Ex-geschützte Gerätetypen

Idempotent: Existierende Einträge werden nicht dupliziert (get_or_create).
"""

import logging

from django.core.management.base import BaseCommand

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Seed globale Explosionsschutz-Stammdaten (idempotent)"

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Nur anzeigen, was erstellt würde",
        )

    def handle(self, *args, **options):
        dry_run = options["dry_run"]
        created_total = 0

        created_total += self._seed_standards(dry_run)
        created_total += self._seed_catalog(dry_run)
        created_total += self._seed_safety_functions(dry_run)
        created_total += self._seed_equipment_types(dry_run)

        prefix = "[DRY-RUN] " if dry_run else ""
        self.stdout.write(
            self.style.SUCCESS(f"{prefix}{created_total} Einträge erstellt/überprüft.")
        )

    def _seed_standards(self, dry_run: bool) -> int:
        from explosionsschutz.models import ReferenceStandard

        standards = [
            {
                "code": "TRGS 720",
                "title": "Gefährliche explosionsfähige Atmosphäre — Allgemeines",
                "category": "TRGS",
            },
            {
                "code": "TRGS 721",
                "title": (
                    "Gefährliche explosionsfähige Atmosphäre"
                    " — Beurteilung der Explosionsgefährdung"
                ),
                "category": "TRGS",
            },
            {
                "code": "TRGS 722",
                "title": "Vermeidung oder Einschränkung gefährlicher explosionsfähiger Atmosphäre",
                "category": "TRGS",
            },
            {
                "code": "TRGS 723",
                "title": "Gefährliche explosionsfähige Gemische — Vermeidung der Entzündung",
                "category": "TRGS",
            },
            {
                "code": "TRGS 724",
                "title": (
                    "Gefährliche explosionsfähige Gemische"
                    " — Maßnahmen des konstruktiven Explosionsschutzes"
                ),
                "category": "TRGS",
            },
            {
                "code": "TRGS 725",
                "title": (
                    "Gefährliche explosionsfähige Atmosphäre"
                    " — Mess-, Steuer- und Regeleinrichtungen"
                ),
                "category": "TRGS",
            },
            {
                "code": "TRGS 746",
                "title": "Ortsfeste Druckanlagen für Gase",
                "category": "TRGS",
            },
            {
                "code": "IEC 60079-10-1",
                "title": "Klassifizierung von Bereichen — Gasexplosionsgefährdete Bereiche",
                "category": "IEC",
            },
            {
                "code": "IEC 60079-10-2",
                "title": "Klassifizierung von Bereichen — Staubexplosionsgefährdete Bereiche",
                "category": "IEC",
            },
            {
                "code": "IEC 60079-14",
                "title": "Projektierung, Auswahl und Errichtung elektrischer Anlagen",
                "category": "IEC",
            },
            {
                "code": "IEC 60079-17",
                "title": "Prüfung und Instandhaltung elektrischer Anlagen",
                "category": "IEC",
            },
            {
                "code": "EN 1127-1",
                "title": (
                    "Explosionsfähige Atmosphären — Explosionsschutz"
                    " — Grundlagen und Methodik"
                ),
                "category": "EN",
            },
            {
                "code": "EN 13463-1",
                "title": "Nicht-elektrische Geräte für explosionsgefährdete Bereiche — Grundlagen",
                "category": "EN",
            },
            {
                "code": "IEC 62061",
                "title": "Sicherheit von Maschinen — Funktionale Sicherheit (SIL)",
                "category": "IEC",
            },
            {
                "code": "ISO 13849-1",
                "title": "Sicherheit von Maschinen — Sicherheitsbezogene Teile (PL)",
                "category": "EN",
            },
        ]

        created = 0
        for data in standards:
            if dry_run:
                self.stdout.write(f"  [DRY] Standard: {data['code']}")
                created += 1
                continue
            _, was_created = ReferenceStandard.objects.get_or_create(
                tenant_id=None,
                code=data["code"],
                defaults={
                    "title": data["title"],
                    "category": data["category"],
                    "is_system": True,
                },
            )
            if was_created:
                created += 1
                logger.info("Created standard: %s", data["code"])

        self.stdout.write(f"  Standards: {created} erstellt")
        return created

    def _seed_catalog(self, dry_run: bool) -> int:
        from explosionsschutz.models import MeasureCatalog

        entries = [
            {
                "code": "M-ERD-001",
                "title": "Erdung aller leitfähigen Teile",
                "default_type": "secondary",
                "description_template": (
                    "Alle leitfähigen Teile im Bereich {bereich}"
                    " sind gemäß TRGS 727 zu erden."
                ),
            },
            {
                "code": "M-LUF-001",
                "title": "Technische Lüftung nach IEC 60079-10-1",
                "default_type": "primary",
                "description_template": (
                    "Technische Raumlüftung mit min."
                    " {luftwechsel} Luftwechseln/h installieren."
                ),
            },
            {
                "code": "M-GAS-001",
                "title": "Gaswarnanlage mit automatischer Abschaltung",
                "default_type": "secondary",
                "description_template": (
                    "Gaswarnanlage für {stoff}"
                    " mit Abschaltung bei {schwelle}% UEG."
                ),
            },
            {
                "code": "M-ELE-001",
                "title": "Ex-geschützte elektrische Betriebsmittel",
                "default_type": "secondary",
                "description_template": (
                    "Alle elektrischen Betriebsmittel im Ex-Bereich"
                    " durch Ex-geschützte Ausführung ersetzen."
                ),
            },
            {
                "code": "M-ORG-001",
                "title": "Arbeitsfreigabeverfahren (Permit to Work)",
                "default_type": "organizational",
                "description_template": (
                    "Vor Beginn von Arbeiten im Ex-Bereich"
                    " ist ein Arbeitsfreigabeschein auszustellen."
                ),
            },
            {
                "code": "M-ORG-002",
                "title": "Unterweisung Explosionsschutz",
                "default_type": "organizational",
                "description_template": (
                    "Alle Mitarbeiter im Bereich {bereich} sind"
                    " jährlich zum Explosionsschutz zu unterweisen."
                ),
            },
            {
                "code": "M-KON-001",
                "title": "Druckentlastungseinrichtung",
                "default_type": "tertiary",
                "description_template": "Druckentlastungsfläche gemäß VDI 3673 dimensionieren.",
            },
            {
                "code": "M-KON-002",
                "title": "Explosionsunterdrückung",
                "default_type": "tertiary",
                "description_template": "HRD-System zur Explosionsunterdrückung installieren.",
            },
            {
                "code": "M-SUB-001",
                "title": "Substitution brennbarer Stoffe",
                "default_type": "primary",
                "description_template": (
                    "Prüfung ob {stoff} durch nicht-brennbare"
                    " Alternative ersetzt werden kann."
                ),
            },
            {
                "code": "M-INE-001",
                "title": "Inertisierung mit Stickstoff",
                "default_type": "primary",
                "description_template": "Inertisierung des Behälters mit N₂ auf O₂ < {grenzwert}%.",
            },
        ]

        created = 0
        for data in entries:
            if dry_run:
                self.stdout.write(f"  [DRY] Katalog: {data['code']}")
                created += 1
                continue
            _, was_created = MeasureCatalog.objects.get_or_create(
                tenant_id=None,
                title=data["title"],
                defaults={
                    "code": data["code"],
                    "default_type": data["default_type"],
                    "description_template": data["description_template"],
                    "is_system": True,
                },
            )
            if was_created:
                created += 1
                logger.info("Created catalog: %s", data["code"])

        self.stdout.write(f"  Katalog: {created} erstellt")
        return created

    def _seed_safety_functions(self, dry_run: bool) -> int:
        from explosionsschutz.models import SafetyFunction

        functions = [
            {
                "name": "GW-GENERIC",
                "description": "Standard-Gaswarnanlage mit Alarmierung",
                "performance_level": "d",
                "sil_level": "2",
                "monitoring_method": "continuous",
                "response_time_ms": 5000,
                "proof_test_interval_months": 12,
            },
            {
                "name": "NOT-AUS-EX",
                "description": "Not-Aus-System für Ex-Bereich mit SIL 2",
                "performance_level": "d",
                "sil_level": "2",
                "monitoring_method": "demand",
                "response_time_ms": 100,
                "proof_test_interval_months": 12,
            },
            {
                "name": "INERT-MON",
                "description": "O₂-Überwachung für Inertisierung",
                "performance_level": "d",
                "sil_level": "2",
                "monitoring_method": "continuous",
                "response_time_ms": 2000,
                "proof_test_interval_months": 6,
            },
        ]

        created = 0
        for data in functions:
            if dry_run:
                self.stdout.write(f"  [DRY] Safety: {data['name']}")
                created += 1
                continue
            _, was_created = SafetyFunction.objects.get_or_create(
                tenant_id=None,
                name=data["name"],
                defaults={
                    "description": data["description"],
                    "performance_level": data["performance_level"],
                    "sil_level": data["sil_level"],
                    "monitoring_method": data["monitoring_method"],
                    "response_time_ms": data["response_time_ms"],
                    "proof_test_interval_months": data["proof_test_interval_months"],
                    "is_system": True,
                },
            )
            if was_created:
                created += 1
                logger.info("Created safety function: %s", data["name"])

        self.stdout.write(f"  Safety Functions: {created} erstellt")
        return created

    def _seed_equipment_types(self, dry_run: bool) -> int:
        from explosionsschutz.models import EquipmentType

        types = [
            {
                "manufacturer": "R. Stahl",
                "model": "LED-Leuchte 6036/1",
                "atex_group": "II",
                "atex_category": "2G",
                "protection_type": "Ex e",
                "explosion_group": "IIC",
                "temperature_class": "T4",
                "epl": "Gb",
                "ip_rating": "IP66",
                "default_inspection_interval_months": 36,
            },
            {
                "manufacturer": "Pepperl+Fuchs",
                "model": "KFD2-SR2-Ex1.W",
                "atex_group": "II",
                "atex_category": "1G",
                "protection_type": "Ex i",
                "explosion_group": "IIC",
                "temperature_class": "T6",
                "epl": "Ga",
                "ip_rating": "IP20",
                "default_inspection_interval_months": 12,
            },
            {
                "manufacturer": "Dräger",
                "model": "PIR 7200",
                "description": "Infrarot-Gasdetektor für brennbare Gase",
                "atex_group": "II",
                "atex_category": "2G",
                "protection_type": "Ex d",
                "explosion_group": "IIC",
                "temperature_class": "T4",
                "epl": "Gb",
                "ip_rating": "IP66",
                "default_inspection_interval_months": 6,
            },
            {
                "manufacturer": "Siemens",
                "model": "SITRANS P DS III EX",
                "description": "Drucktransmitter für Ex-Bereich",
                "atex_group": "II",
                "atex_category": "1G",
                "protection_type": "Ex i",
                "explosion_group": "IIC",
                "temperature_class": "T4",
                "epl": "Ga",
                "ip_rating": "IP67",
                "default_inspection_interval_months": 12,
            },
            {
                "manufacturer": "CEAG",
                "model": "GHG 511",
                "description": "Ex-Steckvorrichtung",
                "atex_group": "II",
                "atex_category": "2G",
                "protection_type": "Ex e",
                "explosion_group": "IIC",
                "temperature_class": "T6",
                "epl": "Gb",
                "ip_rating": "IP66",
                "default_inspection_interval_months": 36,
            },
        ]

        created = 0
        for data in types:
            if dry_run:
                self.stdout.write(f"  [DRY] EquipmentType: {data['manufacturer']} {data['model']}")
                created += 1
                continue
            _, was_created = EquipmentType.objects.get_or_create(
                tenant_id=None,
                manufacturer=data["manufacturer"],
                model=data["model"],
                defaults={
                    "description": data.get("description", ""),
                    "atex_group": data["atex_group"],
                    "atex_category": data["atex_category"],
                    "protection_type": data["protection_type"],
                    "explosion_group": data["explosion_group"],
                    "temperature_class": data["temperature_class"],
                    "epl": data["epl"],
                    "ip_rating": data["ip_rating"],
                    "default_inspection_interval_months": (
                        data["default_inspection_interval_months"]
                    ),
                    "is_system": True,
                },
            )
            if was_created:
                created += 1
                logger.info("Created equipment type: %s %s", data["manufacturer"], data["model"])

        self.stdout.write(f"  Equipment Types: {created} erstellt")
        return created
