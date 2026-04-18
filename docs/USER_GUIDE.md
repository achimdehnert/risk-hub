# Schutztat — Benutzerhandbuch

> **Stand:** April 2026 | **Version:** risk-hub

## Was ist Schutztat?

Schutztat ist eine webbasierte SaaS-Plattform für betriebliches Sicherheitsmanagement.
Sie deckt die Bereiche Explosionsschutz, Gefahrstoffmanagement, Brandschutz,
Datenschutz, Risikobewertung und Compliance ab.

**Zugang:** https://schutztat.de (bzw. https://demo.schutztat.de für Testzwecke)

---

## Anmeldung

1. Öffnen Sie die URL Ihres Mandanten: `https://<mandant>.schutztat.de`
2. Geben Sie Benutzername und Passwort ein
3. Falls Sie mehreren Organisationen angehören, wählen Sie die gewünschte aus

Falls Ihr Unternehmen OIDC (Single Sign-On) nutzt, klicken Sie auf
**"Mit SSO anmelden"** und authentifizieren Sie sich über Ihren Identity Provider.

---

## Dashboard

Nach der Anmeldung sehen Sie das **Compliance-Dashboard** (`/dashboard/`).
Es zeigt eine Übersicht über:

- **Offene Maßnahmen** — Anzahl und Fälligkeit
- **Modul-Status** — Welche Module für Ihren Mandanten aktiv sind
- **Aktuelle Aktivitäten** — Letzte Änderungen im System
- **Compliance-Kennzahlen** — Grad der Erfüllung je Bereich

---

## Module im Überblick

### Explosionsschutz (`/ex/`)

Verwaltung von ATEX-Zonen, Ex-Schutz-Konzepten und Betriebsmitteln.

- **Bereiche** (`/ex/areas/`) — Betriebsbereiche mit Zonen anlegen
- **Konzepte** (`/ex/concepts/`) — Explosionsschutzdokumente erstellen
  - Zonen definieren (Zone 0, 1, 2, 20, 21, 22)
  - Zündquellenanalyse durchführen
  - Schutzmaßnahmen zuordnen
  - Konzept validieren und als PDF exportieren
- **Betriebsmittel** (`/ex/equipment/`) — Geräte mit Ex-Schutz-Kennzeichnung erfassen
- **Zonenvisualisierung** — Grafische Darstellung der Zoneneinteilung
- **Tools** (`/ex/tools/`) — Berechnungen und Hilfstools

### Gefahrstoffe (`/substances/`)

Stoffdatenbank und Sicherheitsdatenblatt-Management.

- **Gefahrstoffe** — Stoffe mit CAS-Nummer, H-Sätzen, Flammpunkt etc.
- **SDS-Upload** — Sicherheitsdatenblätter hochladen und versionieren
- **Substitutionsprüfung** — Weniger gefährliche Alternativen identifizieren

### SDS-Bibliothek (`/sds/`)

Globale, mandantenübergreifende Bibliothek von Sicherheitsdatenblättern.

- Datenblätter suchen und filtern
- Periodische Reviews (Aktualitätsprüfung)
- SDS-Update-Zyklen verwalten

### Gefahrstoffkataster (`/kataster/`)

Produkt- und Verwendungsregister für Gefahrstoffe.

- **Produkte** (`/kataster/produkte/`) — Handelsprodukte mit Gefahrstoffbezug
- **Verwendungen** (`/kataster/verwendungen/`) — Wo und wie Stoffe eingesetzt werden
- **Import** (`/kataster/import/`) — Bulk-Import aus Excel/CSV
- **Versionierung** — Änderungen am Kataster werden historisiert

### Risikobewertung (`/risk/`)

Gefährdungsbeurteilungen nach Bewertungsmatrix.

- Gefährdungen identifizieren
- Eintrittswahrscheinlichkeit und Schadensausmaß bewerten
- Maßnahmen zuordnen und nachverfolgen

### GBU (`/gbu/`)

Erweitertes Modul für Gefährdungsbeurteilungen.

- Strukturierte GBU nach Bereichen und Tätigkeiten
- Maßnahmen-Tracking mit Verantwortlichkeiten
- PDF-Export für Auditierung

### Brandschutz (`/brandschutz/`)

Brandschutzkonzepte und Flucht-/Rettungspläne.

- Brandschutzordnung verwalten
- Fluchtpläne zuordnen
- Brandschutzbegehungen dokumentieren

### Datenschutz — DSB (`/dsb/`)

Datenschutzbeauftragter-Modul nach DSGVO.

