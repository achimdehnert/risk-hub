# UC-001: Betriebsbereich anlegen

**Status:** Draft
**Modul:** Explosionsschutz
**Erstellt:** 2026-04-17

## Akteur

Der Sicherheitsingenieur (Rolle: Editor oder Admin)

## Ziel

Der Sicherheitsingenieur möchte einen neuen Betriebsbereich (z.B. Produktionshalle, Tanklager) im Explosionsschutz-Modul anlegen, damit anschließend Ex-Konzepte und Zonen für diesen Bereich erstellt werden können.

## Vorbedingung

- Der Benutzer ist eingeloggt und hat die Rolle Editor oder Admin
- Ein Tenant (Mandant) ist dem Benutzer zugeordnet
- Mindestens ein Standort (Site) existiert im Mandanten

## Scope

Nur das Anlegen eines Betriebsbereichs. Nicht Teil: Zoneneinteilung, Konzepterstellung, DXF-Upload.

## Schritte

1. Der Sicherheitsingenieur navigiert zu "Bereiche" im Explosionsschutz-Modul
2. Der Sicherheitsingenieur klickt auf "Neuer Bereich"
3. Das System zeigt das Formular mit den Feldern Bereichscode, Bereichsname und Beschreibung
4. Der Sicherheitsingenieur füllt die Pflichtfelder aus (Name ist Pflicht, Code ist optional)
5. Der Sicherheitsingenieur klickt auf "Speichern"
6. Das System validiert die Eingaben und speichert den Bereich
7. Das System leitet zur Bereichsdetailseite weiter

## Fehlerfälle

- Falls kein Tenant zugeordnet ist, erscheint die Meldung "Mandant konnte nicht ermittelt werden"
- Falls der Bereichscode bereits für den Standort existiert, erscheint ein Validierungsfehler
- Falls Pflichtfelder fehlen, zeigt das Formular die Fehlermeldungen inline an

## Akzeptanzkriterien

GIVEN ein eingeloggter Sicherheitsingenieur mit Editor-Rolle
WHEN er einen gültigen Bereichsnamen eingibt und speichert
THEN wird der Bereich in der Datenbank angelegt und die Detailseite angezeigt

GIVEN ein Benutzer ohne Tenant-Zuordnung
WHEN er versucht einen Bereich anzulegen
THEN wird eine Fehlermeldung angezeigt und kein Bereich erstellt
