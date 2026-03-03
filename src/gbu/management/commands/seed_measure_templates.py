"""
Seed-Command: GBU Schutzmaßnahmen-Vorlagen (MeasureTemplate).

Idempotent: update_or_create auf (category, tops_type, title).
Abhängigkeit: seed_hazard_categories muss zuerst ausgeführt worden sein.

Quelle: TRGS 500, TRGS 555, GefStoffV §7-§10 (Stand 2024-09)

TOPS-Hierachie: S (Substitution) > T (Technisch) > O (Organisatorisch) > P (Persönlich)
"""
import logging

from django.core.management.base import BaseCommand
from django.db import transaction

logger = logging.getLogger(__name__)

# Format: (category_code, tops_type, title, description, legal_basis, is_mandatory, sort_order)
MEASURE_TEMPLATES: list[tuple] = [

    # ── BRAND UND EXPLOSION ───────────────────────────────────────────
    ("fire_explosion", "S", "Substitution durch nicht-entzündbare Alternative prüfen",
     "Ersatz durch wasserbasierte oder unbrennbare Produkte (TRGS 600)",
     "GefStoffV §7 Abs. 1, TRGS 600", True, 10),
    ("fire_explosion", "T", "Ex-geschützte Geräte und Installationen (ATEX)",
     "Elektrische Betriebsmittel gemäß Explosionsschutz-Richtlinie 2014/34/EU",
     "BetrSichV, TRGS 720", True, 20),
    ("fire_explosion", "T", "Lüftungsanlage / lokale Absaugung",
     "Technische Lüftung verhindert explosionsfähige Atmosphäre (< 25% UEG)",
     "TRGS 722, GefStoffV §7", False, 30),
    ("fire_explosion", "T", "Zündquellen fernhalten / Rauchverbot",
     "Keine offenen Flammen, heißen Oberflächen oder Funken im Gefahrenbereich",
     "TRGS 722", True, 40),
    ("fire_explosion", "O", "Betriebsanweisung für den Umgang mit entzündbaren Stoffen",
     "Schriftliche Anweisung gemäß TRGS 555 erstellen und aushängen",
     "GefStoffV §14, TRGS 555", True, 50),
    ("fire_explosion", "O", "Lagerung in zugelassenen Behältern / Sicherheitsschrank",
     "Kleinmengenregelung beachten (TRGS 510), Ex-Sicherheitsschrank verwenden",
     "TRGS 510", False, 60),
    ("fire_explosion", "P", "Antistatische Schutzkleidung / ESD-Schuhe",
     "Verhinderung elektrostatischer Entladung als Zündquelle",
     "TRGS 727", False, 70),

    # ── AKUTE TOXIZITÄT ───────────────────────────────────────────────
    ("acute_toxic", "S", "Substitution durch weniger toxische Alternativen",
     "Ersatz durch Stoffe niedrigerer Toxizitätsklasse (GefStoffV §7 Abs. 1)",
     "GefStoffV §7 Abs. 1, TRGS 600", True, 10),
    ("acute_toxic", "T", "Geschlossenes System / vollständige Kapselung",
     "Exposition durch geschlossene Prozessführung auf Null reduzieren",
     "TRGS 500 Nr. 4.1", False, 20),
    ("acute_toxic", "T", "Lokale Absaugung an der Entstehungsstelle",
     "Erfassung von Dämpfen/Aerosolen direkt an der Quelle (mind. 0,5 m/s Strömungsgeschwindigkeit)",
     "TRGS 500 Nr. 4.2, DIN EN 689", True, 30),
    ("acute_toxic", "O", "Betriebsanweisung mit Erste-Hilfe-Maßnahmen",
     "Inhalt: Gefahren, Schutzmaßnahmen, Verhalten im Notfall, Erste Hilfe, Entsorgung",
     "GefStoffV §14, TRGS 555", True, 40),
    ("acute_toxic", "O", "Arbeitsmedizinische Vorsorge (Pflicht)",
     "Angebotsvorsorge oder Pflichtvorsorge gemäß ArbMedVV und DGUV Grundsatz G 29",
     "ArbMedVV Anhang, GefStoffV §15a", True, 50),
    ("acute_toxic", "P", "Atemschutz (Halbmaske FFP3 oder Gasmaske)",
     "Geeigneter Atemschutz entsprechend dem Stoff und der Konzentration",
     "TRGS 500 Nr. 4.4, PSA-BV", True, 60),
    ("acute_toxic", "P", "Schutzhandschuhe (Durchbruchzeit beachten)",
     "Geeignetes Handschuhmaterial entsprechend SDB Abschnitt 8",
     "TRGS 401, PSA-BV", True, 70),

    # ── CHRONISCHE TOXIZITÄT / STOT ───────────────────────────────────
    ("chronic_toxic", "S", "Substitution durch Stoff ohne STOT-Einstufung prüfen",
     "Ersatz durch Produkte ohne Organtoxizität",
     "GefStoffV §7, TRGS 600", True, 10),
    ("chronic_toxic", "T", "Technische Lüftung / Absauganlage",
     "Dauerhafte technische Lüftung zur Unterschreitung von AGW/BGW",
     "TRGS 900, TRGS 500", True, 20),
    ("chronic_toxic", "O", "Regelmäßige Arbeitsplatzmessung (Expositionsermittlung)",
     "Messung der Luft am Arbeitsplatz nach TRGS 402, Dokumentation der Ergebnisse",
     "GefStoffV §10, TRGS 402", True, 30),
    ("chronic_toxic", "O", "Arbeitsmedizinische Vorsorge",
     "Pflicht- oder Angebotsvorsorge abhängig vom AGW-Unterschreitung",
     "ArbMedVV, GefStoffV §15a", True, 40),
    ("chronic_toxic", "P", "Atemschutz entsprechend Konzentration",
     "Filtrierende Halbmaske (FFP2/FFP3) oder umluftunabhängiger Atemschutz",
     "TRGS 500, PSA-BV", False, 50),

    # ── HAUT: ÄTZ-/REIZWIRKUNG ────────────────────────────────────────
    ("skin_corrosion", "S", "Substitution durch hautverträgliche Alternative",
     "Einsatz von Produkten ohne H314/H315-Einstufung wo möglich",
     "GefStoffV §7, TRGS 401", True, 10),
    ("skin_corrosion", "T", "Vollständig geschlossenes System",
     "Kein Hautkontakt durch technische Kapselung",
     "TRGS 401 Nr. 4", False, 20),
    ("skin_corrosion", "O", "Hautschutzplan erstellen und aushängen",
     "Vorsorge, Schutz und Pflege gemäß TRGS 401 und DGUV Information 212-016",
     "TRGS 401", True, 30),
    ("skin_corrosion", "O", "Hautarztverfahren / arbeitsmedizinische Vorsorge Haut",
     "Frühzeitige Erkennung berufsbedingter Hauterkrankungen",
     "ArbMedVV Anhang, BKV", False, 40),
    ("skin_corrosion", "P", "Chemikalienschutzhandschuhe (Norm EN 374)",
     "Geeignetes Material und Dicke gemäß SDB Abschnitt 8; Durchbruchzeit > Tragezeit",
     "TRGS 401, EN 374, PSA-BV", True, 50),
    ("skin_corrosion", "P", "Schutzbrille / Gesichtsschutz bei Spritzgefahr",
     "Bei Spritz- oder Spritzgefahr zusätzlich Gesichtsschutz",
     "PSA-BV", False, 60),

    # ── AUGENSCHÄDEN ──────────────────────────────────────────────────
    ("eye_damage", "T", "Spritzschutz / Abdeckung am Arbeitsplatz",
     "Technische Abdeckungen verhindern Aerosolbildung und Spritzer",
     "ArbStättV, TRGS 500", False, 10),
    ("eye_damage", "O", "Augenspülstation in Reichweite (max. 10 Sek.)",
     "Notaugendusche gemäß DIN EN 15154-2 in unmittelbarer Nähe des Arbeitsplatzes",
     "DGUV Regel 115-002, ArbStättV", True, 20),
    ("eye_damage", "P", "Schutzbrille (EN 166) — Pflicht bei Spritzgefahr",
     "Dicht abschließende Schutzbrille (Typ B oder 3) bei H318-Stoffen Pflicht",
     "PSA-BV, EN 166", True, 30),

    # ── ATEMWEGSSENSIBILISIERUNG ─────────────────────────────────────
    ("respiratory", "S", "Substitution durch nicht-sensibilisierende Alternative",
     "Ersatz durch Stoffe ohne H334-Einstufung, z.B. alternative Reaktivharze",
     "GefStoffV §7, TRGS 600", True, 10),
    ("respiratory", "T", "Vollständig geschlossenes System",
     "Kein Kontakt mit sensibilisierenden Dämpfen oder Aerosolen",
     "TRGS 406", True, 20),
    ("respiratory", "T", "Hochleistungsabsaugung mit HEPA-Filter",
     "Absauganlage mit Partikelabscheidung > 99,95% (HEPA H14)",
     "TRGS 406, TRGS 500", False, 30),
    ("respiratory", "O", "Präventive Arbeitsmedizin (Vorsorge vor Erstexposition)",
     "Lungenfunktionstest und Allergietest vor Beginn der Tätigkeit",
     "ArbMedVV G 23, TRGS 406", True, 40),
    ("respiratory", "P", "Umluftunabhängiger Atemschutz (PAPR oder BA)",
     "Bei Expositionsspitzen Gebgläse-Atemschutz (TH3P) oder Frischluft",
     "PSA-BV, TRGS 406", True, 50),

    # ── HAUTSENSIBILISIERUNG ────────────────────────────────────────────
    ("skin_sens", "S", "Substitution durch nicht-sensibilisierende Alternative",
     "Ersatz durch Produkte ohne H317-Einstufung",
     "GefStoffV §7, TRGS 401", True, 10),
    ("skin_sens", "O", "Hautschutzplan mit geeignetem Vorschutzmittel",
     "Vorschutzcreme vor der Arbeit, Hautreinigung, Hautpflege nach der Arbeit",
     "TRGS 401, DGUV 212-016", True, 20),
    ("skin_sens", "O", "Arbeitsmedizinische Vorsorge Haut (G 24)",
     "Regelmäßige dermatologische Kontrolle auf Sensibilisierung",
     "ArbMedVV, DGUV Grundsatz G 24", True, 30),
    ("skin_sens", "P", "Chemikalienschutzhandschuhe (kein Latex bei Latex-Allergie)",
     "Geeignetes Material gemäß SDB; bei Latex-Sensibilisierung latexfreie Handschuhe",
     "TRGS 401, EN 374", True, 40),

    # ── CMR-STOFFE ────────────────────────────────────────────────────
    ("cmr", "S", "Substitution ist Pflicht (GefStoffV §7 Abs. 1)",
     "CMR-Stoffe Kat. 1A/1B müssen durch weniger gefährliche Stoffe ersetzt werden, "
     "wenn technisch möglich",
     "GefStoffV §7 Abs. 1, TRGS 905", True, 10),
    ("cmr", "T", "Vollständig geschlossenes System (Pflicht bei Kat. 1A/1B)",
     "Kein Freisetzen von CMR-Stoffen; vollständige technische Kapselung",
     "GefStoffV §9, TRGS 910", True, 20),
    ("cmr", "T", "Hochleistungsabsaugung (HEPA H14) an der Quelle",
     "Partikelabscheidung > 99,95%; regelmäßige Filterkontrolle",
     "TRGS 910, TRGS 500", True, 30),
    ("cmr", "O", "Verzeichnis exponierter Beschäftigter führen",
     "Pflicht: Aufzeichnung aller mit CMR-Stoffen Kat. 1A/1B arbeitenden Personen",
     "GefStoffV §14 Abs. 3, TRGS 905", True, 40),
    ("cmr", "O", "Arbeitsmedizinische Pflichtvorsorge",
     "Pflichtvorsorge gemäß ArbMedVV Anhang für CMR-Tätigkeiten",
     "ArbMedVV Anhang Teil 1 Abs. 1, GefStoffV §15a", True, 50),
    ("cmr", "O", "Schwangere und stillende Mütter: Beschäftigungsverbot",
     "Kein Einsatz schwangerer oder stillender Frauen an CMR-Arbeitsplätzen",
     "MuSchG §11, TRGS 905", True, 60),
    ("cmr", "P", "Höchster verfügbarer Atemschutz (P3/ABEK P3 oder Frischluftatem)",
     "Mindestens FFP3 oder Vollmaske mit Kombinationsfilter; "
     "Tragezeitbegrenzer beachten",
     "PSA-BV, TRGS 910", True, 70),

    # ── UMWELTGEFÄHRLICHKEIT ───────────────────────────────────────────
    ("environment", "T", "Auffangwanne / Sekundärcontainment",
     "Bauliche Sicherung gegen unkontrolliertes Austreten (10% oder max. größtes Behältervolumen)",
     "WHG §62, AwSV, VAwS", True, 10),
    ("environment", "O", "Notfallplan Stofffreisetzung und Leckage",
     "Schriftlicher Notfallplan mit zuständigem Sachverständigen für Gewässerschütz",
     "WHG, TRGS 555", True, 20),
    ("environment", "O", "Ordnungsgemäße Entsorgung als Sonderabfall",
     "Vertragspartner für zertifizierte Sonderabfallentsorgung benennen",
     "KrWG, AVV", True, 30),
    ("environment", "P", "Chemikalienschutzanzug bei Leckage-Intervention",
     "CSA Typ 3/4 bei Reinigungs- und Sanierungsarbeiten",
     "PSA-BV", False, 40),

    # ── ERSTICKUNGSGEFAHR ────────────────────────────────────────────
    ("asphyxiant", "T", "O2-Überwachung (Gaswarnanlage, Alarm < 18 Vol-%)",
     "Kontinuierliche Sauerstoffmessung mit akustischem Alarm bei Unterschreitung",
     "TRGS 500, DGUV Regel 113-004", True, 10),
    ("asphyxiant", "O", "Befahren nur mit Erlaubnisschein (Permit-to-Work)",
     "Schriftliche Freigabe für enge Räume, Sicherungsposten außen",
     "DGUV Regel 113-004, BetrSichV", True, 20),
    ("asphyxiant", "P", "Umluftunabhängiger Atemschutz (Pressluftatmer)",
     "Kein Filterschutz — nur umluftunabhängiger Atemschutz in sauerstoffarmer Atmosphäre",
     "PSA-BV, DGUV Regel 113-004", True, 30),
]


