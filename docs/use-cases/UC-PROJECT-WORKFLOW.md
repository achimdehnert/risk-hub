# Use Cases: Projektbasiertes Arbeiten in Schutztat

> Status: DRAFT — Grundlage für ADR zur Projekt-Umstellung
> Erstellt: 2026-03-27

## 1. Kontext

Schutztat (risk-hub) besteht aus mehreren Fachmodulen, die aktuell unabhängig
voneinander arbeiten. In der Praxis bearbeitet ein Sicherheitsingenieur jedoch
immer ein **konkretes Projekt** (Kundenauftrag, Standortbewertung, Anlage),
das Elemente aus mehreren Modulen kombiniert.

### Beteiligte Module

| Modul | App | Beitrag zum Projekt |
|-------|-----|---------------------|
| Explosionsschutz | `explosionsschutz` | Bereiche, Zonen, Betriebsmittel, Ex-Konzepte, Ex-Dokument |
| Gefahrstoffe | `substances` + `global_sds` | Stoffidentifikation, SDS-Daten, H/P-Sätze, Ex-Relevanz |
| GBU | `gbu` | Gefährdungsbeurteilungen pro Tätigkeit/Arbeitsplatz |
| Brandschutz | `brandschutz` | Feuerlöscher, Fluchtwege, Brandschutznachweis |
| Risikobewertung | `risk` | Gesamtrisikobewertung |
| Dokumente | `documents` | Dokumentenverwaltung, Archivierung |
| KI-Analyse | `ai_analysis` | LLM-gestützte Textgenerierung, Dokumentanalyse |

---

## 2. Aktoren

- **Sicherheitsingenieur** (Hauptakteur) — erstellt und bearbeitet Projekte
- **Prüfer/Gutachter** — reviewt und gibt Dokumente frei
- **Auftraggeber** (extern) — liefert Unterlagen, erhält Ergebnisse
- **KI-Assistent** (System) — analysiert Dokumente, generiert Textvorschläge

---

## 3. Use Cases

### UC-01: Projekt anlegen (KI-gestützte Initialisierung)

**Akteur:** Sicherheitsingenieur
**Vorbedingung:** User ist eingeloggt, Tenant + Site existieren
**Auslöser:** Neuer Kundenauftrag

**Ablauf:**
1. User klickt "Neues Projekt"
2. System zeigt Formular:
   - Name, Projektnummer, Auftraggeber, Standort (Site)
   - **Freitext-Feld: "Beschreiben Sie Ihr Projekt"**
     (z.B. "Lackieranlage Halle 3, Lösungsmittel, kein aktuelles Ex-Dokument")
3. **KI analysiert die Beschreibung** und empfiehlt Module:
   - ✅ Modul gebucht + empfohlen → vorausgewählt
   - ⚠️ Modul NICHT gebucht, aber empfohlen → Hinweis + Link "Modul buchen"
   - ☐ Modul gebucht, nicht empfohlen → abwählbar
