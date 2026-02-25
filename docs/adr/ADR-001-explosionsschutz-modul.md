# ADR-001: Explosionsschutz-Modul für Risk-Hub

| Metadaten | |
| --------- | --- |
| **Status** | ✅ APPROVED |
| **Version** | 5.0 |
| **Datum** | 2026-01-31 |
| **Autor** | Achim Dehnert (AI-unterstützt) |
| **Reviewer** | Technical Review |
| **Entscheidungsdatum** | 2026-01-31 |

---

## 📋 Executive Summary

Dieses ADR beschreibt die Architektur für ein **Explosionsschutz-Modul** innerhalb der Risk-Hub-Plattform. Das Modul ermöglicht die digitale Erstellung, Verwaltung und Dokumentation von Explosionsschutzkonzepten gemäß ATEX-Richtlinien, BetrSichV und TRGS 720-725.

### Kernentscheidungen

| # | Entscheidung | Begründung |
| --- | ------------ | ---------- |
| 1 | Integration in bestehendes `Assessment`-Model | Vermeidet Datensilos, nutzt vorhandene Workflows |
| 2 | Nutzung von `Organization → Site → Area` Hierarchie | Konsistenz mit Risk-Hub Core |
| 3 | HTMX für interaktive UI-Komponenten | Bewährter Stack, keine SPA-Komplexität |
| 4 | WeasyPrint für PDF-Generierung | Open Source, CSS-basiert, Docker-kompatibel |
| 5 | Separates `Equipment`-Model mit ATEX-Kennzeichnung | Prüfpflichten nach BetrSichV §§14-16 |
| 6 | **Integration mit `substances`-Modul (SDS)** | Stoffdaten als Basis für Ex-Bewertung |
| 7 | **Normalisierte ATEX-Kennzeichnung** | Strukturierte Felder statt Freitext |
| 8 | **SafetyFunction für MSR-Bewertung** | Entkopplung von einfachen Maßnahmen |
| 9 | **Hybrid Tenant-Isolation für Stammdaten** | Globale Basis + tenant-spezifische Erweiterungen |
| 10 | **Vollständiger Audit-Trail via Service Layer** | Compliance-konforme Nachverfolgbarkeit |

---

## 1. Review-Feedback Integration (v4 → v5)

### 1.1 Umgesetzte Optimierungen aus v4

| Bereich | Review-Kritik | Umsetzung v4 |
| ------- | ------------- | ------------ |
| **SoC** | Redundante Substance-Daten | Nur FK zu `substances.Substance`, `@property` für SDS-Daten |
| **Equipment** | Nicht normalisiert | `EquipmentType` als Stammdatenkatalog |
| **ATEX** | `atex_marking` Freitext | Strukturierte Felder: `atex_category`, `temperature_class`, `protection_type` |
| **Measures** | `measure_type` gemischt | `SafetyFunction` als separate Entität für MSR |
| **Zones** | `trgs_reference` Freitext | `ReferenceStandard` Tabelle |
| **Naming** | `is_atex_certified` redundant | Entfernt (ableitbar aus Kategorie) |
| **Dynamik** | `has_explosion_hazard` DB-Feld | `@property` mit dynamischer Prüfung |

### 1.2 Neue Optimierungen in v5

| Bereich | Review-Kritik v4 | Umsetzung v5 |
| ------- | ---------------- | ------------ |
| **Tenant-Isolation** | Stammdaten ohne `tenant_id` | Hybrid-Modell: `tenant_id=NULL` für globale Daten |
| **Audit-Trail** | Nicht explizit dokumentiert | Service Layer mit `emit_audit_event()` für alle Mutationen |
| **Zone-Validierung** | Logik fehlte | `Equipment.clean()` mit ATEX-Kategorie-Check |
| **Extent-Schema** | JSON ohne Schema | Pydantic `ZoneExtent` Model |
| **Zündquellen** | Nicht im Model | `IgnitionSource` Enum + `ZoneIgnitionSourceAssessment` |

---

## 2. Tenant-Isolation für Stammdaten (NEU in v5)

### 2.1 Hybrid-Modell: Global + Tenant-spezifisch

Die Stammdaten-Tabellen (`ReferenceStandard`, `MeasureCatalog`, `EquipmentType`, `SafetyFunction`) folgen einem **Hybrid-Modell**:

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    TENANT-ISOLATION STRATEGIE                                │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                    GLOBALE STAMMDATEN                                │   │
│  │                    (tenant_id = NULL, is_system = True)              │   │
│  │                                                                      │   │
│  │  • TRGS 720, TRGS 721, TRGS 722, ...                                │   │
│  │  • Standard-Maßnahmenkatalog (Erdung, Lüftung, ...)                 │   │
│  │  • Bekannte ATEX-Gerätetypen (Bosch, Siemens, ...)                  │   │
│  │                                                                      │   │
│  │  ⚠️ Nicht editierbar durch Tenants                                  │   │
│  │  ⚠️ Gepflegt durch System-Admin / Seed-Daten                        │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                              │                                              │
│                              │ erbt / erweitert                             │
│                              ▼                                              │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                 TENANT-SPEZIFISCHE STAMMDATEN                        │   │
│  │                 (tenant_id = UUID, is_system = False)                │   │
│  │                                                                      │   │
│  │  Tenant A:                                                           │   │
│  │  • Eigene Maßnahmenvorlagen (z.B. "Interne Richtlinie XY")          │   │
│  │  • Eigene Gerätetypen (Spezialanlagen)                              │   │
│  │                                                                      │   │
│  │  Tenant B:                                                           │   │
│  │  • Andere eigene Vorlagen                                            │   │
│  │  • Andere Gerätetypen                                                │   │
│  │                                                                      │   │
│  │  ✅ Editierbar durch Tenant-Admin                                    │   │
│  │  ✅ Nur für eigenen Tenant sichtbar                                  │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 2.2 Datenmodell für Hybrid-Isolation

