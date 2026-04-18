# UC-006: Periodische SDS-Prüfung (alle 2 Jahre)

**Status:** Draft
**Modul:** Gefahrstoffe (SDS Library / Compliance)
**Erstellt:** 2026-04-17

## Akteur

Der SDS-Prüfer (Rolle: Editor oder Admin)

## Ziel

Der SDS-Prüfer möchte sicherstellen, dass alle Sicherheitsdatenblätter turnusmäßig (mindestens alle 2 Jahre) auf Aktualität geprüft werden. Das System überwacht die Prüffristen, erinnert rechtzeitig und dokumentiert die Prüfung lückenlos.

## Vorbedingung

- Der Benutzer ist eingeloggt und hat die Rolle Editor oder Admin
- Produkte mit verknüpftem SDS existieren im Kataster
- `SubstanceUsage.last_reviewed` oder `GlobalSdsRevision.revision_date` ist gepflegt

## Scope

Fristüberwachung, Erinnerungen, Prüfprotokoll.
Nicht Teil: Inhaltliche Aktualisierung des SDS (→ UC-005), Ersterfassung (→ UC-003).

## Schritte

### A. Fristüberwachung (automatisch)

1. Das System prüft täglich (Celery-Beat) alle aktiven Produkte:
   - `last_reviewed` älter als 24 Monate → Status **FÄLLIG**
   - `last_reviewed` älter als 21 Monate → Status **BALD FÄLLIG** (Vorwarnung)
   - Kein `last_reviewed` → Status **NIE GEPRÜFT**
2. Das System aktualisiert den Compliance-Status pro Produkt/Standort

### B. Dashboard und Erinnerungen

1. Der SDS-Prüfer öffnet das Compliance-Dashboard
2. Das System zeigt:
   - **Ampel-Übersicht**: Grün (aktuell) / Gelb (bald fällig) / Rot (überfällig)
   - **Fällige SDS**: Sortiert nach Dringlichkeit
   - **Statistik**: % aktuell, % überfällig, Trend vs. Vormonat
3. Optional: E-Mail-Benachrichtigung bei neuen fälligen SDS (konfigurierbar)
4. Optional: Kalendar-Integration (iCal) mit Prüfterminen

### C. Prüfung durchführen

1. Der SDS-Prüfer wählt ein fälliges Produkt aus
2. Das System zeigt:
   - Aktuelles SDS mit Revisionsdatum
   - Hersteller-Kontakt
   - Letzte bekannte Änderungen
3. Der SDS-Prüfer prüft:
   - Ist das SDS noch aktuell? (Hersteller-Website, GESTIS, Anfrage)
   - Hat sich die Einstufung geändert?
   - Sind neue Grenzwerte veröffentlicht?
4. Ergebnis der Prüfung:
   - **Aktuell**: SDS ist auf dem neuesten Stand → `last_reviewed` aktualisieren
   - **Update erforderlich**: Neues SDS einholen → weiter mit UC-005
   - **Produkt nicht mehr im Einsatz**: Status auf PHASED_OUT setzen

### D. Prüfprotokoll

1. Das System dokumentiert jede Prüfung:
   - Prüfdatum, Prüfer, Ergebnis
   - Kommentar des Prüfers
   - Nächster Prüftermin (automatisch: +24 Monate)
2. Das Prüfprotokoll ist revisionssicher (Audit-Trail)

## Fehlerfälle

- Falls ein Produkt kein SDS verknüpft hat: Warnung "Kein SDS vorhanden — Beschaffung einleiten"
- Falls der Prüfer das Prüfdatum ohne Prüfung setzt: System erfordert mindestens einen Kommentar
- Falls >50 SDS gleichzeitig fällig werden: Priorisierung nach Gefährdungspotenzial (WGK, H-Sätze)
- Falls ein Hersteller nicht mehr existiert (Party inaktiv): Warnung + Alternativlieferanten vorschlagen

## Akzeptanzkriterien

GIVEN ein Produkt mit `last_reviewed` vor 25 Monaten
WHEN das System die tägliche Fristprüfung ausführt
THEN wird das Produkt als "FÄLLIG" markiert
AND erscheint im Compliance-Dashboard unter "Überfällig" (rot)

GIVEN ein fälliges Produkt
WHEN der SDS-Prüfer die Prüfung als "Aktuell" bestätigt
THEN wird `last_reviewed` auf heute gesetzt
AND das Prüfprotokoll wird geschrieben

GIVEN konfigurierte E-Mail-Benachrichtigungen
WHEN ein SDS den Status "FÄLLIG" erreicht
THEN erhält der zuständige Prüfer eine E-Mail mit Produkt, Standort und Frist

GIVEN das Compliance-Dashboard
WHEN der SDS-Prüfer es öffnet
THEN sieht er die Ampel-Übersicht über alle Mandanten-Standorte
AND kann nach Standort, Dringlichkeit und Abteilung filtern

## Referenzen

- **Regulatorisch**: REACH Art. 31 Abs. 9 (Aktualisierungspflicht), GefStoffV §6 Abs. 11
- **Frist**: Mindestens alle 2 Jahre oder bei Änderung der Einstufung
- **Verknüpfte UCs**: UC-003 (SDS Upload), UC-005 (SDS Aktualisieren), UC-004 (Kataster)
