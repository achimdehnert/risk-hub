# Schutztat · Produktkonzept Module 1–3
**März 2026 · Vertraulich**

---

## Überblick & Architekturkontext

Dieses Konzept beschreibt die drei priorisierten Produkt-Module für Schutztat. Alle Module bauen direkt auf der bestehenden Risk-Hub-Architektur (Django, HTMX, PostgreSQL/RLS, Celery, WeasyPrint) sowie den bereits implementierten Apps `substances`, `explosionsschutz` und `audit` auf.

| Modul | Regulatorische Basis | Kerndifferenziator | Tier / Preis |
|-------|---------------------|-------------------|-------------|
| **1 · Ex-Schutzdokument-Automation** | BetrSichV §6(9), ATEX 1999/92, TRGS 720–725 | Einzige SaaS-Lösung mit vollautom. Ex-Schutzdokument inkl. Zonenplänen & Zündquellenbewertung | Fortress · 499+ €/Monat/Standort |
| **2 · GBU-Automation aus SDS** | GefStoffV §14, TRGS 400/401/420, CLP-VO | H-Code → GBU → Betriebsanweisung in einem automatisierten Workflow, keine Medienbrüche | Shield · 199 €/Monat |
| **3 · Compliance-Dashboard & Prüfintervalle** | BetrSichV §§14–16, DGUV, ASR A2.2 | Zentrales Fristencockpit für alle Brandschutz- und Ex-Schutz-Anlagen mit Eskalations-Workflow | Guard · 79 €/Monat |

### Architektonische Abhängigkeiten

| App / Modul | Wird genutzt von | Datenfluss |
|-------------|-----------------|-----------|
| `substances` (✅ impl.) | Modul 1 + 2 | `SdsRevision.h_statements` → GBU-Engine, Ex-Konzept-Trigger |
| `explosionsschutz` (✅ impl.) | Modul 1 + 3 | `ExplosionConcept`, `Equipment`, `Inspection` → Automation-Layer |
| `audit` (✅ impl.) | Modul 1 + 2 + 3 | `AuditEvent` für alle Statusänderungen, Compliance-Protokoll |
| `actions` (✅ impl.) | Modul 2 + 3 | Automatische Maßnahmen bei fälligen Prüfungen und GBU-Lücken |
| `outbox` + Celery (✅ impl.) | Modul 1 + 2 + 3 | Async PDF-Generierung, Fristenprüfung, E-Mail-Alerts |
| `documents` (✅ impl.) | Modul 1 + 2 | WeasyPrint-PDFs in S3 ablegen, versioniert (`DocumentVersion`) |
| `notifications` (geplant) | Modul 3 | E-Mail/In-App-Alerts für Fristenüberschreitungen |

---

## MODUL 1: Ex-Schutzdokument-Automation (ATEX / BetrSichV)

### 1.1 Ausgangssituation & Marktlücke

Das Ex-Schutzdokument nach §6(9) GefStoffV i.V.m. §5 BetrSichV ist für jeden Betreiber explosionsgefährdeter Bereiche eine gesetzliche Pflicht. In der Praxis wird es bisher ausschließlich manuell (oft durch externe Berater zu 800–2.000 €/Tag) erstellt. Kein SaaS-Anbieter bietet heute einen geführten, automatisierten Workflow an, der Zoneneinteilung, Zündquellenbewertung und Maßnahmenableitung zu einem fertigen Rechtsdokument zusammenführt.

> **Kern-USP:** Schutztat automatisiert den gesamten Prozess vom Stoff-Upload (SDS) bis zum signierten Ex-Schutzdokument in WeasyPrint-PDF-Qualität — rechtssicher nach TRGS 720–725, EN 1127-1 und BetrSichV.

### 1.2 Prozessfluss & User Journey

