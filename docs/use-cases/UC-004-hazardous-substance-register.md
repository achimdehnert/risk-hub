# UC-004: Gefahrstoffkataster (Standortbezogen)

**Status:** Draft
**Modul:** Gefahrstoffe (Substances / Sites)
**Erstellt:** 2026-04-17

## Akteur

Der Sicherheitsbeauftragte (Rolle: Editor oder Admin)

## Ziel

Der Sicherheitsbeauftragte möchte eine mandanten- und multiuserfähige Gefahrstoffdatenbank führen, die zeigt, welche Gefahrstoffe an welchen Standorten vorliegen. Er kann bestehende Excel-Kataster importieren und erhält eine strukturierte, durchsuchbare Übersicht mit regulatorischen Informationen (GHS, WGK, Lagerklasse, EMKG).

## Vorbedingung

- Der Benutzer ist eingeloggt und hat die Rolle Editor oder Admin
- Das Gefahrstoff-Modul ist für den Mandanten freigeschaltet
- Mindestens ein Standort ist für den Mandanten angelegt

## Scope

Standortverwaltung, Gefahrstoff-Zuordnung zu Standorten, Excel-Import, Kataster-Dashboard.
Nicht Teil: SDS-Upload (→ UC-003), Ex-Schutz-Konzepte (→ UC-002), Freigabe-Workflow.

## Datenmodell — Normalisierte Architektur

### Designprinzipien

1. **Global vs. Tenant**: Stoffdaten sind Naturgesetze (global), Verwendung ist mandantenspezifisch
2. **Produkt ≠ Substanz**: Ein Handelsprodukt (z.B. "Rivolta S.L.X. Aerosol") enthält mehrere chemische Substanzen (Gemisch)
3. **Trennung Identität / Eigenschaften / Verwendung**: Drei separate Normalisierungsebenen
4. **Single Source of Truth**: Kein Feld doppelt, keine Denormalisierung ohne expliziten Grund
5. **BigAutoField PK** überall (Platform-Standard), UUID nur für externe API-Referenz

### ER-Diagramm (3NF)

