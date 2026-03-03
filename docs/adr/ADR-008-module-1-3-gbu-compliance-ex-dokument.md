# ADR-008: Produktarchitektur Module 1–3 — GBU-Automation, Compliance-Dashboard, Ex-Schutzdokument

| Feld | Wert |
|------|------|
| **Status** | **Proposed** |
| **Version** | 1.0 |
| **Datum** | 2026-03-03 |
| **Autor** | Achim Dehnert |
| **Quellen** | `docs/adr/input/Schutztat_Produktkonzept_Module_1-3.md`, `docs/adr/input/Schutztat_Implementierungskonzept_Module_1-3.md`, `docs/adr/input/REVIEW-ADR-007-explosionsschutz-brandschutz.md` |
| **Bezug** | ADR-007 (riskfw-Paketarchitektur), ADR-002 (substances), ADR-001 (explosionsschutz) |

---

## Kurzfassung

Schutztat wird um drei Produkt-Module erweitert, die vollständig auf der bestehenden
Plattform-Basis (`substances`, `explosionsschutz`, `audit`, `documents`, `outbox`)
aufsetzen. Reihenfolge nach time-to-value:

| Priorität | Modul | App | Tier | Preis |
|-----------|-------|-----|------|-------|
| ⭐ 1 | GBU-Automation (H-Code → GBU → BA) | `gbu` (neu) | Shield | 199 €/Monat |
| ⭐ 2 | Compliance-Dashboard & Prüffristen | `compliance` (neu) | Guard | 79 €/Monat |
| ⭐ 3 | Ex-Schutzdokument-Automation | `explosionsschutz` (Erweiterung) | Fortress | 499+ €/Monat |

---

## 1. Kontext

### 1.1 Bestehende Basis (bereits implementiert, nicht anfassen)

| App | Genutzte Artefakte |
|-----|-----------|
| `substances` | `SdsRevision`, `SdsHazardStatement`, `SiteInventoryItem`, `SdsParserService` |
| `explosionsschutz` | `Equipment`, `Inspection`, `ExplosionConcept`, `ZoneDefinition`, `ExIntegrationService` |
| `audit` | `AuditEvent`, `emit_audit_event()`, `AuditCategory` |
| `actions` | `ActionItem`, `create_action()` |
| `documents` | `Document`, `DocumentVersion`, S3-Upload |
| `outbox` | `OutboxMessage`, `emit_outbox_event()` |
| `permissions` | `check_permission()`, `filter_by_permission()` |
| `tenancy` | `Organization`, `Site` |

### 1.2 Verbindliche Plattform-Constraints (aus ADR-003, ADR-006)

Diese Regeln gelten absolut für alle drei Module — keine Ausnahmen:

| Constraint | Regel |
|-----------|-------|
| **Model-Basis** | UUID PK, `tenant_id` (UUID, `db_index=True`), `TimestampedModel` |
| **Service Layer** | Business-Logik ausschließlich in `services.py` — Views delegieren nur HTTP |
| **Kein `post_save`-Signal für Business-Logik** | Explizite Service-Calls statt Magic-Signals (Migration/Loaddata-Schutz) |
| **Audit** | `emit_audit_event()` innerhalb `@transaction.atomic`, immer `AuditCategory` |
| **FK auf Compliance-Daten** | `on_delete=PROTECT` (nie `CASCADE` auf unveränderliche Prüfnachweise) |
| **Serialisierung** | `dataclasses.asdict()` (nie `vars()`) für JSONField-Speicherung |
| **Enums** | `StrEnum` (Python 3.11+) für alle fachlich kritischen CharField-Werte |
| **N+1-Queries** | `select_related()` / `prefetch_related()` verpflichtend in allen Service-Queries |
| **Tenant-Isolation** | Alle Queries mit `tenant_id=tenant_id` — RLS als zweite Verteidigungslinie |
| **DXF-Upload** | Größenlimit 50 MB, `DXFError` explizit fangen, nie nacktes `Exception` |

---

## 2. Entscheidung: Modulare App-Struktur

### 2.1 Neue Apps

```
src/apps/gbu/            # Modul 2 — GBU-Automation
src/apps/compliance/     # Modul 3 — Compliance-Dashboard
```

`explosionsschutz/` wird für Modul 1 additiv erweitert (kein neues Package).