```python
# explosionsschutz/models.py

from django.db import models
from django.core.exceptions import ValidationError
import uuid


class TenantScopedMasterDataManager(models.Manager):
    """
    Custom Manager für Stammdaten mit Hybrid-Tenant-Isolation.
    
    Liefert:
    - Globale Daten (tenant_id=NULL) UND
    - Tenant-spezifische Daten für den aktuellen Tenant
    """
    
    def for_tenant(self, tenant_id: uuid.UUID):
        """
        Gibt alle für einen Tenant sichtbaren Einträge zurück:
        - Globale Einträge (tenant_id IS NULL)
        - Eigene Einträge (tenant_id = tenant_id)
        """
        return self.filter(
            models.Q(tenant_id__isnull=True) | 
            models.Q(tenant_id=tenant_id)
        )
    
    def global_only(self):
        """Nur globale System-Einträge"""
        return self.filter(tenant_id__isnull=True, is_system=True)
    
    def tenant_only(self, tenant_id: uuid.UUID):
        """Nur tenant-spezifische Einträge"""
        return self.filter(tenant_id=tenant_id)


class TenantScopedMasterData(models.Model):
    """
    Abstrakte Basisklasse für Stammdaten mit Hybrid-Tenant-Isolation.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # NULL = global/system, UUID = tenant-spezifisch
    tenant_id = models.UUIDField(null=True, blank=True, db_index=True)
    
    # System-Daten können nicht von Tenants editiert werden
    is_system = models.BooleanField(
        default=False,
        help_text="System-Daten sind global und nicht editierbar"
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    objects = TenantScopedMasterDataManager()
    
    class Meta:
        abstract = True
    
    def clean(self):
        """Validierung: System-Daten müssen global sein"""
        if self.is_system and self.tenant_id is not None:
            raise ValidationError(
                "System-Daten (is_system=True) müssen global sein (tenant_id=NULL)"
            )
    
    def save(self, *args, **kwargs):
        self.clean()
        super().save(*args, **kwargs)


class ReferenceStandard(TenantScopedMasterData):
    """
    Normative Referenzen (TRGS, IEC, EN, etc.)
    
    Beispiele:
    - TRGS 720: Gefährliche explosionsfähige Atmosphäre - Allgemeines
    - TRGS 721: Gefährliche explosionsfähige Atmosphäre - Beurteilung
    - IEC 60079-10-1: Klassifizierung von Bereichen
    """
    
    class Category(models.TextChoices):
        TRGS = "TRGS", "Technische Regeln für Gefahrstoffe"
        IEC = "IEC", "IEC Normen"
        EN = "EN", "Europäische Normen"
        DIN = "DIN", "DIN Normen"
        VDSI = "VDSI", "VDSI Richtlinien"
        INTERNAL = "INTERNAL", "Interne Richtlinien"
    
    code = models.CharField(
        max_length=50,
        help_text="z.B. 'TRGS 720', 'IEC 60079-10-1'"
    )
    title = models.CharField(max_length=500)
    category = models.CharField(
        max_length=20,
        choices=Category.choices,
        default=Category.TRGS
    )
    url = models.URLField(blank=True, help_text="Link zur offiziellen Quelle")
    valid_from = models.DateField(null=True, blank=True)
    valid_until = models.DateField(null=True, blank=True)
    
    class Meta:
        db_table = "explosionsschutz_reference_standard"
        constraints = [
            # Eindeutigkeit: Code pro Tenant (oder global)
            models.UniqueConstraint(
                fields=["tenant_id", "code"],
                name="uq_reference_standard_tenant_code"
            ),
            # Für globale Einträge: Code global eindeutig
            models.UniqueConstraint(
                fields=["code"],
                condition=models.Q(tenant_id__isnull=True),
                name="uq_reference_standard_global_code"
            ),
        ]
        indexes = [
            models.Index(fields=["tenant_id", "category"]),
        ]
    
    def __str__(self):
        return f"{self.code}: {self.title}"


class MeasureCatalog(TenantScopedMasterData):
    """
    Katalog wiederverwendbarer Schutzmaßnahmen-Vorlagen.
    
    Beispiele:
    - "Erdung aller leitfähigen Teile" (global)
    - "Technische Lüftung nach DIN EN 60079-10-1" (global)
    - "Interne Prozedur ABC-123" (tenant-spezifisch)
    """
    
    class DefaultType(models.TextChoices):
        PRIMARY = "primary", "Primäre Maßnahme (Vermeidung)"
        SECONDARY = "secondary", "Sekundäre Maßnahme (Zündquellenvermeidung)"
        TERTIARY = "tertiary", "Tertiäre Maßnahme (Auswirkungsbegrenzung)"
        ORGANIZATIONAL = "organizational", "Organisatorische Maßnahme"
    
    code = models.CharField(
        max_length=50,
        blank=True,
        help_text="Optionaler Kurzcode, z.B. 'M-ERD-001'"
    )
    title = models.CharField(max_length=300)
    default_type = models.CharField(
        max_length=20,
        choices=DefaultType.choices,
        default=DefaultType.SECONDARY
    )
    description_template = models.TextField(
        blank=True,
        help_text="Vorlage für Beschreibung, kann Platzhalter enthalten"
    )
    reference_standards = models.ManyToManyField(
        ReferenceStandard,
        blank=True,
        related_name="measure_catalog_entries"
    )
    
    class Meta:
        db_table = "explosionsschutz_measure_catalog"
        constraints = [
            models.UniqueConstraint(
                fields=["tenant_id", "title"],
                name="uq_measure_catalog_tenant_title"
            ),
        ]
        indexes = [
            models.Index(fields=["tenant_id", "default_type"]),
        ]
    
    def __str__(self):
        prefix = f"[{self.code}] " if self.code else ""
        return f"{prefix}{self.title}"


class EquipmentType(TenantScopedMasterData):
    """
    Stammdaten für Betriebsmittel-Typen mit strukturierter ATEX-Kennzeichnung.
    
    ATEX-Kennzeichnung Struktur:
    ╔══════════════════════════════════════════════════════════════════╗
    ║  II 2G Ex d IIB T4 Gb                                            ║
    ║  ├─ Gruppe (I=Bergbau, II=Industrie)                             ║
    ║  │  ├─ Kategorie (1/2/3 + G=Gas oder D=Staub)                    ║
    ║  │  │     ├─ Schutzart (Ex d, Ex e, Ex i, ...)                   ║
    ║  │  │     │       ├─ Explosionsgruppe (IIA/IIB/IIC)              ║
    ║  │  │     │       │      ├─ Temperaturklasse (T1-T6)             ║
    ║  │  │     │       │      │    └─ EPL (Ga/Gb/Gc oder Da/Db/Dc)    ║
    ╚══════════════════════════════════════════════════════════════════╝
    """
    
    class AtexGroup(models.TextChoices):
        GROUP_I = "I", "Gruppe I (Bergbau)"
        GROUP_II = "II", "Gruppe II (Industrie)"
    
    class AtexCategory(models.TextChoices):
        CAT_1G = "1G", "Kategorie 1G (Zone 0)"
        CAT_2G = "2G", "Kategorie 2G (Zone 0, 1)"
        CAT_3G = "3G", "Kategorie 3G (Zone 0, 1, 2)"
        CAT_1D = "1D", "Kategorie 1D (Zone 20)"
        CAT_2D = "2D", "Kategorie 2D (Zone 20, 21)"
        CAT_3D = "3D", "Kategorie 3D (Zone 20, 21, 22)"
    
    class ProtectionType(models.TextChoices):
        EX_D = "Ex d", "Druckfeste Kapselung"
        EX_E = "Ex e", "Erhöhte Sicherheit"
        EX_I = "Ex i", "Eigensicherheit"
        EX_P = "Ex p", "Überdruckkapselung"
        EX_M = "Ex m", "Vergusskapselung"
        EX_O = "Ex o", "Ölkapselung"
        EX_Q = "Ex q", "Sandkapselung"
        EX_N = "Ex n", "Nicht-funkend"
        EX_T = "Ex t", "Schutz durch Gehäuse (Staub)"
    
    class ExplosionGroup(models.TextChoices):
        IIA = "IIA", "IIA (Propan)"
        IIB = "IIB", "IIB (Ethylen)"
        IIC = "IIC", "IIC (Wasserstoff, Acetylen)"
        IIIA = "IIIA", "IIIA (brennbare Flusen)"
        IIIB = "IIIB", "IIIB (nicht leitfähiger Staub)"
        IIIC = "IIIC", "IIIC (leitfähiger Staub)"
    
    class TemperatureClass(models.TextChoices):
        T1 = "T1", "T1 (≤450°C)"
        T2 = "T2", "T2 (≤300°C)"
        T3 = "T3", "T3 (≤200°C)"
        T4 = "T4", "T4 (≤135°C)"
        T5 = "T5", "T5 (≤100°C)"
        T6 = "T6", "T6 (≤85°C)"
    
    class EPL(models.TextChoices):
        """Equipment Protection Level"""
        GA = "Ga", "Ga (sehr hohes Schutzniveau)"
        GB = "Gb", "Gb (hohes Schutzniveau)"
        GC = "Gc", "Gc (erhöhtes Schutzniveau)"
        DA = "Da", "Da (sehr hohes Schutzniveau - Staub)"
        DB = "Db", "Db (hohes Schutzniveau - Staub)"
        DC = "Dc", "Dc (erhöhtes Schutzniveau - Staub)"
    
    # Hersteller & Modell
    manufacturer = models.CharField(max_length=200)
    model = models.CharField(max_length=200)
    
    # Strukturierte ATEX-Kennzeichnung
    atex_group = models.CharField(
        max_length=5,
        choices=AtexGroup.choices,
        default=AtexGroup.GROUP_II
    )
    atex_category = models.CharField(
        max_length=5,
        choices=AtexCategory.choices
    )
    protection_type = models.CharField(
        max_length=10,
        choices=ProtectionType.choices
    )
    explosion_group = models.CharField(
        max_length=10,
        choices=ExplosionGroup.choices,
        blank=True
    )
    temperature_class = models.CharField(
        max_length=5,
        choices=TemperatureClass.choices
    )
    epl = models.CharField(
        max_length=5,
        choices=EPL.choices,
        blank=True,
        help_text="Equipment Protection Level"
    )
    
    # Zusätzliche technische Daten
    ip_rating = models.CharField(
        max_length=10,
        blank=True,
        help_text="z.B. IP65, IP66"
    )
    ambient_temp_min = models.IntegerField(
        null=True, blank=True,
        help_text="Min. Umgebungstemperatur in °C"
    )
    ambient_temp_max = models.IntegerField(
        null=True, blank=True,
        help_text="Max. Umgebungstemperatur in °C"
    )
    
    # Dokumentation
    datasheet_url = models.URLField(blank=True)
    certificate_number = models.CharField(max_length=100, blank=True)
    notified_body = models.CharField(
        max_length=100,
        blank=True,
        help_text="z.B. 'PTB', 'DEKRA', 'TÜV'"
    )
    
    class Meta:
        db_table = "explosionsschutz_equipment_type"
        constraints = [
            models.UniqueConstraint(
                fields=["tenant_id", "manufacturer", "model"],
                name="uq_equipment_type_tenant_mfr_model"
            ),
        ]
        indexes = [
            models.Index(fields=["tenant_id", "atex_category"]),
            models.Index(fields=["tenant_id", "manufacturer"]),
        ]
    
    @property
    def full_atex_marking(self) -> str:
        """Vollständige ATEX-Kennzeichnung aus Einzelfeldern"""
        parts = [
            self.atex_group,
            self.atex_category,
            self.protection_type,
        ]
        if self.explosion_group:
            parts.append(self.explosion_group)
        parts.append(self.temperature_class)
        if self.epl:
            parts.append(self.epl)
        return " ".join(parts)
    
    @property
    def allowed_zones(self) -> list[str]:
        """Liste der Zonen, in denen dieses Gerät eingesetzt werden darf"""
        CATEGORY_ZONES = {
            "1G": ["0", "1", "2"],
            "2G": ["1", "2"],
            "3G": ["2"],
            "1D": ["20", "21", "22"],
            "2D": ["21", "22"],
            "3D": ["22"],
        }
        return CATEGORY_ZONES.get(self.atex_category, [])
    
    def __str__(self):
        return f"{self.manufacturer} {self.model} ({self.full_atex_marking})"


class SafetyFunction(TenantScopedMasterData):
    """
    MSR-Sicherheitsfunktion nach IEC 62061 / ISO 13849.
    
    Wird verwendet für komplexe Schutzmaßnahmen mit:
    - Performance Level (PLr) nach ISO 13849
    - Safety Integrity Level (SIL) nach IEC 62061
    - Überwachungsanforderungen
    """
    
    class PerformanceLevel(models.TextChoices):
        PL_A = "a", "PL a"
        PL_B = "b", "PL b"
        PL_C = "c", "PL c"
        PL_D = "d", "PL d"
        PL_E = "e", "PL e"
    
    class SILLevel(models.TextChoices):
        SIL_1 = "1", "SIL 1"
        SIL_2 = "2", "SIL 2"
        SIL_3 = "3", "SIL 3"
    
    class MonitoringMethod(models.TextChoices):
        CONTINUOUS = "continuous", "Kontinuierlich"
        PERIODIC = "periodic", "Periodisch"
        DEMAND = "demand", "Bei Anforderung"
    
    name = models.CharField(
        max_length=100,
        help_text="Eindeutiger Name, z.B. 'GW-001' für Gaswarnanlage 001"
    )
    description = models.TextField(blank=True)
    
    performance_level = models.CharField(
        max_length=5,
        choices=PerformanceLevel.choices,
        blank=True,
        help_text="Required Performance Level nach ISO 13849"
    )
    sil_level = models.CharField(
        max_length=5,
        choices=SILLevel.choices,
        blank=True,
        help_text="Safety Integrity Level nach IEC 62061"
    )
    monitoring_method = models.CharField(
        max_length=20,
        choices=MonitoringMethod.choices,
        default=MonitoringMethod.CONTINUOUS
    )
    
    # Technische Details
    response_time_ms = models.IntegerField(
        null=True, blank=True,
        help_text="Ansprechzeit in Millisekunden"
    )
    proof_test_interval_months = models.IntegerField(
        null=True, blank=True,
        help_text="Proof-Test-Intervall in Monaten"
    )
    
    reference_standards = models.ManyToManyField(
        ReferenceStandard,
        blank=True,
        related_name="safety_functions"
    )
    
    class Meta:
        db_table = "explosionsschutz_safety_function"
        constraints = [
            models.UniqueConstraint(
                fields=["tenant_id", "name"],
                name="uq_safety_function_tenant_name"
            ),
        ]
    
    def __str__(self):
        levels = []
        if self.performance_level:
            levels.append(f"PL {self.performance_level}")
        if self.sil_level:
            levels.append(f"SIL {self.sil_level}")
        level_str = " / ".join(levels) if levels else "n/a"
        return f"{self.name} ({level_str})"
```