```
┌──────────────────────────────────────────────────────────────────┐
│                    GLOBALE EBENE (kein tenant_id)                │
│  Naturwissenschaftliche Fakten — für alle Mandanten identisch   │
├──────────────────────────────────────────────────────────────────┤
│                                                                  │
│  GlobalSubstance ◄─────── GlobalSdsRevision                     │
│  ├── cas_number (NK)       ├── source_hash (SHA-256)            │
│  ├── ec_number              ├── product_name                     │
│  ├── name (IUPAC)           ├── manufacturer_name                │
│  ├── chemical_formula       ├── revision_date, version           │
│  └── synonyms (JSON)        ├── signal_word, wgk                 │
│                              ├── flash_point_c, storage_class     │
│  HazardStatementRef         ├── ◄► hazard_statements (M:N)       │
│  PrecautionaryStatementRef  ├── ◄► precautionary_statements (M:N)│
│  PictogramRef               ├── ◄► pictograms (M:N)              │
│                              └── ► GlobalSdsComponent (1:N)       │
│                                   ├── chemical_name, cas          │
│                                   ├── concentration_min/max       │
│                                   └── ► GlobalSdsExposureLimit    │
│                                                                  │
│  RPhrase (Legacy)           ── R-Satz → H-Satz Mapping          │
│  SPhrase (Legacy)           ── S-Satz → P-Satz Mapping          │
│                                                                  │
└──────────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────────┐
│               TENANT-EBENE (mit tenant_id)                       │
│  Mandantenspezifische Verwendung und Organisation                │
├──────────────────────────────────────────────────────────────────┤
│                                                                  │
│  Organization (tenancy)                                          │
│  └── Site (tenancy, erweitert)                                   │
│       ├── code (Kürzel, z.B. "A")                                │
│       ├── site_type (PLANT/WAREHOUSE/OFFICE/LAB)                 │
│       └── is_active                                              │
│       └── Department (NEU)                                       │
│            ├── organization (FK→Organization)                    │
│            ├── site (FK→Site, nullable — standortübergreifend)   │
│            ├── name (z.B. "Produktion", "Haustechnik")           │
│            └── code (z.B. "PROD", "HT")                         │
│                                                                  │
│  Product (NEU) ─── Handelsprodukt / Gemisch                     │
│  ├── tenant_id                                                   │
│  ├── trade_name              "Rivolta S.L.X. Aerosol"           │
│  ├── manufacturer (FK→Party)                                     │
│  ├── material_number         Interne Materialnummer              │
│  ├── sds_revision (FK→GlobalSdsRevision, nullable)               │
│  ├── status (ACTIVE/INACTIVE/ARCHIVED)                           │
│  └── ◄► ProductComponent (1:N)                                  │
│       ├── substance (FK→GlobalSubstance)                         │
│       ├── concentration_pct   100% bei Reinstoff                 │
│       ├── concentration_min/max (%, nullable für Bereiche)       │
│       └── reach_number                                           │
│  INFO: Reinstoff = Product mit 1 Component (100%). Kein          │
│        separater FK global_substance → einheitlicher Query-Pfad  │
│                                                                  │
│  SubstanceUsage (NEU) ─── M:N: Produkt × Standort × Abteilung  │
│  ├── tenant_id                                                   │
│  ├── product (FK→Product)                                        │
│  ├── site (FK→Site)                                              │
│  ├── department (FK→Department, nullable)                        │
│  ├── usage_description       "Reinigung von Kontakten"           │
│  ├── storage_location        "Gefahrstofflager Halle 3"         │
│  ├── storage_class           Lagerklasse TRGS 510 (Choices)     │
│  ├── max_storage_qty         Dezimal                             │
│  ├── max_storage_unit        kg / l / m³ (Choices)              │
│  ├── annual_consumption      Dezimal                             │
│  ├── annual_consumption_unit kg / l (Choices)                    │
│  ├── aggregat_state          SOLID / LIQUID / GAS                │
│  ├── operating_instruction   FK→Document (nullable)              │
│  ├── risk_assessment         FK→Document (nullable)              │
│  ├── substitution_status     OPEN / DONE / NOT_REQUIRED          │
│  ├── substitution_notes      Text                                │
│  ├── status                  ACTIVE / INACTIVE / PHASED_OUT      │
│  ├── last_reviewed           Date                                │
│  └── notes                                                       │
│  UNIQUE: (tenant_id, product, site, department)                  │
│                                                                  │
│  Party (bestehend)                                               │
│  ├── name, party_type                                            │
│  └── address, email, phone, website                              │
│                                                                  │
└──────────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────────┐
│           LEGACY-IMPORT-EBENE (temporär bei Excel-Import)        │
├──────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ImportBatch                                                     │
│  ├── tenant_id                                                   │
│  ├── file_name, file_hash                                        │
│  ├── target_site (FK→Site)                                       │
│  ├── column_mapping (JSON)   Spalten-Zuordnung                  │
│  ├── status (PENDING/PROCESSING/DONE/FAILED)                     │
│  ├── stats (JSON)            {created: 120, updated: 5, ...}    │
│  └── imported_by, imported_at                                    │
│                                                                  │
│  ImportRow                                                       │
│  ├── tenant_id                                                   │
│  ├── batch (FK→ImportBatch)                                      │
│  ├── row_number                                                  │
│  ├── raw_data (JSON)         Original-Zeile                     │
│  ├── resolved_product (FK→Product, nullable)                     │
│  ├── status (OK/WARNING/ERROR)                                   │
│  └── messages (JSON)         Validierungs-/Matchinghinweise     │
│                                                                  │
└──────────────────────────────────────────────────────────────────┘
```

### Normalisierungsregeln (3NF)

| Regel | Umsetzung |
|-------|-----------|
| **1NF** Atomare Werte | H-Sätze als M:N (nicht CSV-String), Standort-Checkboxen → separate Rows |
| **2NF** Volle funktionale Abhängigkeit | Lagerklasse gehört zur Verwendung (SubstanceUsage), nicht zum Stoff — derselbe Stoff kann je nach Standort unterschiedlich gelagert werden |
| **3NF** Keine transitive Abhängigkeit | Herstelleradresse in Party (nicht in Substance), WGK in SDS-Revision (nicht in Usage) |
| **Kein redundanter Stoff** | `GlobalSubstance` ist die einzige Substanz-Entität; `Product` referenziert sie |
| **Produkt ≠ Substanz** | Handelsprodukt ("Rivolta S.L.X. Aerosol") → `Product` mit `ProductComponent` → `GlobalSubstance` |

