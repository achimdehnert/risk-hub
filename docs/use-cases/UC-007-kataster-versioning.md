# UC-007: Gefahrstoffkataster versionieren (Dokumentenlenkung)

**Status:** Draft
**Modul:** Gefahrstoffe (Kataster / Documents)
**Erstellt:** 2026-04-17

## Akteur

Der Sicherheitsbeauftragte (Rolle: Editor oder Admin)

## Ziel

Der Sicherheitsbeauftragte möchte das Gefahrstoffkataster als gelenktes Dokument führen. Jede Änderung wird versioniert, nachvollziehbar dokumentiert und kann als Revision freigegeben werden. Dies erfüllt die Anforderungen an die Dokumentenlenkung nach GefStoffV und ISO 45001.

## Vorbedingung

- Der Benutzer ist eingeloggt und hat die Rolle Editor oder Admin
- Ein Gefahrstoffkataster existiert für mindestens einen Standort
- Das Dokumentenlenkungs-Modul ist aktiviert

## Scope

Versionierung, Änderungshistorie, Freigabe-Workflow, PDF-Export als gelenkte Revision.
Nicht Teil: Inhaltliche Pflege des Katasters (→ UC-004), SDS-Aktualisierung (→ UC-005).

## Schritte

### A. Kataster-Version erstellen

1. Der Sicherheitsbeauftragte öffnet das Kataster für einen Standort
2. Er klickt auf "Neue Revision erstellen"
3. Das System erstellt einen Snapshot des aktuellen Katasters:
   - Alle Produkte mit ihren aktuellen Daten
   - Alle SubstanceUsage-Einträge des Standorts
   - Verknüpfte SDS-Revisionen
   - Zeitstempel und Ersteller
4. Das System vergibt eine Revisionsnummer (z.B. "Rev. 3.0 — 2026-04-17")
5. Optional: Der Sicherheitsbeauftragte ergänzt einen Revisionskommentar

### B. Änderungsverfolgung

1. Das System erfasst automatisch jede Änderung am Kataster:
   - Neues Produkt hinzugefügt
   - Produkt entfernt/archiviert
   - SDS aktualisiert (neue Revision)
   - Lagerort/Lagerklasse geändert
   - Betriebsanweisung verknüpft
2. Zwischen zwei Revisionen zeigt das System einen **Changelog**:
   - Hinzugefügt: X Produkte
   - Geändert: Y Einträge (mit Diff pro Feld)
   - Entfernt/Archiviert: Z Produkte
3. Der Changelog wird als Teil der Revision gespeichert

### C. Freigabe-Workflow

1. Der Sicherheitsbeauftragte reicht die Revision zur Freigabe ein
2. Der Freigeber (Rolle: Admin oder Fachkraft für Arbeitssicherheit) prüft:
   - Vollständigkeit (alle Pflichtfelder gefüllt)
   - Plausibilität (keine offensichtlichen Fehler)
   - Changelog (Änderungen nachvollziehbar)
3. Der Freigeber gibt frei oder fordert Nachbesserung an
4. Bei Freigabe:
   - Status wird auf "FREIGEGEBEN" gesetzt
   - Zeitstempel und Freigeber werden dokumentiert
   - Die Revision ist nicht mehr editierbar (immutable)
5. Bei Nachbesserung: zurück an den Sicherheitsbeauftragten mit Kommentar

### D. PDF-Export (gelenktes Dokument)

1. Der Sicherheitsbeauftragte exportiert eine freigegebene Revision als PDF
2. Das PDF enthält:
   - Kopfzeile: Mandant, Standort, Revisionsnummer, Datum
   - Fußzeile: "Erstellt von [Name], Freigegeben von [Name], Seite X/Y"
   - Wasserzeichen bei Entwürfen: "ENTWURF — NICHT FREIGEGEBEN"
   - Vollständige Produktliste mit allen regulatorischen Daten
   - GHS-Piktogramme als Grafiken
   - Revisions-Historie (Übersicht aller Versionen)
3. Das PDF wird als `Document` im Dokumenten-Modul abgelegt

### E. Archivierung und Aufbewahrung

1. Freigegebene Revisionen werden dauerhaft archiviert
2. Aufbewahrungsfrist: mindestens 40 Jahre (GefStoffV §14 Abs. 3)
3. Alte Revisionen bleiben lesbar, aber nicht editierbar
4. Bei Mandanten-Deaktivierung: Export aller Revisionen als ZIP

## Fehlerfälle

- Falls der Sicherheitsbeauftragte eine Revision ohne Änderungen erstellt: Hinweis "Keine Änderungen seit letzter Revision"
- Falls der Freigeber auch der Ersteller ist: Warnung (Vier-Augen-Prinzip empfohlen, aber nicht erzwungen)
- Falls die PDF-Generierung fehlschlägt: Fehler loggen, HTML-Fallback anbieten
- Falls eine freigegebene Revision nachträglich geändert werden soll: Nur durch neue Revision möglich

## Akzeptanzkriterien

GIVEN ein bestehendes Kataster mit 145 Produkten
WHEN der Sicherheitsbeauftragte "Neue Revision erstellen" klickt
THEN wird ein Snapshot des aktuellen Zustands erstellt
AND eine Revisionsnummer vergeben

GIVEN zwei Revisionen (Rev 2.0 und Rev 3.0)
WHEN der Sicherheitsbeauftragte den Diff anzeigt
THEN sieht er hinzugefügte, geänderte und entfernte Produkte

GIVEN eine zur Freigabe eingereichte Revision
WHEN der Freigeber sie freigibt
THEN wird die Revision als immutable markiert
AND der PDF-Export zeigt "Freigegeben von [Name]"

GIVEN eine freigegebene Revision
WHEN jemand versucht, sie zu bearbeiten
THEN wird dies vom System verhindert
AND ein Hinweis "Freigegebene Revisionen können nicht bearbeitet werden" angezeigt

## Referenzen

- **Regulatorisch**: GefStoffV §6 (Gefahrstoffverzeichnis), GefStoffV §14 Abs. 3 (40 Jahre Aufbewahrung), ISO 45001:2018 Abschnitt 7.5 (Dokumentenlenkung)
- **Verknüpfte UCs**: UC-004 (Kataster), UC-005 (SDS Update), UC-008 (GefBu)
