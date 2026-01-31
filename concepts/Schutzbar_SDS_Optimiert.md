# Schutzbar SDS – Optimiertes Implementierungskonzept

**Version:** 2.0  
**Stand:** 2026-01-31  
**Basis:** Schutzbar_SDS_Implementierungskonzept.md  
**Optimiert für:** risk-hub Platform Architecture

---

## 1. Kernprinzipien (Optimiert)

### 1.1 Lean MVP - Schneller Produktivstart

```
┌─────────────────────────────────────────────────────────────────┐
│                    MVP SCOPE (4 Wochen)                          │
├─────────────────────────────────────────────────────────────────┤
│  Phase 1 (Woche 1-2):                                           │
│    ✅ Substance Model + Party                                    │
│    ✅ SDS-Upload (PDF) mit Versionierung                        │
│    ✅ Manuelle H-/P-Satz Zuordnung                              │
│    ✅ Admin Interface                                            │
│                                                                  │
│  Phase 2 (Woche 3-4):                                           │
│    ✅ Standort-Inventar                                          │
│    ✅ Gefahrstoffverzeichnis Export (Excel)                     │
│    ✅ Integration mit explosionsschutz                          │
│    ✅ Basic HTMX Views                                           │
│                                                                  │
│  Phase 3 (Post-MVP):                                            │
│    ⏳ PDF-Parsing mit AI                                         │
│    ⏳ Workflow (Draft → Approved)                                │
│    ⏳ Betriebsanweisung-Generator                               │
└─────────────────────────────────────────────────────────────────┘
```

### 1.2 Architektur-Alignment mit risk-hub

Das Modul folgt der bestehenden risk-hub Architektur:

```python
# Gleiche Patterns wie explosionsschutz:
- TenantScopedModel für Multi-Tenancy
- UUID Primary Keys
- Services für Business Logic
- Commands/Queries Pattern
- HTMX für Frontend
```

---

## 2. Datenmodell (Optimiert)

### 2.1 Vereinfachtes ER-Diagramm

```
┌─────────────────────────────────────────────────────────────────┐
│                    SUBSTANCES (Minimal Viable)                   │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌─────────────┐       ┌─────────────────┐                      │
│  │   Party     │       │    Substance    │                      │
│  │ (Hersteller)│◄──────│   (Gefahrstoff) │                      │
│  └─────────────┘       └────────┬────────┘                      │
│                                 │                                │
│                    ┌────────────┼────────────┐                  │
│                    │            │            │                  │
│                    ▼            ▼            ▼                  │
│           ┌─────────────┐ ┌──────────┐ ┌──────────────┐        │
│           │ SdsRevision │ │Identifier│ │SiteInventory │        │
│           │   (PDF +    │ │(CAS, UFI)│ │    Item      │        │
│           │ Metadaten)  │ └──────────┘ └──────────────┘        │
│           └──────┬──────┘                                       │
│                  │                                               │
│         ┌────────┼────────┐                                     │
│         ▼        ▼        ▼                                     │
│   ┌──────────┐ ┌────────┐ ┌────────┐                           │
│   │ H-Sätze  │ │P-Sätze │ │Pikto-  │                           │
│   │ (M2M)    │ │ (M2M)  │ │gramme  │                           │
│   └──────────┘ └────────┘ └────────┘                           │
│                                                                  │
│  ════════════════════════════════════════════════════════════   │
│                    REFERENZTABELLEN (Seed Data)                 │
│  ════════════════════════════════════════════════════════════   │
│                                                                  │
│  HazardStatementRef │ PrecautionaryRef │ PictogramRef          │
│  (H200-H420)        │ (P101-P502)      │ (GHS01-GHS09)         │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### 2.2 Django Models (Kompakt)

```python
# src/substances/models.py

from django.db import models
from common.models import TenantScopedModel
import uuid


