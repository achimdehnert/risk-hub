# substances/management/commands/load_ghs_data.py
"""
Management Command: Lädt GHS-Referenzdaten (H-Sätze, P-Sätze, Piktogramme).

Usage:
    python manage.py load_ghs_data
    python manage.py load_ghs_data --clear  # Löscht vorher alle Daten
"""

from django.core.management.base import BaseCommand
from substances.models import (
    HazardStatementRef,
    PrecautionaryStatementRef,
    PictogramRef,
)


# GHS Piktogramme
PICTOGRAMS = [
    {
        "code": "GHS01",
        "name_de": "Explodierende Bombe",
        "name_en": "Exploding bomb",
        "description": "Explosive Stoffe, selbstzersetzliche Stoffe, "
                       "organische Peroxide",
    },
    {
        "code": "GHS02",
        "name_de": "Flamme",
        "name_en": "Flame",
        "description": "Entzündbare Gase, Aerosole, Flüssigkeiten, "
                       "Feststoffe, selbsterhitzungsfähige Stoffe",
    },
    {
        "code": "GHS03",
        "name_de": "Flamme über Kreis",
        "name_en": "Flame over circle",
        "description": "Oxidierende Gase, Flüssigkeiten, Feststoffe",
    },
    {
        "code": "GHS04",
        "name_de": "Gasflasche",
        "name_en": "Gas cylinder",
        "description": "Gase unter Druck",
    },
    {
        "code": "GHS05",
        "name_de": "Ätzwirkung",
        "name_en": "Corrosion",
        "description": "Hautätzend, schwere Augenschädigung, "
                       "korrosiv gegenüber Metallen",
    },
    {
        "code": "GHS06",
        "name_de": "Totenkopf mit Knochen",
        "name_en": "Skull and crossbones",
        "description": "Akute Toxizität (Kategorien 1-3)",
    },
    {
        "code": "GHS07",
        "name_de": "Ausrufezeichen",
        "name_en": "Exclamation mark",
        "description": "Akute Toxizität (Kat. 4), Hautreizung, "
                       "Augenreizung, Sensibilisierung der Haut",
    },
    {
        "code": "GHS08",
        "name_de": "Gesundheitsgefahr",
        "name_en": "Health hazard",
        "description": "Sensibilisierung der Atemwege, Keimzellmutagenität, "
                       "Karzinogenität, Reproduktionstoxizität, STOT",
    },
    {
        "code": "GHS09",
        "name_de": "Umwelt",
        "name_en": "Environment",
        "description": "Gewässergefährdend",
    },
]