### Abgrenzung: Bestehende vs. neue Modelle

| Bestehendes Model | Aktion | Begründung |
|-------------------|--------|------------|
| `global_sds.GlobalSubstance` | **BEIBEHALTEN** | Globale Substanz-Stammdaten (CAS), Single Source |
| `global_sds.GlobalSdsRevision` | **BEIBEHALTEN** | SDS-Versionen, globale Ebene |
| `global_sds.GlobalSdsComponent` | **BEIBEHALTEN** | Inhaltsstoffe eines SDS-Gemischs |
| `global_sds.GlobalSdsExposureLimit` | **BEIBEHALTEN** | AGW/DNEL pro Komponente |
| `substances.Substance` | **MIGRIEREN → Product** | Wird zu tenant-spezifischem Handelsprodukt |
| `substances.Identifier` | **BEIBEHALTEN** | CAS/REACH/UFI pro Produkt |
| `substances.Party` | **BEIBEHALTEN** | Hersteller/Lieferant |
| `substances.SdsRevision` | **ENTFERNEN** (langfristig) | Duplikat von `GlobalSdsRevision`, Daten migrieren |
| `substances.SiteInventoryItem` | **ERSETZEN → SubstanceUsage** | Erweitert um Department, Betriebsanweisung etc. |
| `substances.LocationSubstanceEntry` | **ERSETZEN → SubstanceUsage** | Zusammenführen mit SiteInventoryItem |
| `tenancy.Site` | **ERWEITERN** | + `code`, `site_type`, `is_active` |
| `substances.HazardStatementRef` | **BEIBEHALTEN** | Globale Referenz |
| `substances.PrecautionaryStatementRef` | **BEIBEHALTEN** | Globale Referenz |
| `substances.PictogramRef` | **BEIBEHALTEN** | Globale Referenz |

### Neue Modelle

| Neues Model | App | Zweck |
|-------------|-----|-------|
| `Department` | `tenancy` | Abteilungen pro Standort |
| `Product` | `substances` | Handelsprodukt/Gemisch (tenant-scoped) |
| `ProductComponent` | `substances` | Inhaltsstoffe eines Produkts (M:N → GlobalSubstance) |
| `SubstanceUsage` | `substances` | Welches Produkt an welchem Standort in welcher Abteilung |
| `ImportBatch` | `substances` | Excel-Import-Batch mit Mapping und Status |
| `ImportRow` | `substances` | Einzelzeile eines Imports mit Matching-Ergebnis |
| `RPhrase` | `substances` | Legacy R-Satz → H-Satz Mapping (für Altdaten-Import) |
| `SPhrase` | `substances` | Legacy S-Satz → P-Satz Mapping (für Altdaten-Import) |

### Migrationsstrategie (bestehende Daten)

Die Migration von `substances.Substance` → `Product` erfolgt in 3 Phasen:

1. **Phase A — Additive Models** (diese Iteration): `Product`, `ProductComponent`, `SubstanceUsage`, `Department`, `ImportBatch`, `ImportRow` als neue Models anlegen. Bestehende Models bleiben unverändert.
2. **Phase B — Daten-Migration**: Django Data-Migration schreibt bestehende `Substance`-Einträge in `Product` + `ProductComponent`. `SiteInventoryItem` und `LocationSubstanceEntry` werden in `SubstanceUsage` migriert. Bestehende FKs (z.B. `explosionsschutz.ExConcept.substance`) werden via DB-View/Proxy bedient.
3. **Phase C — Cleanup** (separate ADR): Alte Models (`Substance`, `SiteInventoryItem`, `LocationSubstanceEntry`, `SdsRevision`) entfernen. Erfordert eigene ADR mit Breaking-Change-Analyse.

> **Hinweis:** Das Datenmodell in diesem UC ist umfangreich genug für eine eigene ADR (z.B. ADR-XXX: Normalisiertes Gefahrstoffkataster). Der UC beschreibt den fachlichen Ablauf, die ADR die technische Architekturentscheidung.