class Party(TenantScopedModel):
    """Hersteller oder Lieferant"""
    
    class PartyType(models.TextChoices):
        MANUFACTURER = "manufacturer", "Hersteller"
        SUPPLIER = "supplier", "Lieferant"
    
    name = models.CharField(max_length=240)
    party_type = models.CharField(max_length=20, choices=PartyType.choices)
    email = models.EmailField(blank=True, default="")
    phone = models.CharField(max_length=50, blank=True, default="")
    address = models.TextField(blank=True, default="")
    
    class Meta:
        db_table = "substances_party"
        constraints = [
            models.UniqueConstraint(
                fields=["tenant_id", "party_type", "name"],
                name="uq_party_tenant_type_name"
            ),
        ]


class Substance(TenantScopedModel):
    """Gefahrstoff / Chemisches Produkt"""
    
    class Status(models.TextChoices):
        ACTIVE = "active", "Aktiv"
        INACTIVE = "inactive", "Inaktiv"
        ARCHIVED = "archived", "Archiviert"
    
    class StorageClass(models.TextChoices):
        """Lagerklassen nach TRGS 510 (Kurzform)"""
        SC_3 = "3", "3 - Entzündbare Flüssigkeiten"
        SC_6_1 = "6.1", "6.1 - Toxische Stoffe"
        SC_8 = "8", "8 - Ätzende Stoffe"
        SC_10 = "10", "10 - Brennbare Flüssigkeiten"
        SC_11 = "11", "11 - Brennbare Feststoffe"
        SC_12 = "12", "12 - Nicht brennbare Flüssigkeiten"
        SC_13 = "13", "13 - Nicht brennbare Feststoffe"
    
    # Stammdaten
    name = models.CharField(max_length=240, help_text="Produktname")
    trade_name = models.CharField(max_length=240, blank=True, default="")
    description = models.TextField(blank=True, default="")
    
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
        default=""
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
        related_name="manufactured_substances"
    )
    
    # Ex-Schutz-relevante Daten (aus SDS extrahiert)
    flash_point_c = models.FloatField(null=True, blank=True)
    ignition_temperature_c = models.FloatField(null=True, blank=True)
    lower_explosion_limit = models.FloatField(null=True, blank=True)
    upper_explosion_limit = models.FloatField(null=True, blank=True)
    temperature_class = models.CharField(max_length=10, blank=True, default="")
    explosion_group = models.CharField(max_length=10, blank=True, default="")
    
    class Meta:
        db_table = "substances_substance"
        constraints = [
            models.UniqueConstraint(
                fields=["tenant_id", "name"],
                name="uq_substance_tenant_name"
            ),
        ]
    
    @property
    def current_sds(self):
        """Aktuell gültige SDS-Revision"""
        return self.sds_revisions.filter(
            status="approved"
        ).order_by("-revision_date").first()
    
    @property
    def cas_number(self):
        """CAS-Nummer (falls vorhanden)"""
        ident = self.identifiers.filter(id_type="cas").first()
        return ident.id_value if ident else None


class Identifier(TenantScopedModel):
    """Stoffkennungen (CAS, EC, UFI)"""
    
    class IdType(models.TextChoices):
        CAS = "cas", "CAS-Nummer"
        EC = "ec", "EC-Nummer"
        UFI = "ufi", "UFI-Code"
        INTERNAL = "internal", "Interne Nummer"
    
    substance = models.ForeignKey(
        Substance,
        on_delete=models.CASCADE,
        related_name="identifiers"
    )
    id_type = models.CharField(max_length=20, choices=IdType.choices)
    id_value = models.CharField(max_length=100)
    
    class Meta:
        db_table = "substances_identifier"
        constraints = [
            models.UniqueConstraint(
                fields=["tenant_id", "substance", "id_type"],
                name="uq_identifier_substance_type"
            ),
        ]