### 2.2 Begründung Reihenfolge

- **Modul 2 zuerst:** Baut auf `substances` (vollständig impl.) auf → schnellster
  time-to-value, ~9 Wochen, monetarisierbar ab Phase 2B.
- **Modul 3 parallel:** Unabhängig von Modul 2, nutzt bestehende `Equipment`-Daten,
  hoher Retention-Faktor (Fristen-Lock-in).
- **Modul 1 danach:** Aufwändigste Regulatorik (TRGS 720–725, EN 1127-1),
  Premium-Tier, baut auf Modul 3 (Compliance-Cockpit) auf.

---

## 3. Modul 2: GBU-Automation (`src/apps/gbu/`)

### 3.1 Verzeichnisstruktur

```
src/apps/gbu/
├── __init__.py
├── apps.py
├── admin.py
├── models/
│   ├── __init__.py
│   ├── reference.py       # HazardCategoryRef, HCodeCategoryMapping, MeasureTemplate
│   └── activity.py        # HazardAssessmentActivity, ActivityMeasure
├── services/
│   ├── __init__.py
│   ├── gbu_engine.py      # derive_hazard_categories(), propose_measures(), risk_score()
│   └── pdf_service.py     # generate_gbu_pdf(), generate_ba_pdf()
├── tasks.py               # @shared_task: async PDF-Generierung
├── views.py
├── urls.py
├── forms.py
├── templates/gbu/
│   ├── activity_list.html
│   ├── wizard_step{1-5}.html
│   ├── partials/
│   │   ├── _hazard_list.html    # HTMX: auto-abgeleitete Gefährdungen
│   │   ├── _measure_list.html   # HTMX: TOPS-Maßnahmen
│   │   ├── _risk_badge.html     # HTMX: Risiko-Ampel
│   │   └── _pdf_status.html     # HTMX: PDF-Generierungsstatus (polling)
│   └── pdf/
│       ├── gbu_template.html    # WeasyPrint GBU (TRGS 400/401)
│       └── ba_template.html     # WeasyPrint BA (TRGS 555)
├── fixtures/
│   ├── hazard_categories.json
│   └── h_code_mappings.json
└── management/commands/
    ├── seed_hazard_categories.py
    └── seed_h_code_mappings.py
```

### 3.2 Datenmodell

#### 3.2.1 Referenzdaten (`reference.py`) — tenant-unabhängig, global

```python
from enum import StrEnum
from django.db import models


class HazardCategoryType(StrEnum):
    FIRE_EXPLOSION = "fire_explosion"
    ACUTE_TOXIC    = "acute_toxic"
    CHRONIC_TOXIC  = "chronic_toxic"
    SKIN_CORROSION = "skin_corrosion"
    EYE_DAMAGE     = "eye_damage"
    RESPIRATORY    = "respiratory"
    SKIN_SENS      = "skin_sens"
    CMR            = "cmr"
    ENVIRONMENT    = "environment"
    ASPHYXIANT     = "asphyxiant"


class TOPSType(StrEnum):
    SUBSTITUTION   = "S"
    TECHNICAL      = "T"
    ORGANISATIONAL = "O"
    PERSONAL       = "P"


class HazardCategoryRef(models.Model):
    """Gefährdungskategorie nach TRGS 400 — global, tenant-unabhängig."""
    code           = models.CharField(max_length=30, unique=True)
    name           = models.CharField(max_length=200)
    category_type  = models.CharField(
        max_length=30,
        choices=[(t.value, t.value) for t in HazardCategoryType],
    )
    trgs_reference = models.CharField(max_length=50, blank=True)

    class Meta:
        db_table = "gbu_hazard_category_ref"
        ordering = ["category_type", "name"]


class HCodeCategoryMapping(models.Model):
    """H-Code → Gefährdungskategorie (n:m, admin-pflegbar)."""
    h_code     = models.CharField(max_length=10, db_index=True)
    category   = models.ForeignKey(
        HazardCategoryRef,
        on_delete=models.CASCADE,        # Referenzdaten, kein Compliance-Nachweis
        related_name="h_code_mappings",
    )
    annotation = models.TextField(blank=True)

    class Meta:
        db_table        = "gbu_h_code_category_mapping"
        unique_together = [("h_code", "category")]


class MeasureTemplate(models.Model):
    """Schutzmaßnahmen-Vorlage, verknüpft mit Gefährdungskategorie."""
    category     = models.ForeignKey(
        HazardCategoryRef,
        on_delete=models.CASCADE,
        related_name="measure_templates",
    )
    tops_type    = models.CharField(
        max_length=1,
        choices=[(t.value, t.name.title()) for t in TOPSType],
    )
    title        = models.CharField(max_length=300)
    description  = models.TextField(blank=True)
    is_mandatory = models.BooleanField(default=False)
    sort_order   = models.PositiveSmallIntegerField(default=0)

    class Meta:
        db_table = "gbu_measure_template"
        ordering = ["tops_type", "sort_order"]
```

