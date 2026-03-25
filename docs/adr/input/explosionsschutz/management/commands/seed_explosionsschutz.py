"""
Management Command: seed_explosionsschutz

Befüllt Stammdaten:
  - ReferenceStandard (TRGS 720-727, BetrSichV, EN 1127-1 …)
  - MeasureCatalog (typische Schutzmaßnahmen)
  - EquipmentType (häufige ATEX-Geräte)

Idempotent: update_or_create auf natürlichen Schlüsseln.
Aufruf: python manage.py seed_explosionsschutz [--force]
"""
from __future__ import annotations

from django.core.management.base import BaseCommand, CommandError

from apps.explosionsschutz.models import (
    EquipmentType,
    MeasureCatalog,
    ReferenceStandard,
)

REFERENCE_STANDARDS = [
    # TRGS
    {"code": "TRGS 720:2012-01", "title": "Gefährliche explosionsfähige Gemische – Allgemeines", "category": "trgs", "issue_date": "2012-01"},
    {"code": "TRGS 721:2021-06", "title": "Gefährliche explosionsfähige Atmosphäre (Teile 1–4)", "category": "trgs", "issue_date": "2021-06"},
    {"code": "TRGS 722:2021-06", "title": "Vermeidung oder Einschränkung gefährlicher explosionsfähiger Atmosphäre", "category": "trgs", "issue_date": "2021-06"},
    {"code": "TRGS 723:2021-01", "title": "Vermeidung der Entzündung gefährlicher explosionsfähiger Gemische", "category": "trgs", "issue_date": "2021-01"},
    {"code": "TRGS 724:2021-01", "title": "Maßnahmen des konstruktiven Explosionsschutzes", "category": "trgs", "issue_date": "2021-01"},
    {"code": "TRGS 725:2016-04", "title": "MSR-Einrichtungen im Rahmen von Explosionsschutzmaßnahmen", "category": "trgs", "issue_date": "2016-04"},
    {"code": "TRGS 727:2016-09", "title": "Vermeidung von Zündgefahren infolge elektrostatischer Aufladungen", "category": "trgs", "issue_date": "2016-09"},
    {"code": "TRGS 800:2011-03", "title": "Brandschutzmaßnahmen", "category": "trgs", "issue_date": "2011-03"},
    {"code": "TRGS 407:2019-11", "title": "Tätigkeiten mit Gasen – Gefährdungsbeurteilung", "category": "trgs", "issue_date": "2019-11"},
    {"code": "TRGS 510:2021-04", "title": "Lagerung von Gefahrstoffen in ortsbeweglichen Behältern", "category": "trgs", "issue_date": "2021-04"},
    # TRBS
    {"code": "TRBS 1111:2021-09", "title": "Gefährdungsbeurteilung und sicherheitstechnische Bewertung", "category": "trbs", "issue_date": "2021-09"},
    {"code": "TRBS 1115:2020-01", "title": "Sicherheitsrelevante Mess-, Steuer- und Regeleinrichtungen", "category": "trbs", "issue_date": "2020-01"},
    {"code": "TRBS 1201:2021-09", "title": "Prüfung von Arbeitsmitteln und überwachungsbedürftigen Anlagen (Allgemein)", "category": "trbs", "issue_date": "2021-09"},
    {"code": "TRBS 1203-1:2021-09", "title": "Befähigte Personen – Explosionsgefährdung", "category": "trbs", "issue_date": "2021-09"},
    # Verordnungen
    {"code": "GefStoffV:2021-07", "title": "Verordnung zum Schutz vor Gefahrstoffen (Gefahrstoffverordnung)", "category": "verordnung", "issue_date": "2021-07"},
    {"code": "BetrSichV:2021-07", "title": "Verordnung über Sicherheit und Gesundheitsschutz bei der Verwendung von Arbeitsmitteln", "category": "verordnung", "issue_date": "2021-07"},
    # DIN EN
    {"code": "DIN EN 1127-1:2019-10", "title": "Explosionsfähige Atmosphären – Explosionsschutz – Teil 1: Grundlagen und Methodik", "category": "din_en", "issue_date": "2019-10"},
    {"code": "DIN EN 60079-10-1:2022-02", "title": "Explosionsfähige Atmosphäre – Einteilung der Bereiche – Gasexplosionsgefährdete Bereiche", "category": "din_en", "issue_date": "2022-02"},
    {"code": "DIN EN 60079-14:2020-09", "title": "Explosionsgefährdete Bereiche – Projektierung, Auswahl und Errichtung elektrischer Anlagen", "category": "din_en", "issue_date": "2020-09"},
    {"code": "DIN EN 60079-17:2024-01", "title": "Explosionsgefährdete Bereiche – Prüfung und Instandhaltung elektrischer Anlagen", "category": "din_en", "issue_date": "2024-01"},
    # DGUV
    {"code": "DGUV R 113-001:2019", "title": "Explosionsschutz-Regeln (EX-RL)", "category": "dguv", "issue_date": "2019"},
    {"code": "DGUV I 213-057:2019", "title": "Gaswarneinrichtungen für den Explosionsschutz", "category": "dguv", "issue_date": "2019"},
    # ATEX
    {"code": "ATEX 2014/34/EU", "title": "Richtlinie 2014/34/EU – Geräte und Schutzsysteme für den Einsatz in explosionsgefährdeten Bereichen (ATEX)", "category": "atex", "issue_date": "2014"},
    {"code": "ATEX 1999/92/EG", "title": "Mindestvorschriften zum Schutz von Sicherheit und Gesundheit der Arbeitnehmer (Zoneneinteilung)", "category": "atex", "issue_date": "1999"},
]