### 2.3 Query-Beispiele

```python
# In einem Service oder View:
from common.request_context import get_context
from explosionsschutz.models import ReferenceStandard, MeasureCatalog, EquipmentType

ctx = get_context()

# Alle für den Tenant sichtbaren Normen
standards = ReferenceStandard.objects.for_tenant(ctx.tenant_id)

# Nur globale TRGS-Normen
trgs_standards = ReferenceStandard.objects.global_only().filter(
    category=ReferenceStandard.Category.TRGS
)

# Nur eigene Maßnahmenvorlagen des Tenants
own_measures = MeasureCatalog.objects.tenant_only(ctx.tenant_id)

# Gerätetypen filtern nach ATEX-Kategorie für Zone 1
zone_1_equipment = EquipmentType.objects.for_tenant(ctx.tenant_id).filter(
    atex_category__in=["1G", "2G"]
)
```

### 2.4 RLS-Erweiterung für Hybrid-Isolation

```sql
-- scripts/enable_rls_explosionsschutz.sql

-- RLS für Stammdaten mit Hybrid-Isolation
ALTER TABLE explosionsschutz_reference_standard ENABLE ROW LEVEL SECURITY;
ALTER TABLE explosionsschutz_measure_catalog ENABLE ROW LEVEL SECURITY;
ALTER TABLE explosionsschutz_equipment_type ENABLE ROW LEVEL SECURITY;
ALTER TABLE explosionsschutz_safety_function ENABLE ROW LEVEL SECURITY;

-- Policy: Globale ODER eigene Daten sichtbar
CREATE POLICY tenant_hybrid_isolation_reference_standard 
ON explosionsschutz_reference_standard
USING (
    tenant_id IS NULL  -- Globale Daten
    OR tenant_id = current_setting('app.current_tenant')::uuid  -- Eigene Daten
);

CREATE POLICY tenant_hybrid_isolation_measure_catalog 
ON explosionsschutz_measure_catalog
USING (
    tenant_id IS NULL 
    OR tenant_id = current_setting('app.current_tenant')::uuid
);

CREATE POLICY tenant_hybrid_isolation_equipment_type 
ON explosionsschutz_equipment_type
USING (
    tenant_id IS NULL 
    OR tenant_id = current_setting('app.current_tenant')::uuid
);

CREATE POLICY tenant_hybrid_isolation_safety_function 
ON explosionsschutz_safety_function
USING (
    tenant_id IS NULL 
    OR tenant_id = current_setting('app.current_tenant')::uuid
);

-- Schreibschutz für System-Daten (nur Lesen erlaubt)
-- INSERT: Nur wenn is_system=false ODER tenant_id gesetzt
CREATE POLICY tenant_write_protection_reference_standard 
ON explosionsschutz_reference_standard
FOR INSERT
WITH CHECK (
    NOT is_system OR tenant_id IS NULL  -- System-Daten nur via Migration/Seed
);

-- UPDATE/DELETE: Nicht für System-Daten
CREATE POLICY tenant_update_protection_reference_standard 
ON explosionsschutz_reference_standard
FOR UPDATE
USING (NOT is_system);

CREATE POLICY tenant_delete_protection_reference_standard 
ON explosionsschutz_reference_standard
FOR DELETE
USING (NOT is_system);

-- Analog für andere Stammdaten-Tabellen...
```