| Schritt | Aktivität des Nutzers | Automatisierung durch System | Status-Transition |
|---------|----------------------|-----------------------------|--------------------|
| 1 | Standort & Bereich auswählen, Hauptgefahrstoff aus Inventar wählen | System lädt SDS-Daten (UEG, OEG, Flammpunkt, Zündtemp.) automatisch vor | `draft → in_progress` |
| 2 | Zoneneinteilung: Zonen anlegen, Typ auswählen (0/1/2 oder 20/21/22) | System schlägt Zone-Typ anhand UEG und Freisetzungsrate vor (TRGS 721) | `in_progress` |
| 3 | Zündquellenbewertung: 13-Quellen-Checkliste (EN 1127-1) bestätigen | System markiert Quellen als 'relevant' basierend auf Zone-Typ und Gerätekatalog | `in_progress` |
| 4 | Schutzmaßnahmen: Primär / Sekundär / Konstruktiv aus Katalog wählen | System filtert Maßnahmen nach Zone-Typ und TRGS 722, prüft TOPS-Vollständigkeit | `in_progress → review` |
| 5 | Review & Freigabe: Vorschau-PDF prüfen, elektronisch unterzeichnen | WeasyPrint generiert Ex-Schutzdokument (async via Celery), speichert in `DocumentVersion` | `review → validated` |

### 1.3 Automation-Engine

#### 1.3.1 Stoff-Trigger (bereits in `substances` verankert)

Bei neuem `SiteInventoryItem` mit explosionsrelevanten H-Codes (H220–H225, H240–H242, H250, H261, H270–H272) erzeugt `ExIntegrationService` einen outbox-Event. Dieser triggert:

- Automatische Erstellung eines `ExplosionConcept`-Entwurfs (`status=draft`)
- Vorabfüllung: Stoff, Flammpunkt, UEG/OEG, Zündtemperatur aus `SdsRevision`
- Benachrichtigung an die zuständige Sicherheitsfachkraft

#### 1.3.2 Zonen-Vorschlagsalgorithmus

Regelbasierte Engine nach TRGS 721, Abschnitt 4:

- **Input:** Freisetzungsgrad, Lüftungsgrad, Lüftungsverfügbarkeit
- **Output:** Empfohlener Zone-Typ mit Begründungstext aus TRGS 721-Textbausteinen
- **Implementierung:** `ZoneClassificationEngine` mit datenbankgetriebenem Entscheidungsbaum (admin-pflegbar)
- **Erweiterung:** In Phase 2 LLM-Aufruf für komplexe Szenarien

#### 1.3.3 Zündquellenbewertung (EN 1127-1)

Das bestehende `ZoneIgnitionSourceAssessment`-Model enthält bereits die 13 Zündquellenarten. Erweiterung:

- **Auto-Prefill:** Für jede Zone werden alle 13 Quellen als 'zu prüfen' angelegt
- **Heuristik:** Elektrische Quellen als 'vorhanden' markieren wenn Non-Ex-Equipment in der Zone
- **UI:** HTMX-Checkliste mit Toggle (vorhanden / nicht vorhanden / Maßnahme ergriffen)

#### 1.3.4 PDF-Template (WeasyPrint)

Das Ex-Schutzdokument-PDF enthält:

1. **Deckblatt:** Betrieb, Standort, Bereich, Erstelldatum, Versionsnummer, Unterschrift-Block
2. **Abschnitt 1:** Allgemeine Angaben (Stoff, SDS-Referenz, UEG/OEG, Flammpunkt)
3. **Abschnitt 2:** Zoneneinteilung-Tabelle mit Ausdehnung und Begründung
4. **Abschnitt 3:** Zündquellenbewertung (EN 1127-1) als Tabelle
5. **Abschnitt 4:** Schutzmaßnahmen gegliedert nach primär/sekundär/konstruktiv
6. **Abschnitt 5:** Betriebsmittel-Liste mit ATEX-Kennzeichnung und nächstem Prüfdatum
7. **Anhang:** Genutzte Regelwerke (aus `ReferenceStandard`-Tabelle) und SDS-Versionsverweis

### 1.4 Datenmodell-Erweiterungen

| Neues Feld / Model | Bestehende App | Zweck |
|-------------------|---------------|-------|
| `ZoneClassificationRule` (neu) | `explosionsschutz` | Regelwerk für Zonen-Vorschlag, admin-pflegbar |
| `ExplosionConcept.auto_draft_from_inventory` | `explosionsschutz` | Flag: Konzept automatisch aus `SiteInventoryItem` erzeugt |
| `ExplosionConcept.pdf_document` (FK → `DocumentVersion`) | `explosionsschutz` | Verknüpfung zum generierten PDF |
| `ZoneIgnitionSourceAssessment.auto_prefilled` | `explosionsschutz` | Unterscheidung auto-befüllt vs. manuell geprüft |
| `ExDocumentGenTask` (Celery-Task) | `explosionsschutz` | Async PDF-Generierung, speichert in S3 |