#### 3.2.2 Tätigkeitsdaten (`activity.py`) — tenant-gebunden

```python
import uuid
from enum import StrEnum
from django.db import models
from django.conf import settings


class ActivityFrequency(StrEnum):
    DAILY      = "daily"
    WEEKLY     = "weekly"
    OCCASIONAL = "occasional"
    RARE       = "rare"


class QuantityClass(StrEnum):
    XS = "xs"   # < 1 L / 1 kg
    S  = "s"    # 1–10 L / kg
    M  = "m"    # 10–100 L / kg
    L  = "l"    # > 100 L / kg


class RiskScore(StrEnum):
    LOW      = "low"       # EMKG A
    MEDIUM   = "medium"    # EMKG B
    HIGH     = "high"      # EMKG C
    CRITICAL = "critical"  # Sofortmaßnahme


class ActivityStatus(StrEnum):
    DRAFT    = "draft"
    REVIEW   = "review"
    APPROVED = "approved"
    OUTDATED = "outdated"  # bei SDS-Update


class HazardAssessmentActivity(models.Model):
    """GBU-Tätigkeit mit Gefahrstoff — Kern-Entity Modul 2."""

    id                        = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant_id                 = models.UUIDField(db_index=True)
    site                      = models.ForeignKey("tenancy.Site", on_delete=models.PROTECT)
    sds_revision              = models.ForeignKey(
        "substances.SdsRevision",
        on_delete=models.PROTECT,
        related_name="gbu_activities",
    )
    activity_description      = models.TextField()
    activity_frequency        = models.CharField(
        max_length=15,
        choices=[(f.value, f.name.title()) for f in ActivityFrequency],
    )
    duration_minutes          = models.PositiveSmallIntegerField()
    quantity_class            = models.CharField(
        max_length=2,
        choices=[(q.value, q.name) for q in QuantityClass],
    )
    substitution_checked      = models.BooleanField(default=False)
    substitution_notes        = models.TextField(blank=True)
    derived_hazard_categories = models.ManyToManyField(
        "gbu.HazardCategoryRef", blank=True, related_name="activities",
    )
    risk_score                = models.CharField(
        max_length=10,
        choices=[(r.value, r.name.title()) for r in RiskScore],
        blank=True,
    )
    status                    = models.CharField(
        max_length=10,
        choices=[(s.value, s.name.title()) for s in ActivityStatus],
        default=ActivityStatus.DRAFT,
    )
    approved_by               = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True, related_name="+",
    )
    approved_at               = models.DateTimeField(null=True, blank=True)
    next_review_date          = models.DateField(null=True, blank=True)
    gbu_document              = models.ForeignKey(
        "documents.DocumentVersion",
        on_delete=models.SET_NULL,
        null=True, blank=True, related_name="+",
    )
    ba_document               = models.ForeignKey(
        "documents.DocumentVersion",
        on_delete=models.SET_NULL,
        null=True, blank=True, related_name="+",
    )
    created_at                = models.DateTimeField(auto_now_add=True)
    updated_at                = models.DateTimeField(auto_now=True)

    class Meta:
        db_table            = "gbu_hazard_assessment_activity"
        default_permissions = ("add", "change", "view")  # kein delete
        indexes             = [models.Index(fields=["tenant_id", "status"])]


class ActivityMeasure(models.Model):
    """Konkrete Schutzmaßnahme einer GBU-Tätigkeit."""
    activity     = models.ForeignKey(
        HazardAssessmentActivity,
        on_delete=models.PROTECT,
        related_name="measures",
    )
    template     = models.ForeignKey(
        "gbu.MeasureTemplate",
        on_delete=models.PROTECT,
        null=True, blank=True,
    )
    tops_type    = models.CharField(max_length=1)
    title        = models.CharField(max_length=300)
    description  = models.TextField(blank=True)
    is_confirmed = models.BooleanField(default=False)

    class Meta:
        db_table = "gbu_activity_measure"
        ordering = ["tops_type"]
```

