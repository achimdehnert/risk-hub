# Changelog — Risk-Hub (Schutztat)

## [Unreleased] — 2026-02-19

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
