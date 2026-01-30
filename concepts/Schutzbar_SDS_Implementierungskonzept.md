# Schutzbar SDS – Implementierungskonzept

**Version:** 1.0  
**Stand:** 2026-01-28  
**Modul:** `substances` (Sicherheitsdatenblatt-/Gefahrstoffmanagement)  
**Stack:** Django 5.x + HTMX + Postgres 16 + S3/MinIO  
**Zielgruppe:** Entwicklungsteam, Technische Reviewer

---

## Inhaltsverzeichnis

1. [Executive Summary](#1-executive-summary)
2. [Projektübersicht](#2-projektübersicht)
3. [Technische Architektur](#3-technische-architektur)
4. [Datenmodell](#4-datenmodell)
5. [Service Layer](#5-service-layer)
6. [RBAC & Permissions](#6-rbac--permissions)
7. [API & Views](#7-api--views)
8. [UI/UX Design](#8-uiux-design)
9. [Export-Module](#9-export-module)
10. [Testing-Strategie](#10-testing-strategie)
11. [Implementierungsplan](#11-implementierungsplan)
12. [Deployment & Operations](#12-deployment--operations)
13. [Anhänge](#13-anhänge)

---

## 1. Executive Summary

### 1.1 Projektziel

Entwicklung eines **Sicherheitsdatenblatt-Registers (SDS)** als MVP-Kernmodul der Schutzbar EHS-Plattform. Das Modul dient als "Domain Anchor" für alle weiteren EHS-Funktionalitäten.

### 1.2 Kernergebnisse

| Deliverable | Beschreibung | Timeline |
|-------------|--------------|----------|
| Gefahrstoff-Stammdaten | CRUD für Stoffe, Kennungen, Parteien | Sprint 1-2 |
| SDS-Verwaltung | Upload, Versionierung, Klassifikation | Sprint 2-3 |
| Standort-Inventar | Mengen, Lagerorte pro Site | Sprint 3 |
| Compliance-Exports | Gefahrstoffverzeichnis (Excel/PDF) | Sprint 4 |
| Freigabe-Workflow | Draft → Approved → Archived | Sprint 3 |

### 1.3 Technische Kennzahlen

```
┌─────────────────────────────────────────────────────────────────┐
│                    MVP SCOPE METRIKEN                           │
├─────────────────────────────────────────────────────────────────┤
│  Entwicklungszeit:        6-8 Wochen (4 Sprints)               │
│  Django Models:           10 Entitäten                          │
│  Service Functions:       ~20 Use Cases                         │
│  Views/Endpoints:         ~25 URLs                              │
│  Templates:               ~15 HTMX-fähig                        │
│  Test Coverage Ziel:      ≥80%                                  │
└─────────────────────────────────────────────────────────────────┘
```

---

## 2. Projektübersicht

### 2.1 Fachlicher Kontext

```
┌─────────────────────────────────────────────────────────────────┐
│                 SDS ALS "DOMAIN ANCHOR"                         │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│                      ┌─────────────┐                            │
│                      │     SDS     │                            │
│                      │  (Zentral)  │                            │
│                      └──────┬──────┘                            │
│                             │                                   │
│         ┌───────────────────┼───────────────────┐              │
│         │                   │                   │              │
│         ▼                   ▼                   ▼              │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐        │
│  │    GBU      │    │   Lager     │    │ Betriebsan- │        │
│  │ Gefahrstoff │    │  TRGS 510   │    │   weisung   │        │
│  └─────────────┘    └─────────────┘    └─────────────┘        │
│         │                   │                   │              │
│         ▼                   ▼                   ▼              │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐        │
│  │ Ex-Schutz   │    │  Audits     │    │Unterweisung │        │
│  │   ATEX      │    │             │    │             │        │
│  └─────────────┘    └─────────────┘    └─────────────┘        │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### 2.2 Rechtliche Anforderungen

| Vorschrift | Anforderung | SDS-Modul erfüllt |
|------------|-------------|-------------------|
| **GefStoffV §6** | Gefahrstoffverzeichnis | ✅ Kernfunktion |
| **GefStoffV §14** | 40 Jahre Aufbewahrung (CMR) | ✅ Retention-Policy |
| **TRGS 400** | Informationsermittlung | ✅ H-/P-Sätze strukturiert |
| **TRGS 510** | Lagerkennzeichnung | ✅ Lagerklassen |
| **CLP-Verordnung** | GHS-Kennzeichnung | ✅ Piktogramme, Signalwörter |
| **REACH Art. 31** | SDS vom Lieferanten | ✅ Versionsverwaltung |

### 2.3 Abgrenzung MVP

**Im Scope:**
- ✅ Gefahrstoff-Stammdaten (CRUD)
- ✅ SDS-Upload mit Versionierung
- ✅ Strukturierte Klassifikation (H-/P-Sätze, Piktogramme)
- ✅ Standort-Inventar (Mengen, Lagerorte)
- ✅ Freigabe-Workflow
- ✅ Suche & Filter
- ✅ Excel/PDF-Exports

**Außerhalb Scope (spätere Phasen):**
- ❌ Gefährdungsbeurteilung Gefahrstoffe
- ❌ Betriebsanweisung-Generator
- ❌ Explosionsschutz-Bewertung
- ❌ ERP-Integration
- ❌ OCR/AI-Extraktion aus PDFs
- ❌ Substitutionsprüfung

---

## 3. Technische Architektur

### 3.1 Systemarchitektur

```
┌─────────────────────────────────────────────────────────────────┐
│                      SCHUTZBAR PLATFORM                         │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │                    PRESENTATION LAYER                     │  │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐      │  │
│  │  │   HTMX      │  │   Django    │  │   Static    │      │  │
│  │  │   Views     │  │  Templates  │  │   Assets    │      │  │
│  │  └─────────────┘  └─────────────┘  └─────────────┘      │  │
│  └──────────────────────────────────────────────────────────┘  │
│                              │                                  │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │                   APPLICATION LAYER                       │  │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐      │  │
│  │  │  Services   │  │   Queries   │  │  Commands   │      │  │
│  │  │ (Use Cases) │  │ (Read-only) │  │   (DTOs)    │      │  │
│  │  └─────────────┘  └─────────────┘  └─────────────┘      │  │
│  └──────────────────────────────────────────────────────────┘  │
│                              │                                  │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │                     DOMAIN LAYER                          │  │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐      │  │
│  │  │   Models    │  │  Validators │  │   Domain    │      │  │
│  │  │  (Entities) │  │             │  │   Events    │      │  │
│  │  └─────────────┘  └─────────────┘  └─────────────┘      │  │
│  └──────────────────────────────────────────────────────────┘  │
│                              │                                  │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │                 INFRASTRUCTURE LAYER                      │  │
│  │  ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐        │  │
│  │  │Postgres │ │   S3    │ │  Audit  │ │ Outbox  │        │  │
│  │  │   16    │ │ (MinIO) │ │ Events  │ │ Worker  │        │  │
│  │  └─────────┘ └─────────┘ └─────────┘ └─────────┘        │  │
│  └──────────────────────────────────────────────────────────┘  │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### 3.2 Django App Struktur

```
src/
├── substances/                      # Hauptmodul
│   ├── __init__.py
│   ├── apps.py                     # AppConfig
│   ├── models/                     # Datenmodell (aufgeteilt)
│   │   ├── __init__.py
│   │   ├── substance.py            # Substance, Party, Identifier
│   │   ├── sds.py                  # SdsRevision, Classification
│   │   ├── inventory.py            # SiteInventoryItem
│   │   └── reference.py            # H-/P-Sätze Referenztabellen
│   ├── services/                   # Business Logic
│   │   ├── __init__.py
│   │   ├── substance_service.py    # Substance CRUD
│   │   ├── sds_service.py          # SDS Upload/Classify/Approve
│   │   ├── inventory_service.py    # Inventar-Verwaltung
│   │   └── export_service.py       # Export-Jobs
│   ├── queries/                    # Read-Only Queries
│   │   ├── __init__.py
│   │   ├── substance_queries.py
│   │   ├── inventory_queries.py
│   │   └── export_queries.py
│   ├── commands/                   # Command DTOs
│   │   ├── __init__.py
│   │   └── commands.py
│   ├── permissions.py              # RBAC Codes
│   ├── validators.py               # Validierungslogik
│   ├── views/                      # HTMX Views
│   │   ├── __init__.py
│   │   ├── substance_views.py
│   │   ├── sds_views.py
│   │   ├── inventory_views.py
│   │   └── export_views.py
│   ├── urls.py                     # URL-Routing
│   ├── forms.py                    # Django Forms
│   ├── admin.py                    # Admin-Interface
│   ├── exports/                    # Export-Generatoren
│   │   ├── __init__.py
│   │   ├── hazard_register_excel.py
│   │   └── sds_compliance_pdf.py
│   ├── templates/
│   │   └── substances/
│   │       ├── base_substances.html
│   │       ├── substance_list.html
│   │       ├── substance_detail.html
│   │       ├── substance_form.html
│   │       ├── sds_upload.html
│   │       ├── sds_classify.html
│   │       ├── inventory_list.html
│   │       ├── inventory_form.html
│   │       ├── export_modal.html
│   │       └── partials/
│   │           ├── substance_table.html
│   │           ├── substance_row.html
│   │           ├── sds_card.html
│   │           ├── classification_badges.html
│   │           ├── pictogram_icons.html
│   │           ├── inventory_table.html
│   │           └── search_form.html
│   ├── static/
│   │   └── substances/
│   │       ├── css/
│   │       │   └── substances.css
│   │       ├── js/
│   │       │   └── substances.js
│   │       └── img/
│   │           └── pictograms/     # GHS01-GHS09 SVGs
│   ├── management/
│   │   └── commands/
│   │       ├── __init__.py
│   │       ├── seed_h_statements.py
│   │       ├── seed_p_statements.py
│   │       ├── seed_pictograms.py
│   │       └── seed_demo_substances.py
│   └── tests/
│       ├── __init__.py
│       ├── test_models.py
│       ├── test_services.py
│       ├── test_queries.py
│       ├── test_views.py
│       └── factories.py            # Test-Factories
```

### 3.3 Abhängigkeiten

```
┌─────────────────────────────────────────────────────────────────┐
│                    MODULE DEPENDENCIES                          │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  substances ──────┬───────► tenancy (Organization, Site)       │
│       │           │                                             │
│       │           ├───────► identity (User)                    │
│       │           │                                             │
│       │           ├───────► permissions (RBAC, Scope)          │
│       │           │                                             │
│       │           ├───────► documents (DocumentVersion, S3)    │
│       │           │                                             │
│       │           ├───────► audit (AuditEvent)                 │
│       │           │                                             │
│       │           └───────► outbox (OutboxMessage)             │
│       │                                                         │
│       └───────────────────► reporting (ExportJob) [optional]   │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## 4. Datenmodell

### 4.1 ER-Diagramm

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                              SUBSTANCES MODULE                                   │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                  │
│  ┌─────────────────┐         ┌─────────────────┐                               │
│  │      Party      │         │    Substance    │                               │
│  ├─────────────────┤         ├─────────────────┤                               │
│  │ PK id           │◄───────┐│ PK id           │                               │
│  │ FK tenant_id    │        ││ FK tenant_id    │                               │
│  │    party_type   │        │├─────────────────┤                               │
│  │    name         │        ││    name         │                               │
│  │    email        │        ││    trade_name   │                               │
│  │    phone        │        ││    description  │                               │
│  │    address      │        ││    status       │                               │
│  └─────────────────┘        ││    storage_class│                               │
│                             ││    is_cmr       │                               │
│                             ││ FK manufacturer │───────┘                       │
│                             ││ FK supplier_id  │───────┘                       │
│                             │└────────┬────────┘                               │
│                             │         │                                         │
│                             │         │ 1:n                                     │
│                             │         │                                         │
│  ┌─────────────────┐        │         │        ┌─────────────────┐             │
│  │   Identifier    │◄───────┘         └───────►│   SdsRevision   │             │
│  ├─────────────────┤                           ├─────────────────┤             │
│  │ PK id           │                           │ PK id           │             │
│  │ FK tenant_id    │                           │ FK tenant_id    │             │
│  │ FK substance_id │                           │ FK substance_id │             │
│  │    id_type      │                           │ FK doc_version  │             │
│  │    id_value     │                           │    revision_num │             │
│  └─────────────────┘                           │    revision_date│             │
│                                                │    status       │             │
│                                                │    approved_by  │             │
│                                                │    approved_at  │             │
│                                                └────────┬────────┘             │
│                                                         │                       │
│                            ┌────────────────────────────┼────────────┐         │
│                            │                            │            │         │
│                            ▼                            ▼            ▼         │
│              ┌─────────────────┐          ┌─────────────────┐ ┌────────────┐  │
│              │SdsClassification│          │SdsHazardStatement│ │SdsPictogram│  │
│              ├─────────────────┤          ├─────────────────┤ ├────────────┤  │
│              │ PK id           │          │ PK id           │ │ PK id      │  │
│              │ FK sds_revision │          │ FK sds_revision │ │ FK sds_rev │  │
│              │    signal_word  │          │    code (H225)  │ │    code    │  │
│              │    notes        │          │    text         │ │ (GHS02)    │  │
│              └─────────────────┘          └─────────────────┘ └────────────┘  │
│                                                      │                         │
│                                                      │ (analog)                │
│                                                      ▼                         │
│                                           ┌─────────────────┐                  │
│                                           │SdsPrecautionary │                  │
│                                           │    Statement    │                  │
│                                           ├─────────────────┤                  │
│                                           │ PK id           │                  │
│                                           │ FK sds_revision │                  │
│                                           │    code (P210)  │                  │
│                                           │    text         │                  │
│                                           └─────────────────┘                  │
│                                                                                 │
│  ┌─────────────────────┐                                                       │
│  │  SiteInventoryItem  │                                                       │
│  ├─────────────────────┤                                                       │
│  │ PK id               │                                                       │
│  │ FK tenant_id        │                                                       │
│  │ FK site_id          │                                                       │
│  │ FK substance_id     │◄────────────────────────────────────────────────────  │
│  │    quantity         │                                                       │
│  │    unit             │                                                       │
│  │    state            │                                                       │
│  │    storage_location │                                                       │
│  │ FK responsible_user │                                                       │
│  └─────────────────────┘                                                       │
│                                                                                 │
│  ═══════════════════════════════════════════════════════════════════════════   │
│                           REFERENZTABELLEN (Global)                            │
│  ═══════════════════════════════════════════════════════════════════════════   │
│                                                                                 │
│  ┌─────────────────────┐     ┌─────────────────────┐                          │
│  │ HazardStatementRef  │     │PrecautionaryStmtRef │                          │
│  ├─────────────────────┤     ├─────────────────────┤                          │
│  │ PK code (H200)      │     │ PK code (P200)      │                          │
│  │    text_de          │     │    text_de          │                          │
│  │    text_en          │     │    text_en          │                          │
│  │    category         │     │    category         │                          │
│  └─────────────────────┘     └─────────────────────┘                          │
│                                                                                 │
└─────────────────────────────────────────────────────────────────────────────────┘
```

### 4.2 Django Models

```python
# src/substances/models/substance.py

import uuid
from django.db import models
from django.conf import settings


class Party(models.Model):
    """Hersteller oder Lieferant"""
    
    class PartyType(models.TextChoices):
        MANUFACTURER = "manufacturer", "Hersteller"
        SUPPLIER = "supplier", "Lieferant"
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant_id = models.UUIDField(db_index=True)
    
    party_type = models.CharField(max_length=20, choices=PartyType.choices)
    name = models.CharField(max_length=240)
    email = models.EmailField(blank=True, default="")
    phone = models.CharField(max_length=50, blank=True, default="")
    address = models.TextField(blank=True, default="")
    website = models.URLField(blank=True, default="")
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = "substances_party"
        verbose_name = "Partei"
        verbose_name_plural = "Parteien"
        constraints = [
            models.UniqueConstraint(
                fields=["tenant_id", "party_type", "name"],
                name="uq_party_tenant_type_name"
            ),
        ]
        indexes = [
            models.Index(fields=["tenant_id", "party_type"], name="ix_party_tenant_type"),
        ]
    
    def __str__(self):
        return f"{self.name} ({self.get_party_type_display()})"


class Substance(models.Model):
    """Gefahrstoff / Chemisches Produkt"""
    
    class Status(models.TextChoices):
        ACTIVE = "active", "Aktiv"
        INACTIVE = "inactive", "Inaktiv"
        ARCHIVED = "archived", "Archiviert"
    
    class StorageClass(models.TextChoices):
        """Lagerklassen nach TRGS 510"""
        SC_1 = "1", "1 - Explosive Stoffe"
        SC_2A = "2A", "2A - Verdichtete Gase"
        SC_2B = "2B", "2B - Druckgaspackungen"
        SC_3 = "3", "3 - Entzündbare Flüssigkeiten"
        SC_4_1A = "4.1A", "4.1A - Selbstzersetzliche Stoffe"
        SC_4_1B = "4.1B", "4.1B - Desensibilisierte explosive Stoffe"
        SC_4_2 = "4.2", "4.2 - Pyrophore/selbsterhitzungsfähige Stoffe"
        SC_4_3 = "4.3", "4.3 - Stoffe, die mit Wasser reagieren"
        SC_5_1A = "5.1A", "5.1A - Stark oxidierende Stoffe"
        SC_5_1B = "5.1B", "5.1B - Oxidierende Stoffe"
        SC_5_1C = "5.1C", "5.1C - Ammoniumnitrat"
        SC_5_2 = "5.2", "5.2 - Organische Peroxide"
        SC_6_1A = "6.1A", "6.1A - Brennbare akut toxische Stoffe"
        SC_6_1B = "6.1B", "6.1B - Nicht brennbare akut toxische Stoffe"
        SC_6_1C = "6.1C", "6.1C - Brennbare chronisch toxische Stoffe"
        SC_6_1D = "6.1D", "6.1D - Nicht brennbare chronisch toxische Stoffe"
        SC_6_2 = "6.2", "6.2 - Ansteckungsgefährliche Stoffe"
        SC_7 = "7", "7 - Radioaktive Stoffe"
        SC_8A = "8A", "8A - Brennbare ätzende Stoffe"
        SC_8B = "8B", "8B - Nicht brennbare ätzende Stoffe"
        SC_10 = "10", "10 - Brennbare Flüssigkeiten (nicht LGK 3)"
        SC_11 = "11", "11 - Brennbare Feststoffe"
        SC_12 = "12", "12 - Nicht brennbare Flüssigkeiten"
        SC_13 = "13", "13 - Nicht brennbare Feststoffe"
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant_id = models.UUIDField(db_index=True)
    
    # Stammdaten
    name = models.CharField(
        max_length=240, 
        help_text="Stoffname / Produktbezeichnung"
    )
    trade_name = models.CharField(
        max_length=240, 
        blank=True, 
        default="",
        help_text="Handelsname"
    )
    description = models.TextField(
        blank=True, 
        default="",
        help_text="Beschreibung / Verwendungszweck"
    )
    
    # Klassifikation
    status = models.CharField(
        max_length=20, 
        choices=Status.choices, 
        default=Status.ACTIVE
    )
    storage_class = models.CharField(
        max_length=10,
        choices=StorageClass.choices,
        blank=True,
        default="",
        help_text="Lagerklasse nach TRGS 510"
    )
    is_cmr = models.BooleanField(
        default=False,
        help_text="CMR-Stoff (karzinogen, mutagen, reproduktionstoxisch)"
    )
    
    # Beziehungen
    manufacturer = models.ForeignKey(
        Party,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="manufactured_substances",
        limit_choices_to={"party_type": "manufacturer"}
    )
    supplier = models.ForeignKey(
        Party,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="supplied_substances",
        limit_choices_to={"party_type": "supplier"}
    )
    
    # Audit
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.UUIDField(null=True, blank=True)
    
    class Meta:
        db_table = "substances_substance"
        verbose_name = "Gefahrstoff"
        verbose_name_plural = "Gefahrstoffe"
        constraints = [
            models.UniqueConstraint(
                fields=["tenant_id", "name"],
                name="uq_substance_tenant_name"
            ),
            models.CheckConstraint(
                check=models.Q(status__in=["active", "inactive", "archived"]),
                name="ck_substance_status_valid"
            ),
        ]
        indexes = [
            models.Index(fields=["tenant_id", "status"], name="ix_substance_tenant_status"),
            models.Index(fields=["tenant_id", "is_cmr"], name="ix_substance_tenant_cmr"),
            models.Index(fields=["name"], name="ix_substance_name"),
        ]
    
    def __str__(self):
        return self.name
    
    @property
    def current_sds(self):
        """Aktuell gültige SDS-Revision (approved, neueste)"""
        return self.sds_revisions.filter(
            status=SdsRevision.Status.APPROVED
        ).order_by("-revision_number").first()
    
    @property
    def cas_number(self):
        """CAS-Nummer (falls vorhanden)"""
        identifier = self.identifiers.filter(id_type=Identifier.IdType.CAS).first()
        return identifier.id_value if identifier else None


class Identifier(models.Model):
    """Stoffkennungen (CAS, EC, UFI, GTIN, intern)"""
    
    class IdType(models.TextChoices):
        CAS = "cas", "CAS-Nummer"
        EC = "ec", "EC-Nummer"
        UFI = "ufi", "UFI-Code"
        GTIN = "gtin", "GTIN/EAN"
        INTERNAL = "internal", "Interne Nummer"
        INDEX = "index", "Index-Nummer"
        REACH = "reach", "REACH-Registrierungsnr."
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant_id = models.UUIDField(db_index=True)
    substance = models.ForeignKey(
        Substance,
        on_delete=models.CASCADE,
        related_name="identifiers"
    )
    
    id_type = models.CharField(max_length=20, choices=IdType.choices)
    id_value = models.CharField(max_length=100)
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = "substances_identifier"
        verbose_name = "Stoffkennung"
        verbose_name_plural = "Stoffkennungen"
        constraints = [
            models.UniqueConstraint(
                fields=["tenant_id", "id_type", "id_value"],
                name="uq_identifier_tenant_type_value"
            ),
        ]
        indexes = [
            models.Index(fields=["id_type", "id_value"], name="ix_identifier_lookup"),
            models.Index(fields=["substance"], name="ix_identifier_substance"),
        ]
    
    def __str__(self):
        return f"{self.get_id_type_display()}: {self.id_value}"
```

```python
# src/substances/models/sds.py

import uuid
from django.db import models


class SdsRevision(models.Model):
    """SDS-Revision (Sicherheitsdatenblatt-Version)"""
    
    class Status(models.TextChoices):
        DRAFT = "draft", "Entwurf"
        APPROVED = "approved", "Freigegeben"
        ARCHIVED = "archived", "Archiviert"
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant_id = models.UUIDField(db_index=True)
    substance = models.ForeignKey(
        "Substance",
        on_delete=models.CASCADE,
        related_name="sds_revisions"
    )
    
    # Dokumentenverknüpfung
    document_version_id = models.UUIDField(
        null=True,
        blank=True,
        help_text="FK zu documents_document_version (SDS-PDF)"
    )
    
    # Revisionsdaten
    revision_number = models.PositiveIntegerField(
        help_text="Interne fortlaufende Revisionsnummer"
    )
    revision_date = models.DateField(
        help_text="Revisionsdatum laut SDS (Abschnitt 16)"
    )
    supplier_version = models.CharField(
        max_length=50,
        blank=True,
        default="",
        help_text="Versionsangabe des Lieferanten"
    )
    effective_from = models.DateField(
        null=True,
        blank=True,
        help_text="Gültig ab (für Compliance-Tracking)"
    )
    
    # Workflow
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.DRAFT
    )
    approved_by = models.UUIDField(null=True, blank=True)
    approved_at = models.DateTimeField(null=True, blank=True)
    
    # Metadaten
    language = models.CharField(
        max_length=5,
        default="de",
        help_text="Sprache (ISO 639-1)"
    )
    notes = models.TextField(blank=True, default="")
    
    # Audit
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.UUIDField(null=True, blank=True)
    
    class Meta:
        db_table = "substances_sds_revision"
        verbose_name = "SDS-Revision"
        verbose_name_plural = "SDS-Revisionen"
        ordering = ["-revision_number"]
        constraints = [
            models.UniqueConstraint(
                fields=["substance", "revision_number"],
                name="uq_sds_substance_revision"
            ),
            models.CheckConstraint(
                check=models.Q(status__in=["draft", "approved", "archived"]),
                name="ck_sds_status_valid"
            ),
            models.CheckConstraint(
                check=models.Q(revision_number__gte=1),
                name="ck_sds_revision_positive"
            ),
        ]
        indexes = [
            models.Index(
                fields=["substance", "-revision_number"],
                name="ix_sds_substance_rev"
            ),
            models.Index(
                fields=["tenant_id", "status"],
                name="ix_sds_tenant_status"
            ),
        ]
    
    def __str__(self):
        return f"{self.substance.name} - Rev. {self.revision_number} ({self.get_status_display()})"


class SdsClassification(models.Model):
    """Einstufung und Kennzeichnung nach CLP/GHS"""
    
    class SignalWord(models.TextChoices):
        DANGER = "Danger", "Gefahr"
        WARNING = "Warning", "Achtung"
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant_id = models.UUIDField()
    sds_revision = models.OneToOneField(
        SdsRevision,
        on_delete=models.CASCADE,
        related_name="classification"
    )
    
    signal_word = models.CharField(
        max_length=16,
        choices=SignalWord.choices,
        blank=True,
        default=""
    )
    classification_notes = models.TextField(
        blank=True,
        default="",
        help_text="Ergänzende Hinweise zur Einstufung"
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = "substances_sds_classification"
        verbose_name = "Einstufung"
        verbose_name_plural = "Einstufungen"
    
    def __str__(self):
        return f"Klassifikation für {self.sds_revision}"


class SdsHazardStatement(models.Model):
    """H-Sätze (Gefahrenhinweise)"""
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant_id = models.UUIDField()
    sds_revision = models.ForeignKey(
        SdsRevision,
        on_delete=models.CASCADE,
        related_name="hazard_statements"
    )
    
    code = models.CharField(
        max_length=20,
        help_text="H-Code (z.B. H225, H302+H312)"
    )
    text = models.TextField(
        blank=True,
        default="",
        help_text="Volltext des H-Satzes"
    )
    
    class Meta:
        db_table = "substances_sds_hazard_statement"
        verbose_name = "H-Satz"
        verbose_name_plural = "H-Sätze"
        constraints = [
            models.UniqueConstraint(
                fields=["sds_revision", "code"],
                name="uq_h_statement_revision_code"
            ),
        ]
    
    def __str__(self):
        return f"{self.code}: {self.text[:50]}..." if self.text else self.code


class SdsPrecautionaryStatement(models.Model):
    """P-Sätze (Sicherheitshinweise)"""
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant_id = models.UUIDField()
    sds_revision = models.ForeignKey(
        SdsRevision,
        on_delete=models.CASCADE,
        related_name="precautionary_statements"
    )
    
    code = models.CharField(
        max_length=30,
        help_text="P-Code (z.B. P210, P280, P303+P361+P353)"
    )
    text = models.TextField(
        blank=True,
        default="",
        help_text="Volltext des P-Satzes"
    )
    
    class Meta:
        db_table = "substances_sds_precautionary_statement"
        verbose_name = "P-Satz"
        verbose_name_plural = "P-Sätze"
        constraints = [
            models.UniqueConstraint(
                fields=["sds_revision", "code"],
                name="uq_p_statement_revision_code"
            ),
        ]
    
    def __str__(self):
        return f"{self.code}: {self.text[:50]}..." if self.text else self.code


class SdsPictogram(models.Model):
    """GHS-Piktogramme"""
    
    class PictogramCode(models.TextChoices):
        GHS01 = "GHS01", "GHS01 - Explodierende Bombe"
        GHS02 = "GHS02", "GHS02 - Flamme"
        GHS03 = "GHS03", "GHS03 - Flamme über Kreis"
        GHS04 = "GHS04", "GHS04 - Gasflasche"
        GHS05 = "GHS05", "GHS05 - Ätzwirkung"
        GHS06 = "GHS06", "GHS06 - Totenkopf"
        GHS07 = "GHS07", "GHS07 - Ausrufezeichen"
        GHS08 = "GHS08", "GHS08 - Gesundheitsgefahr"
        GHS09 = "GHS09", "GHS09 - Umwelt"
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant_id = models.UUIDField()
    sds_revision = models.ForeignKey(
        SdsRevision,
        on_delete=models.CASCADE,
        related_name="pictograms"
    )
    
    code = models.CharField(max_length=10, choices=PictogramCode.choices)
    
    class Meta:
        db_table = "substances_sds_pictogram"
        verbose_name = "Piktogramm"
        verbose_name_plural = "Piktogramme"
        constraints = [
            models.UniqueConstraint(
                fields=["sds_revision", "code"],
                name="uq_pictogram_revision_code"
            ),
        ]
    
    def __str__(self):
        return self.get_code_display()
```

```python
# src/substances/models/inventory.py

import uuid
from decimal import Decimal
from django.db import models
from django.core.validators import MinValueValidator


class SiteInventoryItem(models.Model):
    """Gefahrstoff-Bestand pro Standort/Lagerort"""
    
    class AggregateState(models.TextChoices):
        SOLID = "solid", "Feststoff"
        LIQUID = "liquid", "Flüssigkeit"
        GAS = "gas", "Gas"
        AEROSOL = "aerosol", "Aerosol"
        PASTE = "paste", "Paste"
        POWDER = "powder", "Pulver"
    
    class Unit(models.TextChoices):
        KG = "kg", "Kilogramm"
        G = "g", "Gramm"
        MG = "mg", "Milligramm"
        L = "l", "Liter"
        ML = "ml", "Milliliter"
        M3 = "m3", "Kubikmeter"
        PCS = "pcs", "Stück/Gebinde"
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant_id = models.UUIDField(db_index=True)
    site_id = models.UUIDField(
        db_index=True,
        help_text="FK zu tenancy_site"
    )
    substance = models.ForeignKey(
        "Substance",
        on_delete=models.PROTECT,
        related_name="inventory_items"
    )
    
    # Mengenangaben
    quantity = models.DecimalField(
        max_digits=18,
        decimal_places=3,
        default=Decimal("0"),
        validators=[MinValueValidator(Decimal("0"))],
        help_text="Menge"
    )
    max_quantity = models.DecimalField(
        max_digits=18,
        decimal_places=3,
        null=True,
        blank=True,
        validators=[MinValueValidator(Decimal("0"))],
        help_text="Maximale Lagermenge (für Mengenschwellen)"
    )
    unit = models.CharField(max_length=10, choices=Unit.choices)
    state = models.CharField(
        max_length=16,
        choices=AggregateState.choices,
        default=AggregateState.LIQUID
    )
    
    # Lagerort
    storage_location = models.CharField(
        max_length=240,
        blank=True,
        default="",
        help_text="Lagerort (z.B. Raum, Regal, Schrank)"
    )
    storage_area = models.CharField(
        max_length=100,
        blank=True,
        default="",
        help_text="Lagerbereich (z.B. Gefahrstofflager Nord)"
    )
    
    # Verantwortlichkeit
    responsible_user_id = models.UUIDField(
        null=True,
        blank=True,
        help_text="Verantwortlicher Mitarbeiter"
    )
    
    # Metadaten
    notes = models.TextField(blank=True, default="")
    last_inventory_date = models.DateField(
        null=True,
        blank=True,
        help_text="Datum der letzten Bestandsprüfung"
    )
    
    # Audit
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = "substances_site_inventory_item"
        verbose_name = "Inventareintrag"
        verbose_name_plural = "Inventareinträge"
        constraints = [
            models.CheckConstraint(
                check=models.Q(quantity__gte=0),
                name="ck_inventory_qty_nonnegative"
            ),
            models.UniqueConstraint(
                fields=["tenant_id", "site_id", "substance", "storage_location"],
                name="uq_inventory_site_substance_location"
            ),
        ]
        indexes = [
            models.Index(
                fields=["tenant_id", "site_id"],
                name="ix_inventory_tenant_site"
            ),
            models.Index(fields=["substance"], name="ix_inventory_substance"),
        ]
    
    def __str__(self):
        loc = self.storage_location or "unbekannt"
        return f"{self.substance.name} @ {loc} ({self.quantity} {self.unit})"
```

```python
# src/substances/models/reference.py

from django.db import models


class HazardStatementReference(models.Model):
    """Referenztabelle für H-Sätze (CLP-Verordnung, global)"""
    
    code = models.CharField(max_length=20, primary_key=True)
    text_de = models.TextField(help_text="Deutscher Text")
    text_en = models.TextField(blank=True, default="", help_text="Englischer Text")
    
    category = models.CharField(
        max_length=50,
        blank=True,
        default="",
        help_text="Gefahrenkategorie (physical, health, environmental)"
    )
    is_cmr = models.BooleanField(
        default=False,
        help_text="CMR-relevanter H-Satz"
    )
    
    class Meta:
        db_table = "substances_hazard_statement_ref"
        verbose_name = "H-Satz (Referenz)"
        verbose_name_plural = "H-Sätze (Referenz)"
        ordering = ["code"]
    
    def __str__(self):
        return f"{self.code}: {self.text_de[:60]}..."


class PrecautionaryStatementReference(models.Model):
    """Referenztabelle für P-Sätze (CLP-Verordnung, global)"""
    
    code = models.CharField(max_length=30, primary_key=True)
    text_de = models.TextField(help_text="Deutscher Text")
    text_en = models.TextField(blank=True, default="", help_text="Englischer Text")
    
    category = models.CharField(
        max_length=50,
        blank=True,
        default="",
        help_text="Kategorie (prevention, response, storage, disposal)"
    )
    
    class Meta:
        db_table = "substances_precautionary_statement_ref"
        verbose_name = "P-Satz (Referenz)"
        verbose_name_plural = "P-Sätze (Referenz)"
        ordering = ["code"]
    
    def __str__(self):
        return f"{self.code}: {self.text_de[:60]}..."
```

### 4.3 Migrationsplan

```python
# Migrations-Reihenfolge

# 0001_initial.py - Basis-Tabellen
# - Party
# - Substance  
# - Identifier

# 0002_sds_tables.py - SDS-Verwaltung
# - SdsRevision
# - SdsClassification
# - SdsHazardStatement
# - SdsPrecautionaryStatement
# - SdsPictogram

# 0003_inventory.py - Inventar
# - SiteInventoryItem

# 0004_reference_tables.py - Referenzdaten
# - HazardStatementReference
# - PrecautionaryStatementReference

# 0005_indexes.py - Performance-Indizes
# - Trigram-Index für Volltextsuche (optional)
```

---

## 5. Service Layer

### 5.1 Architektur-Regeln

```
┌─────────────────────────────────────────────────────────────────┐
│                    SERVICE LAYER REGELN                         │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  1. ALLE Schreiboperationen gehen durch Services               │
│     → Niemals Model.objects.create() direkt in Views           │
│                                                                 │
│  2. Jeder Write erzeugt:                                       │
│     → AuditEvent (verpflichtend)                               │
│     → OutboxMessage (bei domain-relevanten Events)             │
│                                                                 │
│  3. Authorization VOR jeder Operation:                         │
│     → authorize(user_id, permission, scope_context)            │
│                                                                 │
│  4. Transaktionsgrenzen:                                       │
│     → @transaction.atomic auf Service-Funktionen               │
│     → Eine Transaktion = Ein Use Case                          │
│                                                                 │
│  5. Commands als Eingabe:                                      │
│     → Frozen Dataclasses für Immutabilität                     │
│     → Validierung in der Service-Funktion                      │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### 5.2 Command DTOs

```python
# src/substances/commands/commands.py

from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from typing import Optional, List
from uuid import UUID


# ============================================================
# SUBSTANCE COMMANDS
# ============================================================

@dataclass(frozen=True)
class CreateSubstanceCmd:
    """Neuen Gefahrstoff anlegen"""
    name: str
    trade_name: str = ""
    description: str = ""
    storage_class: str = ""
    is_cmr: bool = False
    manufacturer_id: Optional[UUID] = None
    supplier_id: Optional[UUID] = None


@dataclass(frozen=True)
class UpdateSubstanceCmd:
    """Gefahrstoff aktualisieren"""
    substance_id: UUID
    name: Optional[str] = None
    trade_name: Optional[str] = None
    description: Optional[str] = None
    storage_class: Optional[str] = None
    is_cmr: Optional[bool] = None
    manufacturer_id: Optional[UUID] = None
    supplier_id: Optional[UUID] = None


@dataclass(frozen=True)
class ArchiveSubstanceCmd:
    """Gefahrstoff archivieren"""
    substance_id: UUID
    reason: str = ""


@dataclass(frozen=True)
class AddIdentifierCmd:
    """Stoffkennung hinzufügen"""
    substance_id: UUID
    id_type: str  # cas, ec, ufi, gtin, internal
    id_value: str


@dataclass(frozen=True)
class RemoveIdentifierCmd:
    """Stoffkennung entfernen"""
    identifier_id: UUID


# ============================================================
# SDS COMMANDS
# ============================================================

@dataclass(frozen=True)
class UploadSdsCmd:
    """SDS hochladen"""
    substance_id: UUID
    document_version_id: UUID
    revision_date: date
    supplier_version: str = ""
    effective_from: Optional[date] = None
    language: str = "de"
    notes: str = ""


@dataclass(frozen=True)
class ClassifySdsCmd:
    """SDS klassifizieren"""
    sds_revision_id: UUID
    signal_word: str = ""  # Danger, Warning, oder leer
    hazard_statements: List[str] = field(default_factory=list)  # ["H225", "H302"]
    precautionary_statements: List[str] = field(default_factory=list)  # ["P210"]
    pictograms: List[str] = field(default_factory=list)  # ["GHS02", "GHS07"]
    classification_notes: str = ""


@dataclass(frozen=True)
class ApproveSdsCmd:
    """SDS freigeben"""
    sds_revision_id: UUID
    approval_notes: str = ""


@dataclass(frozen=True)
class ArchiveSdsCmd:
    """SDS archivieren"""
    sds_revision_id: UUID
    reason: str = ""


# ============================================================
# INVENTORY COMMANDS
# ============================================================

@dataclass(frozen=True)
class CreateInventoryItemCmd:
    """Inventareintrag erstellen"""
    site_id: UUID
    substance_id: UUID
    quantity: Decimal
    unit: str
    state: str = "liquid"
    storage_location: str = ""
    storage_area: str = ""
    max_quantity: Optional[Decimal] = None
    responsible_user_id: Optional[UUID] = None
    notes: str = ""


@dataclass(frozen=True)
class UpdateInventoryItemCmd:
    """Inventareintrag aktualisieren"""
    inventory_item_id: UUID
    quantity: Optional[Decimal] = None
    unit: Optional[str] = None
    state: Optional[str] = None
    storage_location: Optional[str] = None
    storage_area: Optional[str] = None
    max_quantity: Optional[Decimal] = None
    responsible_user_id: Optional[UUID] = None
    notes: Optional[str] = None


@dataclass(frozen=True)
class DeleteInventoryItemCmd:
    """Inventareintrag löschen"""
    inventory_item_id: UUID
    reason: str = ""


@dataclass(frozen=True)
class RecordInventoryCheckCmd:
    """Bestandsprüfung dokumentieren"""
    inventory_item_id: UUID
    actual_quantity: Decimal
    check_date: date
    notes: str = ""


# ============================================================
# PARTY COMMANDS
# ============================================================

@dataclass(frozen=True)
class CreatePartyCmd:
    """Hersteller/Lieferant anlegen"""
    party_type: str  # manufacturer, supplier
    name: str
    email: str = ""
    phone: str = ""
    address: str = ""
    website: str = ""


@dataclass(frozen=True)
class UpdatePartyCmd:
    """Hersteller/Lieferant aktualisieren"""
    party_id: UUID
    name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    address: Optional[str] = None
    website: Optional[str] = None


# ============================================================
# EXPORT COMMANDS
# ============================================================

@dataclass(frozen=True)
class CreateHazardRegisterExportCmd:
    """Gefahrstoffverzeichnis-Export erstellen"""
    site_id: Optional[UUID] = None  # None = alle Sites
    include_archived: bool = False
    format: str = "xlsx"  # xlsx, pdf


@dataclass(frozen=True)
class CreateSdsComplianceReportCmd:
    """SDS-Aktualitätsreport erstellen"""
    site_id: Optional[UUID] = None
    max_age_months: int = 24
    format: str = "pdf"
```

### 5.3 Service Implementation

```python
# src/substances/services/substance_service.py

from typing import List
from uuid import UUID

from django.db import transaction
from django.utils import timezone

from common.request_context import get_context
from audit.services import emit_audit_event
from outbox.models import OutboxMessage
from permissions.services import authorize

from ..models import Substance, Identifier, Party
from ..commands.commands import (
    CreateSubstanceCmd, UpdateSubstanceCmd, ArchiveSubstanceCmd,
    AddIdentifierCmd, RemoveIdentifierCmd
)


class SubstanceService:
    """Service für Gefahrstoff-Verwaltung"""
    
    @staticmethod
    @transaction.atomic
    def create_substance(cmd: CreateSubstanceCmd) -> Substance:
        """Neuen Gefahrstoff anlegen"""
        ctx = get_context()
        
        if not ctx.tenant_id:
            raise ValueError("Tenant-Kontext erforderlich")
        
        # Authorization
        authorize(ctx.user_id, "sds.substance.write", tenant_id=ctx.tenant_id)
        
        # Validierung
        name = cmd.name.strip()
        if not name:
            raise ValueError("Stoffname ist erforderlich")
        
        if Substance.objects.filter(tenant_id=ctx.tenant_id, name=name).exists():
            raise ValueError(f"Gefahrstoff '{name}' existiert bereits")
        
        # Erstellen
        substance = Substance.objects.create(
            tenant_id=ctx.tenant_id,
            name=name,
            trade_name=cmd.trade_name.strip(),
            description=cmd.description.strip(),
            storage_class=cmd.storage_class,
            is_cmr=cmd.is_cmr,
            manufacturer_id=cmd.manufacturer_id,
            supplier_id=cmd.supplier_id,
            created_by=ctx.user_id,
        )
        
        # Audit Event
        emit_audit_event(
            tenant_id=ctx.tenant_id,
            category="sds.substance",
            action="created",
            entity_type="substances.Substance",
            entity_id=substance.id,
            payload={
                "name": substance.name,
                "storage_class": substance.storage_class,
                "is_cmr": substance.is_cmr,
            },
        )
        
        # Outbox Event
        OutboxMessage.objects.create(
            tenant_id=ctx.tenant_id,
            topic="sds.substance.created",
            payload={
                "substance_id": str(substance.id),
                "name": substance.name,
            },
        )
        
        return substance
    
    @staticmethod
    @transaction.atomic
    def update_substance(cmd: UpdateSubstanceCmd) -> Substance:
        """Gefahrstoff aktualisieren"""
        ctx = get_context()
        
        if not ctx.tenant_id:
            raise ValueError("Tenant-Kontext erforderlich")
        
        authorize(ctx.user_id, "sds.substance.write", tenant_id=ctx.tenant_id)
        
        substance = Substance.objects.select_for_update().get(
            id=cmd.substance_id,
            tenant_id=ctx.tenant_id
        )
        
        changes = {}
        
        if cmd.name is not None:
            new_name = cmd.name.strip()
            if new_name != substance.name:
                # Prüfen ob Name bereits existiert
                if Substance.objects.filter(
                    tenant_id=ctx.tenant_id, 
                    name=new_name
                ).exclude(id=substance.id).exists():
                    raise ValueError(f"Gefahrstoff '{new_name}' existiert bereits")
                changes["name"] = {"old": substance.name, "new": new_name}
                substance.name = new_name
        
        if cmd.trade_name is not None and cmd.trade_name.strip() != substance.trade_name:
            changes["trade_name"] = {"old": substance.trade_name, "new": cmd.trade_name.strip()}
            substance.trade_name = cmd.trade_name.strip()
        
        if cmd.description is not None and cmd.description.strip() != substance.description:
            changes["description"] = {"old": "...", "new": "..."}  # Kürzen für Audit
            substance.description = cmd.description.strip()
        
        if cmd.storage_class is not None and cmd.storage_class != substance.storage_class:
            changes["storage_class"] = {"old": substance.storage_class, "new": cmd.storage_class}
            substance.storage_class = cmd.storage_class
        
        if cmd.is_cmr is not None and cmd.is_cmr != substance.is_cmr:
            changes["is_cmr"] = {"old": substance.is_cmr, "new": cmd.is_cmr}
            substance.is_cmr = cmd.is_cmr
        
        if cmd.manufacturer_id is not None:
            changes["manufacturer_id"] = {"old": str(substance.manufacturer_id), "new": str(cmd.manufacturer_id)}
            substance.manufacturer_id = cmd.manufacturer_id
        
        if cmd.supplier_id is not None:
            changes["supplier_id"] = {"old": str(substance.supplier_id), "new": str(cmd.supplier_id)}
            substance.supplier_id = cmd.supplier_id
        
        if changes:
            substance.save()
            
            emit_audit_event(
                tenant_id=ctx.tenant_id,
                category="sds.substance",
                action="updated",
                entity_type="substances.Substance",
                entity_id=substance.id,
                payload={"changes": changes},
            )
        
        return substance
    
    @staticmethod
    @transaction.atomic
    def archive_substance(cmd: ArchiveSubstanceCmd) -> Substance:
        """Gefahrstoff archivieren"""
        ctx = get_context()
        
        if not ctx.tenant_id:
            raise ValueError("Tenant-Kontext erforderlich")
        
        authorize(ctx.user_id, "sds.substance.write", tenant_id=ctx.tenant_id)
        
        substance = Substance.objects.select_for_update().get(
            id=cmd.substance_id,
            tenant_id=ctx.tenant_id
        )
        
        if substance.status == Substance.Status.ARCHIVED:
            raise ValueError("Gefahrstoff ist bereits archiviert")
        
        old_status = substance.status
        substance.status = Substance.Status.ARCHIVED
        substance.save(update_fields=["status", "updated_at"])
        
        emit_audit_event(
            tenant_id=ctx.tenant_id,
            category="sds.substance",
            action="archived",
            entity_type="substances.Substance",
            entity_id=substance.id,
            payload={
                "old_status": old_status,
                "reason": cmd.reason,
            },
        )
        
        OutboxMessage.objects.create(
            tenant_id=ctx.tenant_id,
            topic="sds.substance.archived",
            payload={"substance_id": str(substance.id)},
        )
        
        return substance
    
    @staticmethod
    @transaction.atomic
    def add_identifier(cmd: AddIdentifierCmd) -> Identifier:
        """Stoffkennung hinzufügen"""
        ctx = get_context()
        
        if not ctx.tenant_id:
            raise ValueError("Tenant-Kontext erforderlich")
        
        authorize(ctx.user_id, "sds.substance.write", tenant_id=ctx.tenant_id)
        
        substance = Substance.objects.get(
            id=cmd.substance_id,
            tenant_id=ctx.tenant_id
        )
        
        id_value = cmd.id_value.strip().upper()
        
        # Validierung je nach Typ
        if cmd.id_type == "cas":
            # CAS-Format: 7732-18-5 (Wasser)
            if not SubstanceService._validate_cas(id_value):
                raise ValueError(f"Ungültiges CAS-Format: {id_value}")
        
        # Prüfen ob bereits vorhanden
        if Identifier.objects.filter(
            tenant_id=ctx.tenant_id,
            id_type=cmd.id_type,
            id_value=id_value
        ).exists():
            raise ValueError(f"{cmd.id_type.upper()} '{id_value}' existiert bereits")
        
        identifier = Identifier.objects.create(
            tenant_id=ctx.tenant_id,
            substance=substance,
            id_type=cmd.id_type,
            id_value=id_value,
        )
        
        emit_audit_event(
            tenant_id=ctx.tenant_id,
            category="sds.substance",
            action="identifier_added",
            entity_type="substances.Identifier",
            entity_id=identifier.id,
            payload={
                "substance_id": str(substance.id),
                "id_type": cmd.id_type,
                "id_value": id_value,
            },
        )
        
        return identifier
    
    @staticmethod
    def _validate_cas(cas: str) -> bool:
        """CAS-Nummer validieren (Prüfziffer)"""
        # CAS-Format: XXXXXXX-XX-X
        import re
        
        # Nur Ziffern und Bindestriche
        if not re.match(r"^\d{2,7}-\d{2}-\d$", cas):
            return False
        
        # Prüfziffer berechnen
        digits = cas.replace("-", "")
        check = int(digits[-1])
        
        total = 0
        for i, d in enumerate(reversed(digits[:-1])):
            total += int(d) * (i + 1)
        
        return total % 10 == check
```

```python
# src/substances/services/sds_service.py

from typing import List, Set
from uuid import UUID

from django.db import transaction
from django.utils import timezone

from common.request_context import get_context
from audit.services import emit_audit_event
from outbox.models import OutboxMessage
from permissions.services import authorize

from ..models import (
    Substance, SdsRevision, SdsClassification,
    SdsHazardStatement, SdsPrecautionaryStatement, SdsPictogram
)
from ..commands.commands import UploadSdsCmd, ClassifySdsCmd, ApproveSdsCmd


# CMR-relevante H-Sätze (automatische Erkennung)
CMR_H_CODES: Set[str] = {
    "H340", "H341",  # Mutagenität
    "H350", "H350i", "H351",  # Karzinogenität
    "H360", "H360F", "H360D", "H360FD", "H360Fd", "H360Df",  # Reproduktionstoxizität
    "H361", "H361f", "H361d", "H361fd",
    "H362",  # Stillen
}


class SdsService:
    """Service für SDS-Verwaltung"""
    
    @staticmethod
    @transaction.atomic
    def upload_sds(cmd: UploadSdsCmd) -> SdsRevision:
        """SDS hochladen und neue Revision erstellen"""
        ctx = get_context()
        
        if not ctx.tenant_id:
            raise ValueError("Tenant-Kontext erforderlich")
        
        authorize(ctx.user_id, "sds.sdsrevision.write", tenant_id=ctx.tenant_id)
        
        substance = Substance.objects.get(
            id=cmd.substance_id,
            tenant_id=ctx.tenant_id
        )
        
        # Nächste Revisionsnummer
        last_revision = substance.sds_revisions.order_by("-revision_number").first()
        next_number = (last_revision.revision_number + 1) if last_revision else 1
        
        revision = SdsRevision.objects.create(
            tenant_id=ctx.tenant_id,
            substance=substance,
            document_version_id=cmd.document_version_id,
            revision_number=next_number,
            revision_date=cmd.revision_date,
            supplier_version=cmd.supplier_version.strip(),
            effective_from=cmd.effective_from,
            language=cmd.language,
            notes=cmd.notes.strip(),
            status=SdsRevision.Status.DRAFT,
            created_by=ctx.user_id,
        )
        
        emit_audit_event(
            tenant_id=ctx.tenant_id,
            category="sds.sdsrevision",
            action="uploaded",
            entity_type="substances.SdsRevision",
            entity_id=revision.id,
            payload={
                "substance_id": str(substance.id),
                "substance_name": substance.name,
                "revision_number": next_number,
                "revision_date": str(cmd.revision_date),
                "document_version_id": str(cmd.document_version_id),
            },
        )
        
        OutboxMessage.objects.create(
            tenant_id=ctx.tenant_id,
            topic="sds.sdsrevision.uploaded",
            payload={
                "sds_revision_id": str(revision.id),
                "substance_id": str(substance.id),
                "revision_number": next_number,
            },
        )
        
        return revision
    
    @staticmethod
    @transaction.atomic
    def classify_sds(cmd: ClassifySdsCmd) -> SdsClassification:
        """SDS klassifizieren (H-/P-Sätze, Piktogramme)"""
        ctx = get_context()
        
        if not ctx.tenant_id:
            raise ValueError("Tenant-Kontext erforderlich")
        
        authorize(ctx.user_id, "sds.sdsrevision.write", tenant_id=ctx.tenant_id)
        
        revision = SdsRevision.objects.select_for_update().get(
            id=cmd.sds_revision_id,
            tenant_id=ctx.tenant_id
        )
        
        if revision.status != SdsRevision.Status.DRAFT:
            raise ValueError("Nur Entwürfe können klassifiziert werden")
        
        # Classification erstellen/aktualisieren
        classification, _ = SdsClassification.objects.update_or_create(
            sds_revision=revision,
            defaults={
                "tenant_id": ctx.tenant_id,
                "signal_word": cmd.signal_word,
                "classification_notes": cmd.classification_notes.strip(),
            }
        )
        
        # Bestehende Einträge löschen
        revision.hazard_statements.all().delete()
        revision.precautionary_statements.all().delete()
        revision.pictograms.all().delete()
        
        # H-Sätze hinzufügen
        h_codes_added = []
        for code in cmd.hazard_statements:
            code = code.strip().upper()
            if code:
                SdsHazardStatement.objects.create(
                    tenant_id=ctx.tenant_id,
                    sds_revision=revision,
                    code=code,
                )
                h_codes_added.append(code)
        
        # P-Sätze hinzufügen
        p_codes_added = []
        for code in cmd.precautionary_statements:
            code = code.strip().upper()
            if code:
                SdsPrecautionaryStatement.objects.create(
                    tenant_id=ctx.tenant_id,
                    sds_revision=revision,
                    code=code,
                )
                p_codes_added.append(code)
        
        # Piktogramme hinzufügen
        pictograms_added = []
        for code in cmd.pictograms:
            code = code.strip().upper()
            if code:
                SdsPictogram.objects.create(
                    tenant_id=ctx.tenant_id,
                    sds_revision=revision,
                    code=code,
                )
                pictograms_added.append(code)
        
        emit_audit_event(
            tenant_id=ctx.tenant_id,
            category="sds.sdsrevision",
            action="classified",
            entity_type="substances.SdsRevision",
            entity_id=revision.id,
            payload={
                "signal_word": cmd.signal_word,
                "hazard_statements": h_codes_added,
                "precautionary_statements": p_codes_added,
                "pictograms": pictograms_added,
            },
        )
        
        return classification
    
    @staticmethod
    @transaction.atomic
    def approve_sds(cmd: ApproveSdsCmd) -> SdsRevision:
        """SDS freigeben"""
        ctx = get_context()
        
        if not ctx.tenant_id:
            raise ValueError("Tenant-Kontext erforderlich")
        
        authorize(ctx.user_id, "sds.sdsrevision.approve", tenant_id=ctx.tenant_id)
        
        revision = SdsRevision.objects.select_for_update().select_related(
            "substance"
        ).get(
            id=cmd.sds_revision_id,
            tenant_id=ctx.tenant_id
        )
        
        if revision.status != SdsRevision.Status.DRAFT:
            raise ValueError("Nur Entwürfe können freigegeben werden")
        
        # Prüfen ob Klassifikation vorhanden
        if not hasattr(revision, "classification"):
            raise ValueError("SDS muss vor Freigabe klassifiziert werden")
        
        # Bisherige freigegebene Versionen archivieren
        SdsRevision.objects.filter(
            substance=revision.substance,
            status=SdsRevision.Status.APPROVED,
        ).exclude(id=revision.id).update(
            status=SdsRevision.Status.ARCHIVED,
            updated_at=timezone.now()
        )
        
        # Freigeben
        revision.status = SdsRevision.Status.APPROVED
        revision.approved_by = ctx.user_id
        revision.approved_at = timezone.now()
        revision.save(update_fields=["status", "approved_by", "approved_at", "updated_at"])
        
        # CMR-Status automatisch setzen
        h_codes = set(revision.hazard_statements.values_list("code", flat=True))
        has_cmr = bool(h_codes & CMR_H_CODES)
        
        if has_cmr and not revision.substance.is_cmr:
            revision.substance.is_cmr = True
            revision.substance.save(update_fields=["is_cmr", "updated_at"])
        
        emit_audit_event(
            tenant_id=ctx.tenant_id,
            category="sds.sdsrevision",
            action="approved",
            entity_type="substances.SdsRevision",
            entity_id=revision.id,
            payload={
                "substance_id": str(revision.substance.id),
                "substance_name": revision.substance.name,
                "revision_number": revision.revision_number,
                "approved_by": str(ctx.user_id),
                "cmr_detected": has_cmr,
            },
        )
        
        OutboxMessage.objects.create(
            tenant_id=ctx.tenant_id,
            topic="sds.sdsrevision.approved",
            payload={
                "sds_revision_id": str(revision.id),
                "substance_id": str(revision.substance.id),
                "revision_number": revision.revision_number,
            },
        )
        
        return revision
```

### 5.4 Query-Helpers

```python
# src/substances/queries/substance_queries.py

from typing import Optional, List
from uuid import UUID
from django.db.models import QuerySet, Q, Prefetch, Count, Max

from ..models import Substance, SdsRevision, Identifier


def get_substances_for_tenant(
    tenant_id: UUID,
    *,
    status: Optional[str] = None,
    search: Optional[str] = None,
    storage_class: Optional[str] = None,
    is_cmr: Optional[bool] = None,
    has_approved_sds: Optional[bool] = None,
    manufacturer_id: Optional[UUID] = None,
    supplier_id: Optional[UUID] = None,
    order_by: str = "name",
    limit: int = 100,
) -> QuerySet[Substance]:
    """
    Gefahrstoffe für Tenant mit Filtern abrufen.
    
    Optimiert mit Prefetch für:
    - identifiers
    - current_sds (neueste approved)
    """
    qs = Substance.objects.filter(tenant_id=tenant_id)
    
    # Filter
    if status:
        qs = qs.filter(status=status)
    
    if search:
        search = search.strip()
        qs = qs.filter(
            Q(name__icontains=search) |
            Q(trade_name__icontains=search) |
            Q(identifiers__id_value__icontains=search)
        ).distinct()
    
    if storage_class:
        qs = qs.filter(storage_class=storage_class)
    
    if is_cmr is not None:
        qs = qs.filter(is_cmr=is_cmr)
    
    if manufacturer_id:
        qs = qs.filter(manufacturer_id=manufacturer_id)
    
    if supplier_id:
        qs = qs.filter(supplier_id=supplier_id)
    
    if has_approved_sds is True:
        qs = qs.filter(sds_revisions__status="approved").distinct()
    elif has_approved_sds is False:
        qs = qs.exclude(sds_revisions__status="approved")
    
    # Optimierte Prefetches
    qs = qs.select_related("manufacturer", "supplier").prefetch_related(
        "identifiers",
        Prefetch(
            "sds_revisions",
            queryset=SdsRevision.objects.filter(
                status=SdsRevision.Status.APPROVED
            ).select_related("classification").prefetch_related(
                "hazard_statements",
                "pictograms"
            ).order_by("-revision_number")[:1],
            to_attr="current_sds_list"
        )
    )
    
    # Sortierung
    if order_by.startswith("-"):
        qs = qs.order_by(order_by)
    else:
        qs = qs.order_by(order_by)
    
    return qs[:limit]


def get_substance_detail(
    tenant_id: UUID,
    substance_id: UUID
) -> Substance:
    """
    Einzelnen Gefahrstoff mit allen Relationen laden.
    """
    return Substance.objects.select_related(
        "manufacturer", "supplier"
    ).prefetch_related(
        "identifiers",
        Prefetch(
            "sds_revisions",
            queryset=SdsRevision.objects.select_related(
                "classification"
            ).prefetch_related(
                "hazard_statements",
                "precautionary_statements",
                "pictograms"
            ).order_by("-revision_number")
        ),
        "inventory_items"
    ).get(
        id=substance_id,
        tenant_id=tenant_id
    )


def search_substances_by_identifier(
    tenant_id: UUID,
    id_type: str,
    id_value: str
) -> QuerySet[Substance]:
    """
    Stoffe nach Kennung (CAS, EC, UFI) suchen.
    """
    return Substance.objects.filter(
        tenant_id=tenant_id,
        identifiers__id_type=id_type,
        identifiers__id_value__iexact=id_value.strip()
    ).select_related("manufacturer", "supplier")


def get_substances_by_h_statements(
    tenant_id: UUID,
    h_codes: List[str],
) -> QuerySet[Substance]:
    """
    Stoffe nach H-Sätzen filtern (aktuelle SDS).
    """
    return Substance.objects.filter(
        tenant_id=tenant_id,
        status=Substance.Status.ACTIVE,
        sds_revisions__status=SdsRevision.Status.APPROVED,
        sds_revisions__hazard_statements__code__in=h_codes,
    ).distinct()


def get_substances_with_outdated_sds(
    tenant_id: UUID,
    max_age_months: int = 24,
) -> QuerySet[Substance]:
    """
    Aktive Stoffe mit veraltetem SDS (älter als X Monate).
    """
    from django.utils import timezone
    from datetime import timedelta
    
    threshold = timezone.now().date() - timedelta(days=max_age_months * 30)
    
    # Stoffe ohne aktuelles SDS oder mit veraltetem SDS
    return Substance.objects.filter(
        tenant_id=tenant_id,
        status=Substance.Status.ACTIVE,
    ).exclude(
        sds_revisions__status=SdsRevision.Status.APPROVED,
        sds_revisions__revision_date__gte=threshold,
    ).annotate(
        latest_sds_date=Max(
            "sds_revisions__revision_date",
            filter=Q(sds_revisions__status=SdsRevision.Status.APPROVED)
        )
    )


def get_cmr_substances(tenant_id: UUID) -> QuerySet[Substance]:
    """
    Alle CMR-Stoffe für Expositionsverzeichnis.
    """
    return Substance.objects.filter(
        tenant_id=tenant_id,
        is_cmr=True,
        status=Substance.Status.ACTIVE,
    ).select_related("manufacturer", "supplier").prefetch_related(
        "identifiers",
        "inventory_items"
    )
```

---

## 6. RBAC & Permissions

### 6.1 Permission Codes

```python
# src/substances/permissions.py

from enum import Enum
from typing import Dict


class SdsPermission(str, Enum):
    """SDS-Modul Permissions"""
    
    # Substance (Stammdaten)
    SUBSTANCE_READ = "sds.substance.read"
    SUBSTANCE_WRITE = "sds.substance.write"
    
    # SDS Revision
    SDSREVISION_READ = "sds.sdsrevision.read"
    SDSREVISION_WRITE = "sds.sdsrevision.write"
    SDSREVISION_APPROVE = "sds.sdsrevision.approve"
    
    # Inventory
    INVENTORY_READ = "sds.inventory.read"
    INVENTORY_WRITE = "sds.inventory.write"
    
    # Export
    EXPORT_CREATE = "sds.export.create"
    EXPORT_READ = "sds.export.read"
    
    # Party (Hersteller/Lieferant)
    PARTY_READ = "sds.party.read"
    PARTY_WRITE = "sds.party.write"


# Permission Definitionen für Seed
PERMISSION_DEFINITIONS: Dict[str, dict] = {
    SdsPermission.SUBSTANCE_READ: {
        "code": "sds.substance.read",
        "description": "Gefahrstoffe anzeigen",
        "scope": "TENANT",
    },
    SdsPermission.SUBSTANCE_WRITE: {
        "code": "sds.substance.write",
        "description": "Gefahrstoffe erstellen und bearbeiten",
        "scope": "TENANT",
    },
    SdsPermission.SDSREVISION_READ: {
        "code": "sds.sdsrevision.read",
        "description": "SDS-Revisionen anzeigen",
        "scope": "TENANT",
    },
    SdsPermission.SDSREVISION_WRITE: {
        "code": "sds.sdsrevision.write",
        "description": "SDS hochladen und klassifizieren",
        "scope": "TENANT",
    },
    SdsPermission.SDSREVISION_APPROVE: {
        "code": "sds.sdsrevision.approve",
        "description": "SDS freigeben",
        "scope": "TENANT",
    },
    SdsPermission.INVENTORY_READ: {
        "code": "sds.inventory.read",
        "description": "Inventar anzeigen",
        "scope": "SITE",
    },
    SdsPermission.INVENTORY_WRITE: {
        "code": "sds.inventory.write",
        "description": "Inventar bearbeiten",
        "scope": "SITE",
    },
    SdsPermission.EXPORT_CREATE: {
        "code": "sds.export.create",
        "description": "Exporte erstellen",
        "scope": "TENANT",
    },
    SdsPermission.EXPORT_READ: {
        "code": "sds.export.read",
        "description": "Exporte herunterladen",
        "scope": "TENANT",
    },
    SdsPermission.PARTY_READ: {
        "code": "sds.party.read",
        "description": "Hersteller/Lieferanten anzeigen",
        "scope": "TENANT",
    },
    SdsPermission.PARTY_WRITE: {
        "code": "sds.party.write",
        "description": "Hersteller/Lieferanten verwalten",
        "scope": "TENANT",
    },
}


# Vordefinierte Rollen-Templates
ROLE_TEMPLATES = {
    "EHS Manager": [
        SdsPermission.SUBSTANCE_READ,
        SdsPermission.SUBSTANCE_WRITE,
        SdsPermission.SDSREVISION_READ,
        SdsPermission.SDSREVISION_WRITE,
        SdsPermission.SDSREVISION_APPROVE,
        SdsPermission.INVENTORY_READ,
        SdsPermission.INVENTORY_WRITE,
        SdsPermission.EXPORT_CREATE,
        SdsPermission.EXPORT_READ,
        SdsPermission.PARTY_READ,
        SdsPermission.PARTY_WRITE,
    ],
    "Site Safety Officer": [
        SdsPermission.SUBSTANCE_READ,
        SdsPermission.SDSREVISION_READ,
        SdsPermission.INVENTORY_READ,
        SdsPermission.INVENTORY_WRITE,
        SdsPermission.EXPORT_READ,
        SdsPermission.PARTY_READ,
    ],
    "Lagerverantwortlicher": [
        SdsPermission.SUBSTANCE_READ,
        SdsPermission.SDSREVISION_READ,
        SdsPermission.INVENTORY_READ,
        SdsPermission.INVENTORY_WRITE,
        SdsPermission.PARTY_READ,
    ],
    "Auditor": [
        SdsPermission.SUBSTANCE_READ,
        SdsPermission.SDSREVISION_READ,
        SdsPermission.INVENTORY_READ,
        SdsPermission.EXPORT_CREATE,
        SdsPermission.EXPORT_READ,
        SdsPermission.PARTY_READ,
    ],
    "Mitarbeiter": [
        SdsPermission.SUBSTANCE_READ,
        SdsPermission.SDSREVISION_READ,
        SdsPermission.INVENTORY_READ,
        SdsPermission.PARTY_READ,
    ],
}
```

### 6.2 Scope-Matrix

| Permission | Scope | Beschreibung |
|------------|-------|--------------|
| `sds.substance.*` | TENANT | Zentrale Stammdatenverwaltung |
| `sds.sdsrevision.*` | TENANT | SDS-Verwaltung tenant-weit |
| `sds.inventory.*` | SITE | Inventar je Standort |
| `sds.export.*` | TENANT | Exports tenant-weit |
| `sds.party.*` | TENANT | Parteien tenant-weit |

---

## 7. API & Views

### 7.1 URL-Struktur

```python
# src/substances/urls.py

from django.urls import path
from .views import (
    substance_views, sds_views, inventory_views, export_views, party_views
)

app_name = "substances"

urlpatterns = [
    # ============================================================
    # SUBSTANCE ROUTES
    # ============================================================
    path("", 
         substance_views.substance_list, 
         name="substance_list"),
    path("create/", 
         substance_views.substance_create, 
         name="substance_create"),
    path("<uuid:pk>/", 
         substance_views.substance_detail, 
         name="substance_detail"),
    path("<uuid:pk>/edit/", 
         substance_views.substance_edit, 
         name="substance_edit"),
    path("<uuid:pk>/archive/", 
         substance_views.substance_archive, 
         name="substance_archive"),
    
    # Identifiers
    path("<uuid:substance_id>/identifiers/add/", 
         substance_views.identifier_add, 
         name="identifier_add"),
    path("identifiers/<uuid:pk>/delete/", 
         substance_views.identifier_delete, 
         name="identifier_delete"),
    
    # ============================================================
    # SDS ROUTES
    # ============================================================
    path("<uuid:substance_id>/sds/upload/", 
         sds_views.sds_upload, 
         name="sds_upload"),
    path("sds/<uuid:pk>/", 
         sds_views.sds_detail, 
         name="sds_detail"),
    path("sds/<uuid:pk>/classify/", 
         sds_views.sds_classify, 
         name="sds_classify"),
    path("sds/<uuid:pk>/approve/", 
         sds_views.sds_approve, 
         name="sds_approve"),
    path("sds/<uuid:pk>/archive/", 
         sds_views.sds_archive, 
         name="sds_archive"),
    
    # ============================================================
    # INVENTORY ROUTES
    # ============================================================
    path("inventory/", 
         inventory_views.inventory_list, 
         name="inventory_list"),
    path("inventory/create/", 
         inventory_views.inventory_create, 
         name="inventory_create"),
    path("inventory/<uuid:pk>/", 
         inventory_views.inventory_detail, 
         name="inventory_detail"),
    path("inventory/<uuid:pk>/edit/", 
         inventory_views.inventory_edit, 
         name="inventory_edit"),
    path("inventory/<uuid:pk>/delete/", 
         inventory_views.inventory_delete, 
         name="inventory_delete"),
    
    # ============================================================
    # EXPORT ROUTES
    # ============================================================
    path("exports/hazard-register/", 
         export_views.export_hazard_register, 
         name="export_hazard_register"),
    path("exports/sds-compliance/", 
         export_views.export_sds_compliance, 
         name="export_sds_compliance"),
    
    # ============================================================
    # PARTY ROUTES
    # ============================================================
    path("parties/", 
         party_views.party_list, 
         name="party_list"),
    path("parties/create/", 
         party_views.party_create, 
         name="party_create"),
    path("parties/<uuid:pk>/edit/", 
         party_views.party_edit, 
         name="party_edit"),
    
    # ============================================================
    # HTMX PARTIALS
    # ============================================================
    path("htmx/search/", 
         substance_views.htmx_substance_search, 
         name="htmx_substance_search"),
    path("htmx/h-statement-select/", 
         sds_views.htmx_h_statement_select, 
         name="htmx_h_statement_select"),
    path("htmx/p-statement-select/", 
         sds_views.htmx_p_statement_select, 
         name="htmx_p_statement_select"),
]
```

### 7.2 View Implementation (Beispiel)

```python
# src/substances/views/substance_views.py

from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponse, HttpResponseBadRequest
from django.contrib import messages
from django.views.decorators.http import require_http_methods

from common.request_context import get_context
from permissions.decorators import require_permission

from ..models import Substance
from ..services.substance_service import SubstanceService
from ..queries.substance_queries import get_substances_for_tenant, get_substance_detail
from ..commands.commands import CreateSubstanceCmd, UpdateSubstanceCmd, AddIdentifierCmd
from ..forms import SubstanceForm, IdentifierForm
from ..permissions import SdsPermission


@require_permission(SdsPermission.SUBSTANCE_READ)
def substance_list(request):
    """Gefahrstoff-Liste mit Suche und Filtern"""
    ctx = get_context()
    
    # Filter aus Request
    search = request.GET.get("search", "").strip()
    status = request.GET.get("status", "active")
    storage_class = request.GET.get("storage_class", "")
    is_cmr = request.GET.get("is_cmr", "")
    
    # Query
    substances = get_substances_for_tenant(
        tenant_id=ctx.tenant_id,
        status=status if status else None,
        search=search if search else None,
        storage_class=storage_class if storage_class else None,
        is_cmr=True if is_cmr == "true" else (False if is_cmr == "false" else None),
        limit=100,
    )
    
    # HTMX: Nur Tabelle zurückgeben
    if request.htmx:
        return render(request, "substances/partials/substance_table.html", {
            "substances": substances,
        })
    
    context = {
        "substances": substances,
        "search": search,
        "status": status,
        "storage_class": storage_class,
        "is_cmr": is_cmr,
        "storage_class_choices": Substance.StorageClass.choices,
        "status_choices": Substance.Status.choices,
    }
    
    return render(request, "substances/substance_list.html", context)


@require_permission(SdsPermission.SUBSTANCE_READ)
def substance_detail(request, pk):
    """Gefahrstoff-Detailansicht"""
    ctx = get_context()
    
    substance = get_substance_detail(ctx.tenant_id, pk)
    
    # Aktuelle SDS aus prefetch
    current_sds = substance.current_sds_list[0] if hasattr(substance, 'current_sds_list') and substance.current_sds_list else None
    
    context = {
        "substance": substance,
        "current_sds": current_sds,
        "sds_revisions": list(substance.sds_revisions.all()[:10]),
        "inventory_items": list(substance.inventory_items.all()),
        "identifiers": list(substance.identifiers.all()),
    }
    
    return render(request, "substances/substance_detail.html", context)


@require_permission(SdsPermission.SUBSTANCE_WRITE)
@require_http_methods(["GET", "POST"])
def substance_create(request):
    """Neuen Gefahrstoff anlegen"""
    if request.method == "POST":
        form = SubstanceForm(request.POST)
        if form.is_valid():
            try:
                cmd = CreateSubstanceCmd(
                    name=form.cleaned_data["name"],
                    trade_name=form.cleaned_data.get("trade_name", ""),
                    description=form.cleaned_data.get("description", ""),
                    storage_class=form.cleaned_data.get("storage_class", ""),
                    is_cmr=form.cleaned_data.get("is_cmr", False),
                    manufacturer_id=form.cleaned_data.get("manufacturer"),
                    supplier_id=form.cleaned_data.get("supplier"),
                )
                substance = SubstanceService.create_substance(cmd)
                
                messages.success(request, f"Gefahrstoff '{substance.name}' angelegt.")
                return redirect("substances:substance_detail", pk=substance.id)
            
            except ValueError as e:
                messages.error(request, str(e))
    else:
        form = SubstanceForm()
    
    return render(request, "substances/substance_form.html", {
        "form": form,
        "title": "Neuer Gefahrstoff",
        "submit_label": "Anlegen",
    })


@require_permission(SdsPermission.SUBSTANCE_WRITE)
@require_http_methods(["GET", "POST"])
def substance_edit(request, pk):
    """Gefahrstoff bearbeiten"""
    ctx = get_context()
    substance = get_object_or_404(Substance, id=pk, tenant_id=ctx.tenant_id)
    
    if request.method == "POST":
        form = SubstanceForm(request.POST, instance=substance)
        if form.is_valid():
            try:
                cmd = UpdateSubstanceCmd(
                    substance_id=pk,
                    name=form.cleaned_data["name"],
                    trade_name=form.cleaned_data.get("trade_name"),
                    description=form.cleaned_data.get("description"),
                    storage_class=form.cleaned_data.get("storage_class"),
                    is_cmr=form.cleaned_data.get("is_cmr"),
                    manufacturer_id=form.cleaned_data.get("manufacturer"),
                    supplier_id=form.cleaned_data.get("supplier"),
                )
                SubstanceService.update_substance(cmd)
                
                messages.success(request, "Änderungen gespeichert.")
                return redirect("substances:substance_detail", pk=pk)
            
            except ValueError as e:
                messages.error(request, str(e))
    else:
        form = SubstanceForm(instance=substance)
    
    return render(request, "substances/substance_form.html", {
        "form": form,
        "substance": substance,
        "title": f"Bearbeiten: {substance.name}",
        "submit_label": "Speichern",
    })


@require_permission(SdsPermission.SUBSTANCE_READ)
def htmx_substance_search(request):
    """HTMX Live-Suche"""
    ctx = get_context()
    search = request.GET.get("q", "").strip()
    
    if len(search) < 2:
        return HttpResponse("")
    
    substances = get_substances_for_tenant(
        tenant_id=ctx.tenant_id,
        search=search,
        status="active",
        limit=10,
    )
    
    return render(request, "substances/partials/search_results.html", {
        "substances": substances,
        "search": search,
    })
```

---

## 8. UI/UX Design

### 8.1 Wireframes

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│  GEFAHRSTOFFVERZEICHNIS                                    [+ Neu] [📊 Export]  │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                  │
│  🔍 [_____Suche (Name, CAS, UFI)_____]                                         │
│                                                                                  │
│  Filter: [Status ▼] [Lagerklasse ▼] [CMR ▼] [Hersteller ▼]                     │
│                                                                                  │
├─────────────────────────────────────────────────────────────────────────────────┤
│  ┌───┬────────────────┬──────────┬──────────┬────────┬───────┬────────┐       │
│  │   │ Stoffname      │ CAS-Nr.  │ H-Sätze  │ Pikto. │ LGK   │ Status │       │
│  ├───┼────────────────┼──────────┼──────────┼────────┼───────┼────────┤       │
│  │ ☐ │ Aceton         │ 67-64-1  │ H225,H31 │ 🔥⚠️   │ 3     │ ✅     │       │
│  │ ☐ │ Isopropanol    │ 67-63-0  │ H225,H31 │ 🔥⚠️   │ 3     │ ✅     │       │
│  │ ☐ │ Salzsäure 37%  │ 7647-01- │ H314,H33 │ ⚗️⚠️   │ 8B    │ ✅     │       │
│  │ ☐ │ Epoxidharz XY  │ -        │ H315,H31 │ ⚠️🫁   │ 10    │ ⚠️ SDS │       │
│  └───┴────────────────┴──────────┴──────────┴────────┴───────┴────────┘       │
│                                                                                  │
│  Zeige 1-4 von 156 Gefahrstoffen                          [◀ 1 2 3 ... 40 ▶]   │
│                                                                                  │
└─────────────────────────────────────────────────────────────────────────────────┘


┌─────────────────────────────────────────────────────────────────────────────────┐
│  ◀ Zurück                                                                       │
│                                                                                  │
│  ACETON                                                    [✏️ Bearbeiten]      │
│  CAS: 67-64-1 | LGK: 3 | Status: ✅ Aktiv                                      │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                  │
│  ┌─────────────────────────────────────┐  ┌─────────────────────────────────┐  │
│  │  AKTUELLE SDS (Rev. 3)              │  │  KLASSIFIKATION                 │  │
│  │  ────────────────────────────────── │  │  ─────────────────────────────  │  │
│  │  📄 SDS_Aceton_Rev3.pdf             │  │  Signalwort: ⚠️ Gefahr          │  │
│  │  Datum: 15.03.2024                  │  │                                 │  │
│  │  Lieferant: BASF SE                 │  │  Piktogramme:                   │  │
│  │  Status: ✅ Freigegeben             │  │  🔥 GHS02  ⚠️ GHS07             │  │
│  │                                     │  │                                 │  │
│  │  [📥 Download] [🔍 Alle Revisionen] │  │  H-Sätze:                       │  │
│  └─────────────────────────────────────┘  │  H225 - Flüssigkeit und Dampf   │  │
│                                           │         leicht entzündbar       │  │
│  ┌─────────────────────────────────────┐  │  H319 - Verursacht schwere      │  │
│  │  INVENTAR (3 Standorte)             │  │         Augenreizung            │  │
│  │  ────────────────────────────────── │  │  H336 - Kann Schläfrigkeit      │  │
│  │                                     │  │         verursachen             │  │
│  │  📍 Werk Nord - Lager A             │  │                                 │  │
│  │     50 L | Letzte Prüfung: 10.01.26 │  │  P-Sätze:                       │  │
│  │                                     │  │  P210, P233, P240, P241...      │  │
│  │  📍 Werk Süd - Chemielager          │  │                                 │  │
│  │     120 L | Letzte Prüfung: 05.01.26│  └─────────────────────────────────┘  │
│  │                                     │                                       │
│  │  [+ Inventar hinzufügen]            │                                       │
│  └─────────────────────────────────────┘                                       │
│                                                                                  │
└─────────────────────────────────────────────────────────────────────────────────┘
```

### 8.2 Komponenten-Bibliothek

```html
<!-- Piktogramm-Badge -->
<span class="pictogram-badge" title="GHS02 - Flamme">
    <img src="{% static 'substances/img/pictograms/GHS02.svg' %}" 
         alt="GHS02" 
         class="w-6 h-6">
</span>

<!-- Status-Badge -->
<span class="status-badge status-{{ substance.status }}">
    {% if substance.status == 'active' %}✅{% endif %}
    {% if substance.status == 'inactive' %}⏸️{% endif %}
    {% if substance.status == 'archived' %}📦{% endif %}
    {{ substance.get_status_display }}
</span>

<!-- CMR-Warnung -->
{% if substance.is_cmr %}
<span class="cmr-warning" title="CMR-Stoff">
    ⚠️ CMR
</span>
{% endif %}

<!-- SDS-Status -->
{% if substance.current_sds %}
<span class="sds-status sds-ok">✅ SDS aktuell</span>
{% else %}
<span class="sds-status sds-missing">⚠️ Kein SDS</span>
{% endif %}
```

---

## 9. Export-Module

### 9.1 Gefahrstoffverzeichnis (Excel)

```python
# src/substances/exports/hazard_register_excel.py

import openpyxl
from openpyxl.styles import Font, PatternFill, Border, Side, Alignment
from openpyxl.utils import get_column_letter
from io import BytesIO
from datetime import datetime
from typing import Optional
from uuid import UUID

from django.db.models import Prefetch

from ..models import Substance, SdsRevision


class HazardRegisterExcelExport:
    """Gefahrstoffverzeichnis nach GefStoffV §6 als Excel"""
    
    HEADERS = [
        ("Nr.", 6),
        ("Stoffname", 30),
        ("Handelsname", 25),
        ("CAS-Nr.", 15),
        ("Hersteller", 20),
        ("Signalwort", 12),
        ("H-Sätze", 30),
        ("P-Sätze", 35),
        ("Piktogramme", 20),
        ("Lagerklasse", 12),
        ("CMR", 8),
        ("Lagerort", 25),
        ("Menge", 10),
        ("Einheit", 8),
        ("SDS-Datum", 12),
        ("SDS-Status", 12),
    ]
    
    def __init__(
        self,
        tenant_id: UUID,
        tenant_name: str,
        site_id: Optional[UUID] = None,
        site_name: Optional[str] = None,
    ):
        self.tenant_id = tenant_id
        self.tenant_name = tenant_name
        self.site_id = site_id
        self.site_name = site_name
    
    def generate(self) -> BytesIO:
        """Excel-Datei generieren"""
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "Gefahrstoffverzeichnis"
        
        self._write_header(ws)
        row_count = self._write_data(ws)
        self._write_footer(ws, row_count)
        self._apply_formatting(ws, row_count)
        
        output = BytesIO()
        wb.save(output)
        output.seek(0)
        return output
    
    def _write_header(self, ws):
        """Spaltenköpfe schreiben"""
        header_fill = PatternFill(start_color="4472C4", end_color="4472C4", fill_type="solid")
        header_font = Font(bold=True, color="FFFFFF", size=10)
        
        for col, (header, width) in enumerate(self.HEADERS, 1):
            cell = ws.cell(row=1, column=col, value=header)
            cell.fill = header_fill
            cell.font = header_font
            cell.alignment = Alignment(horizontal="center", vertical="center")
            ws.column_dimensions[get_column_letter(col)].width = width
    
    def _write_data(self, ws) -> int:
        """Daten schreiben, gibt Anzahl Zeilen zurück"""
        substances = self._get_substances()
        
        row = 2
        for idx, substance in enumerate(substances, 1):
            # CAS-Nummer
            cas = next(
                (i.id_value for i in substance.identifiers.all() if i.id_type == "cas"),
                ""
            )
            
            # Aktuelle SDS
            current_sds = substance.current_sds_list[0] if substance.current_sds_list else None
            
            if current_sds and hasattr(current_sds, "classification"):
                signal_word = current_sds.classification.signal_word if current_sds.classification else ""
                h_codes = ", ".join(h.code for h in current_sds.hazard_statements.all())
                p_codes = ", ".join(p.code for p in current_sds.precautionary_statements.all())
                pictograms = ", ".join(p.code for p in current_sds.pictograms.all())
                sds_date = current_sds.revision_date.strftime("%d.%m.%Y")
                sds_status = "Freigegeben"
            else:
                signal_word = h_codes = p_codes = pictograms = sds_date = ""
                sds_status = "Fehlt" if not current_sds else "Entwurf"
            
            # Inventar-Einträge
            inventory = list(substance.inventory_items.all())
            if self.site_id:
                inventory = [i for i in inventory if i.site_id == self.site_id]
            
            # Eine Zeile pro Inventar-Eintrag (oder eine wenn kein Inventar)
            for inv in inventory if inventory else [None]:
                ws.cell(row=row, column=1, value=idx)
                ws.cell(row=row, column=2, value=substance.name)
                ws.cell(row=row, column=3, value=substance.trade_name)
                ws.cell(row=row, column=4, value=cas)
                ws.cell(row=row, column=5, value=substance.manufacturer.name if substance.manufacturer else "")
                ws.cell(row=row, column=6, value=signal_word)
                ws.cell(row=row, column=7, value=h_codes)
                ws.cell(row=row, column=8, value=p_codes)
                ws.cell(row=row, column=9, value=pictograms)
                ws.cell(row=row, column=10, value=substance.storage_class)
                ws.cell(row=row, column=11, value="Ja" if substance.is_cmr else "Nein")
                ws.cell(row=row, column=12, value=inv.storage_location if inv else "")
                ws.cell(row=row, column=13, value=float(inv.quantity) if inv else "")
                ws.cell(row=row, column=14, value=inv.unit if inv else "")
                ws.cell(row=row, column=15, value=sds_date)
                ws.cell(row=row, column=16, value=sds_status)
                row += 1
        
        return row - 2  # Anzahl Datenzeilen
    
    def _write_footer(self, ws, row_count: int):
        """Footer mit Metadaten"""
        footer_row = row_count + 4
        ws.cell(row=footer_row, column=1, value=f"Erstellt am: {datetime.now().strftime('%d.%m.%Y %H:%M')}")
        ws.cell(row=footer_row + 1, column=1, value=f"Organisation: {self.tenant_name}")
        if self.site_name:
            ws.cell(row=footer_row + 2, column=1, value=f"Standort: {self.site_name}")
        ws.cell(row=footer_row + 3, column=1, value=f"Anzahl Gefahrstoffe: {row_count}")
    
    def _apply_formatting(self, ws, row_count: int):
        """Formatierung anwenden"""
        border = Border(
            left=Side(style="thin"),
            right=Side(style="thin"),
            top=Side(style="thin"),
            bottom=Side(style="thin"),
        )
        
        # Borders für Datenbereich
        for row in range(1, row_count + 2):
            for col in range(1, len(self.HEADERS) + 1):
                ws.cell(row=row, column=col).border = border
        
        # Autofilter
        ws.auto_filter.ref = f"A1:{get_column_letter(len(self.HEADERS))}{row_count + 1}"
        
        # Zeile fixieren
        ws.freeze_panes = "A2"
    
    def _get_substances(self):
        """Gefahrstoffe mit optimierten Prefetches laden"""
        qs = Substance.objects.filter(
            tenant_id=self.tenant_id,
            status=Substance.Status.ACTIVE,
        ).select_related(
            "manufacturer"
        ).prefetch_related(
            "identifiers",
            Prefetch(
                "sds_revisions",
                queryset=SdsRevision.objects.filter(
                    status=SdsRevision.Status.APPROVED
                ).select_related("classification").prefetch_related(
                    "hazard_statements",
                    "precautionary_statements",
                    "pictograms"
                ).order_by("-revision_number")[:1],
                to_attr="current_sds_list"
            ),
            "inventory_items",
        ).order_by("name")
        
        if self.site_id:
            qs = qs.filter(inventory_items__site_id=self.site_id).distinct()
        
        return qs
```

---

## 10. Testing-Strategie

### 10.1 Test-Pyramide

```
           ╱╲
          ╱  ╲        E2E (5%)
         ╱    ╲       - Kritische User Journeys
        ╱──────╲      - Playwright
       ╱        ╲
      ╱          ╲    Integration (25%)
     ╱            ╲   - Services + DB
    ╱──────────────╲  - Views + Requests
   ╱                ╲
  ╱                  ╲  Unit (70%)
 ╱────────────────────╲ - Models
╱                      ╲- Queries
╲──────────────────────╱- Validators
```

### 10.2 Test-Factories

```python
# src/substances/tests/factories.py

import factory
from factory.django import DjangoModelFactory
from uuid import uuid4
from datetime import date

from ..models import (
    Party, Substance, Identifier, SdsRevision,
    SdsClassification, SdsHazardStatement, SdsPictogram,
    SiteInventoryItem
)


class PartyFactory(DjangoModelFactory):
    class Meta:
        model = Party
    
    id = factory.LazyFunction(uuid4)
    tenant_id = factory.LazyFunction(uuid4)
    party_type = "manufacturer"
    name = factory.Sequence(lambda n: f"Hersteller {n}")


class SubstanceFactory(DjangoModelFactory):
    class Meta:
        model = Substance
    
    id = factory.LazyFunction(uuid4)
    tenant_id = factory.LazyFunction(uuid4)
    name = factory.Sequence(lambda n: f"Gefahrstoff {n}")
    status = "active"


class IdentifierFactory(DjangoModelFactory):
    class Meta:
        model = Identifier
    
    id = factory.LazyFunction(uuid4)
    tenant_id = factory.LazyAttribute(lambda o: o.substance.tenant_id)
    substance = factory.SubFactory(SubstanceFactory)
    id_type = "cas"
    id_value = factory.Sequence(lambda n: f"{1000+n}-00-{n%10}")


class SdsRevisionFactory(DjangoModelFactory):
    class Meta:
        model = SdsRevision
    
    id = factory.LazyFunction(uuid4)
    tenant_id = factory.LazyAttribute(lambda o: o.substance.tenant_id)
    substance = factory.SubFactory(SubstanceFactory)
    revision_number = factory.Sequence(lambda n: n + 1)
    revision_date = factory.LazyFunction(date.today)
    status = "draft"


class SdsClassificationFactory(DjangoModelFactory):
    class Meta:
        model = SdsClassification
    
    id = factory.LazyFunction(uuid4)
    tenant_id = factory.LazyAttribute(lambda o: o.sds_revision.tenant_id)
    sds_revision = factory.SubFactory(SdsRevisionFactory)
    signal_word = "Danger"
```

### 10.3 Service Tests

```python
# src/substances/tests/test_services.py

import pytest
from uuid import uuid4
from datetime import date
from unittest.mock import patch, MagicMock

from django.test import TestCase

from ..services.substance_service import SubstanceService
from ..services.sds_service import SdsService
from ..commands.commands import (
    CreateSubstanceCmd, UpdateSubstanceCmd, AddIdentifierCmd,
    UploadSdsCmd, ClassifySdsCmd, ApproveSdsCmd
)
from ..models import Substance, SdsRevision
from .factories import SubstanceFactory, SdsRevisionFactory


class SubstanceServiceTests(TestCase):
    
    def setUp(self):
        self.tenant_id = uuid4()
        self.user_id = uuid4()
        
        # Mock request context
        self.ctx_patcher = patch('substances.services.substance_service.get_context')
        self.mock_ctx = self.ctx_patcher.start()
        self.mock_ctx.return_value = MagicMock(
            tenant_id=self.tenant_id,
            user_id=self.user_id
        )
        
        # Mock authorization
        self.auth_patcher = patch('substances.services.substance_service.authorize')
        self.mock_auth = self.auth_patcher.start()
    
    def tearDown(self):
        self.ctx_patcher.stop()
        self.auth_patcher.stop()
    
    def test_create_substance_success(self):
        """Gefahrstoff erfolgreich anlegen"""
        cmd = CreateSubstanceCmd(
            name="Aceton",
            trade_name="Aceton technisch",
            storage_class="3",
            is_cmr=False,
        )
        
        substance = SubstanceService.create_substance(cmd)
        
        assert substance.name == "Aceton"
        assert substance.trade_name == "Aceton technisch"
        assert substance.storage_class == "3"
        assert substance.status == "active"
        assert substance.tenant_id == self.tenant_id
    
    def test_create_substance_duplicate_name_fails(self):
        """Doppelter Stoffname wird abgelehnt"""
        SubstanceFactory(tenant_id=self.tenant_id, name="Aceton")
        
        cmd = CreateSubstanceCmd(name="Aceton")
        
        with pytest.raises(ValueError) as exc:
            SubstanceService.create_substance(cmd)
        
        assert "existiert bereits" in str(exc.value)
    
    def test_add_identifier_cas_validation(self):
        """CAS-Nummer wird validiert"""
        substance = SubstanceFactory(tenant_id=self.tenant_id)
        
        # Gültige CAS
        cmd = AddIdentifierCmd(
            substance_id=substance.id,
            id_type="cas",
            id_value="67-64-1"  # Aceton
        )
        identifier = SubstanceService.add_identifier(cmd)
        assert identifier.id_value == "67-64-1"
        
        # Ungültige CAS (falsche Prüfziffer)
        cmd_invalid = AddIdentifierCmd(
            substance_id=substance.id,
            id_type="cas",
            id_value="67-64-9"  # Falsche Prüfziffer
        )
        with pytest.raises(ValueError) as exc:
            SubstanceService.add_identifier(cmd_invalid)
        assert "Ungültiges CAS-Format" in str(exc.value)


class SdsServiceTests(TestCase):
    
    def setUp(self):
        self.tenant_id = uuid4()
        self.user_id = uuid4()
        
        self.ctx_patcher = patch('substances.services.sds_service.get_context')
        self.mock_ctx = self.ctx_patcher.start()
        self.mock_ctx.return_value = MagicMock(
            tenant_id=self.tenant_id,
            user_id=self.user_id
        )
        
        self.auth_patcher = patch('substances.services.sds_service.authorize')
        self.mock_auth = self.auth_patcher.start()
    
    def tearDown(self):
        self.ctx_patcher.stop()
        self.auth_patcher.stop()
    
    def test_approve_sds_archives_previous(self):
        """Freigabe archiviert vorherige genehmigte Version"""
        substance = SubstanceFactory(tenant_id=self.tenant_id)
        
        # Erste SDS freigeben
        sds1 = SdsRevisionFactory(
            substance=substance,
            tenant_id=self.tenant_id,
            revision_number=1,
            status="approved"
        )
        
        # Zweite SDS als Entwurf
        sds2 = SdsRevisionFactory(
            substance=substance,
            tenant_id=self.tenant_id,
            revision_number=2,
            status="draft"
        )
        # Klassifikation hinzufügen (erforderlich für Freigabe)
        from .factories import SdsClassificationFactory
        SdsClassificationFactory(sds_revision=sds2)
        
        # Zweite SDS freigeben
        cmd = ApproveSdsCmd(sds_revision_id=sds2.id)
        SdsService.approve_sds(cmd)
        
        # Prüfen
        sds1.refresh_from_db()
        sds2.refresh_from_db()
        
        assert sds1.status == "archived"
        assert sds2.status == "approved"
    
    def test_approve_sds_detects_cmr(self):
        """CMR-Stoffe werden automatisch erkannt"""
        substance = SubstanceFactory(tenant_id=self.tenant_id, is_cmr=False)
        sds = SdsRevisionFactory(
            substance=substance,
            tenant_id=self.tenant_id,
            status="draft"
        )
        
        # Klassifizieren mit CMR H-Satz
        classify_cmd = ClassifySdsCmd(
            sds_revision_id=sds.id,
            signal_word="Danger",
            hazard_statements=["H350"],  # Kann Krebs erzeugen
            pictograms=["GHS08"],
        )
        SdsService.classify_sds(classify_cmd)
        
        # Freigeben
        approve_cmd = ApproveSdsCmd(sds_revision_id=sds.id)
        SdsService.approve_sds(approve_cmd)
        
        # Prüfen
        substance.refresh_from_db()
        assert substance.is_cmr is True
```

---

## 11. Implementierungsplan

### 11.1 Sprint-Übersicht

```
┌─────────────────────────────────────────────────────────────────┐
│                    IMPLEMENTIERUNGSPLAN                         │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  SPRINT 1 (Woche 1-2): FOUNDATION                              │
│  ════════════════════════════════════════                      │
│  • Django App Struktur                                         │
│  • Models + Migrations                                         │
│  • Seed-Daten (H-/P-Sätze, Piktogramme)                       │
│  • Admin-Interface                                             │
│  • Basis-Tests + Factories                                     │
│                                                                 │
│  SPRINT 2 (Woche 3-4): CORE CRUD                               │
│  ════════════════════════════════════════                      │
│  • Substance Service + Views                                   │
│  • SDS Upload Service                                          │
│  • Klassifikation Service + UI                                 │
│  • Party Management                                            │
│  • HTMX Integration                                            │
│                                                                 │
│  SPRINT 3 (Woche 5-6): FEATURES                                │
│  ════════════════════════════════════════                      │
│  • Freigabe-Workflow                                           │
│  • Inventar-Verwaltung                                         │
│  • Suche + Filter (Live-Search)                               │
│  • RBAC Integration                                            │
│  • Audit-Events                                                │
│                                                                 │
│  SPRINT 4 (Woche 7-8): EXPORT + POLISH                         │
│  ════════════════════════════════════════                      │
│  • Excel-Export (Gefahrstoffverzeichnis)                      │
│  • PDF-Export (SDS-Compliance)                                │
│  • E2E Tests                                                   │
│  • Performance-Optimierung                                     │
│  • Dokumentation                                               │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### 11.2 Detaillierter Taskplan

#### Sprint 1: Foundation (10 Arbeitstage)

| Task | Story Points | Assignee | Status |
|------|-------------|----------|--------|
| App-Struktur erstellen | 1 | - | ⬜ |
| Party Model + Migration | 2 | - | ⬜ |
| Substance Model + Migration | 3 | - | ⬜ |
| Identifier Model + Migration | 2 | - | ⬜ |
| SDS Models + Migration | 3 | - | ⬜ |
| Inventory Model + Migration | 2 | - | ⬜ |
| Reference Tables + Migration | 2 | - | ⬜ |
| Seed Command: H-Sätze | 2 | - | ⬜ |
| Seed Command: P-Sätze | 1 | - | ⬜ |
| Seed Command: Demo-Daten | 2 | - | ⬜ |
| Admin-Interface | 3 | - | ⬜ |
| Test Factories | 2 | - | ⬜ |
| Model Tests | 3 | - | ⬜ |
| **Sprint 1 Total** | **28 SP** | | |

#### Sprint 2: Core CRUD (10 Arbeitstage)

| Task | Story Points | Assignee | Status |
|------|-------------|----------|--------|
| Commands/DTOs definieren | 2 | - | ⬜ |
| SubstanceService implementieren | 5 | - | ⬜ |
| SubstanceService Tests | 3 | - | ⬜ |
| SdsService implementieren | 5 | - | ⬜ |
| SdsService Tests | 3 | - | ⬜ |
| PartyService implementieren | 2 | - | ⬜ |
| Query-Helpers | 3 | - | ⬜ |
| Substance Views | 5 | - | ⬜ |
| SDS Views | 4 | - | ⬜ |
| Templates (Basis) | 5 | - | ⬜ |
| HTMX Partials | 3 | - | ⬜ |
| Forms | 3 | - | ⬜ |
| **Sprint 2 Total** | **43 SP** | | |

#### Sprint 3: Features (10 Arbeitstage)

| Task | Story Points | Assignee | Status |
|------|-------------|----------|--------|
| Freigabe-Workflow | 5 | - | ⬜ |
| InventoryService | 5 | - | ⬜ |
| Inventory Views | 4 | - | ⬜ |
| Inventory Templates | 3 | - | ⬜ |
| Live-Search (HTMX) | 3 | - | ⬜ |
| Filter-Komponenten | 3 | - | ⬜ |
| RBAC Permissions | 3 | - | ⬜ |
| Permission Decorators | 2 | - | ⬜ |
| Audit-Events prüfen | 2 | - | ⬜ |
| Integration Tests | 5 | - | ⬜ |
| **Sprint 3 Total** | **35 SP** | | |

#### Sprint 4: Export + Polish (10 Arbeitstage)

| Task | Story Points | Assignee | Status |
|------|-------------|----------|--------|
| Excel-Export Gefahrstoffverz. | 5 | - | ⬜ |
| PDF-Export SDS-Compliance | 5 | - | ⬜ |
| Export-Views | 3 | - | ⬜ |
| Export als Job/Artefakt | 3 | - | ⬜ |
| E2E Tests (Playwright) | 5 | - | ⬜ |
| Performance-Optimierung | 3 | - | ⬜ |
| UI Polish + Responsive | 3 | - | ⬜ |
| Dokumentation | 3 | - | ⬜ |
| Code Review + Bugfixes | 5 | - | ⬜ |
| **Sprint 4 Total** | **35 SP** | | |

### 11.3 Meilensteine

| Meilenstein | Datum | Deliverable |
|-------------|-------|-------------|
| M1: Foundation Complete | Woche 2 | Models, Migrations, Admin |
| M2: Core CRUD Ready | Woche 4 | Gefahrstoffe + SDS verwaltbar |
| M3: Feature Complete | Woche 6 | Workflow, Inventar, Suche |
| M4: MVP Release | Woche 8 | Exports, Tests, Dokumentation |

---

## 12. Deployment & Operations

### 12.1 Deployment-Checkliste

```markdown
## Pre-Deployment

- [ ] Migrations auf Staging getestet
- [ ] Seed-Daten (H-/P-Sätze) vorhanden
- [ ] RBAC Permissions angelegt
- [ ] Rollen-Templates konfiguriert
- [ ] Feature-Flag gesetzt (falls verwendet)
- [ ] Monitoring-Alerts konfiguriert
- [ ] Backup erstellt

## Deployment

- [ ] Migrations ausführen
- [ ] Seed-Commands ausführen
- [ ] Static Files collecten
- [ ] Cache invalidieren
- [ ] Health-Check bestätigt

## Post-Deployment

- [ ] Smoke Tests durchführen
- [ ] Monitoring prüfen
- [ ] Error-Rate beobachten
- [ ] Performance-Metriken prüfen
```

### 12.2 Rollback-Plan

1. **Feature Flag deaktivieren** (falls vorhanden)
2. **Oder:** Deployment auf vorherige Version
3. Migrations sind backward-compatible (Expand/Contract)
4. Neue Tabellen können bestehen bleiben

### 12.3 Monitoring

```yaml
# Alerts für SDS-Modul

alerts:
  - name: sds_5xx_rate_high
    condition: rate(http_requests_total{status=~"5..", path=~"/substances/.*"}[5m]) > 0.01
    severity: critical
    
  - name: sds_latency_high
    condition: histogram_quantile(0.95, http_request_duration_seconds{path=~"/substances/.*"}) > 2
    severity: warning
    
  - name: sds_export_failures
    condition: rate(sds_export_failures_total[1h]) > 0
    severity: warning
```

---

## 13. Anhänge

### 13.1 H-Sätze (Auszug)

| Code | Kategorie | Text (DE) | CMR |
|------|-----------|-----------|-----|
| H200 | Physikalisch | Instabil, explosiv | - |
| H225 | Physikalisch | Flüssigkeit und Dampf leicht entzündbar | - |
| H302 | Gesundheit | Gesundheitsschädlich bei Verschlucken | - |
| H340 | Gesundheit | Kann genetische Defekte verursachen | ✅ |
| H350 | Gesundheit | Kann Krebs erzeugen | ✅ |
| H360 | Gesundheit | Kann die Fruchtbarkeit beeinträchtigen | ✅ |
| H400 | Umwelt | Sehr giftig für Wasserorganismen | - |

### 13.2 GHS-Piktogramme

| Code | Symbol | Beschreibung |
|------|--------|--------------|
| GHS01 | 💥 | Explodierende Bombe |
| GHS02 | 🔥 | Flamme |
| GHS03 | 🔥⭕ | Flamme über Kreis |
| GHS04 | 🧪 | Gasflasche |
| GHS05 | ⚗️ | Ätzwirkung |
| GHS06 | ☠️ | Totenkopf |
| GHS07 | ⚠️ | Ausrufezeichen |
| GHS08 | 🫁 | Gesundheitsgefahr |
| GHS09 | 🌳 | Umwelt |

### 13.3 Lagerklassen nach TRGS 510

Vollständige Liste im Model `Substance.StorageClass`.

---

**Dokument erstellt:** 2026-01-28  
**Nächste Review:** Nach Sprint 2  
**Verantwortlich:** Development Team