### 3.3 Service-Layer (`gbu_engine.py`)

```python
import dataclasses
from uuid import UUID
from django.db import transaction
from apps.gbu.models.reference import HazardCategoryRef, HCodeCategoryMapping, MeasureTemplate
from apps.gbu.models.activity import (
    HazardAssessmentActivity, ActivityMeasure, ActivityStatus, RiskScore,
)
from apps.audit.services import emit_audit_event, AuditCategory


def derive_hazard_categories(sds_revision_id: UUID, tenant_id: UUID) -> list[HazardCategoryRef]:
    """H-Codes aus SdsRevision → Gefährdungskategorien nach TRGS 400."""
    from apps.substances.models import SdsRevision
    revision = SdsRevision.objects.prefetch_related("h_statements").get(
        id=sds_revision_id,
    )
    h_codes = [stmt.h_code for stmt in revision.h_statements.all()]
    return list(
        HazardCategoryRef.objects.filter(
            h_code_mappings__h_code__in=h_codes,
        ).distinct()
    )


def propose_measures(
    activity: HazardAssessmentActivity,
) -> list[MeasureTemplate]:
    """TOPS-Maßnahmen für die Gefährdungskategorien der Tätigkeit vorschlagen."""
    category_ids = activity.derived_hazard_categories.values_list("id", flat=True)
    return list(
        MeasureTemplate.objects.filter(
            category_id__in=category_ids,
        ).order_by("tops_type", "sort_order")
    )


@transaction.atomic
def approve_activity(
    activity_id: UUID,
    tenant_id: UUID,
    user_id: UUID,
    next_review_date,
) -> HazardAssessmentActivity:
    """GBU freigeben — setzt Status, Freigeber, Revisionsdatum."""
    from django.utils import timezone

    activity = HazardAssessmentActivity.objects.select_for_update().get(
        id=activity_id, tenant_id=tenant_id,
    )
    if activity.status not in (ActivityStatus.DRAFT, ActivityStatus.REVIEW):
        raise ValueError(f"Status '{activity.status}' kann nicht freigegeben werden")

    activity.status           = ActivityStatus.APPROVED
    activity.approved_by_id   = user_id
    activity.approved_at      = timezone.now()
    activity.next_review_date = next_review_date
    activity.save(update_fields=[
        "status", "approved_by_id", "approved_at", "next_review_date", "updated_at",
    ])

    emit_audit_event(
        tenant_id=tenant_id,
        user_id=user_id,
        category=AuditCategory.COMPLIANCE,
        action="gbu_approved",
        entity_type="HazardAssessmentActivity",
        entity_id=activity.id,
    )
    return activity
```

### 3.4 GBU-Engine: EMKG-Risikobewertung

| Input | Expositionsklasse (EMKG) | Risikostufe |
|-------|--------------------------|-------------|
| `quantity_class=xs` + `frequency=rare` | A | `low` |
| `quantity_class=s` + `frequency=occasional` | B | `medium` |
| `quantity_class=m` + beliebig, oder CMR-Stoff | C | `high` |
| CMR-Stoff + `quantity_class≥m` + täglich | — | `critical` |

Matrix wird als datenbankgetriebene `ExposureRiskMatrix`-Tabelle implementiert
(admin-pflegbar, keine Hardcodes).

### 3.5 PDF-Templates (WeasyPrint)

**GBU-Template** (`gbu_template.html`) nach TRGS 400:
- Deckblatt: Betrieb, Bereich, Tätigkeitsbezeichnung, Revisionsdatum, Unterschrift
- Stoff-Steckbrief: Name, CAS, H-Sätze, GHS-Piktogramme (SVG, UNECE-Lizenz)
- Gefährdungstabelle: Kategorie + H-Code-Begründung
- TOPS-Maßnahmen: S → T → O → P
- Expositionsbewertung (EMKG-Klasse)
- Freigabe-Block