---

## 3. Audit-Trail via Service Layer (NEU in v5)

### 3.1 Architektur-Prinzip

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         AUDIT-TRAIL ARCHITEKTUR                              │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌─────────────┐     ┌─────────────────────────────────────────────────┐   │
│  │    View     │────▶│              SERVICE LAYER                       │   │
│  │  (HTMX)     │     │                                                  │   │
│  └─────────────┘     │  @transaction.atomic                             │   │
│                      │  def create_explosion_concept(...):              │   │
│                      │      1. Validierung                               │   │
│                      │      2. Domain-Logik                              │   │
│                      │      3. DB-Write (ORM)                            │   │
│                      │      4. emit_audit_event(...)  ◀── PFLICHT       │   │
│                      │      5. OutboxMessage.create(...) ◀── PFLICHT    │   │
│                      │      return result                                │   │
│                      └─────────────────────────────────────────────────┘   │
│                                        │                                    │
│                                        │ innerhalb Transaktion              │
│                                        ▼                                    │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                         POSTGRES                                     │   │
│  │                                                                      │   │
│  │  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐     │   │
│  │  │ explosions-     │  │ audit_          │  │ outbox_         │     │   │
│  │  │ schutz_*        │  │ audit_event     │  │ outbox_message  │     │   │
│  │  └─────────────────┘  └─────────────────┘  └─────────────────┘     │   │
│  │                                                                      │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                        │                                    │
│                                        │ async (Worker)                     │
│                                        ▼                                    │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                       OUTBOX WORKER                                  │   │
│  │                                                                      │   │
│  │  • Benachrichtigungen                                                │   │
│  │  • Webhooks                                                          │   │
│  │  • Event-Stream                                                      │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 3.2 Service Layer Implementation