class Command(BaseCommand):
    help = (
        "Seed GBU Schutzmaßnahmen-Vorlagen (MeasureTemplate) — "
        "idempotent via update_or_create(category, tops_type, title)"
    )

    @transaction.atomic
    def handle(self, *args, **options) -> None:
        from gbu.models.reference import HazardCategoryRef, MeasureTemplate

        created_count = 0
        updated_count = 0
        error_count = 0

        for (
            category_code, tops_type, title,
            description, legal_basis, is_mandatory, sort_order,
        ) in MEASURE_TEMPLATES:
            try:
                category = HazardCategoryRef.objects.get(code=category_code)
            except HazardCategoryRef.DoesNotExist:
                self.stderr.write(
                    self.style.ERROR(
                        f"  ERROR: Kategorie '{category_code}' nicht gefunden "
                        f"('{title}'). seed_hazard_categories zuerst ausführen."
                    )
                )
                error_count += 1
                continue

            _, created = MeasureTemplate.objects.update_or_create(
                category=category,
                tops_type=tops_type,
                title=title,
                defaults={
                    "description": description,
                    "legal_basis": legal_basis,
                    "is_mandatory": is_mandatory,
                    "sort_order": sort_order,
                },
            )
            if created:
                created_count += 1
                logger.info(
                    "[seed_measure_templates] Erstellt: [%s] %s",
                    tops_type, title,
                )
            else:
                updated_count += 1

        if error_count > 0:
            self.stderr.write(
                self.style.ERROR(
                    f"FEHLER: {error_count} Vorlagen konnten nicht angelegt werden."
                )
            )
            raise SystemExit(1)

        total = MeasureTemplate.objects.count()
        self.stdout.write(
            self.style.SUCCESS(
                f"OK: {created_count} erstellt, {updated_count} aktualisiert "
                f"— {total} Vorlagen gesamt"
            )
        )