**BA-Template** (`ba_template.html`) nach TRGS 555:
- 6 Pflichtabschnitte (Bezeichnung / Gefahren / Schutz / Störfall / Erste Hilfe / Entsorgung)
- GHS-Piktogramme als eingebettete SVGs
- Farbcodierung nach DIN 4844

### 3.6 Implementierungsplan

| Phase | Aufgaben | Dauer |
|-------|---------|-------|
| **2A** | Models + Migrations, `seed_hazard_categories`, `seed_h_code_mappings` (H200–H420) | 2 Wo. |
| **2B** | `GBUEngine`: `derive_hazard_categories`, `propose_measures`, `calculate_risk_score`; Unit-Tests | 2 Wo. |
| **2C** | HTMX-5-Schritt-Wizard (Stoff → Gefährdung → Exposition → Maßnahmen → Freigabe) | 2 Wo. |
| **2D** | WeasyPrint GBU + BA, Celery-Tasks, S3-Upload via `DocumentVersion` | 2 Wo. |
| **2E** | `next_review_date` → Modul 3 Integration, E2E-Tests | 1 Wo. |

---

## 4. Modul 3: Compliance-Dashboard (`src/apps/compliance/`)

### 4.1 Verzeichnisstruktur

```
src/apps/compliance/
├── __init__.py
├── apps.py
├── models/
│   ├── __init__.py
│   ├── preset.py          # InspectionIntervalPreset
│   └── summary.py         # ComplianceSummary (materialized cache)
├── services/
│   ├── __init__.py
│   ├── deadline_service.py   # calculate_status(), get_overdue()
│   └── escalation_service.py # create_overdue_action()
├── tasks.py               # Celery Beat: daily_escalation_check, refresh_compliance_summary
├── views.py
├── urls.py
├── templates/compliance/
│   ├── cockpit.html
│   └── partials/
│       ├── _traffic_light.html
│       ├── _due_list.html
│       └── _overdue_banner.html
└── management/commands/
    └── seed_inspection_presets.py
```

### 4.2 Equipment-Erweiterung (additiv, kein Breaking Change)

```python
# Neue Werte in explosionsschutz.Equipment.equipment_category:
FIRE_EXT    = "fire_ext",    "Tragbarer Feuerlöscher"
FIRE_DOOR   = "fire_door",   "Brandschutztur/-tor"
SMOKE_EX    = "smoke_ex",    "Rauch-/Warmeabzugsanlage (RWA)"
SPRINKLER   = "sprinkler",   "Ortsfeste Loschanlage"
FIRE_ALARM  = "fire_alarm",  "Brandmeldeanlage (BMA)"
EMERG_LIGHT = "emerg_light", "Sicherheitsbeleuchtung"
OTHER_FIRE  = "other_fire",  "Sonstiger Brandschutz"

# Neue Felder (additive Migration):
location_description = models.TextField(blank=True)
responsible          = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
inspector_type       = models.CharField(max_length=20, choices=InspectorType.choices, blank=True)
interval_preset      = models.ForeignKey("compliance.InspectionIntervalPreset", on_delete=models.SET_NULL, null=True, blank=True)
```

### 4.3 `InspectionIntervalPreset`

```python
class InspectionIntervalPreset(models.Model):
    """Prüfintervall-Vorlage nach Rechtsgrundlage — global, seeded."""
    equipment_category  = models.CharField(max_length=20, unique=True)
    interval_days       = models.PositiveIntegerField()
    legal_basis         = models.CharField(max_length=200)
    inspector_type      = models.CharField(max_length=50)
    note                = models.TextField(blank=True)

    class Meta:
        db_table = "compliance_inspection_interval_preset"
```

Seeding-Daten:

| Kategorie | Intervall | Rechtsgrundlage |
|-----------|-----------|----------------|
| `fire_ext` | 365 / 730 Tage | ASR A2.2, DGUV 0.300-001 |
| `fire_door` | 365 Tage | MBO, LBO |
| `smoke_ex` | 182 Tage | DIN 18232, EN 12101 |
| `sprinkler` | 365 Tage | VdS CEA 4001 |
| `fire_alarm` | 365 Tage | DIN VDE 0833, DIN 14675 |
| `atex_equipment` | 365–1095 Tage | BetrSichV §§14–16 |

### 4.4 `ComplianceSummary` (Materialized Cache)