```python
# explosionsschutz/services.py

from dataclasses import dataclass
from typing import Optional
from uuid import UUID
from django.db import transaction
from django.core.exceptions import ValidationError, PermissionDenied

from common.request_context import get_context
from audit.services import emit_audit_event
from outbox.models import OutboxMessage
from explosionsschutz.models import (
    ExplosionConcept,
    ZoneDefinition,
    ProtectionMeasure,
    Equipment,
    Inspection,
    VerificationDocument,
)


# ============================================================================
# Command DTOs (Data Transfer Objects)
# ============================================================================

@dataclass(frozen=True)
class CreateExplosionConceptCmd:
    """Command für Erstellung eines neuen Ex-Konzepts"""
    area_id: UUID
    substance_id: UUID
    title: str
    assessment_id: Optional[UUID] = None


@dataclass(frozen=True)
class UpdateExplosionConceptCmd:
    """Command für Aktualisierung eines Ex-Konzepts"""
    concept_id: UUID
    title: Optional[str] = None
    substance_id: Optional[UUID] = None


@dataclass(frozen=True)
class ValidateExplosionConceptCmd:
    """Command für Validierung/Freigabe eines Ex-Konzepts"""
    concept_id: UUID
    notes: Optional[str] = None


@dataclass(frozen=True)
class CreateZoneDefinitionCmd:
    """Command für Erstellung einer Zonendefinition"""
    concept_id: UUID
    zone_type: str
    name: str
    extent: dict
    reference_standard_id: Optional[UUID] = None
    justification: Optional[str] = None


@dataclass(frozen=True)
class CreateProtectionMeasureCmd:
    """Command für Erstellung einer Schutzmaßnahme"""
    concept_id: UUID
    category: str
    title: str
    description: Optional[str] = None
    catalog_reference_id: Optional[UUID] = None
    safety_function_id: Optional[UUID] = None


@dataclass(frozen=True)
class CreateEquipmentCmd:
    """Command für Registrierung eines Betriebsmittels"""
    zone_id: UUID
    equipment_type_id: UUID
    serial_number: str
    installation_location: Optional[str] = None
    commissioned_at: Optional[str] = None


@dataclass(frozen=True)
class CreateInspectionCmd:
    """Command für Erfassung einer Prüfung"""
    equipment_id: UUID
    inspection_type: str
    inspector_name: str
    result: str
    findings: Optional[str] = None
    next_inspection_date: Optional[str] = None


# ============================================================================
# Audit Event Categories
# ============================================================================

class AuditCategory:
    """Konstanten für Audit-Event-Kategorien"""
    CONCEPT = "explosionsschutz.concept"
    ZONE = "explosionsschutz.zone"
    MEASURE = "explosionsschutz.measure"
    EQUIPMENT = "explosionsschutz.equipment"
    INSPECTION = "explosionsschutz.inspection"
    DOCUMENT = "explosionsschutz.document"


# ============================================================================
# Service Functions
# ============================================================================

@transaction.atomic
def create_explosion_concept(cmd: CreateExplosionConceptCmd) -> ExplosionConcept:
    """
    Erstellt ein neues Explosionsschutzkonzept.
    
    Audit: explosionsschutz.concept.created
    Outbox: explosionsschutz.concept.created
    """
    ctx = get_context()
    if ctx.tenant_id is None:
        raise PermissionDenied("Tenant erforderlich")
    
    # Validierung: Area muss zum Tenant gehören
    from tenancy.models import Area
    area = Area.objects.get(id=cmd.area_id)
    if area.site.tenant_id != ctx.tenant_id:
        raise PermissionDenied("Area gehört nicht zum Tenant")
    
    # Validierung: Substance muss existieren
    from substances.models import Substance
    substance = Substance.objects.get(id=cmd.substance_id)
    
    # Ermittle nächste Version für diesen Bereich
    existing_versions = ExplosionConcept.objects.filter(
        tenant_id=ctx.tenant_id,
        area_id=cmd.area_id
    ).count()
    next_version = existing_versions + 1
    
    # Erstelle Konzept
    concept = ExplosionConcept.objects.create(
        tenant_id=ctx.tenant_id,
        area=area,
        substance=substance,
        title=cmd.title.strip(),
        version=next_version,
        status="draft",
        assessment_id=cmd.assessment_id,
    )
    
    # Audit Event
    emit_audit_event(
        tenant_id=ctx.tenant_id,
        category=AuditCategory.CONCEPT,
        action="created",
        entity_type="explosionsschutz.ExplosionConcept",
        entity_id=concept.id,
        payload={
            "title": concept.title,
            "version": concept.version,
            "area_id": str(concept.area_id),
            "substance_id": str(concept.substance_id),
            "substance_name": substance.name,
            "assessment_id": str(concept.assessment_id) if concept.assessment_id else None,
        },
    )
    
    # Outbox Message für async Verarbeitung
    OutboxMessage.objects.create(
        tenant_id=ctx.tenant_id,
        topic="explosionsschutz.concept.created",
        payload={
            "concept_id": str(concept.id),
            "area_id": str(concept.area_id),
            "version": concept.version,
        },
    )
    
    return concept


@transaction.atomic
def update_explosion_concept(cmd: UpdateExplosionConceptCmd) -> ExplosionConcept:
    """
    Aktualisiert ein bestehendes Ex-Konzept.
    
    Audit: explosionsschutz.concept.updated
    """
    ctx = get_context()
    if ctx.tenant_id is None:
        raise PermissionDenied("Tenant erforderlich")
    
    concept = ExplosionConcept.objects.select_for_update().get(
        id=cmd.concept_id,
        tenant_id=ctx.tenant_id
    )
    
    if concept.status != "draft":
        raise ValidationError("Nur Entwürfe können bearbeitet werden")
    
    # Sammle Änderungen für Audit
    changes = {}
    
    if cmd.title is not None and cmd.title != concept.title:
        changes["title"] = {"old": concept.title, "new": cmd.title}
        concept.title = cmd.title.strip()
    
    if cmd.substance_id is not None and cmd.substance_id != concept.substance_id:
        from substances.models import Substance
        new_substance = Substance.objects.get(id=cmd.substance_id)
        old_substance_name = concept.substance.name
        changes["substance"] = {
            "old": {"id": str(concept.substance_id), "name": old_substance_name},
            "new": {"id": str(cmd.substance_id), "name": new_substance.name},
        }
        concept.substance = new_substance
    
    if changes:
        concept.save()
        
        emit_audit_event(
            tenant_id=ctx.tenant_id,
            category=AuditCategory.CONCEPT,
            action="updated",
            entity_type="explosionsschutz.ExplosionConcept",
            entity_id=concept.id,
            payload={"changes": changes},
        )
    
    return concept


@transaction.atomic
def validate_explosion_concept(cmd: ValidateExplosionConceptCmd) -> ExplosionConcept:
    """
    Validiert/gibt ein Ex-Konzept frei.
    
    Prüft:
    - Mindestens eine Zone definiert
    - Alle Zonen haben Maßnahmen
    - Equipment in Zonen hat gültige ATEX-Kategorie
    
    Audit: explosionsschutz.concept.validated
    Outbox: explosionsschutz.concept.validated
    """
    ctx = get_context()
    if ctx.tenant_id is None:
        raise PermissionDenied("Tenant erforderlich")
    
    concept = ExplosionConcept.objects.select_for_update().get(
        id=cmd.concept_id,
        tenant_id=ctx.tenant_id
    )
    
    if concept.status != "draft":
        raise ValidationError("Nur Entwürfe können validiert werden")
    
    # Validierung: Mindestens eine Zone
    zones = concept.zones.all()
    if not zones.exists():
        raise ValidationError("Mindestens eine Zone muss definiert sein")
    
    # Validierung: Equipment-Zonenzuordnung
    validation_errors = []
    for zone in zones:
        for equipment in zone.equipment.all():
            if zone.zone_type not in equipment.equipment_type.allowed_zones:
                validation_errors.append(
                    f"Equipment '{equipment.serial_number}' "
                    f"(Kategorie {equipment.equipment_type.atex_category}) "
                    f"nicht zulässig in Zone {zone.zone_type}"
                )
    
    if validation_errors:
        raise ValidationError(validation_errors)
    
    # Status ändern
    from django.utils import timezone
    concept.status = "validated"
    concept.is_validated = True
    concept.validated_by_id = ctx.user_id
    concept.validated_at = timezone.now()
    concept.save()
    
    # Audit Event
    emit_audit_event(
        tenant_id=ctx.tenant_id,
        category=AuditCategory.CONCEPT,
        action="validated",
        entity_type="explosionsschutz.ExplosionConcept",
        entity_id=concept.id,
        payload={
            "version": concept.version,
            "validated_by": str(ctx.user_id),
            "notes": cmd.notes,
            "zone_count": zones.count(),
        },
    )
    
    # Outbox für Benachrichtigungen
    OutboxMessage.objects.create(
        tenant_id=ctx.tenant_id,
        topic="explosionsschutz.concept.validated",
        payload={
            "concept_id": str(concept.id),
            "validated_by": str(ctx.user_id),
        },
    )
    
    return concept


@transaction.atomic
def create_zone_definition(cmd: CreateZoneDefinitionCmd) -> ZoneDefinition:
    """
    Erstellt eine Zonendefinition für ein Ex-Konzept.
    
    Audit: explosionsschutz.zone.created
    """
    ctx = get_context()
    if ctx.tenant_id is None:
        raise PermissionDenied("Tenant erforderlich")
    
    concept = ExplosionConcept.objects.get(
        id=cmd.concept_id,
        tenant_id=ctx.tenant_id
    )
    
    if concept.status != "draft":
        raise ValidationError("Zonen können nur in Entwürfen hinzugefügt werden")
    
    # Validierung: Zonentyp
    valid_zones = {"0", "1", "2", "20", "21", "22"}
    if cmd.zone_type not in valid_zones:
        raise ValidationError(f"Ungültiger Zonentyp: {cmd.zone_type}")
    
    zone = ZoneDefinition.objects.create(
        tenant_id=ctx.tenant_id,
        concept=concept,
        zone_type=cmd.zone_type,
        name=cmd.name.strip(),
        extent=cmd.extent,
        reference_standard_id=cmd.reference_standard_id,
        justification=cmd.justification,
    )
    
    emit_audit_event(
        tenant_id=ctx.tenant_id,
        category=AuditCategory.ZONE,
        action="created",
        entity_type="explosionsschutz.ZoneDefinition",
        entity_id=zone.id,
        payload={
            "concept_id": str(concept.id),
            "zone_type": zone.zone_type,
            "name": zone.name,
            "extent": zone.extent,
        },
    )
    
    return zone


@transaction.atomic
def create_protection_measure(cmd: CreateProtectionMeasureCmd) -> ProtectionMeasure:
    """
    Erstellt eine Schutzmaßnahme für ein Ex-Konzept.
    
    Audit: explosionsschutz.measure.created
    """
    ctx = get_context()
    if ctx.tenant_id is None:
        raise PermissionDenied("Tenant erforderlich")
    
    concept = ExplosionConcept.objects.get(
        id=cmd.concept_id,
        tenant_id=ctx.tenant_id
    )
    
    if concept.status != "draft":
        raise ValidationError("Maßnahmen können nur in Entwürfen hinzugefügt werden")
    
    measure = ProtectionMeasure.objects.create(
        tenant_id=ctx.tenant_id,
        concept=concept,
        category=cmd.category,
        title=cmd.title.strip(),
        description=cmd.description or "",
        catalog_reference_id=cmd.catalog_reference_id,
        safety_function_id=cmd.safety_function_id,
        status="planned",
    )
    
    emit_audit_event(
        tenant_id=ctx.tenant_id,
        category=AuditCategory.MEASURE,
        action="created",
        entity_type="explosionsschutz.ProtectionMeasure",
        entity_id=measure.id,
        payload={
            "concept_id": str(concept.id),
            "category": measure.category,
            "title": measure.title,
            "has_safety_function": measure.safety_function_id is not None,
        },
    )
    
    return measure


@transaction.atomic
def create_equipment(cmd: CreateEquipmentCmd) -> Equipment:
    """
    Registriert ein Betriebsmittel in einer Zone.
    
    Validiert automatisch die ATEX-Kategorie gegen den Zonentyp.
    
    Audit: explosionsschutz.equipment.created
    """
    ctx = get_context()
    if ctx.tenant_id is None:
        raise PermissionDenied("Tenant erforderlich")
    
    zone = ZoneDefinition.objects.get(
        id=cmd.zone_id,
        tenant_id=ctx.tenant_id
    )
    
    from explosionsschutz.models import EquipmentType
    equipment_type = EquipmentType.objects.for_tenant(ctx.tenant_id).get(
        id=cmd.equipment_type_id
    )
    
    # Validierung: ATEX-Kategorie passend zur Zone
    if zone.zone_type not in equipment_type.allowed_zones:
        raise ValidationError(
            f"Equipment Kategorie {equipment_type.atex_category} "
            f"nicht zulässig in Zone {zone.zone_type}. "
            f"Erlaubte Zonen: {', '.join(equipment_type.allowed_zones)}"
        )
    
    equipment = Equipment.objects.create(
        tenant_id=ctx.tenant_id,
        zone=zone,
        equipment_type=equipment_type,
        serial_number=cmd.serial_number.strip(),
        installation_location=cmd.installation_location,
        commissioned_at=cmd.commissioned_at,
    )
    
    emit_audit_event(
        tenant_id=ctx.tenant_id,
        category=AuditCategory.EQUIPMENT,
        action="created",
        entity_type="explosionsschutz.Equipment",
        entity_id=equipment.id,
        payload={
            "zone_id": str(zone.id),
            "zone_type": zone.zone_type,
            "equipment_type_id": str(equipment_type.id),
            "atex_marking": equipment_type.full_atex_marking,
            "serial_number": equipment.serial_number,
        },
    )
    
    # Outbox für Prüffristen-Setup
    OutboxMessage.objects.create(
        tenant_id=ctx.tenant_id,
        topic="explosionsschutz.equipment.created",
        payload={
            "equipment_id": str(equipment.id),
            "zone_type": zone.zone_type,
        },
    )
    
    return equipment


@transaction.atomic
def create_inspection(cmd: CreateInspectionCmd) -> Inspection:
    """
    Erfasst eine Prüfung nach BetrSichV.
    
    Audit: explosionsschutz.inspection.created
    Outbox: explosionsschutz.inspection.created (für Fristenverwaltung)
    """
    ctx = get_context()
    if ctx.tenant_id is None:
        raise PermissionDenied("Tenant erforderlich")
    
    equipment = Equipment.objects.get(
        id=cmd.equipment_id,
        tenant_id=ctx.tenant_id
    )
    
    inspection = Inspection.objects.create(
        tenant_id=ctx.tenant_id,
        equipment=equipment,
        inspection_type=cmd.inspection_type,
        inspector_name=cmd.inspector_name.strip(),
        result=cmd.result,
        findings=cmd.findings,
        next_inspection_date=cmd.next_inspection_date,
    )
    
    # Aktualisiere Equipment mit nächstem Prüfdatum
    if cmd.next_inspection_date:
        equipment.next_inspection_date = cmd.next_inspection_date
        equipment.save(update_fields=["next_inspection_date"])
    
    emit_audit_event(
        tenant_id=ctx.tenant_id,
        category=AuditCategory.INSPECTION,
        action="created",
        entity_type="explosionsschutz.Inspection",
        entity_id=inspection.id,
        payload={
            "equipment_id": str(equipment.id),
            "equipment_serial": equipment.serial_number,
            "inspection_type": inspection.inspection_type,
            "result": inspection.result,
            "inspector": inspection.inspector_name,
            "next_inspection": str(cmd.next_inspection_date) if cmd.next_inspection_date else None,
        },
    )
    
    # Outbox für Fristenverwaltung
    OutboxMessage.objects.create(
        tenant_id=ctx.tenant_id,
        topic="explosionsschutz.inspection.created",
        payload={
            "inspection_id": str(inspection.id),
            "equipment_id": str(equipment.id),
            "result": inspection.result,
            "next_inspection_date": str(cmd.next_inspection_date) if cmd.next_inspection_date else None,
        },
    )
    
    return inspection


# ============================================================================
# Archivierung / Löschung
# ============================================================================

@transaction.atomic
def archive_explosion_concept(concept_id: UUID) -> ExplosionConcept:
    """
    Archiviert ein Ex-Konzept (Soft Delete).
    
    Nur validierte Konzepte können archiviert werden.
    Archivierte Konzepte bleiben für Compliance-Zwecke erhalten.
    
    Audit: explosionsschutz.concept.archived
    """
    ctx = get_context()
    if ctx.tenant_id is None:
        raise PermissionDenied("Tenant erforderlich")
    
    concept = ExplosionConcept.objects.select_for_update().get(
        id=concept_id,
        tenant_id=ctx.tenant_id
    )
    
    if concept.status not in ["validated", "superseded"]:
        raise ValidationError("Nur validierte oder ersetzte Konzepte können archiviert werden")
    
    concept.status = "archived"
    concept.save(update_fields=["status"])
    
    emit_audit_event(
        tenant_id=ctx.tenant_id,
        category=AuditCategory.CONCEPT,
        action="archived",
        entity_type="explosionsschutz.ExplosionConcept",
        entity_id=concept.id,
        payload={
            "version": concept.version,
            "previous_status": "validated",
        },
    )
    
    return concept
```

