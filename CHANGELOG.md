# Changelog — Risk-Hub (Schutztat)

## [Unreleased]

### Added
- tenancy: **Facility-Modell** (Produktionsstätten) — neue Hierarchieebene `Organization → Site → Facility`
  - `FacilityType` choices: Produktion, Lager, Labor, Büro, Werkstatt, Sonstiges
  - CRUD-Services, Forms, Views, URLs (`/tenants/sites/<pk>/facilities/`)
  - Templates: `facility_list.html`, `facility_form.html`
  - Optionaler `facility`-FK in `SubstanceUsage`, `SiteInventoryItem`, `KatasterRevision`
- dashboard: Standorte-KPI-Karte immer sichtbar (auch ohne Module)
- tenancy: "Produktionsstätten"-Link pro Standort-Karte in `site_list.html`

### Removed
- projects: `DocumentTemplate`-Modell + DB-Tabelle `project_doc_template` entfernt (war toter Code, 0 Einträge)
  - `OutputDocument.template`-FK (wurde intern nie gesetzt — immer NULL)
  - 5 CRUD-Views (`template_list/create/upload/edit/delete`) + URL-Patterns
  - Services: `create_template`, `update_template`, `delete_template`, `get_document_templates`
  - `DocumentTemplateAdmin`, `DocumentTemplateFactory`

### Fixed
- ruff: 12 Lint-Fehler automatisch behoben (F401, I001, UP037 across 8 files)
- tenancy/services.py: falsche Forward-Reference-Annotationen in Facility-Services entfernt

### Known Lint Issues (pre-existing, nicht durch diese Session eingeführt)
- `explosionsschutz/api.py:191` E741 — ambiguous variable name `l`
- `explosionsschutz/template_views.py:1337` F821 — `logger` undefiniert
- `substances/services/sds_parser.py` B007 — unused loop variables (2x)

### Previous [Unreleased] additions (noch nicht released)
- global-sds: Vollextraktion + PubChem-Anreicherung + JSON-View
- explosionsschutz: Schritt 6 Zusammenführen — `ConceptFinalizeView` + `finalize.html`
- explosionsschutz: Vorlagen-Tab zeigt `doc_templates.DocumentTemplate` (externe Vorlagen)
- explosionsschutz: KI-Accept für `chapter=measures` erstellt `ProtectionMeasure`-Objekte (Parser + Apply)
- doc_templates: Löschen-Button neben Speichern im Edit-Formular (Template-Override)
- test: `tests/utils/html_assertions.py` — `assert_valid_html()` für nested-form, hx-target Checks
- test: `tests/completeness/test_html_structure.py` — 232 HTML-Struktur-Tests für alle Templates

### Previous [Unreleased] fixes
- training: `signed_at` bei present-Status setzen
- global-sds: H/P-Statements + Pictogramme in Pipeline persistieren
- explosionsschutz: `IntegrityError` bei Konzept-Erstellung — `project` nullable gemacht
- explosionsschutz: `HtmxAddMeasureView` zeigt Formfehler statt stiller Ignorierung
- risk: `hazard_form.html`, `measure_form.html`, `substitution_form.html` — nested `<form>` entfernt
- doc_templates: nested `<form>` in `edit.html` — Aktionen außerhalb Haupt-Form, HTML5 `form=`-Attribut
- projects: `sync_completion` erfordert `action_code` als erstes Argument
- projects: Vorlagen-Picker + template_list zeigen `doc_templates.DocumentTemplate`

## [0.1.0] — 2026-04-23

### Added
- SDS OCR-Fallback: `PDFExtractor(ocr_fallback=True)` mit Tesseract für gescannte PDFs
- `tesseract-ocr` + `poppler-utils` im Dockerfile, `iil-ingest[pdf,ocr]` als Dependency
- Lokaler Dev-Server via `make dev` (→ `platform/scripts/dev.sh`)
- global-sds: erweiterte Parser + GHS-Datenlader + Detail-Template

### Changed
- ADR-170: gesamte PDF-Extraktion auf `iil-ingest PDFExtractor` migriert (sds_parser, ai_extraction, substance_import, pdf_utils, explosionsschutz)
- global-sds: `sds_sections` + `raw_text_length` im revision_detail Context