```python
class ComplianceSummary(models.Model):
    """Täglicher Snapshot-Cache für Dashboard-Performance (O(1) statt O(n))."""
    tenant_id          = models.UUIDField(db_index=True)
    site               = models.ForeignKey("tenancy.Site", on_delete=models.CASCADE)
    equipment_category = models.CharField(max_length=20)
    overdue_count      = models.PositiveIntegerField(default=0)
    due_within_7_days  = models.PositiveIntegerField(default=0)
    due_within_30_days = models.PositiveIntegerField(default=0)
    compliant_count    = models.PositiveIntegerField(default=0)
    generated_at       = models.DateTimeField()

    class Meta:
        db_table        = "compliance_summary"
        unique_together = [("tenant_id", "site", "equipment_category")]
        indexes         = [models.Index(fields=["tenant_id", "generated_at"])]
```

Dashboard liest aus `ComplianceSummary`, nie direkt aus `Equipment`.
Refresh: Celery Beat täglich 05:00 (vor Eskalations-Check 06:00).

### 4.5 Eskalations-Workflow (Celery Beat, täglich 06:00)

```python
@shared_task
def daily_escalation_check():
    """Läuft täglich 06:00 — Fristenprüfung für alle Tenants."""
    from django.utils import timezone
    today = timezone.now().date()
    for tenant_id in active_tenant_ids():
        _check_equipment_deadlines(tenant_id, today)
        _check_gbu_review_dates(tenant_id, today)
        _check_ex_concept_status(tenant_id, today)
```

| Trigger | Aktion | Kanal |
|---------|--------|-------|
| 30 Tage vor Fälligkeit | Erinnerungs-Notification | E-Mail / In-App |
| 7 Tage vor Fälligkeit | Eskalations-Notification | E-Mail (dringend) |
| 1 Tag vor Fälligkeit | Letzte Erinnerung | E-Mail + In-App |
| Tag der Fälligkeit (offen) | `create_action()` → SiFa als Assignee | In-App Badge |
| Überfällig | Rote Ampel in `ComplianceSummary`, täglicher Reminder | In-App dauerhaft |

**Kritisch:** Eskalations-Service ruft `create_action()` direkt im Service auf —
kein Signal. Tenant-Kontext ist explizit verfügbar, keine Seiteneffekte bei `loaddata`.

### 4.6 Dashboard-Architektur (HTMX)

```
GET /compliance/cockpit/
  → cockpit.html (Shell mit Polling-Containern)
  → hx-get="/compliance/partials/traffic-light/" hx-trigger="every 60s"
  → hx-get="/compliance/partials/due-list/?days=30"
  → hx-get="/compliance/partials/overdue-banner/"
```

Alle Partials lesen aus `ComplianceSummary` — kein Live-Query auf `Equipment` im Dashboard-Pfad.

### 4.7 Implementierungsplan

| Phase | Aufgaben | Dauer |
|-------|---------|-------|
| **3A** | Equipment-Typ-Erweiterung (additive Migration), `InspectionIntervalPreset`-Seeding | 1 Wo. |
| **3B** | `ComplianceSummary`-Model, Refresh-Task, Dashboard-View (HTMX-Partials) | 2 Wo. |
| **3C** | Celery-Beat Eskalations-Task, Notification-Templates, `create_action()` bei Fälligkeit | 2 Wo. |
| **3D** | Multi-Standort-Aggregation, CSV/PDF-Export, Kalender-View | 1 Wo. |
| **3E** | Integration `next_review_date` (Modul 2), `ExplosionConcept.status` (Modul 1) | 1 Wo. |

---

## 5. Modul 1: Ex-Schutzdokument-Automation (Erweiterung `explosionsschutz`)

### 5.1 Neue Models (additiv in `explosionsschutz`)

```python
class ZoneClassificationRule(models.Model):
    """Regelwerk für Zonen-Vorschlag nach TRGS 721, admin-pflegbar."""
    release_degree      = models.CharField(max_length=20)
    ventilation_degree  = models.CharField(max_length=20)
    ventilation_avail   = models.CharField(max_length=20)
    recommended_zone    = models.CharField(max_length=5)
    justification_text  = models.TextField()
    norm_clause         = models.CharField(max_length=50)

    class Meta:
        db_table = "ex_zone_classification_rule"


# Erweiterungsfelder für ExplosionConcept (additive Migration):
# auto_draft_from_inventory = BooleanField(default=False)
# pdf_document = FK → DocumentVersion (SET_NULL)
# basis_norm = CharField: "BetrSichV §6(9) i.V.m. TRGS 720:2012-08"

# Erweiterungsfelder für ZoneIgnitionSourceAssessment:
# auto_prefilled = BooleanField(default=False)
```