MEASURE_CATALOG = [
    # Primäre Maßnahmen
    {
        "title": "Erstinertisierung (N₂-Spülung)",
        "default_category": "primary",
        "description_template": (
            "Erstinertisierung der {ANLAGE} durch N₂-Spülung vor Inbetriebnahme. "
            "Spüldauer: {DAUER} min. Überwachung via MFC (Durchflussmessung ≥ {FLUSS} l/min). "
            "Nachweis durch O₂-Messung (< 1,0 Vol.%) am Ausgang."
        ),
    },
    {
        "title": "Durchflussinertisierung (N₂/H₂-Betrieb)",
        "default_category": "primary",
        "description_template": (
            "Permanente Inertisierung im Betrieb durch kontinuierliche N₂-/Schutzgas-Zufuhr. "
            "Mindestdurchfluss: {FLUSS} l/min. Überwachung durch Durchflusswächter mit Alarm."
        ),
    },
    {
        "title": "Technische Lüftung (Objektabsaugung)",
        "default_category": "primary",
        "description_template": (
            "Objektabsaugung des {BEREICH} mit {VOLUMENSTROM} m³/h. "
            "Lüftungseffektivität gemäß TRGS 722 nachgewiesen. "
            "Überwachung der Lüftungsanlage durch Differenzdruckwächter."
        ),
    },
    {
        "title": "Gaswarnanlage (Gasdetektion UEG)",
        "default_category": "primary",
        "description_template": (
            "Gaswarneinrichtung für {GAS} nach DGUV Information 213-057. "
            "Voralarm bei {VORALARM} % UEG, Hauptalarm + Notabschaltung bei {HAUPTALARM} % UEG. "
            "Jährliche Überprüfung durch Sachkundigen."
        ),
    },
    # Sekundäre Maßnahmen
    {
        "title": "Ex-geschützte Elektroinstallation",
        "default_category": "secondary",
        "description_template": (
            "Alle elektrischen Betriebsmittel in Zone {ZONE} entsprechen der "
            "ATEX-Kategorie {KATEGORIE}. Errichten und Prüfen nach DIN EN 60079-14/-17."
        ),
    },
    {
        "title": "Potenzialausgleich / Erdung (Antistatik)",
        "default_category": "secondary",
        "description_template": (
            "Leitfähige Verbindung aller Anlagenteile und Behälter. "
            "Erdungswiderstand < 1 MΩ nach TRGS 727. "
            "Prüfung vor Arbeitsbeginn und mindestens jährlich."
        ),
    },
    {
        "title": "Zündquellenkontrolle – Heiße Oberflächen",
        "default_category": "secondary",
        "description_template": (
            "Alle Oberflächen in der Zone bleiben unterhalb der Zündtemperatur "
            "des {GAS} ({ZUENDTEMP} °C). Maximale Oberflächentemperatur: {MAXTEMP} °C. "
            "Entspricht Temperaturklasse {TEMP_KLASSE}."
        ),
    },
    {
        "title": "Funkenfallschutz / Funkenfänger",
        "default_category": "secondary",
        "description_template": (
            "Mechanische Arbeiten (Schleifen, Bohren) in Zone {ZONE} nur mit "
            "genehmigten Werkzeugen (funkenarmes Werkzeug). "
            "Heißarbeiten nur mit Erlaubnisschein und Feuerwache."
        ),
    },
    # Konstruktive Maßnahmen
    {
        "title": "Druckfeste Kapselung (Ex d)",
        "default_category": "constructive",
        "description_template": (
            "Einschluss zündfähiger Teile in druckfestem Gehäuse nach IEC 60079-1 "
            "(Schutzart Ex d). Für Zone {ZONE}."
        ),
    },
    {
        "title": "Überdruckkapselung (Ex p)",
        "default_category": "constructive",
        "description_template": (
            "Schaltschrank/Gehäuse mit Überdruckkapselung (Ex p) gemäß IEC 60079-2. "
            "Spülgas: {GAS}. Mindestüberdruck: {DRUCK} Pa."
        ),
    },
    # Organisatorische Maßnahmen
    {
        "title": "Betriebsanweisung nach §14 GefStoffV",
        "default_category": "organisational",
        "description_template": (
            "Schriftliche Betriebsanweisung für Tätigkeiten mit {STOFF} nach §14 GefStoffV. "
            "Unterrichtung der Beschäftigten mindestens jährlich."
        ),
    },
    {
        "title": "Unterweisung Explosionsschutz",
        "default_category": "organisational",
        "description_template": (
            "Jährliche Unterweisung aller Beschäftigten im Explosionsschutz "
            "nach §14 GefStoffV und Anhang 1 Nr. 1 GefStoffV. "
            "Dokumentation der Unterweisungen."
        ),
    },
    {
        "title": "Erlaubnisschein-Verfahren (Heißarbeiten)",
        "default_category": "organisational",
        "description_template": (
            "Vor Heißarbeiten (Schweißen, Schleifen, …) in oder nahe explosionsgefährdeter "
            "Bereiche ist ein Erlaubnisschein nach DGUV R 113-001 einzuholen. "
            "Gültigkeitsdauer: {DAUER} Stunden."
        ),
    },
    {
        "title": "Rauchverbot / Zündquellenverbot",
        "default_category": "organisational",
        "description_template": (
            "Striktes Rauchverbot und Verbot offener Zündquellen in und um "
            "{BEREICH}. Kennzeichnung nach ASR A1.3."
        ),
    },
]

