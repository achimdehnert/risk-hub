# UC-008: Gefährdungsbeurteilung (GefBu) aktualisieren

**Status:** Draft
**Modul:** Gefahrstoffe / Risk Assessment
**Erstellt:** 2026-04-17

## Akteur

Die Fachkraft für Arbeitssicherheit (FaSi) (Rolle: Editor oder Admin)

## Ziel

Die FaSi möchte Gefährdungsbeurteilungen für Gefahrstoffe systematisch aktualisieren. Das umfasst Substitutionsprüfung, Maßnahmenableitung (nach STOP-Prinzip: Substitution → Technisch → Organisatorisch → Persönlich), Risikoanalyse und die Dokumentation der Ergebnisse.

## Vorbedingung

- Der Benutzer ist eingeloggt und hat die Rolle Editor oder Admin
- Produkte mit Gefahrstoffdaten existieren im Kataster
- Standorte und Abteilungen sind angelegt

## Scope

GefBu-Aktualisierung: Substitutionsprüfung, Maßnahmenableitung (STOP), Risikoanalyse, Dokumentation.
Nicht Teil: Initiale Erstellung einer GefBu, Ex-Schutz-Beurteilung (→ UC-002), SDS-Aktualisierung (→ UC-005).

## Schritte

### A. GefBu-Überprüfung auslösen

1. Anlässe für eine GefBu-Aktualisierung:
   - **SDS-Änderung**: Neue Einstufung, neue H-Sätze (automatischer Trigger aus UC-005)
   - **Periodisch**: Alle 2 Jahre oder häufiger bei hohem Gefährdungspotenzial
   - **Anlassbezogen**: Neuer Arbeitsplatz, Arbeitsunfall, Beschwerde, neue Erkenntnisse
   - **Manuell**: FaSi startet Überprüfung
2. Das System zeigt offene GefBu-Aufgaben im Dashboard

### B. Substitutionsprüfung (STOP — S)

1. Die FaSi wählt ein Produkt/einen Arbeitsbereich
2. Das System zeigt:
   - Aktuelle Gefährdungseinstufung (H-Sätze, WGK, CMR-Eigenschaft)
   - EMKG-Stufe (Einfaches Maßnahmenkonzept Gefahrstoffe)
   - Existierende Substitutionsprüfungen (Historie)
3. Die FaSi prüft Substitutionsmöglichkeiten:
   - Gibt es ein weniger gefährliches Alternativprodukt?
   - Ist eine Prozessänderung möglich (z.B. wässrig statt lösemittelbasiert)?
   - Kann die eingesetzte Menge reduziert werden?
4. Ergebnis dokumentieren:
   - **Substitution möglich**: Alternativprodukt angeben, Umsetzungsplan erstellen
   - **Substitution geprüft, nicht möglich**: Begründung dokumentieren
   - **Nicht erforderlich**: Begründung (z.B. Gefährdung gering)
5. `SubstanceUsage.substitution_status` aktualisieren (OPEN → DONE / NOT_REQUIRED)

### C. Maßnahmen ableiten (STOP — T, O, P)

1. Die FaSi leitet Schutzmaßnahmen ab, geordnet nach STOP-Hierarchie:

#### Technische Maßnahmen (T)
- Absaugung / Lüftung (z.B. "Absaugung an Arbeitsplatz 3 installieren")
- Geschlossene Systeme (z.B. "Dosierpumpe statt offenes Umfüllen")
- Technische Barrieren (z.B. "Auffangwanne unter Lagerfass")
- Messung: AGW-Monitoring installieren

#### Organisatorische Maßnahmen (O)
- Betriebsanweisung erstellen/aktualisieren (→ Dokument verknüpfen)
- Zugangs-/Zugangsbeschränkungen (z.B. "Nur unterwiesenes Personal")
- Arbeitszeit begrenzen (z.B. "Max. 4h Exposition pro Schicht")
- Lagervorschriften (Zusammenlagerungsverbote nach TRGS 510)
- Hautschutzplan erstellen

#### Persönliche Schutzmaßnahmen (P)
- PSA festlegen: Handschuhe (Material+Durchbruchzeit), Schutzbrille, Atemschutz
- PSA-Tragepflicht dokumentieren
- Hygienemaßnahmen (Waschgelegenheit, Verbot von Essen/Trinken)