### 1.5 Implementierungsplan Modul 1

| Phase | Aufgaben | Dauer | Output |
|-------|---------|-------|--------|
| 1A | `ZoneClassificationEngine`, Regelwerk-Seeding, SDS-Trigger-Erweiterung | 2 Wo. | Auto-Draft-Erzeugung läuft |
| 1B | `ZoneIgnitionSourceAssessment` Auto-Prefill, HTMX-Wizard-Flow (5 Schritte) | 3 Wo. | Vollständiger geführter Wizard |
| 1C | WeasyPrint-Template, Celery-Task, `DocumentVersion`-Speicherung, Audit-Event | 2 Wo. | Generiertes PDF abrufbar |
| 1D | TOPS-Vollständigkeitsprüfung, Review-Workflow, elektronische Freigabe | 2 Wo. | Freigegebenes Ex-Schutzdokument |
| 1E | Tests (E2E, Compliance-Szenarien), Dokumentation, Seed-Daten | 1 Wo. | Release-fähig |

---

## MODUL 2: GBU-Automation aus SDS (H-Code → GBU → Betriebsanweisung)

### 2.1 Ausgangssituation

Die Gefährdungsbeurteilung für Tätigkeiten mit Gefahrstoffen (GefStoffV §6, TRGS 400/401) muss tätigkeitsbezogen erstellt und dokumentiert werden. Basis sind die H-Sätze aus dem Sicherheitsdatenblatt. Heute ist dieser Prozess überall manuell: SDB lesen → Gefährdungen ableiten → GBU schreiben → Betriebsanweisung erstellen.

> **Kern-USP:** Schutztat liest H-Codes direkt aus der vorhandenen `SdsRevision` und erzeugt daraus automatisch eine tätigkeitsbezogene GBU-Vorlage sowie eine druckfertige Betriebsanweisung nach TRGS 555 — der Nutzer validiert nur noch, anstatt zu schreiben.

### 2.2 Prozessfluss

| Schritt | Nutzeraktion | System-Automatisierung | Zeitersparnis |
|---------|-------------|----------------------|--------------|
| 1 | Tätigkeit anlegen: Stoff aus Inventar auswählen, Tätigkeit beschreiben | System lädt H-Sätze, P-Sätze, Piktogramme aus `SdsRevision`; ordnet H-Sätze den TRGS 400 Gefährdungskategorien zu | ~90 % der Recherche |
| 2 | Gefährdungsableitung prüfen: Auto-generierte Liste bestätigen/anpassen | `HCodeMappingEngine`: H200–H420 → Gefährdungskategorien; Schutzmaßnahmen nach TOPS vorschlagen | ~80 % Zeitersparnis |
| 3 | Expositionsszenario ergänzen: Häufigkeit, Dauer, Substitutionsprüfung (§7 GefStoffV) | Risikobewertungs-Score basierend auf EMKG-Methode | Berechnung automatisch |
| 4 | GBU freigeben: Review, Unterschrift, Revisionsdatum | PDF-Generierung, `DocumentVersion`-Speicherung, Erinnerung nächste Überprüfung | Dokumentation vollständig |
| 5 | Betriebsanweisung erzeugen: Knopfdruck aus genehmigter GBU | BA nach TRGS 555 aus GBU-Daten: Stoff, Gefahr, Schutzmaßnahmen, Erste Hilfe — farbig mit GHS-Piktogrammen | BA-Erstellung entfällt |

### 2.3 H-Code Mapping Engine

#### Datenstruktur (datenbankgetrieben, admin-pflegbar)

- **`HazardCategoryRef`:** Gefährdungskategorie (Brand/Explosion, Akute Toxizität, CMR, ...)
- **`HCodeCategoryMapping`:** H-Code → `HazardCategoryRef` (1:n)
- **`MeasureTemplate`:** Schutzmaßnahme-Vorlage mit TOPS-Kategorie
- **`ExposureRiskMatrix`:** EMKG-Methode: Menge × Flüchtigkeit → Expositionsklasse

#### GBU-Generator-Service