EQUIPMENT_TYPES = [
    {
        "manufacturer": "asecos",
        "model_name": "Gefahrstoffschrank Select W-123",
        "atex_group": "II",
        "atex_category": "3G",
        "protection_type": "Ex ic nA",
        "explosion_group": "IIB",
        "temperature_class": "T4",
        "default_inspection_interval_months": 12,
    },
    {
        "manufacturer": "Pepperl+Fuchs",
        "model_name": "Näherungsschalter NBN-Serie (Zone 1)",
        "atex_group": "II",
        "atex_category": "2G",
        "protection_type": "Ex ia",
        "explosion_group": "IIC",
        "temperature_class": "T6",
        "default_inspection_interval_months": 12,
    },
    {
        "manufacturer": "Bartec",
        "model_name": "Ex-Schaltkasten Typ EPLX (Zone 1)",
        "atex_group": "II",
        "atex_category": "2G",
        "protection_type": "Ex de",
        "explosion_group": "IIC",
        "temperature_class": "T4",
        "default_inspection_interval_months": 12,
    },
    {
        "manufacturer": "Generisch",
        "model_name": "Ex-Motor Zone 2 (3G, IIB, T3)",
        "atex_group": "II",
        "atex_category": "3G",
        "protection_type": "Ex ec",
        "explosion_group": "IIB",
        "temperature_class": "T3",
        "default_inspection_interval_months": 24,
    },
    {
        "manufacturer": "MSA",
        "model_name": "Gasdetektor ULTIMA X5000",
        "atex_group": "II",
        "atex_category": "2G",
        "protection_type": "Ex d ia",
        "explosion_group": "IIC",
        "temperature_class": "T4",
        "default_inspection_interval_months": 12,
    },
]


class Command(BaseCommand):
    help = "Lädt Stammdaten für das Explosionsschutz-Modul (idempotent)"

    def add_arguments(self, parser):
        parser.add_argument(
            "--force",
            action="store_true",
            help="Vorhandene Einträge überschreiben",
        )

    def handle(self, *args, **options):
        force = options["force"]

        # ── ReferenceStandard ────────────────────────────────────────────
        created_rs = updated_rs = 0
        for data in REFERENCE_STANDARDS:
            obj, created = ReferenceStandard.objects.update_or_create(
                code=data["code"],
                tenant_id=None,  # globale Systemdaten
                defaults={**data, "is_system": True, "is_active": True},
            )
            if created:
                created_rs += 1
            elif force:
                for k, v in data.items():
                    setattr(obj, k, v)
                obj.is_system = True
                obj.save()
                updated_rs += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"ReferenceStandard: {created_rs} neu, {updated_rs} aktualisiert"
            )
        )

        # ── MeasureCatalog ───────────────────────────────────────────────
        created_mc = updated_mc = 0
        for data in MEASURE_CATALOG:
            obj, created = MeasureCatalog.objects.update_or_create(
                title=data["title"],
                tenant_id=None,
                defaults={**data, "is_system": True, "is_active": True},
            )
            if created:
                created_mc += 1
            elif force:
                for k, v in data.items():
                    setattr(obj, k, v)
                obj.is_system = True
                obj.save()
                updated_mc += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"MeasureCatalog: {created_mc} neu, {updated_mc} aktualisiert"
            )
        )

        # ── EquipmentType ────────────────────────────────────────────────
        created_et = updated_et = 0
        for data in EQUIPMENT_TYPES:
            obj, created = EquipmentType.objects.update_or_create(
                manufacturer=data["manufacturer"],
                model_name=data["model_name"],
                tenant_id=None,
                defaults={**data, "is_system": True},
            )
            if created:
                created_et += 1
            elif force:
                for k, v in data.items():
                    setattr(obj, k, v)
                obj.is_system = True
                obj.save()
                updated_et += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"EquipmentType: {created_et} neu, {updated_et} aktualisiert"
            )
        )

        self.stdout.write(self.style.SUCCESS("\n✓ seed_explosionsschutz abgeschlossen."))
        return 0
