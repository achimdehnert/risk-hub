# REFLEX Audit — Explosionsschutz Modul

**Datum:** 2026-04-16
**Umgebung:** localhost:8001 (docker-compose)
**Branch:** main
**Auditor:** Cascade (AI)

---

## Zusammenfassung

| Kategorie | Ergebnis |
|-----------|----------|
| Views getestet | 20 von ~20 HTML-Routen |
| Kritische Bugs | 1 (tenant_id beim Area-Create ohne User.tenant_id) |
| UX-Issues | 3 |
| Console Errors | 1 (favicon 404 — minor) |
| Gesamtbewertung | **GUT** — Modul ist funktional und professionell |

---

## Views Audit Matrix

| # | URL | View | Status | Notizen |
|---|-----|------|--------|---------|
| 1 | `/ex/` | HomeView | ✅ OK | Dashboard mit Stats, Quick-Links, Regelwerke, Maßnahmenkatalog |
| 2 | `/ex/areas/` | AreaListView | ✅ OK | Suchfeld, Filter, leerer Zustand korrekt |
| 3 | `/ex/areas/create/` | AreaCreateView | ⚠️ BUG | IntegrityError wenn User.tenant_id=None (siehe F-01) |
| 4 | `/ex/areas/2/` | AreaDetailView | ✅ OK | Stats, Details, Konzepte, Betriebsmittel |
| 5 | `/ex/areas/2/edit/` | AreaEditView | ✅ OK | Vorausgefüllt, speichert korrekt |
| 6 | `/ex/areas/2/brandschutz/` | AreaBrandschutzView | ✅ OK | DXF-Upload empty state |
| 7 | `/ex/concepts/` | ConceptListView | ✅ OK | Card-Layout, Filter, Zonencount |
| 8 | `/ex/concepts/new/` | ConceptCreateView | ✅ OK | Area-Dropdown, Gefahrstoff-Feld |
| 9 | `/ex/concepts/1/` | ConceptDetailView | ✅ OK | Tabs: Zonen, Maßnahmen, Dokumente, Vorlagen |
| 10 | `/ex/concepts/1/edit/` | ConceptEditView | ✅ OK | Vorausgefüllt |
| 11 | `/ex/concepts/1/validate/` | ConceptValidateView | ✅ OK | Status → "In Prüfung", Success-Banner |
| 12 | `/ex/concepts/1/preview/` | ConceptPreviewView | ✅ OK | Professionelles Explosionsschutzdokument-Layout |
| 13 | `/ex/concepts/1/zone-map/` | ZoneMapView | ✅ OK | Zonenvisualisierung mit Legende und Sidebar |
| 14 | `/ex/equipment/` | EquipmentListView | ✅ OK | Suchfeld, Filter, leerer Zustand |
| 15 | `/ex/equipment/create/` | EquipmentCreateView | ✅ OK | Bereich, Zone, Gerätetyp, Seriennummer |
| 16 | `/ex/tools/` | ToolsView | ✅ OK | 3 Tools: Zonenberechnung, Geräteprüfung, Lüftungsanalyse |
| 17 | `/ex/doc-templates/` | template_list | ✅ OK | PDF hochladen, Leere Vorlage |
| 18 | HTMX: Zone hinzufügen | HtmxAddZoneView | ✅ OK | Inline-Add ohne Page Reload |
| 19 | Export Dropdown | PDF/DOCX/GAEB | ✅ OK | 4 Formate: PDF, DOCX, GAEB Excel, GAEB XML |
| 20 | HTMX Tabs | Zonen/Maßnahmen/Dokumente/Vorlagen | ✅ OK | Alle Tabs laden korrekt |

---

## Findings

### F-01: IntegrityError bei Area-Create ohne User.tenant_id (KRITISCH)

- **Severity:** 🔴 Critical
- **View:** `AreaCreateView.post()` (`template_views.py:473`)
- **Symptom:** `IntegrityError: null value in column "tenant_id" of relation "ex_area"`
- **Root Cause:** `request.tenant_id` is `None` weil die Tenant-Middleware den User nicht auflösen kann, wenn `User.tenant_id` nicht gesetzt ist. Die View setzt `area.tenant_id = tenant_id` (Zeile 478), aber das ist `None`.
- **Betroffene Views:** Alle Create-Views die `request.tenant_id` verwenden
- **Workaround:** `User.tenant_id` muss beim User-Setup gesetzt werden
- **Fix-Vorschlag:** Guard in den Create-Views: wenn `tenant_id is None` → 400/403 statt IntegrityError

### F-02: Gemischte DE/EN Labels in Concept-Detail-Tabs (UX)

- **Severity:** 🟡 Medium
- **Views:** Concept Detail — Zonen-Tab, Maßnahmen-Tab, Dokumente-Tab
- **Symptom:** Form-Labels sind Englisch ("Zone type", "Name", "Description", "Justification", "Category", "Title", "Due date", "Document type", "File", "Issued by"), während Buttons und Überschriften Deutsch sind
- **Fix-Vorschlag:** Alle Form-Labels auf Deutsch übersetzen (Zonentyp, Bezeichnung, Beschreibung, Begründung, Kategorie, Titel, Fälligkeitsdatum, Dokumenttyp, Datei, Ausgestellt von)

### F-03: Zonen-Counter nicht aktualisiert nach HTMX-Add (UX)

- **Severity:** 🟢 Low
- **View:** ConceptDetailView — Stats-Karten
- **Symptom:** Stats-Karte "Zonen: 0" bleibt nach Zone hinzufügen stehen (erst nach Page-Reload korrekt "1")
- **Fix-Vorschlag:** HTMX-Response sollte auch den Stats-Counter partial updaten (hx-swap-oob)

### F-04: Standort-ID zeigt rohe UUID (UX)

- **Severity:** 🟢 Low
- **View:** AreaDetailView
- **Symptom:** "Standort-ID: 05fd8441-817b-4d7a-adbd-52b62c2b2f34" — dem Endnutzer nicht hilfreich
- **Fix-Vorschlag:** Entweder den Organisationsnamen anzeigen oder das Feld für Nicht-Admins ausblenden

---

## Docker-Compose Fixes (während Setup entdeckt)

| Fix | Beschreibung |
|-----|-------------|
| `env_file: .env.local` | `.env.example` hat `localhost` als DB-Host, Compose braucht `db` |
| `command: ["web"]` | Dockerfile hat `ENTRYPOINT`, Compose hatte `/entrypoint.sh web` → doppelt |
| Port `5436:5432` | Port 5434 war bereits belegt |

---

## Nicht getestet (Out of Scope)

- DXF-Upload (benötigt echte DXF-Datei)
- IFC-Upload (benötigt echte IFC-Datei)
- PDF/DOCX Export Download (benötigt weasyprint/python-docx Runtime)
- LLM-Prefill (benötigt LLM Gateway)
- Inspection-Create (benötigt Equipment-Datensatz)
- GAEB Export (benötigt Maßnahmen-Daten)

---

## Screenshots

Alle Screenshots unter `.playwright-mcp/reflex-audit-*.png`