### 5.2 Automation-Engine: Stoff-Trigger (SDS → Ex-Konzept-Draft)

Explosionsrelevante H-Codes: H220–H225, H240–H242, H250, H261, H270–H272

```python
# KORREKT: Expliziter Service-Call aus dem Inventar-Service
# apps/substances/services.py → add_inventory_item():
    if has_explosion_relevant_h_codes(sds_revision):
        ExIntegrationService.create_draft_concept(
            site=site,
            sds_revision=sds_revision,
            tenant_id=tenant_id,
            user_id=user_id,
        )
# VERBOTEN: post_save-Signal für diese Logik
```

### 5.3 `ZoneClassificationEngine`

```python
class ZoneClassificationEngine:
    """Regelbasierter Zonen-Vorschlag nach TRGS 721, Abschnitt 4."""

    def suggest_zone_type(
        self,
        release_degree: str,
        ventilation_degree: str,
        ventilation_availability: str,
    ) -> tuple[str, str]:
        """
        Returns: (zone_type, justification_text)
        zone_type: "0" | "1" | "2" | "NE"
        """
        rule = ZoneClassificationRule.objects.filter(
            release_degree=release_degree,
            ventilation_degree=ventilation_degree,
            ventilation_avail=ventilation_availability,
        ).first()
        if rule is None:
            raise ValueError(
                f"Keine Klassifizierungsregel für: {release_degree}/"
                f"{ventilation_degree}/{ventilation_availability}"
            )
        return rule.recommended_zone, rule.justification_text
```

### 5.4 `ZoneCalculationResult` — Compliance-Constraints

```python
class ZoneCalculationResult(models.Model):
    """
    Unveränderlicher Berechnungsnachweis — Compliance-kritisch (BetrSichV §§14–17).
    Kein Update, kein Delete nach Erstellung.
    """
    id          = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant_id   = models.UUIDField(db_index=True)
    zone        = models.ForeignKey(
        "ZoneDefinition",
        on_delete=models.PROTECT,    # PROTECT (nie CASCADE) — Review B1
        related_name="calculations",
    )
    raw_result  = models.JSONField()  # dataclasses.asdict(result) — nie vars() — Review B2
    calculated_zone_type = models.CharField(
        max_length=5,
        choices=[("0","Zone 0"),("1","Zone 1"),("2","Zone 2"),("NE","Nicht Ex")],
    )
    calculated_by_id    = models.UUIDField(null=True)
    calculated_at       = models.DateTimeField(auto_now_add=True)
    riskfw_version      = models.CharField(max_length=20)
    basis_norm          = models.CharField(max_length=100)  # "TRGS 721:2017-09"

    class Meta:
        db_table            = "ex_zone_calculation_result"
        default_permissions = ("add", "view")  # kein change, kein delete
```

Migration zusätzlich mit Row-Level-Security:

```sql
ALTER TABLE ex_zone_calculation_result ENABLE ROW LEVEL SECURITY;
CREATE POLICY no_delete ON ex_zone_calculation_result FOR DELETE USING (FALSE);
```

### 5.5 Implementierungsplan

| Phase | Aufgaben | Dauer |
|-------|---------|-------|
| **1A** | `ZoneClassificationRule`-Model + Seeding, SDS-Trigger (explizit im `substances`-Service) | 2 Wo. |
| **1B** | `ZoneIgnitionSourceAssessment`-Auto-Prefill, HTMX-Wizard 5 Schritte | 3 Wo. |
| **1C** | WeasyPrint Ex-Schutzdokument-Template, Celery-Task, `DocumentVersion` | 2 Wo. |
| **1D** | TOPS-Vollständigkeitsprüfung, Review-Workflow, elektronische Freigabe | 2 Wo. |
| **1E** | E2E-Tests (Compliance-Szenarien), Seed-Daten, Dokumentation | 1 Wo. |

---

## 6. Übergreifende Architektur-Entscheidungen

