# UC-002: Ex-Schutzkonzept erstellen

**Status:** Draft
**Modul:** Explosionsschutz
**Erstellt:** 2026-04-17

## Akteur

Der Sicherheitsingenieur (Rolle: Editor oder Admin)

## Ziel

Der Sicherheitsingenieur möchte ein Explosionsschutzkonzept für einen Betriebsbereich erstellen, damit die Zoneneinteilung, Schutzmaßnahmen und das Ex-Dokument dokumentiert werden können.

## Vorbedingung

- Der Benutzer ist eingeloggt und hat die Rolle Editor oder Admin
- Mindestens ein Betriebsbereich existiert im Mandanten
- Ein Tenant ist dem Benutzer zugeordnet

## Scope

Nur das Erstellen eines neuen Ex-Konzepts. Nicht Teil: Zonen hinzufügen, Maßnahmen definieren, Dokument exportieren.

## Schritte

1. Der Sicherheitsingenieur navigiert zum gewünschten Betriebsbereich
2. Der Sicherheitsingenieur klickt auf "Neues Ex-Konzept"
3. Das System zeigt das Formular mit Bereich-Dropdown und Gefahrstoff-Feld
4. Der Sicherheitsingenieur wählt den Bereich und trägt den relevanten Gefahrstoff ein
5. Der Sicherheitsingenieur klickt auf "Speichern"
6. Das System erstellt das Konzept mit Status "Entwurf"
7. Das System leitet zur Konzeptdetailseite mit Tabs (Zonen, Maßnahmen, Dokumente, Vorlagen) weiter

## Fehlerfälle

- Falls kein Bereich existiert, ist das Dropdown leer und der Speichern-Button deaktiviert
- Falls kein Tenant zugeordnet ist, erscheint die Meldung "Mandant konnte nicht ermittelt werden"
- Falls Pflichtfelder fehlen, zeigt das Formular Fehlermeldungen inline an

## Akzeptanzkriterien

GIVEN ein eingeloggter Sicherheitsingenieur mit mindestens einem Bereich
WHEN er ein Ex-Konzept mit gültigem Bereich und Gefahrstoff erstellt
THEN wird das Konzept mit Status "Entwurf" gespeichert und die Detailseite angezeigt

GIVEN ein eingeloggter Sicherheitsingenieur
WHEN er das Ex-Konzept-Formular ohne Bereich absendet
THEN wird ein Validierungsfehler angezeigt und kein Konzept erstellt