class SdsRevision(TenantScopedModel):
    """Sicherheitsdatenblatt-Revision"""
    
    class Status(models.TextChoices):
        DRAFT = "draft", "Entwurf"
        APPROVED = "approved", "Freigegeben"
        ARCHIVED = "archived", "Archiviert"
    
    class SignalWord(models.TextChoices):
        DANGER = "danger", "Gefahr"
        WARNING = "warning", "Achtung"
        NONE = "none", "Kein Signalwort"
    
    substance = models.ForeignKey(
        Substance,
        on_delete=models.CASCADE,
        related_name="sds_revisions"
    )
    
    # Versionierung
    revision_number = models.PositiveIntegerField(default=1)
    revision_date = models.DateField()
    
    # Dokument
    document = models.ForeignKey(
        "documents.DocumentVersion",
        on_delete=models.PROTECT,
        null=True,
        blank=True
    )
    
    # Klassifikation
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.DRAFT
    )
    signal_word = models.CharField(
        max_length=20,
        choices=SignalWord.choices,
        default=SignalWord.NONE
    )
    
    # H-/P-Sätze (ManyToMany zu Referenztabellen)
    hazard_statements = models.ManyToManyField(
        "HazardStatementRef",
        blank=True,
        related_name="sds_revisions"
    )
    precautionary_statements = models.ManyToManyField(
        "PrecautionaryStatementRef",
        blank=True,
        related_name="sds_revisions"
    )
    pictograms = models.ManyToManyField(
        "PictogramRef",
        blank=True,
        related_name="sds_revisions"
    )
    
    # Freigabe
    approved_by = models.UUIDField(null=True, blank=True)
    approved_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        db_table = "substances_sds_revision"
        ordering = ["-revision_date", "-revision_number"]
        constraints = [
            models.UniqueConstraint(
                fields=["substance", "revision_number"],
                name="uq_sds_substance_revision"
            ),
        ]


class SiteInventoryItem(TenantScopedModel):
    """Standort-Inventar: Welcher Stoff wo und wieviel"""
    
    class State(models.TextChoices):
        SOLID = "solid", "Fest"
        LIQUID = "liquid", "Flüssig"
        GAS = "gas", "Gasförmig"
    
    substance = models.ForeignKey(
        Substance,
        on_delete=models.CASCADE,
        related_name="inventory_items"
    )
    site = models.ForeignKey(
        "tenancy.Site",
        on_delete=models.CASCADE,
        related_name="substance_inventory"
    )
    
    quantity = models.DecimalField(max_digits=12, decimal_places=3)
    unit = models.CharField(max_length=20, default="kg")
    state = models.CharField(
        max_length=20,
        choices=State.choices,
        default=State.LIQUID
    )
    storage_location = models.CharField(max_length=200, blank=True, default="")
    
    responsible_user = models.UUIDField(null=True, blank=True)
    
    class Meta:
        db_table = "substances_site_inventory"
        constraints = [
            models.UniqueConstraint(
                fields=["tenant_id", "site", "substance", "storage_location"],
                name="uq_inventory_site_substance_location"
            ),
        ]


# ============================================================================
# REFERENZTABELLEN (Global, nicht tenant-spezifisch)
# ============================================================================

class HazardStatementRef(models.Model):
    """H-Sätze Referenztabelle (GHS)"""
    
    code = models.CharField(max_length=10, primary_key=True)  # H200, H225, etc.
    text_de = models.TextField()
    text_en = models.TextField(blank=True, default="")
    category = models.CharField(max_length=50, blank=True, default="")
    
    class Meta:
        db_table = "substances_ref_hazard_statement"
        ordering = ["code"]


class PrecautionaryStatementRef(models.Model):
    """P-Sätze Referenztabelle (GHS)"""
    
    code = models.CharField(max_length=20, primary_key=True)  # P101, P210+P233, etc.
    text_de = models.TextField()
    text_en = models.TextField(blank=True, default="")
    category = models.CharField(max_length=50, blank=True, default="")
    
    class Meta:
        db_table = "substances_ref_precautionary_statement"
        ordering = ["code"]


class PictogramRef(models.Model):
    """GHS-Piktogramme Referenztabelle"""
    
    code = models.CharField(max_length=10, primary_key=True)  # GHS01-GHS09
    name_de = models.CharField(max_length=100)
    name_en = models.CharField(max_length=100, blank=True, default="")
    svg_path = models.CharField(max_length=200, blank=True, default="")
    
    class Meta:
        db_table = "substances_ref_pictogram"
        ordering = ["code"]
```

---

## 3. Integration mit Explosionsschutz

### 3.1 Verbindung zu ExplosionConcept

```python
# src/explosionsschutz/models.py - Erweiterung