4. KI begründet jede Empfehlung (z.B. "Lösungsmittel + offener Prozess →
   Explosionsschutz erforderlich")
5. User prüft Empfehlung und kann Module an-/abwählen
6. **Falls nicht-gebuchte Module empfohlen:**
   - User kann Modul über django-module-shop buchen (Redirect + Rückkehr)
   - Oder bewusst darauf verzichten (Entscheidung wird dokumentiert)
7. System erstellt Projekt mit gewählten Modulen, Status "Aktiv"
8. System zeigt Projekt-Dashboard mit aktivierten Modul-Kacheln

**Ergebnis:** Projekt existiert mit KI-empfohlener, user-bestätigter Modulauswahl

**KI-Empfehlung (Beispiel):**
```
Basierend auf Ihrer Beschreibung empfehle ich:

✅ Explosionsschutz      (gebucht)
   → Lösungsmittel + offener Lackierprozess = Ex-gefährdeter Bereich
✅ Gefahrstoffe/SDS      (gebucht)
   → Lösungsmittel erfordern SDS-Analyse und H/P-Sätze
✅ GBU                   (gebucht)
   → Tätigkeiten mit Gefahrstoffen → Gefährdungsbeurteilung pflicht
⚠️ Brandschutz           (NICHT gebucht)
   → Lackieranlage = erhöhte Brandgefahr, Brandschutznachweis empfohlen
   [Modul jetzt buchen →]
☐ Risikobewertung       (gebucht, für dieses Projekt optional)
```

**Varianten:**
- 1a. Projekt aus bestehendem Projekt klonen (z.B. jährliche Aktualisierung)
- 1b. User überspringt KI-Empfehlung und wählt Module manuell
- 1c. User hat keine Freitextbeschreibung → nur manuelle Modulauswahl

---

### UC-02: Projektunterlagen hochladen

**Akteur:** Sicherheitsingenieur
**Vorbedingung:** Projekt existiert (UC-01)
**Auslöser:** Unterlagen vom Auftraggeber erhalten

**Ablauf:**
1. User öffnet Projekt → Tab "Unterlagen"
2. User lädt Dateien hoch (PDF, DXF, DOCX) oder gibt URLs ein
3. System klassifiziert automatisch:
   - `sds` → Sicherheitsdatenblatt
   - `plan` → Grundriss/Anlagenplan
   - `gutachten` → Bestehendes Gutachten/Ex-Dokument
   - `regulation` → Regelwerk/Norm
   - `process_description` → Verfahrensbeschreibung
   - `link` → Internet-Referenz (TRGS, BG-Regeln, etc.)
   - `other` → Sonstiges
4. System extrahiert Text (OCR/Parsing) und erstellt KI-Zusammenfassung
5. User korrigiert ggf. Klassifizierung

**Ergebnis:** Alle Projektunterlagen zentral verfügbar mit durchsuchbarem Text

**KI-Aspekt:**
- Automatische Dokumentklassifizierung
- Extraktion von Stoffnamen, Bereichen, Anlagenteilen aus dem Text
- Zusammenfassung pro Dokument (3-5 Sätze)

---

### UC-03: Gefahrstoffe aus Unterlagen identifizieren

**Akteur:** KI-Assistent → Sicherheitsingenieur (Review)
**Vorbedingung:** Projektunterlagen hochgeladen (UC-02)
**Auslöser:** Automatisch nach Upload oder manuell

**Ablauf:**
1. KI analysiert hochgeladene Dokumente auf Stoffnennungen
2. KI gleicht mit SDS-Bibliothek (`global_sds`) ab
3. System zeigt Vorschlagsliste: "Folgende Stoffe wurden identifiziert"
   - Stoff, Fundstelle (Dokument + Seite), SDS vorhanden (ja/nein)
4. User bestätigt/verwirft/ergänzt Vorschläge
5. Bestätigte Stoffe werden dem Projekt zugeordnet
6. Fehlende SDS können aus Bibliothek verknüpft oder hochgeladen werden

**Ergebnis:** Projekt hat eine vollständige Stoffliste mit SDS-Verknüpfung

---

### UC-04: Bereiche und Betriebsmittel aus Unterlagen ableiten

**Akteur:** KI-Assistent → Sicherheitsingenieur (Review)
**Vorbedingung:** Projektunterlagen hochgeladen (UC-02)
**Auslöser:** Automatisch oder manuell

**Ablauf:**
1. KI analysiert Anlagenbeschreibungen, Grundrisse, Verfahrensbeschreibungen
2. KI schlägt Betriebsbereiche vor (Name, Beschreibung, Quelle)
3. KI schlägt Betriebsmittel vor (Typ, Standort, Ex-Relevanz)
4. User reviewt Vorschläge in einer Übersicht
5. User bestätigt → System erstellt Area/Equipment-Einträge im Projekt
6. User kann manuell ergänzen/ändern

**Ergebnis:** Projektbereiche und Betriebsmittel angelegt, basierend auf Quelldokumenten

**Wichtig:** Zonen werden NICHT automatisch festgelegt — nur als Empfehlung mit
Begründung vorgeschlagen (→ UC-05)

---

### UC-05: Zoneneinteilung erarbeiten

**Akteur:** Sicherheitsingenieur (KI unterstützt)
**Vorbedingung:** Bereiche und Stoffe identifiziert (UC-03 + UC-04)
**Auslöser:** Manuell

**Ablauf:**
1. User wählt Bereich aus Projekt
2. System zeigt: Stoffe im Bereich, Betriebsmittel, verfügbare Dokumente
3. User kann KI-Empfehlung anfordern:
   - KI analysiert Stoff-Ex-Daten + Verfahrensbeschreibung
   - KI schlägt Zonentyp + Ausdehnung + Begründung vor
   - KI referenziert TRGS 720ff / EN 60079-10
4. User prüft, passt an und bestätigt Zoneneinteilung
5. System speichert Zone mit Begründung und Quellenangaben

**Ergebnis:** Zoneneinteilung mit nachvollziehbarer Herleitung

---

### UC-06: GBU für Projekttätigkeiten erstellen

**Akteur:** Sicherheitsingenieur
**Vorbedingung:** Projekt mit identifizierten Stoffen und Bereichen
**Auslöser:** Manuell

**Ablauf:**
1. User erstellt GBU im Kontext des Projekts
2. System bietet Projekt-Stoffe und -Bereiche als Auswahl an
3. GBU-Wizard nutzt Projektkontext (Stoffe, SDS-Daten, Bereiche)
4. KI kann Gefährdungen auf Basis der Projektunterlagen vorschlagen

**Ergebnis:** GBU ist mit Projekt verknüpft und nutzt dessen Daten

---

### UC-07: Brandschutz im Projektkontext

**Akteur:** Sicherheitsingenieur
**Vorbedingung:** Projekt mit Bereichen
**Auslöser:** Manuell

**Ablauf:**
1. User öffnet Brandschutz im Projekt-Kontext
2. System zeigt Bereiche des Projekts
3. User erfasst Feuerlöscher, Fluchtwege je Bereich
4. Optional: DXF-Analyse für Fluchtweg-Bewertung

**Ergebnis:** Brandschutz-Daten projektbezogen erfasst

---

### UC-08: Explosionsschutzdokument generieren (Kernstück)

**Akteur:** Sicherheitsingenieur
**Vorbedingung:** Projekt hat Bereiche, Zonen, Stoffe, Maßnahmen
**Auslöser:** Manuell

**Ablauf:**
1. User öffnet "Ex-Schutzdokument erstellen" im Projekt
2. System erstellt Dokument mit Standard-Abschnitten:
   - 1. Allgemeines (Zweck, Geltungsbereich)
   - 2. Betriebsbeschreibung
   - 3. Verwendete Gefahrstoffe
   - 4. Zoneneinteilung
   - 5. Zündquellenanalyse
   - 6. Schutzmaßnahmen (primär, sekundär, tertiär)
   - 7. Betriebsmittel und ATEX-Eignung
   - 8. Organisatorische Maßnahmen
   - 9. Prüfungen und Inspektionen
   - 10. Anlagen (Zonenplan, Geräteverzeichnis)
3. **Pro Abschnitt:**
   a. User sieht aktuellen Inhalt (leer oder vorausgefüllt)
   b. User kann "KI generieren" klicken
   c. Dialog: Quellen auswählen
      - ☑ Projektunterlagen (Checkbox-Liste)
      - ☑ Internet-Links (TRGS, Normen)
      - ☑ Projektdaten (Zonen, Stoffe, Maßnahmen aus DB)
   d. KI generiert Text auf Basis der ausgewählten Quellen
   e. User bearbeitet, ergänzt, korrigiert
   f. Quellenangaben werden am Abschnitt gespeichert
4. User kann Abschnitte einzeln oder komplett bearbeiten
5. Status-Workflow: Entwurf → In Prüfung → Freigegeben

**Ergebnis:** Vollständiges Ex-Schutzdokument mit nachvollziehbaren Quellen

**UX-Detail: Quellauswahl-Dialog**
```
┌─────────────────────────────────────────────────────┐
│  KI-Generierung: "4. Zoneneinteilung"               │
│                                                     │
│  Quellen auswählen:                                 │
│                                                     │
│  📁 Projektunterlagen                               │
│  ☑ Bestehendes_ExDok_2019.pdf (S. 12-18)          │
│  ☑ Anlagenbeschreibung.pdf                         │
│  ☐ SDB_Ethanol.pdf                                 │
│  ☑ Verfahrensbeschreibung_Lackierung.pdf           │
│                                                     │
│  🌐 Internet-Referenzen                             │
│  ☑ TRGS 720 (baua.de)                             │
│  ☐ EN 60079-10-1 (beuth.de)                       │
│  [+ Link hinzufügen]                               │
│                                                     │
│  📊 Projektdaten (automatisch einbezogen)           │
│  ✓ 3 Zonen definiert (Zone 1, Zone 2, Nicht-Ex)   │
│  ✓ 2 Stoffe: Ethanol, Toluol                      │
│  ✓ 5 Betriebsmittel                               │
│                                                     │
│  [🤖 Generieren]  [Abbrechen]                      │
└─────────────────────────────────────────────────────┘
```

---

### UC-09: Dokument exportieren (PDF)

**Akteur:** Sicherheitsingenieur
**Vorbedingung:** Ex-Schutzdokument fertiggestellt (UC-08)
**Auslöser:** Manuell

**Ablauf:**
1. User klickt "PDF exportieren"
2. System generiert PDF mit:
   - Deckblatt (Projekt, Auftraggeber, Datum, Version)
   - Alle Abschnitte
   - Quellenverzeichnis
   - Anlagen (Zonenplan, Geräteverzeichnis, ggf. DXF-Auszüge)
3. PDF wird gespeichert und zum Download angeboten

**Ergebnis:** Druckfertiges Ex-Schutzdokument nach §6 GefStoffV

---

### UC-10: Projekt aktualisieren (Revision)

**Akteur:** Sicherheitsingenieur
**Vorbedingung:** Bestehendes Projekt
**Auslöser:** Änderung an Anlage, neue Stoffe, jährliche Prüfung

**Ablauf:**
1. User klickt "Neue Revision erstellen"
2. System kopiert aktuelles Projekt mit allen Daten
3. User ändert nur die betroffenen Teile
4. KI kann Änderungen gegenüber Vorversion hervorheben
5. Neues Dokument mit Revisionsnummer

**Ergebnis:** Aktualisiertes Projekt mit Versionshistorie

---

## 4. Modulübergreifende Aspekte

### 4.1 Projekt als Container

Das **Projekt** ist der zentrale Knotenpunkt:

```
                    ┌─────────────┐
                    │   Projekt   │
                    │  (Auftrag)  │
                    └──────┬──────┘
                           │
          ┌────────────────┼────────────────┐
          │                │                │
    ┌─────┴─────┐   ┌─────┴─────┐   ┌─────┴─────┐
    │ Unterlagen │   │  Bereiche │   │  Output-  │
    │  (Input)   │   │  + Daten  │   │ Dokumente │
    └─────┬─────┘   └─────┬─────┘   └─────┬─────┘
          │                │                │
    ┌─────┴─────┐   ┌─────┴──────────┐   ┌┴──────────┐
    │ PDFs      │   │ Stoffe         │   │ Ex-Dok    │
    │ DXFs      │   │ Bereiche       │   │ GBU       │
    │ Links     │   │ Zonen          │   │ Brandschutz│
    │ Gutachten │   │ Betriebsmittel │   │ Risiko-   │
    │ SDS       │   │ Maßnahmen      │   │ bewertung │
    └───────────┘   │ GBU-Daten      │   └───────────┘
                    │ Brandschutz    │
                    └────────────────┘
```

### 4.2 Wo lebt das Projekt-Model?

Optionen:
- **A) Neue App `projects`** — eigenständig, clean separation
- **B) In `common`** — da modulübergreifend
- **C) In `tenancy`** — nah am Standort/Site-Konzept