| Service-Methode | Input | Output |
|----------------|-------|--------|
| `derive_hazard_categories(sds_revision)` | `SdsRevision`-ID | Liste `HazardCategory` mit H-Code-Begründung |
| `propose_measures(hazard_categories, activity)` | Kategorien + Tätigkeitsbeschreibung | TOPS-geordnete Maßnahmen-Liste |
| `calculate_risk_score(sds, exposure_params)` | H-Codes + Menge/Häufigkeit/Dauer | Risikostufe (niedrig/mittel/hoch) + EMKG-Klasse |
| `generate_gbu_pdf(assessment_id)` | GBU-Model-ID | WeasyPrint-PDF + `DocumentVersion` |
| `generate_ba_pdf(assessment_id)` | Freigegebene GBU-ID | BA-PDF nach TRGS 555-Layout (farbig, GHS-Piktogramme) |

### 2.4 Betriebsanweisung-Template (WeasyPrint)

| Abschnitt | Inhalt | Datenquelle |
|-----------|--------|------------|
| Kopf | Betrieb, Bereich, BA-Nr., Datum, Unterschrift | `Organization`, `Site`, GBU-Metadaten |
| Gefahrstoffbezeichnung | Name, CAS-Nr., Signalwort, GHS-Piktogramme | `Substance.name`, `SdsClassification.signal_word`, `SdsPictogram` |
| Gefahren | H-Sätze in Klartext | `SdsHazardStatement.statement_text` |
| Schutzmaßnahmen & Hygiene | Technisch, organisatorisch, PSA (TOPS) | `ActivityMeasure` aus GBU |
| Verhalten bei Störungen | P-Sätze P300–P400, Erste Hilfe | `SdsPrecautionaryStatement` |
| Erste Hilfe | P-Sätze P300–P315, Notruf | `SdsPrecautionaryStatement`-Filter |

> GHS-Piktogramme werden als SVG eingebettet (UNECE-Lizenz: frei verwendbar).

### 2.5 Datenmodell: `HazardAssessmentActivity`

| Feld | Typ | Beschreibung |
|------|-----|-------------|
| `id` | UUID PK | Primary Key |
| `tenant_id` | UUID | Mandanten-Isolation (RLS) |
| `site` | FK → `Site` | Standort der Tätigkeit |
| `sds_revision` | FK → `SdsRevision` | Verwendetes SDB (Versionierung!) |
| `activity_description` | `TextField` | Tätigkeitsbeschreibung |
| `activity_frequency` | `CharField Enum` | täglich / wöchentlich / gelegentlich / selten |
| `duration_minutes` | `IntegerField` | Expositionsdauer pro Vorgang |
| `quantity_class` | `CharField Enum` | <1L / 1-10L / 10-100L / >100L |
| `derived_hazard_categories` | M2M → `HazardCategoryRef` | Auto-abgeleitete Gefährdungskategorien |
| `risk_score` | `CharField Enum` | niedrig / mittel / hoch (EMKG-Methode) |
| `status` | `CharField Enum` | draft / review / approved / outdated |
| `approved_by` | FK → `User` | Freigebende Person |
| `next_review_date` | `DateField` | Nächste Überprüfung (GefStoffV §6) |
| `gbu_document` | FK → `DocumentVersion` | Generiertes GBU-PDF |
| `ba_document` | FK → `DocumentVersion` | Generierte Betriebsanweisung-PDF |

### 2.6 Implementierungsplan Modul 2

| Phase | Aufgaben | Dauer | Output |
|-------|---------|-------|--------|
| 2A | `HCodeCategoryMapping` + `MeasureTemplate` Seeding (H200–H420), `HazardAssessmentActivity`-Model + Migrations | 2 Wo. | Datengrundlage + Admin-Pflege möglich |
| 2B | GBU-Generator-Service (`derive_hazard_categories`, `propose_measures`, `calculate_risk_score`), Unit-Tests | 2 Wo. | Core-Engine funktionsfähig |
| 2C | HTMX-5-Schritt-Wizard | 2 Wo. | Vollständiger Wizard im Browser |
| 2D | WeasyPrint GBU-Template + BA-Template (GHS-Piktogramme als SVG), Celery-Tasks | 2 Wo. | PDF-Ausgabe GBU + BA |
| 2E | `next_review_date`-Logik → Übergabe an Modul 3, Integration Tests | 1 Wo. | Release-fähig + verknüpft mit Modul 3 |