class ExplosionConcept(TenantScopedModel):
    # Bestehende Felder...
    
    # NEU: Direkter FK zu Substance
    substance = models.ForeignKey(
        "substances.Substance",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="explosion_concepts",
        help_text="Verknüpfter Gefahrstoff aus SDS-Register"
    )
    
    def sync_from_substance(self):
        """Synchronisiert Ex-relevante Daten vom Stoff"""
        if self.substance:
            self.flash_point_c = self.substance.flash_point_c
            self.ignition_temperature_c = self.substance.ignition_temperature_c
            self.lower_explosion_limit = self.substance.lower_explosion_limit
            self.upper_explosion_limit = self.substance.upper_explosion_limit
            self.temperature_class = self.substance.temperature_class
            self.explosion_group = self.substance.explosion_group
            self.save(update_fields=[
                "flash_point_c", "ignition_temperature_c",
                "lower_explosion_limit", "upper_explosion_limit",
                "temperature_class", "explosion_group"
            ])
```

### 3.2 Calculation Tools - Substance Lookup

```python
# src/explosionsschutz/calculations.py - Erweiterung

def get_substance_properties(substance_name: str) -> dict:
    """
    Sucht Stoffeigenschaften:
    1. Zuerst in substances.Substance (DB)
    2. Fallback: SUBSTANCE_DATABASE (hardcoded)
    """
    from substances.models import Substance
    
    # 1. DB-Suche
    substance = Substance.objects.filter(
        name__iexact=substance_name,
        status="active"
    ).first()
    
    if substance:
        return {
            "success": True,
            "substance": {
                "name": substance.name,
                "cas_number": substance.cas_number,
                "lower_explosion_limit": substance.lower_explosion_limit,
                "upper_explosion_limit": substance.upper_explosion_limit,
                "flash_point_c": substance.flash_point_c,
                "ignition_temperature_c": substance.ignition_temperature_c,
                "temperature_class": substance.temperature_class,
                "explosion_group": substance.explosion_group,
            },
            "source": "Schutzbar SDS-Register"
        }
    
    # 2. Fallback: Hardcoded Database
    return _get_from_hardcoded_db(substance_name)
```

---

## 4. Services (Command/Query Pattern)

### 4.1 Commands

```python
# src/substances/commands.py

from dataclasses import dataclass
from typing import Optional, List
from uuid import UUID
from datetime import date


@dataclass
class CreateSubstanceCmd:
    name: str
    manufacturer_id: Optional[UUID] = None
    trade_name: str = ""
    description: str = ""
    storage_class: str = ""
    is_cmr: bool = False
    cas_number: Optional[str] = None


@dataclass
class UploadSdsCmd:
    substance_id: UUID
    revision_date: date
    document_id: UUID
    signal_word: str = "none"
    hazard_statement_codes: List[str] = None
    precautionary_statement_codes: List[str] = None
    pictogram_codes: List[str] = None


@dataclass  
class ApproveSdsCmd:
    sds_revision_id: UUID
    notes: str = ""


@dataclass
class UpdateInventoryCmd:
    substance_id: UUID
    site_id: UUID
    quantity: float
    unit: str = "kg"
    state: str = "liquid"
    storage_location: str = ""
```

### 4.2 Services

```python
# src/substances/services.py

from django.db import transaction
from .models import Substance, SdsRevision, SiteInventoryItem
from .commands import CreateSubstanceCmd, UploadSdsCmd, ApproveSdsCmd


def create_substance(
    cmd: CreateSubstanceCmd,
    tenant_id: UUID,
    user_id: UUID
) -> Substance:
    """Erstellt neuen Gefahrstoff"""
    with transaction.atomic():
        substance = Substance.objects.create(
            tenant_id=tenant_id,
            name=cmd.name,
            trade_name=cmd.trade_name,
            description=cmd.description,
            storage_class=cmd.storage_class,
            is_cmr=cmd.is_cmr,
            manufacturer_id=cmd.manufacturer_id,
            created_by=user_id,
        )
        
        if cmd.cas_number:
            substance.identifiers.create(
                tenant_id=tenant_id,
                id_type="cas",
                id_value=cmd.cas_number
            )
        
        return substance