**Empfehlung:** Option A — `projects` App, da es ein eigenständiges Fachkonzept ist

### 4.3 Beziehungen zu bestehenden Models

| Bestehend | Änderung |
|-----------|----------|
| `Area` | + `project = FK(Project, null=True)` |
| `ExplosionConcept` | + `project = FK(Project, null=True)` |
| `gbu.HazardAssessment` | + `project = FK(Project, null=True)` |
| `risk.Assessment` | + `project = FK(Project, null=True)` |
| `brandschutz.*` | + `project = FK(Project, null=True)` |
| `ExDocInstance` | Bleibt, wird zum "Abschnittsdokument" im Projekt |

Alle FKs sind `null=True` für Rückwärtskompatibilität (bestehende Daten ohne Projekt).

---

## 5. Priorisierung

| Prio | Use Case | Begründung |
|------|----------|-----------|
| 🔴 P1 | UC-01 Projekt anlegen | Fundament |
| 🔴 P1 | UC-02 Unterlagen hochladen | Datenbasis |
| 🔴 P1 | UC-08 Ex-Dokument mit KI-Abschnitten | Kernmehrwert |
| 🟡 P2 | UC-03 Stoffe identifizieren | KI-Automatisierung |
| 🟡 P2 | UC-04 Bereiche ableiten | KI-Automatisierung |
| 🟡 P2 | UC-05 Zoneneinteilung | Fachkern Ex-Schutz |
| 🟢 P3 | UC-06 GBU Integration | Modulverknüpfung |
| 🟢 P3 | UC-07 Brandschutz Integration | Modulverknüpfung |
| 🟢 P3 | UC-09 PDF Export | Output |
| 🟢 P3 | UC-10 Revisionen | Lifecycle |

