# UC-005: Sicherheitsdatenblätter aktualisieren

**Status:** Draft
**Modul:** Gefahrstoffe (SDS Library)
**Erstellt:** 2026-04-17

## Akteur

Der SDS-Prüfer (Rolle: Editor oder Admin)

## Ziel

Der SDS-Prüfer möchte Sicherheitsdatenblätter (SDS) seiner Gefahrstoffe auf dem aktuellen Stand halten. Das System unterstützt den kompletten Aktualisierungszyklus: Einholen neuer Versionen (PDF, Web, Mail), Sichten, Prüfen und Ableiten von Konsequenzen aus Änderungen.

## Vorbedingung

- Der Benutzer ist eingeloggt und hat die Rolle Editor oder Admin
- Mindestens ein Produkt mit verknüpftem SDS existiert im Kataster
- Das SDS-Modul ist für den Mandanten freigeschaltet

## Scope

Kompletter SDS-Aktualisierungszyklus: Einholen, Aktualisieren, Sichten, Prüfen, Konsequenzen ableiten.
Nicht Teil: Initiale SDS-Erfassung (→ UC-003), Gefahrstoffkataster-Pflege (→ UC-004).

## Schritte

### A. SDS einholen (Multi-Kanal)

1. Das System identifiziert Produkte mit veraltetem oder fehlendem SDS
2. Der SDS-Prüfer wählt Produkte zur Aktualisierung aus
3. Das System bietet mehrere Beschaffungswege:
   - **PDF-Upload**: Manueller Upload einer neuen SDS-Version
   - **Web-Recherche**: System schlägt Hersteller-Webseiten vor (basierend auf `Party.website`)
   - **Mail-Anforderung**: System generiert eine vorformulierte Anfrage an den Hersteller (Template mit Produktname, CAS, aktueller SDS-Version)
   - **Automatischer Abgleich**: System prüft bekannte SDS-Portale (z.B. GESTIS, Hersteller-APIs) auf neuere Versionen

### B. SDS aktualisieren

1. Der SDS-Prüfer lädt das neue SDS als PDF hoch
2. Das System extrahiert die Daten (→ UC-003 Pipeline)
3. Das System erstellt eine neue `GlobalSdsRevision` (Versionierung)
4. Das System zeigt einen **Diff** zwischen alter und neuer SDS-Version:
   - Geänderte H-/P-Sätze (rot hervorgehoben)
   - Neue/entfallene Inhaltsstoffe
   - Geänderte Grenzwerte (AGW, DNEL)
   - Geändertes Signalwort oder WGK
5. Die alte SDS-Version bleibt als Revisionshistorie erhalten

### C. SDS sichten und prüfen

1. Der SDS-Prüfer prüft die extrahierten Änderungen
2. Er bestätigt oder korrigiert die extrahierten Daten
3. Er bewertet die Relevanz der Änderungen:
   - **Keine Auswirkung**: Kosmetische Änderungen (Layout, Formatierung)
   - **Informativ**: Neue Formulierungen, gleiche Gefährdung
   - **Handlungsbedarf**: Neue Gefährdungen, geänderte Grenzwerte, neue H-Sätze
4. Das System setzt `Product.sds_revision` auf die neue Version

### D. Konsequenzen ableiten

1. Bei Handlungsbedarf zeigt das System automatisch betroffene Bereiche:
   - **Standorte/Abteilungen**: Alle `SubstanceUsage`-Einträge des Produkts
   - **Betriebsanweisungen**: Müssen aktualisiert werden (→ UC-008)
   - **Gefährdungsbeurteilungen**: Müssen überprüft werden (→ UC-008)
   - **Lagerung**: Lagerklasse oder Zusammenlagerung betroffen?
   - **Schulungen**: Betroffene Mitarbeiter müssen informiert werden (→ UC-009)
2. Das System erstellt automatisch Aufgaben (Tasks) für die betroffenen Bereiche
3. Der SDS-Prüfer kann Aufgaben zuweisen und Fristen setzen

## Fehlerfälle

- Falls das neue SDS eine geringere Revisionsnummer hat als das aktuelle: Warnung "Ältere Version als aktuell gespeichert"
- Falls die CAS-Nummern zwischen alter und neuer Version abweichen: "Produkt-Identität konnte nicht bestätigt werden — bitte manuell prüfen"
- Falls die Extraktion fehlschlägt: SDS wird mit Status "Manuell prüfen" gespeichert, Diff nicht möglich
- Falls die Hersteller-Mail unzustellbar ist: Warnung + alternativer Kontakt vorschlagen
- Falls ein SDS-Portal nicht erreichbar ist: Timeout-Warnung, manuelle Beschaffung vorschlagen

## Akzeptanzkriterien

GIVEN ein Produkt mit verknüpftem SDS (Version 3.0)
WHEN der SDS-Prüfer eine neue PDF (Version 4.0) hochlädt
THEN wird eine neue GlobalSdsRevision angelegt
AND der Diff zeigt die Unterschiede zur Vorgängerversion
AND die alte Version bleibt in der Revisionshistorie erhalten

GIVEN ein SDS-Diff mit neuen H-Sätzen (Handlungsbedarf)
WHEN der SDS-Prüfer die Änderung bestätigt
THEN erstellt das System automatisch Aufgaben für betroffene Betriebsanweisungen und Gefährdungsbeurteilungen

GIVEN ein Produkt ohne aktualisierten Kontakt
WHEN der SDS-Prüfer "Mail-Anforderung" wählt
THEN generiert das System eine vorformulierte Anfrage mit Produktname, CAS und aktueller SDS-Version

GIVEN ein SDS-Diff ohne sicherheitsrelevante Änderungen
WHEN der SDS-Prüfer "Keine Auswirkung" bestätigt
THEN werden keine Folge-Aufgaben erstellt
AND das Prüfdatum wird aktualisiert

## Referenzen

- **Regulatorisch**: REACH Anhang II (SDS-Aktualisierung), GefStoffV §6 Abs. 11 (Aktualitätspflicht)
- **Verknüpfte UCs**: UC-003 (SDS Upload), UC-004 (Kataster), UC-008 (GefBu), UC-009 (Schulungen)