### Fixed
- sds-parser: 5 Regex-Bugs + EU Wert-Format-Extraktion + LLM-Fallback
- sds-ui: SDS-Sektionen nach Key sortiert (01→16)
- dashboard: `module_shop:catalogue` URL mit Conditional gegen NoReverseMatch

## [0.0.9] — 2026-02-19

### Added

#### Datenpannen-Workflow (Art. 33 DSGVO)
- Neues `BreachStatus` TextChoices + `BREACH_TRANSITIONS` State-Machine im `Breach`-Model
- 5-Schritte-Workflow: Gemeldet → DSB kontaktiert → Behörde benachrichtigt → Behebung läuft → Behoben
- `breach_workflow.py`: E-Mail-Versand je Workflow-Schritt
- 5 HTML-E-Mail-Templates (`templates/dsb/emails/breach_0[1-5]_*.html`)
- Views: `breach_list`, `breach_create`, `breach_detail`, `breach_advance`
- Templates: `breach_form.html`, `breach_detail.html`, `breach_list.html` (mit Status, klickbaren Zeilen)
- URLs: `/dsb/breaches/`, `/dsb/breaches/new/`, `/dsb/breaches/<pk>/`, `/dsb/breaches/<pk>/advance/`

#### Löschungsworkflow (Art. 17 DSGVO)
- Neues Model `DeletionRequest` mit 7-Schritte-Status-Machine
- `deletion_workflow.py`: E-Mail-Versand je Workflow-Schritt
- 6 HTML-E-Mail-Templates (`templates/dsb/emails/deletion_0[1-6]_*.html`)
- Views: `deletion_request_list`, `deletion_request_create`, `deletion_request_detail`, `deletion_request_advance`
- Templates: `deletion_request_form.html`, `deletion_request_detail.html`, `deletion_request_list.html`
- URLs: `/dsb/loeschantraege/`, `/dsb/loeschantraege/neu/`, `/dsb/loeschantraege/<pk>/`, `/dsb/loeschantraege/<pk>/advance/`
- Migration `0003_add_deletion_request`

#### Dokumentenarchiv (PDF-Upload)
- Neues Model `DsbDocument` — generisch verknüpfbar mit AVV, VVT, TOM, Datenpanne, Löschantrag, Mandat
- Felder: `file`, `title`, `description`, `document_date`, `original_filename`, `file_size`, `mime_type`
- `MEDIA_ROOT`/`MEDIA_URL` in Settings konfiguriert (max. 20 MB)
- Views: `document_list`, `document_upload`, `document_download`, `document_delete`
- Templates: `document_list.html` (mit Filter), `document_upload.html` (Drag & Drop)
- URLs: `/dsb/dokumente/`, `/dsb/dokumente/upload/`, `/dsb/dokumente/<pk>/download/`, `/dsb/dokumente/<pk>/delete/`
- Dokument-Sektionen in `breach_detail.html` und `deletion_request_detail.html`
- Migration `0005_add_dsb_document`

#### AVV CSV-Import
- Dedizierter `import_avv()` Parser in `import_csv.py`
- CSV-Format: `Partner;Rolle;Gegenstand;Status;Gueltig_ab;Gueltig_bis;Unterauftragsverarbeiter;Notizen`
- CSV-Vorlage-Download (`?template=1`)
- View `avv_import` + Template `avv_import.html` mit Drag & Drop
- URL: `/dsb/avv/import/`
- `detect_csv_type()` erkennt jetzt auch AVV-Header

#### DSB Dashboard
- Prominente „Neu erfassen" Aktionskarten für alle 7 Einstiegspunkte
- Links zu: VVT, TOM, TOM-Org, AVV, Datenpanne, Löschantrag, Mandat

### Changed
- AVV-Liste: Import-Button zeigt jetzt auf dedizierten AVV-Import, Zeilen klickbar
- Mandat-Dropdown: Auto-Select wenn nur ein Mandat vorhanden (`_apply_mandate_autoselect`)
- TOM-Liste: Zeilen klickbar (→ Edit-View)
- `dsb_components.py`: `abs_val` Filter hinzugefügt

---

## [0.9.0] — 2026-01-xx

- ADR-046 Phase 2: Cleanup und Dokumentation
- Secrets-Management (ADR-045)
- CSV-Import für VVT und TOM
