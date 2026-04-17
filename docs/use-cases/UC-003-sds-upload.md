# UC-003: Sicherheitsdatenblatt hochladen

**Status:** Draft
**Modul:** Gefahrstoffe (SDS Library)
**Erstellt:** 2026-04-17

## Akteur

Der SDS-Prüfer (Rolle: Editor oder Admin)

## Ziel

Der SDS-Prüfer möchte ein Sicherheitsdatenblatt (SDS) als PDF hochladen, damit das System die Stoffidentifikation durchführt und die relevanten Gefahrstoffdaten extrahiert.

## Vorbedingung

- Der Benutzer ist eingeloggt und hat die Rolle Editor oder Admin
- Das Gefahrstoff-Modul ist für den Mandanten freigeschaltet
- Die PDF-Datei liegt als gültiges SDS nach GHS/CLP vor

## Scope

Nur der Upload und die initiale Verarbeitung. Nicht Teil: manuelle Nachbearbeitung, Freigabe-Workflow, Zuordnung zu Ex-Konzepten.

## Schritte

1. Der SDS-Prüfer navigiert zur SDS-Bibliothek
2. Der SDS-Prüfer klickt auf "SDS hochladen"
3. Das System zeigt den Upload-Dialog mit Drag-and-Drop-Bereich
4. Der SDS-Prüfer wählt eine PDF-Datei aus oder zieht sie in den Bereich
5. Das System startet die Verarbeitung und zeigt einen Fortschrittsbalken
6. Das System identifiziert den Stoff (CAS-Nummer, Produktname, Hersteller)
7. Das System zeigt die extrahierten Daten zur Überprüfung an

## Fehlerfälle

- Falls die Datei kein PDF ist, erscheint die Meldung "Nur PDF-Dateien werden akzeptiert"
- Falls die Datei größer als 50 MB ist, erscheint ein Hinweis auf die Maximalgröße
- Falls die Stoffidentifikation fehlschlägt, wird der Upload mit Status "Manuell prüfen" gespeichert

## Akzeptanzkriterien

GIVEN ein eingeloggter SDS-Prüfer
WHEN er ein gültiges SDS-PDF hochlädt
THEN wird der Stoff identifiziert und die Daten zur Überprüfung angezeigt

GIVEN ein eingeloggter SDS-Prüfer
WHEN er eine Nicht-PDF-Datei hochlädt
THEN wird der Upload abgelehnt mit einer verständlichen Fehlermeldung

GIVEN ein eingeloggter SDS-Prüfer
WHEN die automatische Stoffidentifikation fehlschlägt
THEN wird das SDS mit Status "Manuell prüfen" gespeichert