---

## 6. Entschiedene Designfragen

### 6.1 Projekt-Dashboard als Startseite → JA

Das Projekt-Dashboard wird zur neuen Startseite. Die **verfügbaren Module**
ergeben sich aus den **gebuchten Modulen des Tenants** (django-module-shop).
Der User wählt beim Projekterstellen, welche seiner gebuchten Module er
in diesem Projekt nutzen möchte.

```python
# Verfügbare Module = gebuchte Module des Tenants (ModuleSubscription)
# Projekt-Module = Teilmenge davon, vom User gewählt
enabled_modules = ["explosionsschutz", "gbu"]  # ⊆ tenant.subscribed_modules
```

**Konsequenz:** Die Modulauswahl im Projekt ist nach oben durch die
Tenant-Subscription begrenzt. Kein Modul kann aktiviert werden, das
nicht gebucht ist.

### 6.2 Projekte mit Teilaspekten → JA

Projekte können nur einzelne Module aktivieren (z.B. reine GBU, nur Brandschutz).
Deshalb lebt das `Project`-Model in einer eigenen `projects`-App — nicht in
`explosionsschutz`.

### 6.3 Daten-Lifecycle: Archivierung bei Projektabschluss

Beim Beenden eines Projekts entscheidet der User, welche Dokumente er
**archivieren** möchte. Archivierte Dokumente stehen weiterhin für andere
Projekte zur Verfügung (z.B. SDS, Gutachten, Normen).