- Verarbeitungsverzeichnis (Art. 30 DSGVO)
- Technisch-organisatorische Maßnahmen (TOMs)
- Datenschutz-Folgenabschätzung (DSFA)

### Dokumente (`/documents/`)

Zentrales Dokumentenmanagement mit Versionierung.

- Dokumente hochladen und kategorisieren
- Versionskontrolle (jede Änderung wird versioniert)
- Freigabe-Workflows

### Projekte (`/projects/`)

Projektbasierte Organisation von Aufgaben und Dokumenten.

- Projekte anlegen und zuordnen
- Aufgaben und Meilensteine verwalten
- Projektübergreifende Übersicht

### Training / Unterweisungen (`/training/`)

Unterweisungsmanagement für Mitarbeitende.

- **Themen** — Unterweisungsthemen definieren (z.B. Brandschutz, Gefahrstoffe)
- **Sitzungen** — Unterweisungstermine planen und durchführen
- **Teilnahme** — Anwesenheit dokumentieren und nachweisen

### Audit-Log (`/audit/`)

Vollständige Protokollierung aller Änderungen im System.

- Wer hat wann was geändert?
- Filterbar nach Zeitraum, Benutzer, Modul
- Unveränderliches Audit-Trail für Compliance-Zwecke

### Benachrichtigungen (`/notifications/`)

Systemweite Hinweise und Alerts.

- Fällige Maßnahmen
- Review-Erinnerungen für SDS
- Freigabe-Anfragen

---

## Rollen und Berechtigungen

### Organisationsrollen

| Rolle | Beschreibung |
|-------|-------------|
| **Owner** | Voller Zugriff, Mandant-Einstellungen |
| **Admin** | Voller Zugriff, Benutzerverwaltung |
| **Member** | Standard-Zugriff auf freigegebene Module |
| **Viewer** | Nur-Lese-Zugriff |
| **External** | Eingeschränkter Zugriff (z.B. Auditoren) |

### Modulzugriff

Jedes Modul (Explosionsschutz, Risiko, GBU, DSB) kann separat
freigeschaltet werden. Die Aktivierung erfolgt über den Modul-Shop
(`/billing/modules/`) oder durch den Administrator.

Innerhalb eines Moduls können individuelle Rollen vergeben werden:
`viewer < member < manager < admin`

### Was passiert ohne Modulzugriff?

Wenn ein Benutzer ein nicht freigeschaltetes Modul aufruft, erhält er
eine **403-Fehlermeldung** mit Hinweis auf die Modulfreischaltung.

---

## API-Zugang

Schutztat bietet eine REST-API für externe Integrationen.

- **Dokumentation:** https://schutztat.de/api/v1/docs
- **Authentifizierung:** Bearer Token (im Profil generierbar)
- **Format:** JSON

Beispiel:

```bash
curl -H "Authorization: Bearer <token>" \
     https://demo.schutztat.de/api/v1/substances/
```

---

## Häufige Fragen

### Wie lege ich einen neuen Bereich an?

1. Navigieren Sie zu **Explosionsschutz → Bereiche**
2. Klicken Sie **"Bereich anlegen"**
3. Füllen Sie Name, Beschreibung und Zonenklasse aus
4. Speichern

### Wie lade ich ein Sicherheitsdatenblatt hoch?

1. Navigieren Sie zu **Gefahrstoffe → SDS-Upload**
2. Klicken Sie **"SDS hochladen"**
3. Wählen Sie die PDF-Datei aus
4. System extrahiert automatisch Metadaten (CAS-Nr., H-Sätze etc.)

### Wie exportiere ich ein Explosionsschutzdokument als PDF?

1. Öffnen Sie das Konzept unter **Explosionsschutz → Konzepte**
2. Klicken Sie auf **"Vorschau"** (`/ex/concepts/<id>/preview/`)
3. Nutzen Sie die Druckfunktion des Browsers oder den **PDF-Export**-Button

### Mein Modul zeigt "Zugriff verweigert" (403)?

- Prüfen Sie, ob das Modul für Ihren Mandanten aktiviert ist
- Kontaktieren Sie Ihren Administrator für die Freischaltung
- Modulstatus: **Profil → Meine Module**

### Wie funktioniert die Mandantentrennung?

Jeder Mandant hat eine eigene Subdomain (z.B. `firma.schutztat.de`).
Alle Daten sind strikt voneinander getrennt. Ein Zugriff auf Daten
anderer Mandanten ist technisch ausgeschlossen.

---

## Support

- **GitHub Issues:** https://github.com/achimdehnert/risk-hub/issues
- **E-Mail:** support@iil.gmbh