# H-Sätze (Hazard Statements) - Auswahl der wichtigsten
H_STATEMENTS = [
    # Physikalische Gefahren
    ("H200", "Instabil, explosiv", "physical"),
    ("H201", "Explosiv; Gefahr der Massenexplosion", "physical"),
    ("H202", "Explosiv; große Gefahr durch Splitter, Spreng- und "
             "Wurfstücke", "physical"),
    ("H203", "Explosiv; Gefahr durch Feuer, Luftdruck oder Splitter, "
             "Spreng- und Wurfstücke", "physical"),
    ("H204", "Gefahr durch Feuer oder Splitter, Spreng- und Wurfstücke",
     "physical"),
    ("H205", "Gefahr der Massenexplosion bei Feuer", "physical"),
    ("H220", "Extrem entzündbares Gas", "physical"),
    ("H221", "Entzündbares Gas", "physical"),
    ("H222", "Extrem entzündbares Aerosol", "physical"),
    ("H223", "Entzündbares Aerosol", "physical"),
    ("H224", "Flüssigkeit und Dampf extrem entzündbar", "physical"),
    ("H225", "Flüssigkeit und Dampf leicht entzündbar", "physical"),
    ("H226", "Flüssigkeit und Dampf entzündbar", "physical"),
    ("H227", "Entzündbare Flüssigkeit", "physical"),
    ("H228", "Entzündbarer Feststoff", "physical"),
    ("H229", "Behälter steht unter Druck: kann bei Erwärmung bersten",
     "physical"),
    ("H230", "Kann auch in Abwesenheit von Luft explosionsartig reagieren",
     "physical"),
    ("H231", "Kann auch in Abwesenheit von Luft bei erhöhtem Druck und/oder "
             "erhöhter Temperatur explosionsartig reagieren", "physical"),
    ("H240", "Erwärmung kann Explosion verursachen", "physical"),
    ("H241", "Erwärmung kann Brand oder Explosion verursachen", "physical"),
    ("H242", "Erwärmung kann Brand verursachen", "physical"),
    ("H250", "Entzündet sich in Berührung mit Luft von selbst", "physical"),
    ("H251", "Selbsterhitzungsfähig; kann in Brand geraten", "physical"),
    ("H252", "In großen Mengen selbsterhitzungsfähig; kann in Brand geraten",
     "physical"),
    ("H260", "In Berührung mit Wasser entstehen entzündbare Gase, "
             "die sich spontan entzünden können", "physical"),
    ("H261", "In Berührung mit Wasser entstehen entzündbare Gase", "physical"),
    ("H270", "Kann Brand verursachen oder verstärken; Oxidationsmittel",
     "physical"),
    ("H271", "Kann Brand oder Explosion verursachen; starkes "
             "Oxidationsmittel", "physical"),
    ("H272", "Kann Brand verstärken; Oxidationsmittel", "physical"),
    ("H280", "Enthält Gas unter Druck; kann bei Erwärmung explodieren",
     "physical"),
    ("H281", "Enthält tiefgekühltes Gas; kann Kälteverbrennungen oder "
             "-verletzungen verursachen", "physical"),
    ("H290", "Kann gegenüber Metallen korrosiv sein", "physical"),

    # Gesundheitsgefahren
    ("H300", "Lebensgefahr bei Verschlucken", "health"),
    ("H301", "Giftig bei Verschlucken", "health"),
    ("H302", "Gesundheitsschädlich bei Verschlucken", "health"),
    ("H304", "Kann bei Verschlucken und Eindringen in die Atemwege "
             "tödlich sein", "health"),
    ("H310", "Lebensgefahr bei Hautkontakt", "health"),
    ("H311", "Giftig bei Hautkontakt", "health"),
    ("H312", "Gesundheitsschädlich bei Hautkontakt", "health"),
    ("H314", "Verursacht schwere Verätzungen der Haut und schwere "
             "Augenschäden", "health"),
    ("H315", "Verursacht Hautreizungen", "health"),
    ("H317", "Kann allergische Hautreaktionen verursachen", "health"),
    ("H318", "Verursacht schwere Augenschäden", "health"),
    ("H319", "Verursacht schwere Augenreizung", "health"),
    ("H330", "Lebensgefahr bei Einatmen", "health"),
    ("H331", "Giftig bei Einatmen", "health"),
    ("H332", "Gesundheitsschädlich bei Einatmen", "health"),
    ("H334", "Kann bei Einatmen Allergie, asthmaartige Symptome oder "
             "Atembeschwerden verursachen", "health"),
    ("H335", "Kann die Atemwege reizen", "health"),
    ("H336", "Kann Schläfrigkeit und Benommenheit verursachen", "health"),
    ("H340", "Kann genetische Defekte verursachen", "health"),
    ("H341", "Kann vermutlich genetische Defekte verursachen", "health"),
    ("H350", "Kann Krebs erzeugen", "health"),
    ("H351", "Kann vermutlich Krebs erzeugen", "health"),
    ("H360", "Kann die Fruchtbarkeit beeinträchtigen oder das Kind "
             "im Mutterleib schädigen", "health"),
    ("H361", "Kann vermutlich die Fruchtbarkeit beeinträchtigen oder das Kind "
             "im Mutterleib schädigen", "health"),
    ("H362", "Kann Säuglinge über die Muttermilch schädigen", "health"),
    ("H370", "Schädigt die Organe", "health"),
    ("H371", "Kann die Organe schädigen", "health"),
    ("H372", "Schädigt die Organe bei längerer oder wiederholter "
             "Exposition", "health"),
    ("H373", "Kann die Organe schädigen bei längerer oder wiederholter "
             "Exposition", "health"),

    # Umweltgefahren
    ("H400", "Sehr giftig für Wasserorganismen", "environment"),
    ("H410", "Sehr giftig für Wasserorganismen mit langfristiger Wirkung",
     "environment"),
    ("H411", "Giftig für Wasserorganismen, mit langfristiger Wirkung",
     "environment"),
    ("H412", "Schädlich für Wasserorganismen, mit langfristiger Wirkung",
     "environment"),
    ("H413", "Kann für Wasserorganismen schädlich sein, mit langfristiger "
             "Wirkung", "environment"),
    ("H420", "Schädigt die öffentliche Gesundheit und die Umwelt durch "
             "Ozonabbau in der äußeren Atmosphäre", "environment"),
]