## Excel-Spalten-Mapping (Import)

Basierend auf Analyse des Beispiel-Katasters "Werk Freiburg" (145 Gefahrstoffe):

| Excel-Spalte | Ziel-Model.Feld | Normalform | Bemerkung |
|--------------|-----------------|------------|-----------|
| Lfdnr. | `ImportRow.raw_data` | — | Nur für Referenz, nicht in Datenmodell |
| Handelsname/Produkt | **`Product.trade_name`** | 2NF | Handelsprodukt, nicht Substanz |
| Firma/Hersteller | **`Party.name`** + `Party.address` | 3NF | Adresse separieren, FK von Product |
| Materialnummer | `Product.material_number` | 2NF | Intern pro Mandant |
| Abteilung (FR/HA/P/Prod…) | **`Department`** (FK) → **`SubstanceUsage`** | 1NF | Checkbox-Spalten → je eine SubstanceUsage-Row |
| Verwendung im Betrieb | `SubstanceUsage.usage_description` | 2NF | Abhängig von Produkt+Standort |
| Symbol (alt: F+, Xi…) | `ImportRow.raw_data` → R/S→H/P Mapping | 1NF | Legacy, konvertiert via `RPhrase`-Tabelle |
| R-Sätze | → `RPhrase` → `HazardStatementRef` (M:N) | 1NF | Altdaten via Mapping-Tabelle konvertiert |
| S-Sätze | → `SPhrase` → `PrecautionaryStatementRef` (M:N) | 1NF | Altdaten via Mapping-Tabelle konvertiert |
| GHS-Symbol | → `PictogramRef` (M:N auf SDS) | 1NF | GHS02, GHS07 etc. |
| H-Sätze | → `HazardStatementRef` (M:N auf SDS) | 1NF | Bestehende Relation |
| P-Sätze | → `PrecautionaryStatementRef` (M:N auf SDS) | 1NF | Bestehende Relation |
| WGK | `GlobalSdsRevision.wgk` | 3NF | Stoffeigenschaft, nicht Usage-abhängig |
| VOC % | `GlobalSdsRevision.voc_percent` | 3NF | Stoffeigenschaft |
| Dichte g/l | `GlobalSdsRevision` (neues Feld) | 3NF | Stoffeigenschaft |
| AGW (Bestandteil/Typ/Wert) | → `GlobalSdsExposureLimit` (1:N) | 1NF+3NF | Pro Komponente, Typ+Route+Wert+Einheit |
| REACH-Nr. | `ProductComponent.reach_number` oder `Identifier` | 2NF | Pro Substanz-Anteil im Produkt |
| Biologische Grenzwerte | → `GlobalSdsExposureLimit` (LimitType=BGW) | 1NF | Gleiche Tabelle, anderer Typ |
| Max. zul. Lagermenge | `SubstanceUsage.max_storage_qty` + `_unit` | 2NF | Pro Standort+Abteilung |
| Verbrauch pro Jahr | `SubstanceUsage.annual_consumption` + `_unit` | 2NF | Pro Standort+Abteilung |
| Lagerklasse | `SubstanceUsage.storage_class` | 2NF | TRGS 510, abhängig von Lagerort |
| Lagerort | `SubstanceUsage.storage_location` | 2NF | Freitext, standortabhängig |
| SDB (Ablage/Stand) | `Product.sds_revision` (FK→GlobalSdsRevision) | 3NF | Verknüpfung, nicht Kopie |
| Betriebsanweisung | `SubstanceUsage.operating_instruction` (FK→Document) | 3NF | Dokument-Referenz |
| Gefährdungsbeurteilung | `SubstanceUsage.risk_assessment` (FK→Document) | 3NF | Dokument-Referenz |
| Substitutionsprüfung | `SubstanceUsage.substitution_status` | 2NF | OPEN/DONE/NOT_REQUIRED |
| Bemerkung | `SubstanceUsage.notes` | — | Freitext |
| Bearbeitungsdatum | `SubstanceUsage.last_reviewed` | 2NF | Pro Verwendungs-Eintrag |