### 6.1 `riskfw` als PyPI-Dependency (aus ADR-007)

- 2FA auf PyPI-Account `iildehnert` — **bereits aktiviert** ✅
- Pinning via SHA256-Hash in `requirements.txt`
- `difflib.SequenceMatcher` für Stoff-Lookup (stdlib only, kein `rapidfuzz`)

### 6.2 GESTIS-Stoff-Datenbank: Statisch

```python
# riskfw/substances/database.py
# Quelle: GESTIS Stoffdatenbank, https://gestis.dguv.de/
# Stand: 2026-03-01 (manuell geprüft)
# Nächste Prüfung fällig: 2027-03-01
```

### 6.3 Norm-Versionsstrategie für `riskfw`

```
MAJOR: Norm-Ausgabe ändert sich (TRGS 721:2017 → TRGS 721:202x)
MINOR: Neue Norm-Unterstützung (z.B. TRGS 753)
PATCH: Bugfix ohne normative Auswirkung
```

---

## 7. Gesamtroadmap

```
Woche   1-2          3-4              5-6              7-8              9-10
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
M2 GBU  2A: Models   2B: GBU-Engine   2C: HTMX-Wizard  2D: PDF GBU+BA  2E: →M3
M3 Comp 3A: Equip    3B: Dashboard    3C: Eskalation   3D: Export       3E: M1+M2
M1 ExDoc    —        1A: Zone-Engine  1B: Wizard       1C: PDF          1D+1E
```

**Gesamt:** ~26 Wochen. **MVP (Shield + Guard):** ~10 Wochen.

---

## 8. Abgelehnte Alternativen

| Alternative | Grund für Ablehnung |
|-------------|---------------------|
| `post_save`-Signal für Ex-Konzept-Draft | Läuft bei `loaddata`/Fixtures, kein Tenant-Kontext, verboten |
| `CASCADE` auf `ZoneCalculationResult.zone` | Verletzt BetrSichV §§14–17 Aufbewahrungspflicht |
| `vars(result)` für JSONField | Bricht bei `frozen=True`+`__slots__`, keine tiefe Serialisierung |
| `rapidfuzz` in `riskfw` | Verletzt "stdlib only"-Versprechen, unnötig für ≤500 Substanzen |
| Materialized PostgreSQL View für ComplianceSummary | Weniger Django-nativ; Django-Model + Celery-Refresh bevorzugt |

---

## 9. Offene Entscheidungen

| ID | Frage | Empfehlung | Bis |
|----|-------|-----------|-----|
| F1 | LLM-Fallback für komplexe Zoneneinteilung | Separates ADR-009 nach Phase 1B | Sprint 6 |
| F2 | Prüffristen: Tagesgenau oder kalendermonatlich? | Tagesgenau (`date`-Arithmetik) | Sprint 2 |
| F3 | E-Mail: Django `send_mail` oder SMTP-Service? | Django `send_mail` + Celery-Task | Sprint 4 |
| F4 | `IgnitionRisk` in riskfw: `StrEnum` oder Dataclass? | `StrEnum`: `NONE/LOW/HIGH` | Sprint 5 |

---

## 10. Normbezüge

| Modul | Norm | Bezug |
|-------|------|-------|
| M1 | BetrSichV §6(9) i.V.m. GefStoffV §5 | Ex-Schutzdokument-Pflicht |
| M1 | TRGS 720, 721, 722 | Zoneneinteilung, Schutzmaßnahmen |
| M1 | EN 1127-1:2019 | Zündquellenbewertung (13 Quellen) |
| M1 | ATEX-RL 1999/92/EG | Betriebsmittel-Anforderungen |
| M2 | GefStoffV §6, §14 | GBU-Pflicht, Betriebsanweisung |
| M2 | TRGS 400, 401, 420 | GBU-Methodik, EMKG |
| M2 | TRGS 555 | Betriebsanweisungs-Format |
| M3 | BetrSichV §§14–16 | Prüffristen ATEX-Equipment |
| M3 | ASR A2.2, DGUV 0.300-001 | Feuerlöscher-Prüffristen |
| M3 | DIN VDE 0833, DIN 14675 | BMA-Prüffristen |
| M3 | VdS CEA 4001 | Sprinkler-Prüffristen |

---

*ADR-008 · Status: Proposed · 2026-03-03*