# P-Sätze (Precautionary Statements) - Auswahl der wichtigsten
P_STATEMENTS = [
    # Prävention
    ("P201", "Vor Gebrauch besondere Anweisungen einholen", "prevention"),
    ("P202", "Vor Gebrauch alle Sicherheitshinweise lesen und verstehen",
     "prevention"),
    ("P210", "Von Hitze, heißen Oberflächen, Funken, offenen Flammen sowie "
             "anderen Zündquellen fernhalten. Nicht rauchen", "prevention"),
    ("P211", "Nicht gegen offene Flamme oder andere Zündquelle sprühen",
     "prevention"),
    ("P220", "Von Kleidung und anderen brennbaren Materialien fernhalten",
     "prevention"),
    ("P221", "Mischen mit brennbaren Stoffen unbedingt verhindern",
     "prevention"),
    ("P222", "Kontakt mit Luft nicht zulassen", "prevention"),
    ("P223", "Kontakt mit Wasser wegen heftiger Reaktion und möglichem "
             "Aufflammen unbedingt verhindern", "prevention"),
    ("P230", "Feucht halten mit ...", "prevention"),
    ("P231", "Inhalt unter inertem Gas/... handhaben und aufbewahren",
     "prevention"),
    ("P232", "Vor Feuchtigkeit schützen", "prevention"),
    ("P233", "Behälter dicht verschlossen halten", "prevention"),
    ("P234", "Nur in Originalverpackung aufbewahren", "prevention"),
    ("P235", "Kühl halten", "prevention"),
    ("P240", "Behälter und zu befüllende Anlage erden", "prevention"),
    ("P241", "Explosionsgeschützte elektrische Geräte/Lüftungsanlagen/"
             "Beleuchtung/... verwenden", "prevention"),
    ("P242", "Funkenarme Werkzeuge verwenden", "prevention"),
    ("P243", "Maßnahmen gegen elektrostatische Aufladungen treffen",
     "prevention"),
    ("P244", "Ventile und Ausrüstungsteile öl- und fettfrei halten",
     "prevention"),
    ("P250", "Nicht schleifen/stoßen/.../reiben", "prevention"),
    ("P251", "Nicht durchstechen oder verbrennen, auch nicht nach Gebrauch",
     "prevention"),
    ("P260", "Staub/Rauch/Gas/Nebel/Dampf/Aerosol nicht einatmen",
     "prevention"),
    ("P261", "Einatmen von Staub/Rauch/Gas/Nebel/Dampf/Aerosol vermeiden",
     "prevention"),
    ("P262", "Nicht in die Augen, auf die Haut oder auf die Kleidung "
             "gelangen lassen", "prevention"),
    ("P263", "Kontakt während der Schwangerschaft und der Stillzeit "
             "vermeiden", "prevention"),
    ("P264", "Nach Gebrauch ... gründlich waschen", "prevention"),
    ("P270", "Bei Gebrauch nicht essen, trinken oder rauchen", "prevention"),
    ("P271", "Nur im Freien oder in gut belüfteten Räumen verwenden",
     "prevention"),
    ("P272", "Kontaminierte Arbeitskleidung nicht außerhalb des "
             "Arbeitsplatzes tragen", "prevention"),
    ("P273", "Freisetzung in die Umwelt vermeiden", "prevention"),
    ("P280", "Schutzhandschuhe/Schutzkleidung/Augenschutz/Gesichtsschutz "
             "tragen", "prevention"),
    ("P282", "Schutzhandschuhe und Schutzkleidung mit Kälteisolierung "
             "tragen", "prevention"),
    ("P283", "Schwer entflammbare oder flammhemmende Kleidung tragen",
     "prevention"),
    ("P284", "Atemschutz tragen", "prevention"),
    ("P285", "Bei unzureichender Belüftung Atemschutz tragen", "prevention"),

    # Reaktion
    ("P301", "BEI VERSCHLUCKEN:", "response"),
    ("P302", "BEI BERÜHRUNG MIT DER HAUT:", "response"),
    ("P303", "BEI BERÜHRUNG MIT DER HAUT (oder dem Haar):", "response"),
    ("P304", "BEI EINATMEN:", "response"),
    ("P305", "BEI KONTAKT MIT DEN AUGEN:", "response"),
    ("P306", "BEI KONTAMINIERTER KLEIDUNG:", "response"),
    ("P308", "BEI Exposition oder falls betroffen:", "response"),
    ("P310", "Sofort GIFTINFORMATIONSZENTRUM/Arzt anrufen", "response"),
    ("P311", "GIFTINFORMATIONSZENTRUM/Arzt anrufen", "response"),
    ("P312", "Bei Unwohlsein GIFTINFORMATIONSZENTRUM/Arzt anrufen",
     "response"),
    ("P313", "Ärztlichen Rat einholen/ärztliche Hilfe hinzuziehen",
     "response"),
    ("P314", "Bei Unwohlsein ärztlichen Rat einholen/ärztliche Hilfe "
             "hinzuziehen", "response"),
    ("P315", "Sofort ärztlichen Rat einholen/ärztliche Hilfe hinzuziehen",
     "response"),
    ("P320", "Besondere Behandlung dringend erforderlich (siehe ... auf "
             "diesem Kennzeichnungsetikett)", "response"),
    ("P321", "Besondere Behandlung (siehe ... auf diesem "
             "Kennzeichnungsetikett)", "response"),
    ("P330", "Mund ausspülen", "response"),
    ("P331", "KEIN Erbrechen herbeiführen", "response"),
    ("P332", "Bei Hautreizung:", "response"),
    ("P333", "Bei Hautreizung oder -ausschlag:", "response"),
    ("P334", "In kaltes Wasser tauchen oder nassen Verband anlegen",
     "response"),
    ("P335", "Lose Partikel von der Haut abbürsten", "response"),
    ("P336", "Vereiste Bereiche mit lauwarmem Wasser auftauen. "
             "Betroffenen Bereich nicht reiben", "response"),
    ("P337", "Bei anhaltender Augenreizung:", "response"),
    ("P338", "Eventuell vorhandene Kontaktlinsen nach Möglichkeit "
             "entfernen. Weiter ausspülen", "response"),
    ("P340", "Die Person an die frische Luft bringen und für ungehinderte "
             "Atmung sorgen", "response"),
    ("P341", "Bei Atembeschwerden an die frische Luft bringen und in einer "
             "Position ruhigstellen, die das Atmen erleichtert", "response"),
    ("P342", "Bei Symptomen der Atemwege:", "response"),
    ("P350", "Behutsam mit viel Wasser und Seife waschen", "response"),
    ("P351", "Einige Minuten lang behutsam mit Wasser ausspülen", "response"),
    ("P352", "Mit viel Wasser/... waschen", "response"),
    ("P353", "Haut mit Wasser abwaschen oder duschen", "response"),
    ("P360", "Kontaminierte Kleidung und Haut sofort mit viel Wasser "
             "abwaschen und danach Kleidung ausziehen", "response"),
    ("P361", "Alle kontaminierten Kleidungsstücke sofort ausziehen",
     "response"),
    ("P362", "Kontaminierte Kleidung ausziehen", "response"),
    ("P363", "Kontaminierte Kleidung vor erneutem Tragen waschen", "response"),
    ("P370", "Bei Brand:", "response"),
    ("P371", "Bei Großbrand und großen Mengen:", "response"),
    ("P372", "Explosionsgefahr", "response"),
    ("P373", "KEINE Brandbekämpfung, wenn das Feuer explosive Stoffe/... "
             "erreicht", "response"),
    ("P374", "Brandbekämpfung mit üblichen Vorsichtsmaßnahmen aus "
             "angemessener Entfernung", "response"),
    ("P375", "Wegen Explosionsgefahr Brand aus der Entfernung bekämpfen",
     "response"),
    ("P376", "Undichtigkeit beseitigen, wenn gefahrlos möglich", "response"),
    ("P377", "Brand von ausströmendem Gas: Nicht löschen, bis Undichtigkeit "
             "gefahrlos beseitigt werden kann", "response"),
    ("P378", "... zum Löschen verwenden", "response"),
    ("P380", "Umgebung räumen", "response"),
    ("P381", "Bei Undichtigkeit alle Zündquellen entfernen", "response"),
    ("P390", "Verschüttete Mengen aufnehmen, um Materialschäden zu "
             "vermeiden", "response"),
    ("P391", "Verschüttete Mengen aufnehmen", "response"),

    # Lagerung
    ("P401", "... aufbewahren", "storage"),
    ("P402", "An einem trockenen Ort aufbewahren", "storage"),
    ("P403", "An einem gut belüfteten Ort aufbewahren", "storage"),
    ("P404", "In einem geschlossenen Behälter aufbewahren", "storage"),
    ("P405", "Unter Verschluss aufbewahren", "storage"),
    ("P406", "In korrosionsbeständigem Behälter aufbewahren", "storage"),
    ("P407", "Luftspalt zwischen Stapeln oder Paletten lassen", "storage"),
    ("P410", "Vor Sonnenbestrahlung schützen", "storage"),
    ("P411", "Bei Temperaturen bis max. ...°C aufbewahren", "storage"),
    ("P412", "Nicht Temperaturen über 50°C aussetzen", "storage"),
    ("P413", "Schüttgut in Mengen von mehr als ... kg bei Temperaturen "
             "bis max. ...°C aufbewahren", "storage"),
    ("P420", "Getrennt aufbewahren", "storage"),
    ("P422", "Inhalt unter ... aufbewahren", "storage"),

    # Entsorgung
    ("P501", "Inhalt/Behälter ... zuführen", "disposal"),
    ("P502", "Informationen zur Wiederverwendung oder Wiederverwertung "
             "beim Hersteller erfragen", "disposal"),
    ("P503", "Informationen zur Entsorgung beim Hersteller, Händler oder "
             "der zuständigen Behörde erfragen", "disposal"),
]