## Schritte

### A. Standorte verwalten

1. Der Sicherheitsbeauftragte navigiert zu "Standorte"
2. Er legt einen neuen Standort an (Name, Kürzel, Adresse, Typ)
3. Das System speichert den Standort mandantengebunden

### B. Excel-Import (normalisierte Pipeline)

1. Der Sicherheitsbeauftragte navigiert zum Gefahrstoffkataster
2. Er klickt auf "Excel importieren"
3. Das System zeigt den Upload-Dialog (Drag-and-Drop, .xls/.xlsx)
4. Der Sicherheitsbeauftragte wählt die Excel-Datei und den Ziel-Standort
5. **Phase 1 — Spaltenanalyse**: Das System erkennt die Spaltenstruktur (Multi-Row-Header) und erstellt einen `ImportBatch` mit `column_mapping` (JSON)
6. Das System zeigt eine Vorschau:
   - Erkannte Spalten mit Mapping-Vorschlag (editierbar)
   - Anzahl erkannter Produkte/Stoffe
   - Erkannte Abteilungen (aus Checkbox-Spalten)
7. Der Sicherheitsbeauftragte bestätigt oder korrigiert das Mapping
8. **Phase 2 — Normalisierte Import-Pipeline**:
   - **Party**: Hersteller/Lieferant aus "Firma/Hersteller" extrahieren (Name+Adresse trennen), deduplizieren via `uq_party_tenant_type_name`
   - **Product**: Handelsprodukt anlegen mit `trade_name`, FK→Party, `material_number`
   - **GlobalSubstance**: Falls CAS vorhanden → Match gegen `GlobalSubstance.cas_number_normalized`; falls neu → anlegen
   - **ProductComponent**: Bei Gemischen (mehrere CAS in einer Zeile) → je ein Eintrag mit `concentration_min/max`
   - **Department**: Aus Checkbox-Spalten (FR, HA, P, Prod…) → `Department` per Standort anlegen
   - **SubstanceUsage**: Je Produkt × Standort × Abteilung eine Row (1NF: keine Checkbox-Arrays)
   - **R→H Konvertierung**: Alt-Kennzeichnung (R-Sätze) → H-Sätze via `RPhrase`-Mapping
   - **SDS-Matching**: Wenn `GlobalSdsRevision` mit gleicher CAS existiert → `Product.sds_revision` verknüpfen
9. **Phase 3 — Validierung**: Jede Zeile wird als `ImportRow` gespeichert mit Status (OK/WARNING/ERROR) und Validierungs-Messages
10. Das System zeigt den Import-Report:
    - Erstellt: X Produkte, Y Substanzen, Z Verwendungen
    - Aktualisiert: N (bei Re-Import)
    - Warnungen: Fehlende CAS, unbekannte Lagerklasse, R→H-Konvertierung unsicher
    - Fehler: Ungültige Zeilen (mit Zeilennummer + Grund)

### C. Kataster-Dashboard (Standortübersicht)

1. Der Sicherheitsbeauftragte öffnet das Kataster-Dashboard
2. Das System zeigt pro Standort:
   - Anzahl Gefahrstoffe
   - WGK-Verteilung (Ampel: grün/gelb/rot)
   - Lagerklassen-Übersicht
   - Offene Substitutionsprüfungen
   - Stoffe mit abgelaufenem SDS
3. Filter: nach Standort, Abteilung, WGK, Lagerklasse, GHS-Piktogramm
4. Export: gefilterte Ansicht als Excel/PDF

### D. Einzelstoff-Ansicht

1. Der Sicherheitsbeauftragte klickt auf einen Gefahrstoff
2. Das System zeigt:
   - Stammdaten (Name, CAS, Hersteller)
   - GHS-Kennzeichnung (Piktogramme, H-/P-Sätze, Signalwort)
   - Regulatorische Daten (WGK, Lagerklasse, AGW, REACH)
   - Standorte, an denen der Stoff verwendet wird
   - Verknüpftes SDS (mit Link zur Revision)
   - Betriebsanweisung, Gefährdungsbeurteilung

## Fehlerfälle