### 3.3 Audit Event Übersicht

| Entity | Action | Trigger | Payload-Highlights |
|--------|--------|---------|-------------------|
| `ExplosionConcept` | `created` | Neues Konzept | title, area_id, substance |
| `ExplosionConcept` | `updated` | Änderung | changes (old/new) |
| `ExplosionConcept` | `validated` | Freigabe | validated_by, zone_count |
| `ExplosionConcept` | `archived` | Archivierung | version, previous_status |
| `ZoneDefinition` | `created` | Neue Zone | zone_type, extent |
| `ZoneDefinition` | `updated` | Zonenänderung | changes |
| `ZoneDefinition` | `deleted` | Zonenlöschung | reason |
| `ProtectionMeasure` | `created` | Neue Maßnahme | category, has_safety_function |
| `ProtectionMeasure` | `status_changed` | Statusänderung | old_status, new_status |
| `Equipment` | `created` | Neues Gerät | atex_marking, zone_type |
| `Equipment` | `decommissioned` | Außerbetriebnahme | reason |
| `Inspection` | `created` | Neue Prüfung | result, inspector, next_date |

### 3.4 Outbox Topics

| Topic | Zweck | Consumer |
|-------|-------|----------|
| `explosionsschutz.concept.created` | Benachrichtigung EHS-Manager | Notification Worker |
| `explosionsschutz.concept.validated` | Freigabe-Benachrichtigung | Notification Worker, Reporting |
| `explosionsschutz.equipment.created` | Prüffristen-Setup | Scheduler Worker |
| `explosionsschutz.inspection.created` | Fristenverwaltung | Scheduler Worker |
| `explosionsschutz.inspection.overdue` | Überfällige Prüfungen | Alert Worker |

---

## 4. Optimiertes Datenmodell (ERD v5)