**Ablauf:**
1. User klickt "Projekt abschließen"
2. System zeigt Liste aller Projektdokumente
3. User wählt: "Archivieren" (→ tenant-weit verfügbar) oder "Nur in Projekt"
4. Projekt-Status → "Abgeschlossen" (read-only)
5. Archivierte Dokumente erscheinen in der globalen Dokumentenbibliothek

```python
class ProjectDocument(models.Model):
    project = FK(Project)
    is_archived = BooleanField(default=False)  # True → tenant-weit sichtbar
    archived_at = DateTimeField(null=True)
```

**Bestehende Daten:** Kein automatisches Umhängen in Legacy-Projekte nötig.
GBU und SDS sind bereits architektonisch für Archivierung angedacht.

### 6.4 Internet-Links → Snapshot + Live-Check (Hybrid)

**Problem:** Nachvollziehbarkeit ist juristisch relevant bei Ex-Schutzdokumenten.
Live-Abruf hat bessere Aktualität, aber der Gutachter muss wissen, welche
Version der Quelle verwendet wurde.

**Lösung: Snapshot + Live-Check**

| Zeitpunkt | Verhalten |
|-----------|-----------|
| Beim Verknüpfen | URL + Inhalt als Snapshot archivieren (HTML→Text, Datum, SHA256) |
| Im Dokument | Referenz zeigt: URL + Abrufdatum + Titel zum Zeitpunkt des Snapshots |
| Aktualisierung | Button "Quelle aktualisieren" → neuer Snapshot, Diff zum alten anzeigen |
| Nachvollziehbarkeit | Jeder Snapshot hat Zeitstempel — Gutachter sieht exakt verwendete Version |