- Falls die Excel-Datei kein erkennbares Kataster-Format hat: "Spaltenstruktur nicht erkannt — bitte Mapping manuell zuordnen"
- Falls ein Stoff ohne CAS-Nummer importiert wird: Anlage als Product ohne ProductComponent, Markierung zur manuellen Nachpflege
- Falls Lagerklassen-Konflikte existieren (z.B. Zusammenlagerungsverbot nach TRGS 510): Warnung im Import-Report
- Falls dieselbe Excel erneut importiert wird (gleicher `file_hash`): System erkennt Duplikat und bietet "Aktualisieren" oder "Abbrechen" an
- Falls CAS-Nummer-Format ungültig (nicht NNN-NN-N): Warnung + Zeile als WARNING markiert, Import fortsetzen
- Falls mehrere Hersteller mit gleichem Namen aber unterschiedlicher Adresse existieren: Vorschau zeigt Match-Kandidaten, Benutzer wählt
- Falls Excel >1000 Zeilen: Import wird als Celery-Task im Hintergrund ausgeführt, Fortschrittsanzeige via WebSocket/Polling
- Falls R-Satz keinem H-Satz zugeordnet werden kann: Warnung in ImportRow, Originalwert in `raw_data` erhalten

## Akzeptanzkriterien

### Funktional

GIVEN ein eingeloggter Sicherheitsbeauftragter mit mindestens einem Standort
WHEN er eine Excel-Datei mit Gefahrstoffdaten hochlädt
THEN werden Produkte, Substanzen und Verwendungen normalisiert importiert

GIVEN ein importiertes Kataster
WHEN der Sicherheitsbeauftragte das Dashboard öffnet
THEN sieht er pro Standort die Gefahrstoff-Übersicht mit WGK-Ampel und Lagerklassen

GIVEN ein Handelsprodukt mit CAS-Nummer im Import
WHEN eine `GlobalSubstance` mit derselben CAS bereits existiert
THEN wird keine Dublette angelegt, sondern die bestehende referenziert

GIVEN ein Produkt mit CAS-Nummer
WHEN ein SDS mit derselben CAS in der globalen SDS-Bibliothek existiert
THEN wird `Product.sds_revision` automatisch verknüpft (kein Copy!)

GIVEN mehrere Mandanten
WHEN Mandant A ein Kataster importiert
THEN sieht Mandant B weder Produkte noch Verwendungen (Mandantentrennung)
AND Mandant B sieht die gleichen `GlobalSubstance`-Stammdaten (globale Ebene)

GIVEN ein Handelsprodukt an Standort X
WHEN der Sicherheitsbeauftragte das Produkt einem weiteren Standort Y zuordnet
THEN entsteht eine neue `SubstanceUsage`-Row (nicht eine Kopie des Produkts)

GIVEN eine Excel mit R-Sätzen (Altdaten) statt H-Sätzen
WHEN der Import durchgeführt wird
THEN werden R-Sätze via `RPhrase`-Mapping zu H-Sätzen konvertiert
AND der Import-Report zeigt die Konvertierung an

### Normalisierung (technisch)

GIVEN das Datenmodell
THEN gilt: Kein Feld existiert doppelt in zwei Tabellen (3NF)
AND `GlobalSubstance` hat kein `tenant_id` (globale Fakten)
AND `SubstanceUsage` hat `tenant_id` (mandantenspezifisch)
AND Lagerklasse steht auf `SubstanceUsage`, nicht auf `Product` (standortabhängig)
AND H-/P-Sätze sind M:N-Relationen (nicht CSV-Strings)
AND Herstelleradresse steht in `Party`, nicht in `Product`

## Referenzen

- **Beispiel-Excel**: Gefahrstoffkataster Werk Freiburg (145 Stoffe, 7 Standorte, 53 Spalten)
- **Regulatorisch**: GefStoffV §6 (Gefahrstoffverzeichnis), TRGS 400, TRGS 510 (Zusammenlagerung)
- **Bestehende Module**: UC-003 (SDS Upload), global_sds (SDS-Bibliothek)
- **Standortkürzel** (aus Excel): A=Offenburg, B=St. Ingbert, C=Heddesheim, D=Bahlingen, E=Ellhofen, F=Kempf Offenburg, G=Kempf Bahlingen