---

## MODUL 3: Compliance-Dashboard & Prüfintervall-Management

### 3.1 Ausgangssituation

Brandschutz- und Ex-Schutz-Betreiber verwalten heute Prüftermine in Excel, Papierordnern oder gar nicht. Prüffristen für Feuerlöscher (jährlich), Brandschutztüren, RWA-Anlagen, Sprinkler, Brandmeldeanlagen und Ex-Betriebsmittel sind komplex und standortübergreifend kaum überschaubar.

> **Kern-USP:** Ein einziges Cockpit für alle Prüffristen — Brandschutz und Explosionsschutz — mit automatischem Eskalations-Workflow: System → Erinnerung → Mahnung → offene Maßnahme im `actions`-Modul.

### 3.2 Scope: Anlagentypen & Prüfintervalle

| Anlagentyp | Rechtsgrundlage | Standard-Intervall | Prüfer | Im Model |
|-----------|----------------|-------------------|--------|---------|
| Tragbare Feuerlöscher | ASR A2.2, DGUV 0.300-001 | 2 Jahre (Sichtprüfung: jährl.) | Befähigte Person | `Equipment` (neu: `fire_ext`) |
| Brandschutztüren/-tore | MBO, LBO | jährlich | Sachkundiger | `Equipment` (neu: `fire_door`) |
| Rauch- u. Wärmeabzugsanlagen | DIN 18232, EN 12101 | halbjährlich | Sachkundiger | `Equipment` (neu: `smoke_ex`) |
| Ortsfeste Löschanlagen (Sprinkler) | VdS CEA 4001 | jährlich | Sachverständiger | `Equipment` (neu: `sprinkler`) |
| Brandmeldeanlagen (BMA) | DIN VDE 0833, DIN 14675 | jährlich | ZÜS | `Equipment` (neu: `fire_alarm`) |
| Ex-Betriebsmittel (ATEX) | BetrSichV §14–16 | nach Prüfplan (1–3 J.) | ZÜS | `Equipment` (bereits impl.) |
| GBU Gefahrstoffe | GefStoffV §6 Abs.1 | bei Änderung, mind. regelm. | SiFa | `HazardAssessmentActivity.next_review_date` |
| Ex-Schutzdokument | BetrSichV §6, GefStoffV §6(9) | bei wesentl. Änderung | SiFa | `ExplosionConcept` |

### 3.3 Dashboard-Architektur

#### Hauptansicht: Compliance-Cockpit (HTMX-Polling alle 60s)

| Widget | Datenquelle | Aktualisierung |
|--------|------------|---------------|
| Ampelstatus (gesamt) | `Equipment.next_inspection` × heute | HTMX live |
| Fällige Prüfungen (7 / 30 / 90 Tage) | `Equipment.next_inspection_date`-Filter | HTMX live |
| Überfällige Anlagen (rot) | `next_inspection_date < heute` | HTMX live, Alert-Banner |
| GBU-Reviews fällig | `HazardAssessmentActivity.next_review_date` | HTMX live |
| Ex-Dokumente in Review | `ExplosionConcept.status` | HTMX live |
| Offene Maßnahmen | `Action.status=open, entity_type=Inspection` | HTMX live |
| Kalender-View | Alle `next_inspection_dates` aller Anlagen | täglich regeneriert |

#### Eskalations-Workflow (Celery Beat täglich 06:00)

| Trigger | Aktion | Empfänger | Kanal |
|---------|--------|-----------|-------|
| 30 Tage vor Fälligkeit | Erinnerungs-Benachrichtigung | Zuständige Person | E-Mail / In-App |
| 7 Tage vor Fälligkeit | Eskalations-Benachrichtigung | Zuständige + SiFa-Rolle | E-Mail (dringend) |
| 1 Tag vor Fälligkeit | Letzte Erinnerung | Alle mit Inspection-Recht | E-Mail + In-App |
| Tag der Fälligkeit (nicht erledigt) | Automatisch: `ActionItem` erstellen | SiFa-Rolle als Assignee | In-App Badge |
| Überfällig (>0 Tage) | Rote Ampel, täglicher Reminder | Alle mit Dashboard-Zugriff | In-App dauerhaft |