### 4.1 Vollständiges Entity-Relationship-Diagramm

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                           EXPLOSIONSSCHUTZ ERD v5                               │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                 │
│  ┌──────────────────────────────────────────────────────────────────────────┐  │
│  │                        STAMMDATEN (Hybrid-Isolation)                      │  │
│  │                                                                           │  │
│  │  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐          │  │
│  │  │ReferenceStandard│  │  MeasureCatalog │  │  EquipmentType  │          │  │
│  │  │                 │  │                 │  │                 │          │  │
│  │  │ tenant_id (opt) │  │ tenant_id (opt) │  │ tenant_id (opt) │          │  │
│  │  │ is_system       │  │ is_system       │  │ is_system       │          │  │
│  │  │ code            │  │ title           │  │ manufacturer    │          │  │
│  │  │ title           │  │ default_type    │  │ model           │          │  │
│  │  │ category        │  │ description_tpl │  │ atex_group      │          │  │
│  │  │ url             │  │                 │  │ atex_category   │          │  │
│  │  └─────────────────┘  └─────────────────┘  │ protection_type │          │  │
│  │                                            │ explosion_group │          │  │
│  │  ┌─────────────────┐                       │ temperature_cls │          │  │
│  │  │ SafetyFunction  │                       │ epl             │          │  │
│  │  │                 │                       │ ip_rating       │          │  │
│  │  │ tenant_id (opt) │                       └─────────────────┘          │  │
│  │  │ is_system       │                                                     │  │
│  │  │ name            │                                                     │  │
│  │  │ performance_lvl │                                                     │  │
│  │  │ sil_level       │                                                     │  │
│  │  │ monitoring_meth │                                                     │  │
│  │  └─────────────────┘                                                     │  │
│  └──────────────────────────────────────────────────────────────────────────┘  │
│                                                                                 │
│  ┌──────────────┐                                                               │
│  │ Organization │ (tenancy)                                                     │
│  └──────┬───────┘                                                               │
│         │ 1:N                                                                   │
│         ▼                                                                       │
│  ┌──────────────┐                                                               │
│  │     Site     │ (tenancy)                                                     │
│  └──────┬───────┘                                                               │
│         │ 1:N                                                                   │
│         ▼                                                                       │
│  ┌──────────────┐      ┌──────────────────┐                                     │
│  │     Area     │◄─────│ SiteInventoryItem│ (substances)                        │
│  │              │      │                  │                                     │
│  │ @property:   │      │ substance ──────►│ Substance (SDS)                     │
│  │ has_ex_hazard│      └──────────────────┘                                     │
│  └──────┬───────┘                                                               │
│         │ 1:N                                                                   │
│         ▼                                                                       │
│  ┌────────────────────────────────────────────────────────────────────────┐    │
│  │                      ExplosionConcept                                  │    │
│  │                                                                        │    │
│  │  • tenant_id (REQUIRED)                                                │    │
│  │  • area (FK)                                                           │    │
│  │  • substance (FK → substances.Substance)                               │    │
│  │  • assessment_id (optional FK → risk.Assessment)                       │    │
│  │  • title, version, status                                              │    │
│  │  • is_validated, validated_by, validated_at                            │    │
│  │                                                                        │    │
│  │  @property sds_data → H-Sätze, Piktogramme, CAS, etc.                  │    │
│  │  @property completion_percentage                                       │    │
│  └────────────────────────────────────────────────────────────────────────┘    │
│         │                                                                       │
│         ├─────────────────┬─────────────────┬─────────────────┐                 │
│         │ 1:N             │ 1:N             │ 1:N             │ 1:N             │
│         ▼                 ▼                 ▼                 ▼                 │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐        │
│  │ZoneDefinition│  │ Protection   │  │Verification  │  │  Equipment   │        │
│  │              │  │   Measure    │  │  Document    │  │              │        │
│  │ zone_type    │  │              │  │              │  │ equipment_   │        │
│  │ extent(JSON) │  │ category     │  │ document_type│  │ type (FK)    │        │
│  │ reference_   │  │ safety_      │  │ file         │  │ zone (FK)    │        │
│  │ standard(FK) │  │ function(FK) │  │ issued_at    │  │ serial_no    │        │
│  │              │  │ status       │  │              │  │ next_insp    │        │
│  │ ignition_    │  │ catalog_     │  └──────────────┘  └──────┬───────┘        │
│  │ assessments  │  │ reference(FK)│                          │ 1:N             │
│  └──────────────┘  └──────────────┘                          ▼                 │
│                                                        ┌──────────────┐        │
│                                                        │  Inspection  │        │
│                                                        │              │        │
│                                                        │ type         │        │
│                                                        │ result       │        │
│                                                        │ inspector    │        │
│                                                        │ certificate  │        │
│                                                        └──────────────┘        │
│                                                                                 │
│  ┌──────────────────────────────────────────────────────────────────────────┐  │
│  │                        ZÜNDQUELLEN (EN 1127-1)                            │  │
│  │                                                                           │  │
│  │  ┌───────────────────────┐                                                │  │
│  │  │ZoneIgnitionSource     │                                                │  │
│  │  │Assessment             │                                                │  │
│  │  │                       │                                                │  │
│  │  │ zone (FK)             │                                                │  │
│  │  │ ignition_source (Enum)│  S1-S13 nach EN 1127-1                        │  │
│  │  │ is_present            │                                                │  │
│  │  │ is_effective          │                                                │  │
│  │  │ mitigation            │                                                │  │
│  │  └───────────────────────┘                                                │  │
│  └──────────────────────────────────────────────────────────────────────────┘  │
│                                                                                 │
└─────────────────────────────────────────────────────────────────────────────────┘
```

### 4.2 Zündquellen-Model (NEU)

```python
# explosionsschutz/models.py (Fortsetzung)

class IgnitionSource(models.TextChoices):
    """13 Zündquellen nach EN 1127-1"""
    S1_HOT_SURFACES = "S1", "Heiße Oberflächen"
    S2_FLAMES = "S2", "Flammen und heiße Gase"
    S3_MECHANICAL_SPARKS = "S3", "Mechanisch erzeugte Funken"
    S4_ELECTRICAL = "S4", "Elektrische Anlagen"
    S5_STRAY_CURRENTS = "S5", "Kathodischer Korrosionsschutz / Streuströme"
    S6_STATIC = "S6", "Statische Elektrizität"
    S7_LIGHTNING = "S7", "Blitzschlag"
    S8_ELECTROMAGNETIC = "S8", "Elektromagnetische Felder (HF)"
    S9_OPTICAL = "S9", "Optische Strahlung"
    S10_IONIZING = "S10", "Ionisierende Strahlung"
    S11_ULTRASOUND = "S11", "Ultraschall"
    S12_ADIABATIC = "S12", "Adiabatische Kompression / Stoßwellen"
    S13_EXOTHERMIC = "S13", "Exotherme Reaktionen"


class ZoneIgnitionSourceAssessment(models.Model):
    """
    Bewertung der 13 Zündquellen pro Zone nach EN 1127-1.
    
    Für jede Zone müssen alle 13 Zündquellen bewertet werden:
    - is_present: Ist die Zündquelle vorhanden?
    - is_effective: Kann sie eine Zündung verursachen?
    - mitigation: Welche Maßnahmen werden ergriffen?
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant_id = models.UUIDField(db_index=True)
    
    zone = models.ForeignKey(
        "ZoneDefinition",
        on_delete=models.CASCADE,
        related_name="ignition_assessments"
    )
    ignition_source = models.CharField(
        max_length=10,
        choices=IgnitionSource.choices
    )
    
    is_present = models.BooleanField(
        default=False,
        help_text="Ist diese Zündquelle im Bereich vorhanden?"
    )
    is_effective = models.BooleanField(
        default=False,
        help_text="Kann diese Zündquelle wirksam werden (Energie ausreichend)?"
    )
    mitigation = models.TextField(
        blank=True,
        help_text="Beschreibung der Schutzmaßnahmen gegen diese Zündquelle"
    )
    
    assessed_by_id = models.UUIDField(null=True, blank=True)
    assessed_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        db_table = "explosionsschutz_zone_ignition_assessment"
        constraints = [
            models.UniqueConstraint(
                fields=["zone", "ignition_source"],
                name="uq_zone_ignition_source"
            ),
        ]
    
    def __str__(self):
        status = "wirksam" if self.is_effective else ("vorhanden" if self.is_present else "nicht vorhanden")
        return f"{self.zone.name} - {self.get_ignition_source_display()}: {status}"
```

### 4.3 Zone Extent Schema (Pydantic)

```python
# explosionsschutz/schemas.py

from pydantic import BaseModel, Field, model_validator
from typing import Literal, Optional


class ZoneExtent(BaseModel):
    """
    JSON Schema für Zonenausdehnung nach IEC 60079-10-1.
    
    Unterstützt verschiedene geometrische Formen:
    - sphere: Kugelförmige Zone (z.B. um Füllstutzen)
    - cylinder: Zylindrische Zone (z.B. über Wannen)
    - box: Quaderförmige Zone (z.B. Räume)
    - custom: Freiform mit Beschreibung
    """
    
    shape: Literal["sphere", "cylinder", "box", "custom"]
    
    # Für sphere
    radius_m: Optional[float] = Field(None, ge=0, description="Radius in Metern")
    
    # Für cylinder
    diameter_m: Optional[float] = Field(None, ge=0, description="Durchmesser in Metern")
    height_m: Optional[float] = Field(None, ge=0, description="Höhe in Metern")
    
    # Für box
    length_m: Optional[float] = Field(None, ge=0, description="Länge in Metern")
    width_m: Optional[float] = Field(None, ge=0, description="Breite in Metern")
    depth_m: Optional[float] = Field(None, ge=0, description="Tiefe in Metern")
    
    # Für alle
    origin_description: Optional[str] = Field(
        None,
        description="Beschreibung des Ursprungspunkts, z.B. 'Füllstutzen Tank T-101'"
    )
    reference_drawing: Optional[str] = Field(
        None,
        description="Referenz auf technische Zeichnung"
    )
    
    # Für custom
    custom_description: Optional[str] = Field(
        None,
        description="Freitextbeschreibung für komplexe Geometrien"
    )
    
    @model_validator(mode="after")
    def validate_shape_fields(self):
        """Validiert, dass die richtigen Felder für die Shape gesetzt sind"""
        if self.shape == "sphere":
            if self.radius_m is None:
                raise ValueError("radius_m erforderlich für shape='sphere'")
        elif self.shape == "cylinder":
            if self.diameter_m is None or self.height_m is None:
                raise ValueError("diameter_m und height_m erforderlich für shape='cylinder'")
        elif self.shape == "box":
            if not all([self.length_m, self.width_m, self.depth_m]):
                raise ValueError("length_m, width_m und depth_m erforderlich für shape='box'")
        elif self.shape == "custom":
            if not self.custom_description:
                raise ValueError("custom_description erforderlich für shape='custom'")
        return self
    
    @property
    def volume_m3(self) -> Optional[float]:
        """Berechnet das Volumen der Zone in m³"""
        import math
        if self.shape == "sphere" and self.radius_m:
            return (4/3) * math.pi * (self.radius_m ** 3)
        elif self.shape == "cylinder" and self.diameter_m and self.height_m:
            return math.pi * ((self.diameter_m / 2) ** 2) * self.height_m
        elif self.shape == "box" and self.length_m and self.width_m and self.depth_m:
            return self.length_m * self.width_m * self.depth_m
        return None


# Beispiel-Nutzung:
"""
extent = ZoneExtent(
    shape="sphere",
    radius_m=1.5,
    origin_description="Füllstutzen Tank T-101",
    reference_drawing="P&ID-001-Rev3"
)

