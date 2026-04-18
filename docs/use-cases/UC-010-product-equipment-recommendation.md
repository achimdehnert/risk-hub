# UC-010: Produkte und Ausrüstung für Maßnahmen vorschlagen

**Status:** Draft
**Modul:** Gefahrstoffe / Maßnahmen / Beschaffung
**Erstellt:** 2026-04-17

## Akteur

Die Fachkraft für Arbeitssicherheit (FaSi) oder der Einkäufer (Rolle: Editor oder Admin)

## Ziel

Das System schlägt geeignete Produkte und Ausrüstung vor, um Schutzmaßnahmen aus der Gefährdungsbeurteilung umzusetzen. Dies umfasst PSA (Persönliche Schutzausrüstung), technische Schutzeinrichtungen und Ersatzprodukte für Substitutionen. Der Vorschlag basiert auf den konkreten Gefährdungen (H-Sätze, Exposition) und den Maßnahmen aus der GefBu.

## Vorbedingung

- Der Benutzer ist eingeloggt und hat die Rolle Editor oder Admin
- Gefährdungsbeurteilungen mit abgeleiteten Maßnahmen existieren (→ UC-008)
- Optional: Produktkatalog mit Lieferanten ist gepflegt

## Scope

Produktvorschläge für Schutzmaßnahmen: PSA, technische Geräte, Substitutionsprodukte.
Nicht Teil: Bestellprozess, Lagerverwaltung, Budgetplanung.

## Schritte

### A. PSA-Empfehlungen (Persönliche Schutzmaßnahmen)

1. Die FaSi öffnet eine Maßnahme vom Typ PERSONAL aus der GefBu
2. Das System analysiert die Gefährdung:
   - H-Sätze des Gefahrstoffs
   - Aggregatzustand (fest/flüssig/gasförmig)
   - Expositionsart (Hautkontakt, Einatmen, Verschlucken, Augenkontakt)
   - P-Sätze (empfohlene Schutzmaßnahmen aus SDS)
3. Das System empfiehlt passende PSA:
   - **Handschuhe**: Material basierend auf Chemikalie (z.B. Nitril bei Lösemitteln, Butyl bei Säuren), Durchbruchzeit aus SDS Abschnitt 8
   - **Atemschutz**: Filtertyp (A=organisch, B=anorganisch, E=Säure, K=Ammoniak, P=Partikel), Schutzstufe (FFP2/FFP3)
   - **Augenschutz**: Schutzbrille, Gesichtsschild (bei Spritzgefahr)
   - **Körperschutz**: Schürze, Schutzanzug (Material + Schutzklasse)
4. Jede Empfehlung enthält:
   - PSA-Kategorie und Spezifikation
   - Begründung (welche H-Sätze/Gefährdungen abgedeckt werden)
   - Normreferenz (z.B. EN 374 für Schutzhandschuhe, EN 14387 für Gasfilter)
   - Optional: Konkrete Produkte aus dem Lieferantenkatalog

### B. Technische Schutzeinrichtungen

1. Die FaSi öffnet eine Maßnahme vom Typ TECHNICAL
2. Das System schlägt vor basierend auf Gefährdungstyp:
   - **Absaugung**: Typ (Punktabsaugung, Raumbelüftung), Volumenstrom
   - **Auffangwannen**: Volumen basierend auf Lagermenge
   - **Messgeräte**: AGW-Monitor, Gaswarngeräte (Gastyp aus H-Sätzen)
   - **Notduschen/Augenspülungen**: Norm EN 15154
   - **Brandschutz**: Löschmittel passend zum Gefahrstoff (aus SDS Abschnitt 5)
3. Empfehlungen mit technischen Spezifikationen und Normbezug

### C. Substitutionsprodukte

1. Die FaSi öffnet eine Substitutionsprüfung (Status: OFFEN oder MÖGLICH)
2. Das System analysiert das aktuelle Produkt:
   - CMR-Eigenschaft (krebserzeugend, mutagen, reproduktionstoxisch)
   - WGK (Wassergefährdungsklasse)
   - H-Satz-Profil
   - VOC-Gehalt
3. Das System sucht in der globalen Produktdatenbank nach Alternativen:
   - Gleiche Verwendungskategorie
   - Niedrigere Gefährdungseinstufung (weniger/mildere H-Sätze)
   - Niedrigere WGK
   - Geringerer VOC-Gehalt
4. Vorschläge werden nach Verbesserungspotenzial gerankt:
   - **Hoch**: CMR → nicht CMR
   - **Mittel**: WGK 3 → WGK 1
   - **Niedrig**: Gleiche Gefährdung, aber bessere Handhabung
5. Jeder Vorschlag enthält:
   - Produktname, Hersteller
   - Gegenüberstellung: Alt vs. Neu (H-Sätze, WGK, VOC)
   - Einschränkungen/Anmerkungen

### D. Zusammenfassung und Export

1. Die FaSi sammelt alle Empfehlungen in einem Beschaffungsvorschlag
2. Export als:
   - **PDF**: Für Freigabe durch Vorgesetzten
   - **Excel**: Für Einkauf (Produkt, Spezifikation, Menge, Lieferant)
3. Verknüpfung: Beschaffte PSA/Ausrüstung wird mit der Maßnahme verknüpft (Status → UMGESETZT)

## Fehlerfälle

- Falls kein SDS für den Gefahrstoff vorliegt: "Keine Empfehlung möglich — SDS erforderlich"
- Falls die Produktdatenbank keine Alternativen enthält: "Keine passenden Substitutionsprodukte gefunden — manuelle Recherche empfohlen"
- Falls Handschuhmaterial und Gefahrstoff inkompatibel: Warnung mit Erklärung
- Falls mehrere Gefahrstoffe gleichzeitig auftreten (Gemisch-Exposition): Empfehlung für die höchste Schutzstufe

## Akzeptanzkriterien

GIVEN eine Maßnahme "Schutzhandschuhe tragen" für ein Lösemittelprodukt
WHEN die FaSi Produktvorschläge anfordert
THEN empfiehlt das System Handschuhmaterial basierend auf den Chemikalien im SDS
AND nennt die erforderliche Durchbruchzeit und EN-Norm

GIVEN ein CMR-Stoff (H350: krebserzeugend)
WHEN die FaSi eine Substitutionsprüfung öffnet
THEN schlägt das System Alternativen ohne CMR-Eigenschaft vor
AND rankt diese nach Verbesserungspotenzial

GIVEN eine technische Maßnahme "Absaugung installieren"
WHEN die FaSi Details anfordert
THEN zeigt das System den empfohlenen Anlagentyp und Volumenstrom

GIVEN mehrere Maßnahmen mit Produktvorschlägen
WHEN die FaSi "Beschaffungsvorschlag exportieren" wählt
THEN wird ein Excel mit Produkt, Spezifikation und Lieferant erstellt

## Referenzen

- **Regulatorisch**: GefStoffV §8-10 (Schutzmaßnahmen), TRGS 401 (Hautkontakt), TRGS 402 (Inhalative Exposition), TRGS 500 (Schutzmaßnahmen)
- **PSA-Normen**: EN 374 (Handschuhe), EN 166 (Augenschutz), EN 14387 (Gasfilter), EN 943 (Schutzanzüge)
- **Verknüpfte UCs**: UC-008 (GefBu), UC-004 (Kataster), UC-005 (SDS Update)
