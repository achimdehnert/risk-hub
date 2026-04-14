"""Project constants and configuration data.

Extracted from projects/views.py for service-layer compliance.
"""

DOCUMENT_KIND_META = {
    "ex_schutz": {
        "label": "Explosionsschutzdokument",
        "icon": "zap",
        "default_sections": [
            ("1_allgemeines", "1. Allgemeines"),
            ("2_betrieb", "2. Beschreibung des Betriebs"),
            ("3_stoffe", "3. Verwendete Gefahrstoffe"),
            ("4_zonen", "4. Zoneneinteilung"),
            ("5_zuendquellen", "5. Zündquellenanalyse"),
            ("6_massnahmen", "6. Schutzmaßnahmen"),
            ("7_betriebsmittel", "7. Betriebsmittel"),
            ("8_pruefung", "8. Prüfung und Wartung"),
            ("9_unterweisung", "9. Unterweisung"),
            ("10_zusammenfassung", "10. Zusammenfassung"),
        ],
    },
    "gbu": {
        "label": "Gefährdungsbeurteilung",
        "icon": "clipboard-check",
        "default_sections": [
            ("1_allgemeines", "1. Allgemeines"),
            ("2_taetigkeit", "2. Tätigkeit / Arbeitsplatz"),
            ("3_gefaehrdungen", "3. Gefährdungen"),
            ("4_massnahmen", "4. Schutzmaßnahmen"),
            ("5_bewertung", "5. Risikobewertung"),
            ("6_ergebnis", "6. Ergebnis"),
        ],
    },
    "brandschutz": {
        "label": "Brandschutznachweis",
        "icon": "flame",
        "default_sections": [
            ("1_allgemeines", "1. Allgemeines"),
            ("2_baulich", "2. Baulicher Brandschutz"),
            ("3_anlagentechnisch", "3. Anlagentechnischer Brandschutz"),
            ("4_organisatorisch", "4. Organisatorischer Brandschutz"),
            ("5_flucht", "5. Flucht- und Rettungswege"),
            ("6_ergebnis", "6. Ergebnis"),
        ],
    },
}