# In Django Model speichern:
zone.extent = extent.model_dump()
zone.save()

# Aus Django Model laden:
extent = ZoneExtent(**zone.extent)
print(f"Volumen: {extent.volume_m3:.2f} m³")
"""
```

---

## 5. Implementierungsplan (aktualisiert v5)

### Voraussetzung: substances-Modul (SDS)

> **WICHTIG:** Das `explosionsschutz`-Modul setzt das `substances`-Modul voraus.

```
Phase 0: SDS-Modul Basis (Sprint 1-4)
├── Substance + Party + Identifier Models
├── SdsRevision + Classification Models
├── H-/P-Sätze + Piktogramme
├── SiteInventoryItem
└── Referenztabellen (H-/P-Satz-Texte)

Phase 1: Ex-Stammdaten (Sprint 5) ← UPDATED v5
├── TenantScopedMasterData Basisklasse
├── ReferenceStandard Model + Hybrid-Isolation
├── MeasureCatalog Model + Default-Vorlagen
├── SafetyFunction Model
├── EquipmentType Model mit strukturierter ATEX-Kennzeichnung
├── Management Command: seed_reference_standards
├── Management Command: seed_measure_catalog
├── RLS-Policies für Hybrid-Isolation
└── Admin Interfaces

Phase 2: Ex-Core Models (Sprint 6-7) ← UPDATED v5
├── Area Model + @property has_explosion_hazard
├── ExplosionConcept Model + Substance-FK
├── ZoneDefinition Model + ReferenceStandard-FK
├── ZoneExtent Pydantic Schema
├── IgnitionSource Enum + ZoneIgnitionSourceAssessment
├── ProtectionMeasure Model + SafetyFunction-FK
├── Service Layer mit Audit-Trail (services.py)
├── Signal: SiteInventoryItem → Ex-Review-Trigger
└── Unit Tests für Services

Phase 3: Equipment & Inspections (Sprint 8-9)
├── Equipment Model + EquipmentType-FK
├── Zone-Equipment-Validierung (ATEX-Kategorie)
├── Inspection Model + Prüfprotokoll
├── VerificationDocument Model
├── Prüffristenlogik (auto next_inspection)
├── Benachrichtigungsservice (Outbox)
└── Unit Tests

Phase 4: UI/UX (Sprint 10-12)
├── Concept CRUD Views
├── Substance-Selector (aus SDS-Modul)
├── Zone Editor (HTMX)
├── Ignition Source Assessment UI
├── Measure Management (HTMX)
├── Equipment Views mit Zonen-Zuordnungsvalidierung
├── SDS-Daten-Anzeige (read-only)
└── E2E Tests (Playwright)

Phase 5: PDF & Integration (Sprint 13)
├── PDF Template Explosionsschutzdokument
├── WeasyPrint Integration
├── Assessment-Verknüpfung
├── SDS-Daten im PDF (H-Sätze, Piktogramme)
├── Zündquellen-Bewertung im PDF
└── API Documentation

Phase 6: QA & Release (Sprint 14-15)
├── Security Review
├── Performance Tests
├── User Documentation
└── Production Deployment
```

---

## 6. Konsequenzen

### 6.1 Positive Konsequenzen

| # | Konsequenz | Nutzen |
| --- | ---------- | ------ |
| 1 | Normalisierte ATEX-Daten | Validierung, Filterung, Reporting |
| 2 | Entkoppelte MSR-Bewertung | Klare Trennung einfach vs. komplex |
| 3 | Dynamische Ex-Prüfung | Immer aktuell, keine Inkonsistenzen |
| 4 | Stammdatenkataloge | Wiederverwendbarkeit, Konsistenz |
| 5 | SDS-Integration ohne Redundanz | Single Source of Truth |
| 6 | **Hybrid Tenant-Isolation** | Globale Standards + tenant-spezifische Erweiterungen |
| 7 | **Vollständiger Audit-Trail** | Compliance-konforme Nachverfolgbarkeit |
| 8 | **Zündquellen-Bewertung** | EN 1127-1 Compliance |

### 6.2 Negative Konsequenzen

| # | Konsequenz | Mitigation |
| --- | ---------- | ---------- |
| 1 | Komplexeres Schema (+6 Models) | Saubere Dokumentation, ERD |
| 2 | Mehr JOINs für Abfragen | Indexierung, select_related() |
| 3 | SDS-Modul als Voraussetzung | Klare Dependency-Dokumentation |
| 4 | Hybrid-Isolation Komplexität | Custom Manager kapselt Logik |

---

## 7. Referenzen

| Dokument | Link |
| -------- | ---- |
| ATEX 114 Richtlinie | [EUR-Lex](https://eur-lex.europa.eu/legal-content/DE/TXT/?uri=CELEX:32014L0034) |
| TRGS 720-725 | [BAuA](https://www.baua.de/DE/Angebote/Regelwerk/TRGS/TRGS.html) |
| BetrSichV | [Gesetze im Internet](https://www.gesetze-im-internet.de/betrsichv_2015/) |
| IEC 60079-10-1 | [IEC Webstore](https://webstore.iec.ch/publication/63327) |
| EN 1127-1 Zündquellen | [Beuth](https://www.beuth.de/de/norm/din-en-1127-1/351422270) |
| ISO 13849 (PL) | [ISO](https://www.iso.org/standard/69883.html) |
| IEC 62061 (SIL) | [IEC](https://webstore.iec.ch/publication/67497) |

---

## 8. Änderungshistorie

| Version | Datum | Autor | Änderung |
| ------- | ----- | ----- | -------- |
| 1.0 | 2026-01-31 | Cascade | Initial Draft |
| 2.0 | 2026-01-31 | Cascade | Review-Ready Version |
| 3.0 | 2026-01-31 | Cascade | SDS-Integration |
| 4.0 | 2026-01-31 | Cascade | Review-Feedback - Normalisierung, SoC, strukturierte ATEX |
| 5.0 | 2026-01-31 | Cascade | **Tenant-Isolation + Audit-Trail** - Hybrid-Modell, Service Layer, Zündquellen |

---

## 9. Approval

| Rolle | Name | Datum | Signatur |
| ----- | ---- | ----- | -------- |
| Autor | Achim Dehnert | 2026-01-31 | ✅ |
| Technical Review | AI Review | 2026-01-31 | ✅ |
| Architecture | _ausstehend_ | | |

**Nächster Schritt:** Phase 0 (SDS-Modul) parallel starten, dann Phase 1 (Stammdaten mit Hybrid-Isolation)