def upload_sds(
    cmd: UploadSdsCmd,
    tenant_id: UUID,
    user_id: UUID
) -> SdsRevision:
    """Lädt neue SDS-Revision hoch"""
    substance = Substance.objects.get(id=cmd.substance_id, tenant_id=tenant_id)
    
    # Nächste Revisionsnummer
    last_rev = substance.sds_revisions.order_by("-revision_number").first()
    next_num = (last_rev.revision_number + 1) if last_rev else 1
    
    with transaction.atomic():
        sds = SdsRevision.objects.create(
            tenant_id=tenant_id,
            substance=substance,
            revision_number=next_num,
            revision_date=cmd.revision_date,
            document_id=cmd.document_id,
            signal_word=cmd.signal_word,
            created_by=user_id,
        )
        
        # H-Sätze
        if cmd.hazard_statement_codes:
            sds.hazard_statements.set(
                HazardStatementRef.objects.filter(
                    code__in=cmd.hazard_statement_codes
                )
            )
        
        # P-Sätze
        if cmd.precautionary_statement_codes:
            sds.precautionary_statements.set(
                PrecautionaryStatementRef.objects.filter(
                    code__in=cmd.precautionary_statement_codes
                )
            )
        
        # Piktogramme
        if cmd.pictogram_codes:
            sds.pictograms.set(
                PictogramRef.objects.filter(code__in=cmd.pictogram_codes)
            )
        
        return sds


def approve_sds(
    cmd: ApproveSdsCmd,
    tenant_id: UUID,
    user_id: UUID
) -> SdsRevision:
    """Gibt SDS-Revision frei"""
    from django.utils import timezone
    
    sds = SdsRevision.objects.get(
        id=cmd.sds_revision_id,
        tenant_id=tenant_id
    )
    
    # Vorherige Revision archivieren
    sds.substance.sds_revisions.filter(
        status="approved"
    ).update(status="archived")
    
    sds.status = "approved"
    sds.approved_by = user_id
    sds.approved_at = timezone.now()
    sds.save()
    
    return sds
```

---

## 5. Export: Gefahrstoffverzeichnis

```python
# src/substances/exports/hazard_register_excel.py

import io
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Border, Alignment
from django.db.models import Q


def generate_hazard_register_excel(tenant_id: UUID, site_id: UUID = None) -> io.BytesIO:
    """
    Generiert Gefahrstoffverzeichnis nach GefStoffV §6 als Excel.
    """
    wb = Workbook()
    ws = wb.active
    ws.title = "Gefahrstoffverzeichnis"
    
    # Header
    headers = [
        "Nr.", "Stoffname", "CAS-Nr.", "Handelsname", 
        "Hersteller", "Lagerklasse", "CMR", "Menge", "Einheit",
        "Lagerort", "H-Sätze", "P-Sätze", "Piktogramme",
        "SDS-Datum", "SDS-Status"
    ]
    
    header_fill = PatternFill(start_color="4472C4", fill_type="solid")
    header_font = Font(color="FFFFFF", bold=True)
    
    for col, header in enumerate(headers, 1):
        cell = ws.cell(row=1, column=col, value=header)
        cell.fill = header_fill
        cell.font = header_font
        cell.alignment = Alignment(horizontal="center")
    
    # Daten
    query = Q(tenant_id=tenant_id, status="active")
    if site_id:
        substances = Substance.objects.filter(
            query,
            inventory_items__site_id=site_id
        ).distinct()
    else:
        substances = Substance.objects.filter(query)
    
    for row_num, substance in enumerate(substances, 2):
        current_sds = substance.current_sds
        inventory = substance.inventory_items.first()
        
        ws.cell(row=row_num, column=1, value=row_num - 1)
        ws.cell(row=row_num, column=2, value=substance.name)
        ws.cell(row=row_num, column=3, value=substance.cas_number or "")
        ws.cell(row=row_num, column=4, value=substance.trade_name)
        ws.cell(row=row_num, column=5, value=substance.manufacturer.name if substance.manufacturer else "")
        ws.cell(row=row_num, column=6, value=substance.storage_class)
        ws.cell(row=row_num, column=7, value="Ja" if substance.is_cmr else "Nein")
        ws.cell(row=row_num, column=8, value=float(inventory.quantity) if inventory else "")
        ws.cell(row=row_num, column=9, value=inventory.unit if inventory else "")
        ws.cell(row=row_num, column=10, value=inventory.storage_location if inventory else "")
        
        if current_sds:
            ws.cell(row=row_num, column=11, value=", ".join(
                h.code for h in current_sds.hazard_statements.all()
            ))
            ws.cell(row=row_num, column=12, value=", ".join(
                p.code for p in current_sds.precautionary_statements.all()
            ))
            ws.cell(row=row_num, column=13, value=", ".join(
                p.code for p in current_sds.pictograms.all()
            ))
            ws.cell(row=row_num, column=14, value=current_sds.revision_date.strftime("%d.%m.%Y"))
            ws.cell(row=row_num, column=15, value=current_sds.get_status_display())
    
    # Spaltenbreiten
    column_widths = [5, 30, 15, 25, 20, 10, 5, 10, 8, 20, 30, 40, 20, 12, 12]
    for i, width in enumerate(column_widths, 1):
        ws.column_dimensions[chr(64 + i)].width = width
    
    buffer = io.BytesIO()
    wb.save(buffer)
    buffer.seek(0)
    return buffer