class Command(BaseCommand):
    """Lädt GHS-Referenzdaten in die Datenbank."""

    help = "Lädt H-Sätze, P-Sätze und GHS-Piktogramme in die Datenbank"

    def add_arguments(self, parser):
        parser.add_argument(
            "--clear",
            action="store_true",
            help="Löscht alle Referenzdaten vor dem Import",
        )

    def handle(self, *args, **options):
        if options["clear"]:
            self.stdout.write("Lösche bestehende Referenzdaten...")
            HazardStatementRef.objects.all().delete()
            PrecautionaryStatementRef.objects.all().delete()
            PictogramRef.objects.all().delete()

        # Piktogramme laden
        self.stdout.write("Lade GHS-Piktogramme...")
        for p in PICTOGRAMS:
            PictogramRef.objects.update_or_create(
                code=p["code"],
                defaults={
                    "name_de": p["name_de"],
                    "name_en": p["name_en"],
                    "description": p["description"],
                    "svg_path": f"ghs/{p['code'].lower()}.svg",
                }
            )
        self.stdout.write(
            self.style.SUCCESS(f"  {len(PICTOGRAMS)} Piktogramme geladen")
        )

        # H-Sätze laden
        self.stdout.write("Lade H-Sätze...")
        for code, text_de, category in H_STATEMENTS:
            HazardStatementRef.objects.update_or_create(
                code=code,
                defaults={
                    "text_de": text_de,
                    "category": category,
                }
            )
        self.stdout.write(
            self.style.SUCCESS(f"  {len(H_STATEMENTS)} H-Sätze geladen")
        )

        # P-Sätze laden
        self.stdout.write("Lade P-Sätze...")
        for code, text_de, category in P_STATEMENTS:
            PrecautionaryStatementRef.objects.update_or_create(
                code=code,
                defaults={
                    "text_de": text_de,
                    "category": category,
                }
            )
        self.stdout.write(
            self.style.SUCCESS(f"  {len(P_STATEMENTS)} P-Sätze geladen")
        )

        self.stdout.write(self.style.SUCCESS(
            "\n✓ GHS-Referenzdaten erfolgreich geladen!"
        ))