```
Quelle: TRGS 720 (BAuA)
URL: https://www.baua.de/DE/Angebote/Regelwerk/TRGS/TRGS-720.html
Abgerufen: 2026-03-15
Status: ✅ Aktuell (letzter Check: 2026-03-27)
[🔄 Aktualisieren]  [📄 Snapshot anzeigen]
```

**Model-Entwurf:**

```python
class ProjectSource(models.Model):
    """Externe Quelle mit Snapshot für Nachvollziehbarkeit."""
    project = FK(ExProject)
    source_type = CharField()        # "document", "url", "regulation"
    url = URLField(blank=True)
    title = CharField()

    # Snapshot
    snapshot_text = TextField()       # Archivierter Inhalt
    snapshot_date = DateTimeField()   # Wann abgerufen
    snapshot_hash = CharField()       # SHA256 zum Änderungsvergleich

    # Aktualisierung
    last_checked = DateTimeField(null=True)
    has_changed = BooleanField(default=False)
```

**Vorteile:**
- Juristische Nachvollziehbarkeit (Snapshot + Datum)
- KI nutzt Snapshot-Text als Kontext (stabil, nicht live)
- Änderungserkennung: "TRGS 720 wurde seit letztem Abruf aktualisiert"

### 6.5 Quellenzuordnung → Seite/Absatz (granular)

Quellenzuordnung pro Abschnitt im Ex-Dokument auf Seiten-/Absatzebene.

```python
class SectionSourceReference(models.Model):
    """Quellenzuordnung pro Abschnitt im Ex-Dokument."""
    section = FK(DocumentSection)
    source = FK(ProjectSource)       # oder ProjectDocument
    page_from = IntegerField(null=True)
    page_to = IntegerField(null=True)
    paragraph = TextField(blank=True) # Relevanter Textauszug
    relevance_note = TextField()      # Warum diese Quelle hier
```

**Effekt auf KI:** Statt ganzes Dokument als Kontext → nur relevanter Ausschnitt
(Seite X-Y). Bessere Ergebnisse, weniger Token-Kosten.

---

## 7. Offene Fragen (verbleibend)

1. Soll die Modulauswahl pro Projekt änderbar sein (nachträgliches Aktivieren)?
2. Brauchen wir Projekt-Templates (z.B. "Standard Ex-Schutz-Projekt" mit
   vordefinierten Modulen und Dokumentabschnitten)?
3. Wer darf Projekte anlegen — nur Manager oder alle Mitglieder?
4. Soll der Snapshot-Abruf für Links automatisch periodisch laufen (Celery-Task)?