```

---

## 6. Implementierungsreihenfolge

### Woche 1: Foundation

```bash
# 1. App erstellen
python manage.py startapp substances src/substances

# 2. Models implementieren
# 3. Migrations erstellen
python manage.py makemigrations substances
python manage.py migrate

# 4. Admin Interface
# 5. Seed Data (H-/P-Sätze, Piktogramme)
python manage.py seed_hazard_statements
python manage.py seed_pictograms
```

### Woche 2: Core Services

- [ ] Services (create_substance, upload_sds, approve_sds)
- [ ] SDS-Upload View mit Dokument-Handling
- [ ] Basic API Endpoints

### Woche 3: Inventory & Integration

- [ ] SiteInventoryItem CRUD
- [ ] Integration mit explosionsschutz
- [ ] Substance Lookup in Calculations

### Woche 4: Export & Polish

- [ ] Gefahrstoffverzeichnis Excel Export
- [ ] HTMX Views für Frontend
- [ ] Testing & Documentation

---

## 7. Dateien zu erstellen

```
src/substances/
├── __init__.py
├── apps.py
├── models.py                 # Alle Models
├── admin.py                  # Admin Interface
├── services.py               # Business Logic
├── commands.py               # Command DTOs
├── urls.py                   # URL Routing
├── views.py                  # API Views
├── template_views.py         # HTMX Views
├── serializers.py            # DRF Serializers
├── forms.py                  # Django Forms
├── exports/
│   ├── __init__.py
│   └── hazard_register_excel.py
├── management/
│   └── commands/
│       ├── seed_hazard_statements.py
│       └── seed_pictograms.py
├── fixtures/
│   ├── h_statements.json
│   ├── p_statements.json
│   └── pictograms.json
├── templates/
│   └── substances/
│       ├── home.html
│       ├── substance_list.html
│       ├── substance_detail.html
│       ├── substance_form.html
│       ├── sds_upload.html
│       └── inventory_list.html
└── tests/
    ├── __init__.py
    ├── test_models.py
    ├── test_services.py
    └── test_views.py
```

---

## 8. Zusammenfassung

| Aspekt | Original | Optimiert |
|--------|----------|-----------|
| Timeline | 6-8 Wochen | **4 Wochen** |
| Models | 10 | **8** (weniger Komplexität) |
| Workflow | 4 Status | **3 Status** (Draft→Approved→Archived) |
| Integration | Separat | **Direkt mit explosionsschutz** |
| Referenzdaten | Inline | **Fixtures + Seed Commands** |
| Export | Excel + PDF | **Excel MVP** (PDF später) |

**Nächster Schritt:** `python manage.py startapp substances src/substances`
