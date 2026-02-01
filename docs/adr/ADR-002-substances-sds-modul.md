# ADR-002: Substances/SDS-Modul (Gefahrstoffmanagement)

| Status | Datum | Entscheidungsträger |
|--------|-------|---------------------|
| **IMPLEMENTED** | 2026-02-01 | Tech Lead |

## Kontext

Die Schutzbar-Plattform benötigt ein zentrales **Sicherheitsdatenblatt-Register (SDS)** als Kernmodul für alle EHS-Funktionalitäten. Das SDS-Modul dient als "Domain Anchor" für:

- Gefährdungsbeurteilung Gefahrstoffe (GBU)
- Explosionsschutz (ATEX) - bereits implementiert
- Lagerung nach TRGS 510
- Betriebsanweisungen
- Unterweisungen

### Rechtliche Anforderungen

| Vorschrift | Anforderung |
|------------|-------------|
| **GefStoffV §6** | Gefahrstoffverzeichnis führen |
| **GefStoffV §14** | 40 Jahre Aufbewahrung (CMR-Stoffe) |
| **TRGS 400** | Informationsermittlung (H-/P-Sätze) |
| **TRGS 510** | Lagerklassen-Zuordnung |
| **CLP-Verordnung** | GHS-Kennzeichnung |
| **REACH Art. 31** | SDS-Versionsverwaltung |

## Entscheidung

Implementierung eines `substances`-Moduls mit folgender Architektur:

### Kernentitäten

```
┌─────────────────────────────────────────────────────────────────┐
│                    SUBSTANCES MODULE                             │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  Party (Hersteller/Lieferant)                                   │
│    └── Substance (Gefahrstoff)                                  │
│          ├── Identifier (CAS, UFI, EC, GTIN)                    │
│          ├── SdsRevision (Versionierte Sicherheitsdatenblätter) │
│          │     ├── SdsClassification (Signalwort, Notizen)      │
│          │     ├── SdsHazardStatement (H-Sätze)                 │
│          │     ├── SdsPrecautionaryStatement (P-Sätze)          │
│          │     └── SdsPictogram (GHS01-GHS09)                   │
│          └── SiteInventoryItem (Standort-Inventar)              │
│                                                                  │
│  Referenztabellen (Global):                                      │
│    - HazardStatementRef (H200-H420)                             │
│    - PrecautionaryStatementRef (P101-P502)                      │
│    - PictogramRef (GHS01-GHS09)                                 │
│    - StorageClassRef (LGK 1-13)                                 │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### Verzeichnisstruktur

```
src/substances/
├── models/
│   ├── substance.py      # Substance, Party, Identifier
│   ├── sds.py            # SdsRevision, Classification, Statements
│   ├── inventory.py      # SiteInventoryItem
│   └── reference.py      # H-/P-Sätze Referenztabellen
├── services/
│   ├── substance_service.py
│   ├── sds_service.py
│   ├── inventory_service.py
│   └── export_service.py
├── views/
├── templates/substances/
├── exports/
│   ├── hazard_register_excel.py
│   └── sds_compliance_pdf.py
└── management/commands/
    ├── seed_h_statements.py
    ├── seed_p_statements.py
    └── seed_pictograms.py
```

### Workflow

```
┌─────────┐     ┌──────────┐     ┌──────────┐     ┌──────────┐
│  DRAFT  │────►│ PENDING  │────►│ APPROVED │────►│ ARCHIVED │
│         │     │  REVIEW  │     │          │     │          │
└─────────┘     └──────────┘     └──────────┘     └──────────┘
    │                │                                   ▲
    │                │                                   │
    └────────────────┴───────────────────────────────────┘
                         (Neue Revision)
```

### Integration mit Explosionsschutz

```python
# src/explosionsschutz/models.py - ExplosionConcept
class ExplosionConcept(models.Model):
    # Bestehend:
    substance_id = models.UUIDField(...)
    substance_name = models.CharField(...)  # Cache
    
    # NEU: Direkter FK wenn substances-Modul existiert
    substance = models.ForeignKey(
        "substances.Substance",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="explosion_concepts"
    )
    
    @property
    def ex_relevant_data(self) -> dict:
        """Ex-relevante Daten aus aktuellem SDS"""
        if self.substance and self.substance.current_sds:
            sds = self.substance.current_sds
            return {
                "flash_point": sds.flash_point_c,
                "ignition_temp": sds.ignition_temperature_c,
                "explosion_limits": {
                    "lower": sds.lower_explosion_limit,
                    "upper": sds.upper_explosion_limit,
                },
                "temperature_class": sds.temperature_class,
                "explosion_group": sds.explosion_group,
            }
        return {}