### 3.4 Datenmodell-Erweiterungen

#### Equipment-Typen-Erweiterung (additiv, kein Breaking Change)

```python
# Neue equipment_category-Enum-Werte
('fire_ext',    'Tragbarer Feuerlöscher'),
('fire_door',   'Brandschutztür/-tor'),
('smoke_ex',    'Rauch-/Wärmeabzugsanlage (RWA)'),
('sprinkler',   'Ortsfeste Löschanlage'),
('fire_alarm',  'Brandmeldeanlage (BMA)'),
('emerg_light', 'Sicherheitsbeleuchtung'),
('other_fire',  'Sonstiger Brandschutz'),
```

Neue Felder: `location_description`, `responsible` (FK → User), `inspector_type`, `preset` (FK → `InspectionIntervalPreset`)

#### `ComplianceSummary` (Materialized Cache)

Täglicher Snapshot: `tenant_id`, `site_id`, `equipment_category`, `overdue_count`, `due_within_30_days`, `compliant_count`, `generated_at`

→ Dashboard-Seite liest aus `ComplianceSummary` statt direkt aus `Equipment` (O(1) statt O(n))

### 3.5 Implementierungsplan Modul 3

| Phase | Aufgaben | Dauer | Output |
|-------|---------|-------|--------|
| 3A | Equipment-Typ-Erweiterung, `InspectionIntervalPreset`-Seeding | 1 Wo. | Alle Anlagentypen erfassbar |
| 3B | Compliance-Cockpit-View (HTMX), Ampel-KPIs, Fälligkeitslisten | 2 Wo. | Dashboard sichtbar |
| 3C | Celery-Beat-Eskalations-Task, E-Mail-Templates, Action-Auto-Erstellung | 2 Wo. | Vollautomatischer Eskalations-Workflow |
| 3D | `ComplianceSummary`-Snapshot-Task, Multi-Standort-Aggregation, CSV/PDF-Export | 1 Wo. | Performance-optimiert, exportierbar |
| 3E | Integration: `next_review_date` aus Modul 2, Ex-Schutzdokument-Status aus Modul 1 | 1 Wo. | Vollständig integriertes Cockpit |

---

## Gesamtroadmap & Abhängigkeiten

| Woche | 1–2 | 3–4 | 5–6 | 7–8 | 9–10 |
|-------|-----|-----|-----|-----|------|
| **Modul 2** | 2A: H-Code-Mapping Seeding, Model | 2B: GBU-Engine Service | 2C: HTMX-Wizard | 2D: PDF GBU + BA | 2E: next_review → M3 |
| **Modul 3** | 3A: Equipment-Typen | 3B: Dashboard-View | 3C: Celery-Eskalation | 3D: Snapshot + Export | 3E: M1+M2-Integration |
| **Modul 1** | — | 1A: Zone-Engine, SDS-Trigger | 1B: HTMX-Wizard 5 Schritte | 1C: PDF Ex-Schutzdokument | 1D: Review-Workflow + 1E |

> **Empfehlung:** Start mit Modul 2 (GBU-Engine), da es auf dem bereits vollständig implementierten `substances`-Modul aufsetzt und den schnellsten time-to-value hat. Modul 3 läuft parallel. Modul 1 baut auf Modul 3 auf.

### Vergleich der Module

| Dimension | Modul 2: GBU-Automation | Modul 3: Compliance-Dashboard | Modul 1: Ex-Schutzdokument |
|-----------|------------------------|------------------------------|--------------------------|
| Bereits impl. Basis | `substances` ✅, `documents` ✅ | `explosionsschutz/Equipment` ✅ | `explosionsschutz` ✅, `substances` ✅ |
| Aufwand (Wochen) | ~9 Wochen | ~7 Wochen | ~10 Wochen |
| Monetarisierung | Shield · 199 €/Monat | Guard · 79 €/Monat | Fortress · 499+ €/Monat |
| Retention-Faktor | hoch (BA-Pflege) | sehr hoch (Fristen-Daten) | sehr hoch (Dokument-Pflege) |
| **Priorität** | **⭐ 1 (Quick Win)** | **⭐ 2 (Retention-Anker)** | **⭐ 3 (Premium-Tier)** |
