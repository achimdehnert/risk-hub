# UC-009: Gefahrstoff-Schulungen organisieren

**Status:** Draft
**Modul:** Gefahrstoffe / Schulungen
**Erstellt:** 2026-04-17

## Akteur

Die Fachkraft für Arbeitssicherheit (FaSi) oder der Schulungsbeauftragte (Rolle: Editor oder Admin)

## Ziel

Der Schulungsbeauftragte möchte Gefahrstoff-Unterweisungen und -Schulungen systematisch planen, Materialien erstellen und die Durchführung dokumentieren. Das System unterstützt den kompletten Schulungszyklus: Bedarf ermitteln, Materialien erstellen, Termine organisieren, Teilnahme dokumentieren.

## Vorbedingung

- Der Benutzer ist eingeloggt und hat die Rolle Editor oder Admin
- Gefahrstoffdaten existieren im Kataster (→ UC-004)
- Standorte und Abteilungen sind angelegt
- Optional: Betriebsanweisungen sind verknüpft (→ UC-008)

## Scope

Schulungsbedarf, Materialerstellung, Terminierung, Dokumentation.
Nicht Teil: Allgemeine Arbeitssicherheitsschulungen (nicht gefahrstoffspezifisch), E-Learning-Plattform.

## Schritte

### A. Schulungsbedarf ermitteln

1. Das System identifiziert Schulungsbedarf automatisch:
   - **Neue Mitarbeiter**: Erstunterweisung vor Arbeitsaufnahme
   - **SDS-Änderung**: Betroffene Mitarbeiter bei geänderten Gefährdungen (Trigger aus UC-005)
   - **GefBu-Update**: Neue oder geänderte Maßnahmen (Trigger aus UC-008)
   - **Periodisch**: Mindestens jährliche Wiederholungsunterweisung (GefStoffV §14)
   - **Neue Gefahrstoffe**: Erstunterweisung bei neuen Produkten am Arbeitsplatz
2. Das System zeigt im Dashboard:
   - Offene Schulungsbedarfe pro Standort/Abteilung
   - Überfällige Unterweisungen (>12 Monate)
   - Betroffene Mitarbeiteranzahl

### B. Schulungsmaterialien erstellen

1. Der Schulungsbeauftragte wählt einen Schulungsbedarf
2. Das System schlägt Inhalte vor basierend auf:
   - Betroffene Gefahrstoffe (aus Kataster)
   - H-/P-Sätze und GHS-Piktogramme
   - Betriebsanweisungen des Arbeitsbereichs
   - Schutzmaßnahmen aus der GefBu (STOP-Maßnahmen)
3. Der Schulungsbeauftragte erstellt/bearbeitet Schulungsmaterialien:
   - **Unterweisungsunterlage**: Zusammenfassung der relevanten Gefahren und Maßnahmen
   - **Betriebsanweisungen**: Verknüpfung mit existierenden BA
   - **Praxisteil**: Checkliste für praktische Demonstration (z.B. PSA anlegen)
   - **Wissenstest**: Optional, Multiple-Choice-Fragen zur Erfolgskontrolle
4. Das System generiert automatisch:
   - GHS-Piktogramm-Übersicht für die betroffenen Stoffe
   - Erste-Hilfe-Maßnahmen (aus SDS Abschnitt 4)
   - Notfall-Kontakte und Sammelplätze (pro Standort)
5. Export als PDF oder als Präsentation

### C. Schulung organisieren

1. Der Schulungsbeauftragte erstellt einen Schulungstermin:
   - Titel, Beschreibung
   - Standort + Raum
   - Datum/Uhrzeit + Dauer
   - Schulungstyp: ERSTUNTERWEISUNG / WIEDERHOLUNG / ANLASSBEZOGEN
   - Zielgruppe: Abteilung(en) + optionale Mitarbeiterliste
   - Referent
   - Verknüpfte Materialien
2. Optional: Einladungs-Mail an Teilnehmer
3. Optional: Kalender-Integration (iCal-Export)

### D. Teilnahme dokumentieren

1. Nach der Schulung dokumentiert der Schulungsbeauftragte:
   - Tatsächliche Teilnehmer (Anwesenheitsliste)
   - Dauer
   - Behandelte Themen (Verknüpfung zu Materialien)
   - Ergebnis Wissenstest (wenn durchgeführt)
2. Jeder Teilnehmer wird als "unterwiesen" markiert:
   - `last_training_date` pro Mitarbeiter/Gefahrstoff-Gruppe
   - Nächster Unterweisungstermin: automatisch +12 Monate
3. Die Dokumentation ist revisionssicher (Audit-Trail)
4. Export: Unterweisungsnachweis als PDF mit:
   - Datum, Thema, Referent
   - Teilnehmerliste mit Unterschriftsfeld
   - Behandelte Gefahrstoffe/Betriebsanweisungen

### E. Nachverfolgung

1. Das System verfolgt:
   - Wer wurde wann zu welchen Stoffen unterwiesen?
   - Wer hat gefehlt? → Nachholtermin vorschlagen
   - Welche Abteilungen sind vollständig unterwiesen?
2. Compliance-Report: %-Anteil unterwiesener Mitarbeiter pro Standort/Abteilung

## Fehlerfälle

- Falls ein Mitarbeiter bei der Schulung fehlt: System erstellt automatisch Nachholbedarf
- Falls keine Betriebsanweisung für einen Gefahrstoff existiert: Warnung "BA erstellen empfohlen"
- Falls die Unterweisungsfrist <30 Tage: Eskalations-Mail an Vorgesetzten
- Falls der Referent kein FaSi/Editor ist: Hinweis "Fachkundige Unterweisung sicherstellen"

## Akzeptanzkriterien

GIVEN ein SDS-Update mit neuen H-Sätzen (aus UC-005)
WHEN die GefBu aktualisiert wurde
THEN erstellt das System automatisch einen Schulungsbedarf für betroffene Abteilungen

GIVEN einen Schulungstermin mit 20 Teilnehmern
WHEN der Schulungsbeauftragte die Anwesenheit dokumentiert (18 von 20)
THEN werden 18 Mitarbeiter als "unterwiesen" markiert
AND für 2 fehlende Mitarbeiter wird ein Nachholbedarf erstellt

GIVEN einen Schulungsbedarf für Abteilung "Produktion"
WHEN der Schulungsbeauftragte Materialien erstellt
THEN schlägt das System automatisch die relevanten Gefahrstoffe, H-Sätze und Betriebsanweisungen vor

GIVEN das Schulungs-Dashboard
WHEN der Schulungsbeauftragte es öffnet
THEN sieht er den %-Anteil unterwiesener Mitarbeiter pro Standort
AND überfällige Unterweisungen sind rot markiert

## Referenzen

- **Regulatorisch**: GefStoffV §14 (Unterrichtung und Unterweisung), ArbSchG §12 (Unterweisung)
- **Frist**: Mindestens jährlich, vor Arbeitsaufnahme, bei wesentlichen Änderungen
- **Verknüpfte UCs**: UC-004 (Kataster), UC-005 (SDS Update), UC-008 (GefBu)