```

### API-Endpunkte

| Methode | Pfad | Beschreibung |
|---------|------|--------------|
| GET | `/api/substances/` | Liste Gefahrstoffe |
| POST | `/api/substances/` | Neuer Gefahrstoff |
| GET | `/api/substances/{id}/` | Detail |
| PUT | `/api/substances/{id}/` | Update |
| GET | `/api/substances/{id}/sds/` | SDS-Revisionen |
| POST | `/api/substances/{id}/sds/upload/` | SDS hochladen |
| POST | `/api/substances/{id}/sds/{rev}/approve/` | SDS freigeben |
| GET | `/api/inventory/` | Standort-Inventar |
| GET | `/api/exports/hazard-register/` | Gefahrstoffverzeichnis |

### Permissions (RBAC)

| Permission | Beschreibung |
|------------|--------------|
| `substances.view` | Stoffe ansehen |
| `substances.create` | Stoffe anlegen |
| `substances.edit` | Stoffe bearbeiten |
| `substances.delete` | Stoffe löschen |
| `substances.sds.upload` | SDS hochladen |
| `substances.sds.approve` | SDS freigeben |
| `substances.inventory.manage` | Inventar verwalten |
| `substances.export` | Exporte erstellen |

## Alternativen

### A) Minimaler Ansatz (abgelehnt)
Nur einfache Stoffliste ohne SDS-Versionierung. Erfüllt nicht GefStoffV §14.

### B) Externer Service (abgelehnt)
Integration mit externem SDS-Provider. Zu teuer, Vendor Lock-in.

### C) **Gewählt: Vollständiges Modul**
Eigenentwicklung mit allen rechtlichen Anforderungen.

## Konsequenzen

### Positiv
- ✅ Rechtskonforme Gefahrstoffverwaltung
- ✅ Integration mit Explosionsschutz-Modul
- ✅ Grundlage für GBU, Betriebsanweisungen
- ✅ Multi-Tenant-fähig
- ✅ 40-Jahre-Aufbewahrung für CMR-Stoffe

### Negativ
- ⚠️ Entwicklungsaufwand: 6-8 Wochen (4 Sprints)
- ⚠️ Pflege der Referenzdaten (H-/P-Sätze)
- ⚠️ Storage-Kosten für PDF-Dateien

## Implementierungsplan

| Sprint | Deliverable | Story Points |
|--------|-------------|--------------|
| 1 | Models, Migrations, Admin | 13 |
| 2 | Services, SDS-Upload | 21 |
| 3 | Workflow, Inventar, Views | 21 |
| 4 | Exports, Integration Ex-Schutz | 13 |

## Implementierungsstatus (2026-02-01)

### ✅ Implementiert

| Komponente | Status | Details |
|------------|--------|---------|
| **Models** | ✅ | Party, Substance, Identifier, SdsRevision, SiteInventoryItem |
| **Referenztabellen** | ✅ | H-Sätze, P-Sätze, Piktogramme, Lagerklassen |
| **REST API** | ✅ | ViewSets für alle Entitäten |
| **HTML Views** | ✅ | Dashboard, Listen, Detail, Formulare |
| **SDS Parser** | ✅ | PDF-Text-Extraktion mit pdfplumber + PyPDF2 |
| **Ex-Integration** | ✅ | ExIntegrationService für Explosionsschutz |

### SDS Parser Service

```python
# src/substances/services/sds_parser.py
class SdsParserService:
    """Extrahiert Daten aus Sicherheitsdatenblättern (PDF)"""
    
    def parse_pdf(self, pdf_file) -> SdsParseResult:
        # Extrahiert:
        # - H-Sätze (H200-H420)
        # - P-Sätze (P101-P502)
        # - GHS-Piktogramme
        # - Signalwort (Gefahr/Achtung)
        # - Flammpunkt
        # - Zündtemperatur
        # - Explosionsgrenzen (UEG/OEG)
```

### URL-Konfiguration

```python
# HTML Views: /substances/
app_name = "substances"  # html_urls.py

# API Endpoints: /api/substances/
app_name = "substances-api"  # urls.py
```

### Tests

- **52 Unit-Tests** für Models und Services
- **14 Parser-Tests** für SDS-Extraktion (deutsche Formate)

## Referenzen

- [Schutzbar_SDS_Implementierungskonzept.md](../../concepts/Schutzbar_SDS_Implementierungskonzept.md)
- [ADR-001: Explosionsschutz-Modul](./ADR-001-explosionsschutz-modul-v4.md)
- TRGS 400, 510
- GefStoffV §6, §14
- CLP-Verordnung (EG) Nr. 1272/2008