2. Jede Maßnahme wird als strukturierter Datensatz erfasst:
   - Typ: SUBSTITUTION / TECHNICAL / ORGANIZATIONAL / PERSONAL
   - Standort + Abteilung (FK → Site, Department)
   - Beschreibung
   - Verantwortlicher
   - Frist
   - Status: OFFEN / IN_UMSETZUNG / UMGESETZT / NICHT_MÖGLICH
   - Wirksamkeitsprüfung: Datum + Ergebnis

### D. Risikoanalyse

1. Die FaSi bewertet das Restrisiko nach Umsetzung der Maßnahmen:
   - **Expositionsszenario**: Wie oft, wie lange, welche Menge?
   - **EMKG-Einstufung**: Gefährlichkeitsgruppe × Mengenstufe × Dauer → Maßnahmenstufe
   - **Risikomatrix**: Eintrittswahrscheinlichkeit × Schadensausmaß → Risikostufe (1-5)
2. Das System berechnet die EMKG-Stufe automatisch (wenn Daten vorhanden)
3. Die FaSi dokumentiert:
   - Risiko vor Maßnahmen
   - Risiko nach Maßnahmen
   - Akzeptables Restrisiko? (Ja/Nein mit Begründung)

### E. Dokumentation und Freigabe

1. Das System erstellt die GefBu als strukturiertes Dokument:
   - Arbeitsbereich, Tätigkeit, beteiligte Stoffe
   - Gefährdungen (aus SDS: H-Sätze, Expositionsszenarien)
   - Substitutionsprüfung (Ergebnis + Begründung)
   - Maßnahmen (STOP-Hierarchie)
   - Risikoanalyse (vorher/nachher)
   - Nächster Überprüfungstermin
2. Freigabe-Workflow (analog UC-007):
   - Ersteller → Prüfer → Freigabe
   - Revisionierung bei jeder Aktualisierung
3. PDF-Export mit Unterschriftenfeld für Arbeitgeber

## Fehlerfälle

- Falls keine EMKG-Daten vorhanden: Manuelle Einstufung erforderlich, System zeigt Formular
- Falls Substitutionsprüfung >2 Jahre alt: Warnung "Erneute Prüfung empfohlen"
- Falls eine Maßnahme überfällig ist: Eskalation an den Verantwortlichen
- Falls CMR-Stoff (krebserzeugend, mutagen, reproduktionstoxisch): Verschärfte Anforderungen hervorheben

## Akzeptanzkriterien

GIVEN ein Produkt mit neuen H-Sätzen (aus UC-005 SDS-Update)
WHEN die SDS-Aktualisierung abgeschlossen wird
THEN wird automatisch eine GefBu-Aufgabe erstellt
AND die betroffenen Standorte/Abteilungen sind vorausgewählt

GIVEN eine GefBu mit Substitutionsprüfung "möglich"
WHEN die FaSi ein Alternativprodukt angibt
THEN wird ein Umsetzungsplan mit Frist erstellt
AND der Status wechselt auf "IN_UMSETZUNG"

GIVEN eine abgeleitete technische Maßnahme
WHEN die FaSi "Umgesetzt" markiert
THEN fragt das System nach Wirksamkeitsprüfung (Datum + Ergebnis)

GIVEN eine vollständige GefBu mit STOP-Maßnahmen
WHEN der PDF-Export erstellt wird
THEN enthält das PDF alle Abschnitte in der vorgeschriebenen Reihenfolge
AND ein Unterschriftenfeld für den Arbeitgeber

GIVEN ein CMR-Stoff im Arbeitsbereich
WHEN die GefBu erstellt wird
THEN weist das System auf die verschärften Anforderungen nach §10 GefStoffV hin

## Referenzen

- **Regulatorisch**: GefStoffV §6 (Gefährdungsbeurteilung), §7 (Grundpflichten), §8-10 (Schutzmaßnahmen), TRGS 400 (Gefährdungsbeurteilung), TRGS 600 (Substitution)
- **EMKG**: BAuA Einfaches Maßnahmenkonzept Gefahrstoffe
- **STOP-Prinzip**: Substitution → Technisch → Organisatorisch → Persönlich (ArbSchG §4)
- **Verknüpfte UCs**: UC-004 (Kataster), UC-005 (SDS Update), UC-007 (Versionierung), UC-009 (Schulungen)
