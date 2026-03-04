# Schutztat · Implementierungskonzept Module 1–3
**Stack: Django · PostgreSQL/RLS · HTMX · Celery · WeasyPrint · Outbox**  
`src/apps/gbu/` · `src/apps/compliance/` · `src/apps/explosionsschutz/` (Erweiterung)

---

## 0 Plattform-Kontext & Konventionen

### 0.1 Existierende Basis (bereits implementiert)

| App / Modul | Pfad | Genutzte Artefakte | Status |
|-------------|------|--------------------|--------|
| `substances` | `src/apps/substances/` | `SdsRevision`, `SdsHazardStatement`, `SiteInventoryItem`, `SdsParserService` | ✅ impl. |
| `explosionsschutz` | `src/apps/explosionsschutz/` | `Equipment`, `Inspection`, `ExplosionConcept`, `ZoneDefinition`, `ExIntegrationService` | ✅ impl. |
| `audit` | `src/apps/audit/` | `AuditEvent`, `emit_audit_event()`, `AuditCategory` | ✅ impl. |
| `actions` | `src/apps/actions/` | `ActionItem`, `create_action()` | ✅ impl. |
| `documents` | `src/apps/documents/` | `Document`, `DocumentVersion`, S3-Upload | ✅ impl. |
| `outbox` | `src/apps/outbox/` | `OutboxMessage`, `emit_outbox_event()` | ✅ impl. |
| `permissions` | `src/apps/permissions/` | `check_permission()`, `filter_by_permission()` | ✅ impl. |
| `tenancy` | `src/apps/tenancy/` | `Organization`, `Site` | ✅ impl. |

### 0.2 Verbindliche Plattform-Patterns

| Pattern | Konvention | Beispiel aus Codebase |
|---------|-----------|----------------------|
| Model-Basis | UUID PK, `tenant_id` (UUID, `db_index`), `TimestampedModel` | `substances.Substance`, `explosionsschutz.Equipment` |
| Service Layer | Alle Business-Logik in `services.py`, Views nur HTTP-Delegation | `explosionsschutz/services.py: create_explosion_concept()` |
| Audit | `emit_audit_event()` in `@transaction.atomic`, immer mit `AuditCategory` | `audit/services.py` |
| Outbox | `OutboxMessage.objects.create()` im selben `@transaction.atomic` | `outbox/models.py` |
| Context | `get_context()` → `tenant_id`, `user_id` aus Middleware | `core/request_context.py` |
| HTMX | `hx-get/post/target/swap`, HTMX-Partials in `partials/` Ordner | `risk/templates/risk/partials/` |
| URL-Namen | `<app>:<entity>-<action>`, z.B. `gbu:activity-list` | `config/urls.py` |
| Permissions | `<app>.<entity>.<action>` Strings, RBAC via `permissions`-App | `permissions/services.py` |
| Tests | `pytest` + `factory_boy`, `conftest.py` mit tenant/user Fixtures | `tests/conftest.py` |
| Management Commands | `seed_*.py` für Referenzdaten | `substances/management/commands/seed_h_statements.py` |

---

## 1 Modul 2: GBU-Automation (`src/apps/gbu/`)

Neue Django-App `gbu`. Baut vollständig auf dem bereits implementierten `substances`-Modul auf.

### 1.1 Verzeichnisstruktur

```
src/apps/gbu/
├── __init__.py
├── apps.py
├── admin.py
├── models/
│   ├── __init__.py
│   ├── reference.py               # HazardCategoryRef, HCodeCategoryMapping, MeasureTemplate
│   └── activity.py                # HazardAssessmentActivity, ActivityMeasure
├── services/
│   ├── __init__.py
│   ├── gbu_engine.py              # derive_hazard_categories(), propose_measures(), risk_score()
│   └── pdf_service.py             # generate_gbu_pdf(), generate_ba_pdf()
├── tasks.py                       # @shared_task: generate_gbu_pdf_task, generate_ba_pdf_task
├── views.py
├── urls.py
├── forms.py
├── templates/gbu/
│   ├── activity_list.html
│   ├── wizard_step1.html
│   ├── wizard_step2.html
│   ├── wizard_step3.html
│   ├── wizard_step4.html
│   ├── wizard_step5.html
│   ├── partials/
│   │   ├── _hazard_list.html      # HTMX: Auto-abgeleitete Gefährdungen
│   │   ├── _measure_list.html     # HTMX: TOPS-Maßnahmen
│   │   ├── _risk_badge.html       # HTMX: Risiko-Ampel
│   │   └── _pdf_status.html       # HTMX: PDF-Generierungsstatus (polling)
│   └── pdf/
│       ├── gbu_template.html      # WeasyPrint GBU (TRGS 400/401)
│       └── ba_template.html       # WeasyPrint Betriebsanweisung (TRGS 555)
├── fixtures/
│   ├── hazard_categories.json
│   └── h_code_mappings.json
└── management/commands/
    ├── seed_hazard_categories.py
    └── seed_h_code_mappings.py
```

### 1.2 Datenmodell: `reference.py`

```python
# src/apps/gbu/models/reference.py
import uuid
from django.db import models


class HazardCategoryRef(models.Model):
    """Gefährdungskategorie nach TRGS 400 – global, tenant-unabhängig."""

    class CategoryType(models.TextChoices):
        FIRE_EXPLOSION  = "fire_explosion",  "Brand/Explosion"
        ACUTE_TOXIC     = "acute_toxic",     "Akute Toxizität"
        CHRONIC_TOXIC   = "chronic_toxic",   "Chronische Toxizität"
        SKIN_CORROSION  = "skin_corrosion",  "Ätz-/Reizwirkung Haut"
        EYE_DAMAGE      = "eye_damage",      "Augenschäden"
        RESPIRATORY     = "respiratory",     "Atemwegssensibilisierung"
        SKIN_SENS       = "skin_sens",       "Hautsensibilisierung"
        CMR             = "cmr",             "CMR-Stoff (Karzinogen/Mutagen/Repr.)"
        ENVIRONMENT     = "environment",     "Umweltgefährlichkeit"
        ASPHYXIANT      = "asphyxiant",      "Erstickungsgefahr"

    code           = models.CharField(max_length=30, unique=True)
    name           = models.CharField(max_length=200)
    category_type  = models.CharField(max_length=30, choices=CategoryType.choices)
    trgs_reference = models.CharField(max_length=50, blank=True)
    tops_level     = models.CharField(
        max_length=1,
        choices=[('T','Technisch'),('O','Organisatorisch'),('P','PSA'),('S','Substitution')],
        default='T',
    )

    class Meta:
        db_table = "gbu_hazard_category_ref"
        ordering = ['category_type', 'name']


class HCodeCategoryMapping(models.Model):
    """Mapping H-Code → Gefährdungskategorie (n:m, datenbankgetrieben)."""

    h_code     = models.CharField(max_length=10, db_index=True)  # H220
    category   = models.ForeignKey(
        HazardCategoryRef, on_delete=models.CASCADE, related_name='h_code_mappings',
    )
    annotation = models.TextField(blank=True)

    class Meta:
        db_table       = "gbu_h_code_category_mapping"
        unique_together = [('h_code', 'category')]


class MeasureTemplate(models.Model):
    """Schutzmaßnahmen-Vorlage, verknüpft mit Gefährdungskategorie."""

    class TOPSType(models.TextChoices):
        SUBSTITUTION   = "S", "Substitution (§7 GefStoffV)"
        TECHNICAL      = "T", "Technisch"
        ORGANISATIONAL = "O", "Organisatorisch"
        PERSONAL       = "P", "PSA"

    category     = models.ForeignKey(
        HazardCategoryRef, on_delete=models.CASCADE, related_name='measure_templates'
    )
    tops_type    = models.CharField(max_length=1, choices=TOPSType.choices)
    title        = models.CharField(max_length=300)
    description  = models.TextField(blank=True)
    is_mandatory = models.BooleanField(default=False)
    sort_order   = models.PositiveSmallIntegerField(default=0)

    class Meta:
        db_table = "gbu_measure_template"
        ordering = ['tops_type', 'sort_order']
```

### 1.3 Datenmodell: `activity.py`

```python
# src/apps/gbu/models/activity.py
import uuid
from django.db import models
from django.conf import settings
from apps.gbu.models.reference import HazardCategoryRef, MeasureTemplate


class HazardAssessmentActivity(models.Model):
    """GBU-Tätigkeit mit Gefahrstoff – Kern-Entity von Modul 2."""

    class Status(models.TextChoices):
        DRAFT    = "draft",    "Entwurf"
        REVIEW   = "review",   "In Prüfung"
        APPROVED = "approved", "Freigegeben"
        OUTDATED = "outdated", "Veraltet (SDS-Update)"

    class FrequencyChoice(models.TextChoices):
        DAILY      = "daily",      "Täglich"
        WEEKLY     = "weekly",     "Wöchentlich"
        OCCASIONAL = "occasional", "Gelegentlich"
        RARE       = "rare",       "Selten (<1x/Monat)"

    class QuantityClass(models.TextChoices):
        XS = "xs", "< 1 L / 1 kg"
        S  = "s",  "1–10 L / kg"
        M  = "m",  "10–100 L / kg"
        L  = "l",  "> 100 L / kg"

    class RiskScore(models.TextChoices):
        LOW      = "low",      "Niedrig (EMKG A)"
        MEDIUM   = "medium",   "Mittel (EMKG B)"
        HIGH     = "high",     "Hoch (EMKG C)"
        CRITICAL = "critical", "Kritisch – Sofortmaßnahme"

    id                    = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant_id             = models.UUIDField(db_index=True)
    site                  = models.ForeignKey('tenancy.Site', on_delete=models.PROTECT)
    sds_revision          = models.ForeignKey(
        'substances.SdsRevision', on_delete=models.PROTECT, related_name='gbu_activities',
    )
    activity_description  = models.TextField()
    activity_frequency    = models.CharField(max_length=15, choices=FrequencyChoice.choices)
    duration_minutes      = models.PositiveSmallIntegerField()
    quantity_class        = models.CharField(max_length=2, choices=QuantityClass.choices)
    substitution_checked  = models.BooleanField(default=False)
    substitution_notes    = models.TextField(blank=True)
    derived_hazard_categories = models.ManyToManyField(
        HazardCategoryRef, blank=True, related_name='activities',
    )
    risk_score            = models.CharField(max_length=10, choices=RiskScore.choices, blank=True)
    status                = models.CharField(max_length=10, choices=Status.choices, default=Status.DRAFT)
    approved_by           = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='+',
    )
    approved_at           = models.DateTimeField(null=True, blank=True)
    next_review_date      = models.DateField(null=True, blank=True)
    gbu_document          = models.ForeignKey(
        'documents.DocumentVersion', on_delete=models.SET_NULL,
        null=True, blank=True, related_name='+',
    )
    ba_document           = models.ForeignKey(
        'documents.DocumentVersion', on_delete=models.SET_NULL,
        null=True, blank=True, related_name='+',
    )
    created_at            = models.DateTimeField(auto_now_add=True)
    updated_at            = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "gbu_activity"
        indexes  = [
            models.Index(fields=['tenant_id', 'status']),
            models.Index(fields=['tenant_id', 'next_review_date']),
            models.Index(fields=['sds_revision', 'status']),
        ]


class ActivityMeasure(models.Model):
    """Konkrete Schutzmaßnahme (aus Template oder frei)."""
    activity       = models.ForeignKey(
        HazardAssessmentActivity, on_delete=models.CASCADE, related_name='measures'
    )
    template       = models.ForeignKey(MeasureTemplate, on_delete=models.SET_NULL, null=True, blank=True)
    tops_type      = models.CharField(max_length=1)
    title          = models.CharField(max_length=300)
    description    = models.TextField(blank=True)
    is_implemented = models.BooleanField(default=False)
    responsible    = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True
    )

    class Meta:
        db_table = "gbu_activity_measure"
        ordering = ['tops_type']
```

### 1.4 Service Layer: `gbu_engine.py`

```python
# src/apps/gbu/services/gbu_engine.py
from __future__ import annotations
from uuid import UUID
from django.db import transaction
from apps.gbu.models.reference import HazardCategoryRef, HCodeCategoryMapping, MeasureTemplate
from apps.gbu.models.activity import HazardAssessmentActivity, ActivityMeasure
from apps.audit.services import emit_audit_event, AuditCategory
from apps.outbox.models import OutboxMessage
from apps.core.request_context import get_context


def derive_hazard_categories(sds_revision_id: UUID) -> list[HazardCategoryRef]:
    """
    Leitet Gefährdungskategorien aus H-Codes des SDB ab.
    Pure function – kein DB-Schreibzugriff, testbar ohne Seiteneffekte.
    """
    from apps.substances.models import SdsRevision
    sds = SdsRevision.objects.prefetch_related('hazard_statements').get(id=sds_revision_id)
    h_codes = [hs.h_code for hs in sds.hazard_statements.all()]

    category_ids = (
        HCodeCategoryMapping.objects
        .filter(h_code__in=h_codes)
        .values_list('category_id', flat=True)
        .distinct()
    )
    return list(HazardCategoryRef.objects.filter(id__in=category_ids))


def calculate_risk_score(
    h_codes: list[str],
    quantity_class: str,
    frequency: str,
    duration_minutes: int,
) -> str:
    """
    Vereinfachte EMKG-Methode: Menge × Volatilität × Exposition → Risikostufe.
    Gibt einen der RiskScore-Werte zurück: low / medium / high / critical.
    """
    cmr_codes = {c for c in h_codes if c in ('H340','H350','H360','H341','H351','H361')}
    fire_codes = {c for c in h_codes if c.startswith(('H22', 'H24', 'H25', 'H27'))}

    # CMR sofort → mindestens high
    if cmr_codes:
        if quantity_class in ('m', 'l') or frequency == 'daily':
            return HazardAssessmentActivity.RiskScore.CRITICAL
        return HazardAssessmentActivity.RiskScore.HIGH

    score = 0
    score += {'xs': 0, 's': 1, 'm': 2, 'l': 3}.get(quantity_class, 0)
    score += {'rare': 0, 'occasional': 1, 'weekly': 2, 'daily': 3}.get(frequency, 0)
    score += 1 if duration_minutes > 60 else 0
    score += 2 if fire_codes else 0

    if score <= 2: return HazardAssessmentActivity.RiskScore.LOW
    if score <= 4: return HazardAssessmentActivity.RiskScore.MEDIUM
    if score <= 6: return HazardAssessmentActivity.RiskScore.HIGH
    return HazardAssessmentActivity.RiskScore.CRITICAL


@transaction.atomic
def create_activity(*, site_id: UUID, sds_revision_id: UUID, **kwargs) -> HazardAssessmentActivity:
    """Erstellt GBU-Tätigkeit und leitet sofort Gefährdungen ab."""
    ctx = get_context()

    activity = HazardAssessmentActivity.objects.create(
        tenant_id=ctx.tenant_id, site_id=site_id,
        sds_revision_id=sds_revision_id, **kwargs,
    )

    categories = derive_hazard_categories(sds_revision_id)
    activity.derived_hazard_categories.set(categories)

    from apps.substances.models import SdsRevision
    sds = SdsRevision.objects.prefetch_related('hazard_statements').get(id=sds_revision_id)
    h_codes = [hs.h_code for hs in sds.hazard_statements.all()]
    activity.risk_score = calculate_risk_score(
        h_codes=h_codes,
        quantity_class=activity.quantity_class,
        frequency=activity.activity_frequency,
        duration_minutes=activity.duration_minutes,
    )
    activity.save(update_fields=['risk_score'])

    _propose_measures(activity, categories)

    emit_audit_event(
        tenant_id=ctx.tenant_id, category=AuditCategory.COMPLIANCE,
        action='created', entity_type='gbu.HazardAssessmentActivity',
        entity_id=activity.id,
        payload={
            'site_id': str(site_id),
            'sds_revision_id': str(sds_revision_id),
            'risk_score': activity.risk_score,
            'categories': len(categories),
        },
    )
    return activity


def _propose_measures(activity: HazardAssessmentActivity, categories: list[HazardCategoryRef]) -> None:
    category_ids = [c.id for c in categories]
    templates = MeasureTemplate.objects.filter(
        category_id__in=category_ids
    ).order_by('tops_type', 'sort_order')

    ActivityMeasure.objects.bulk_create([
        ActivityMeasure(
            activity=activity, template=tmpl,
            tops_type=tmpl.tops_type, title=tmpl.title,
            description=tmpl.description,
        )
        for tmpl in templates
    ])
```

### 1.5 Celery Tasks

```python
# src/apps/gbu/tasks.py
from celery import shared_task
from uuid import UUID
import logging

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3, default_retry_delay=30)
def generate_gbu_pdf_task(self, activity_id: str) -> dict:
    """Async: Generiert GBU-PDF via WeasyPrint, speichert in S3 via documents-App."""
    from apps.gbu.services.pdf_service import GbuPdfService
    try:
        result = GbuPdfService().generate_gbu(UUID(activity_id))
        return {'status': 'ok', 'document_version_id': str(result.id)}
    except Exception as exc:
        raise self.retry(exc=exc)


@shared_task(bind=True, max_retries=3, default_retry_delay=30)
def generate_ba_pdf_task(self, activity_id: str) -> dict:
    """Async: Generiert Betriebsanweisung nach TRGS 555."""
    from apps.gbu.services.pdf_service import GbuPdfService
    try:
        result = GbuPdfService().generate_ba(UUID(activity_id))
        return {'status': 'ok', 'document_version_id': str(result.id)}
    except Exception as exc:
        raise self.retry(exc=exc)
```

### 1.6 HTMX View-Pattern

```python
# src/apps/gbu/views.py – Schritt 2: Gefährdungsableitung (HTMX-Partial)
from django.shortcuts import get_object_or_404
from django.template.response import TemplateResponse
from apps.gbu.models.activity import HazardAssessmentActivity
from apps.gbu.services.gbu_engine import derive_hazard_categories
from apps.permissions.services import check_permission


def activity_hazards_partial(request, pk):
    """
    HTMX-Partial: liefert die abgeleiteten Gefährdungen für eine Tätigkeit.
    Aufruf via hx-get nach SDS-Auswahl in Schritt 1.
    """
    activity = get_object_or_404(HazardAssessmentActivity, pk=pk, tenant_id=request.tenant_id)
    check_permission(request.user, 'gbu.activity.read', obj=activity)

    categories = derive_hazard_categories(activity.sds_revision_id)
    return TemplateResponse(request, 'gbu/partials/_hazard_list.html', {
        'activity': activity,
        'categories': categories,
    })
```

```html
<!-- gbu/partials/_hazard_list.html -->
<div id="hazard-list" hx-swap-oob="true">
  {% for cat in categories %}
  <div class="hazard-card {{ cat.category_type }}">
    <span class="badge">{{ cat.name }}</span>
    <p class="small">{{ cat.trgs_reference }}</p>
  </div>
  {% endfor %}
</div>

<!-- Aufruf in wizard_step1.html: -->
<select name="sds_revision"
        hx-get="{% url 'gbu:activity-hazards' activity.pk %}"
        hx-target="#hazard-list"
        hx-trigger="change">
```

### 1.7 URL-Konfiguration

```python
# src/apps/gbu/urls.py
from django.urls import path
from . import views

app_name = 'gbu'

urlpatterns = [
    path('',                        views.ActivityListView.as_view(),   name='activity-list'),
    path('create/',                 views.ActivityCreateView.as_view(), name='activity-create'),
    path('<uuid:pk>/',              views.ActivityDetailView.as_view(), name='activity-detail'),
    path('<uuid:pk>/step2/',        views.activity_hazards_partial,     name='activity-hazards'),
    path('<uuid:pk>/step3/',        views.activity_measures_partial,    name='activity-measures'),
    path('<uuid:pk>/step4/',        views.activity_risk_partial,        name='activity-risk'),
    path('<uuid:pk>/approve/',      views.activity_approve,             name='activity-approve'),
    path('<uuid:pk>/generate-gbu/', views.trigger_gbu_pdf,             name='generate-gbu'),
    path('<uuid:pk>/generate-ba/',  views.trigger_ba_pdf,              name='generate-ba'),
    path('<uuid:pk>/pdf-status/',   views.pdf_status_partial,          name='pdf-status'),
]

# In config/urls.py ergänzen:
# path('gbu/', include('apps.gbu.urls')),
```

### 1.8 Neue Permissions

```python
# In permissions/services.py → DEFAULT_PERMISSIONS ergänzen:
('gbu.activity.read',    'GBU Tätigkeit lesen'),
('gbu.activity.write',   'GBU Tätigkeit anlegen/bearbeiten'),
('gbu.activity.approve', 'GBU Tätigkeit freigeben'),
('gbu.activity.delete',  'GBU Tätigkeit löschen'),
```

### 1.9 Seed-Daten (Auszug)

```python
# src/apps/gbu/management/commands/seed_h_code_mappings.py
H_CODE_MAPPINGS = [
    # (h_code, category_code, annotation)
    ('H220', 'fire_explosion', 'Extrem entzündbares Gas – Zone 0 prüfen (TRGS 720)'),
    ('H224', 'fire_explosion', 'Flüssigkeit mit Flammpunkt < 23°C'),
    ('H225', 'fire_explosion', 'Leichtentzündbare Flüssigkeit (Fp 23–60°C)'),
    ('H300', 'acute_toxic',    'Lebensgefahr bei Verschlucken'),
    ('H330', 'acute_toxic',    'Lebensgefahr bei Einatmen'),
    ('H334', 'respiratory',    'Kann bei Einatmen Allergien/Asthma verursachen'),
    ('H340', 'cmr',            'Kann genetische Defekte verursachen – Kat. 1A/1B'),
    ('H350', 'cmr',            'Kann Krebs erzeugen – Kat. 1A/1B'),
    ('H360', 'cmr',            'Kann Fruchtbarkeit/ungeborenes Kind schädigen'),
    # ... (alle H-Codes bis H420)
]
```

### 1.10 Teststruktur

```python
# tests/gbu/test_gbu_engine.py
import pytest
from apps.gbu.services.gbu_engine import derive_hazard_categories, calculate_risk_score


class TestDeriveHazardCategories:
    def test_fire_h_codes_yield_fire_explosion_category(self, sds_with_h224, db):
        categories = derive_hazard_categories(sds_with_h224.id)
        codes = [c.code for c in categories]
        assert 'fire_explosion' in codes

    def test_cmr_h_codes_yield_cmr_category(self, sds_with_h350, db):
        categories = derive_hazard_categories(sds_with_h350.id)
        assert any(c.category_type == 'cmr' for c in categories)

    def test_unknown_h_code_yields_no_category(self, sds_empty, db):
        assert derive_hazard_categories(sds_empty.id) == []


class TestCalculateRiskScore:
    def test_cmr_large_quantity_daily_is_critical(self):
        assert calculate_risk_score(['H350'], 'l', 'daily', 480) == 'critical'

    def test_low_exposure_is_low(self):
        assert calculate_risk_score(['H302'], 'xs', 'rare', 10) == 'low'
```

---

## 2 Modul 3: Compliance-Dashboard (`src/apps/compliance/`)

Neue Django-App `compliance`. Greift lesend auf `Equipment` (explosionsschutz), `HazardAssessmentActivity` (gbu) und `ExplosionConcept` (explosionsschutz) zu.

### 2.1 Verzeichnisstruktur

```
src/apps/compliance/
├── __init__.py
├── apps.py
├── admin.py
├── models/
│   ├── __init__.py
│   ├── presets.py          # InspectionIntervalPreset
│   └── snapshot.py         # ComplianceSummary (Materialized Cache, täglich)
├── services/
│   ├── __init__.py
│   ├── compliance_query.py # get_overdue(), get_due_soon(), dashboard_stats()
│   └── snapshot_service.py # rebuild_compliance_snapshot(tenant_id)
├── tasks.py                # compliance_snapshot_task, escalation_task
├── views.py
├── urls.py
├── templates/compliance/
│   ├── dashboard.html
│   ├── calendar.html
│   ├── equipment_list.html
│   └── partials/
│       ├── _kpi_cards.html
│       ├── _overdue_list.html
│       ├── _due_soon_list.html
│       ├── _gbu_reviews.html
│       └── _ex_doc_status.html
└── management/commands/
    └── seed_inspection_presets.py
```

### 2.2 Equipment-Model Erweiterung (additiv, kein Breaking Change)

```python
# Neue equipment_category-Enum-Werte (Migration 0012_equipment_brandschutz.py)
NEUE_KATEGORIEN = [
    ('fire_ext',    'Tragbarer Feuerlöscher'),
    ('fire_door',   'Brandschutztür/-tor'),
    ('smoke_ex',    'Rauch-/Wärmeabzugsanlage (RWA)'),
    ('sprinkler',   'Ortsfeste Löschanlage (Sprinkler/Gas)'),
    ('fire_alarm',  'Brandmeldeanlage (BMA)'),
    ('emerg_light', 'Sicherheitsbeleuchtung'),
    ('other_fire',  'Sonstiger Brandschutz'),
]

# Neue Felder am Equipment-Model:
# location_description = models.TextField(blank=True)
# responsible = models.ForeignKey(AUTH_USER_MODEL, null=True, blank=True, on_delete=SET_NULL)
# inspector_type = models.CharField(max_length=20, choices=[
#     ('internal','Interne Befähigte Person'),
#     ('qualified','Befähigte Person extern'),
#     ('zuev','ZÜS'),
# ])
# preset = models.ForeignKey('compliance.InspectionIntervalPreset', null=True, on_delete=SET_NULL)
```

### 2.3 Datenmodell: `presets.py`

```python
# src/apps/compliance/models/presets.py
from django.db import models


class InspectionIntervalPreset(models.Model):
    """Standard-Prüfintervalle pro Anlagentyp (admin-pflegbar)."""

    equipment_category      = models.CharField(max_length=30, unique=True)
    display_name            = models.CharField(max_length=200)
    default_interval_months = models.PositiveSmallIntegerField()
    legal_basis             = models.CharField(max_length=200)
    inspector_type_required = models.CharField(max_length=20, blank=True)
    notes                   = models.TextField(blank=True)

    class Meta:
        db_table = "compliance_inspection_interval_preset"


# Seed-Werte:
PRESET_DATA = [
    ('fire_ext',   'Tragb. Feuerlöscher',    24, 'ASR A2.2, DGUV 0.300-001', 'qualified'),
    ('fire_door',  'Brandschutztür/-tor',     12, 'MBO, LBO',                 'qualified'),
    ('smoke_ex',   'RWA-Anlage',               6, 'DIN 18232, EN 12101',      'qualified'),
    ('sprinkler',  'Sprinkleranlage',          12, 'VdS CEA 4001',            'zuev'),
    ('fire_alarm', 'Brandmeldeanlage (BMA)',   12, 'DIN VDE 0833, DIN 14675', 'zuev'),
    ('1G',         'ATEX-Betriebsmittel 1G',  12, 'BetrSichV §14-16',        'zuev'),
    ('2G',         'ATEX-Betriebsmittel 2G',  36, 'BetrSichV §14-16',        'qualified'),
]
```

### 2.4 Datenmodell: `snapshot.py`

```python
# src/apps/compliance/models/snapshot.py
import uuid
from django.db import models


class ComplianceSummary(models.Model):
    """
    Täglicher Snapshot für Dashboard-Performance (O(1) statt O(n)).
    Wird von compliance_snapshot_task um 05:00 neu aufgebaut.
    """
    id                  = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant_id           = models.UUIDField(db_index=True)
    site_id             = models.UUIDField(null=True, blank=True, db_index=True)
    equipment_category  = models.CharField(max_length=30)
    total_count         = models.PositiveIntegerField(default=0)
    overdue_count       = models.PositiveIntegerField(default=0)
    due_7d_count        = models.PositiveIntegerField(default=0)
    due_30d_count       = models.PositiveIntegerField(default=0)
    compliant_count     = models.PositiveIntegerField(default=0)
    generated_at        = models.DateTimeField(auto_now=True)

    class Meta:
        db_table        = "compliance_summary"
        unique_together = [('tenant_id', 'site_id', 'equipment_category')]
```

### 2.5 Service Layer: `compliance_query.py`

```python
# src/apps/compliance/services/compliance_query.py
from datetime import date, timedelta
from uuid import UUID
from apps.explosionsschutz.models import Equipment
from apps.compliance.models.snapshot import ComplianceSummary


def get_overdue(tenant_id: UUID, site_id: UUID | None = None) -> list[Equipment]:
    """Alle Anlagen mit überfälliger Prüfung."""
    qs = Equipment.objects.filter(
        tenant_id=tenant_id, is_active=True,
        next_inspection_date__lt=date.today(),
    ).select_related('area__site', 'preset')
    if site_id:
        qs = qs.filter(area__site_id=site_id)
    return list(qs.order_by('next_inspection_date'))


def get_due_soon(tenant_id: UUID, days: int = 30) -> list[Equipment]:
    today = date.today()
    return list(
        Equipment.objects.filter(
            tenant_id=tenant_id, is_active=True,
            next_inspection_date__range=(today, today + timedelta(days=days)),
        ).select_related('area__site').order_by('next_inspection_date')
    )


def dashboard_stats(tenant_id: UUID) -> dict:
    """Aggregierte KPIs aus ComplianceSummary-Snapshot (O(1))."""
    from django.db.models import Sum
    agg = ComplianceSummary.objects.filter(tenant_id=tenant_id).aggregate(
        total=Sum('total_count'), overdue=Sum('overdue_count'),
        due7=Sum('due_7d_count'),  due30=Sum('due_30d_count'),
    )
    return {
        'total':   agg['total'] or 0,
        'overdue': agg['overdue'] or 0,
        'due_7d':  agg['due7'] or 0,
        'due_30d': agg['due30'] or 0,
        'status':  'red'    if (agg['overdue'] or 0) > 0 else
                   'yellow' if (agg['due7'] or 0) > 0    else 'green',
    }
```

### 2.6 Celery Tasks

```python
# src/apps/compliance/tasks.py
from celery import shared_task
from datetime import date, timedelta
import logging

logger = logging.getLogger(__name__)


@shared_task
def compliance_snapshot_task():
    """Täglich 05:00: ComplianceSummary für alle aktiven Tenants neu aufbauen."""
    from apps.tenancy.models import Organization
    from apps.compliance.services.snapshot_service import rebuild_compliance_snapshot
    for org in Organization.objects.filter(is_active=True):
        rebuild_compliance_snapshot(org.tenant_id)


@shared_task
def escalation_task():
    """Täglich 06:00: Fristenprüfung + Benachrichtigungen + Action-Erstellung."""
    from apps.explosionsschutz.models import Equipment
    from apps.outbox.models import OutboxMessage
    from django.db import transaction
    today = date.today()

    for days, topic in [(30, 'compliance.due.30d'), (7, 'compliance.due.7d'), (1, 'compliance.due.1d')]:
        threshold = today + timedelta(days=days)
        due = Equipment.objects.filter(is_active=True, next_inspection_date=threshold)
        for eq in due:
            with transaction.atomic():
                OutboxMessage.objects.create(
                    tenant_id=eq.tenant_id,
                    event_type=topic,
                    aggregate_type='Equipment',
                    aggregate_id=eq.id,
                    payload={
                        'equipment_id': str(eq.id),
                        'equipment_name': eq.name,
                        'due_date': str(threshold),
                        'days_remaining': days,
                    },
                )

    # Überfällige → automatisch Action erstellen (idempotent)
    overdue = Equipment.objects.filter(is_active=True, next_inspection_date__lt=today)
    for eq in overdue:
        _ensure_overdue_action(eq)


def _ensure_overdue_action(equipment) -> None:
    from apps.actions.models import ActionItem
    from apps.actions.services import create_action
    from apps.core.request_context import system_context

    exists = ActionItem.objects.filter(
        tenant_id=equipment.tenant_id,
        entity_type='Equipment', entity_id=equipment.id,
        status='open',
    ).exists()
    if not exists:
        with system_context(tenant_id=equipment.tenant_id):
            create_action(
                entity_type='Equipment', entity_id=equipment.id,
                title=f'Überfällige Prüfung: {equipment.name}',
                description=f'Prüfung war fällig am {equipment.next_inspection_date}',
                priority='high',
            )


# Ergänzungen config/celery.py beat_schedule:
# 'compliance-snapshot':   {'task': 'apps.compliance.tasks.compliance_snapshot_task',
#                            'schedule': crontab(hour=5, minute=0)},
# 'compliance-escalation': {'task': 'apps.compliance.tasks.escalation_task',
#                            'schedule': crontab(hour=6, minute=0)},
```

### 2.7 Dashboard View (HTMX-Polling)

```python
# src/apps/compliance/views.py
from django.views.generic import TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin
from apps.compliance.services.compliance_query import dashboard_stats


class DashboardView(LoginRequiredMixin, TemplateView):
    template_name = 'compliance/dashboard.html'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['stats'] = dashboard_stats(self.request.tenant_id)
        return ctx


def kpi_cards_partial(request):
    """HTMX Polling-Partial: KPI-Kacheln, alle 60s aktualisiert."""
    stats = dashboard_stats(request.tenant_id)
    return TemplateResponse(request, 'compliance/partials/_kpi_cards.html', {'stats': stats})
```

```html
<!-- dashboard.html – HTMX-Polling Pattern -->
<div id="kpi-cards"
     hx-get="{% url 'compliance:kpi-cards' %}"
     hx-trigger="load, every 60s"
     hx-swap="innerHTML">
  {% include 'compliance/partials/_kpi_cards.html' %}
</div>
```

---

## 3 Modul 1: Ex-Schutzdokument-Automation (Erweiterung `explosionsschutz/`)

Kein neues App-Verzeichnis. Modul 1 erweitert die bestehende `explosionsschutz`-App.

### 3.1 Neue Dateien in `src/apps/explosionsschutz/`

```
src/apps/explosionsschutz/
├── ...  (bestehend)
├── services/
│   ├── __init__.py
│   ├── zone_classification.py     # ZoneClassificationEngine
│   ├── ignition_prefill.py        # IgnitionSourceAutoFill
│   └── ex_document_pdf.py         # ExDocumentPdfService
├── models/
│   └── zone_rule.py               # ZoneClassificationRule (admin-pflegbar)
└── templates/explosionsschutz/
    ├── wizard/
    │   ├── step1_substance.html
    │   ├── step2_zones.html
    │   ├── step3_ignition.html
    │   ├── step4_measures.html
    │   └── step5_review.html
    └── pdf/
        └── ex_schutzdokument.html
```

### 3.2 ZoneClassificationEngine

```python
# src/apps/explosionsschutz/services/zone_classification.py
from dataclasses import dataclass
from enum import Enum


class ReleaseGrade(str, Enum):
    CONTINUOUS = "continuous"
    PRIMARY    = "primary"
    SECONDARY  = "secondary"

class VentilationGrade(str, Enum):
    HIGH   = "high"
    MEDIUM = "medium"
    LOW    = "low"

class AtmosphereType(str, Enum):
    GAS  = "gas"
    DUST = "dust"

@dataclass
class ZoneProposal:
    zone_type:     str   # '0','1','2','20','21','22'
    confidence:    str   # 'high','medium','low'
    justification: str
    trgs_reference: str


class ZoneClassificationEngine:
    """
    Regelbasierte Zoneneinteilung nach TRGS 721, Abschnitt 4.
    Regeln sind datenbankgetrieben (ZoneClassificationRule), Fallback auf Defaults.
    """

    def propose_zone(
        self,
        atmosphere: AtmosphereType,
        release_grade: ReleaseGrade,
        ventilation_grade: VentilationGrade,
        ventilation_available: bool,
    ) -> ZoneProposal:
        key = (atmosphere, release_grade, ventilation_grade, ventilation_available)
        rules = self._load_rules()
        if key in rules:
            return rules[key]
        return self._default_proposal(atmosphere, release_grade)

    def _load_rules(self) -> dict:
        from apps.explosionsschutz.models.zone_rule import ZoneClassificationRule
        result = {}
        for rule in ZoneClassificationRule.objects.filter(is_active=True):
            k = (
                AtmosphereType(rule.atmosphere),
                ReleaseGrade(rule.release_grade),
                VentilationGrade(rule.ventilation_grade),
                rule.ventilation_available,
            )
            result[k] = ZoneProposal(
                zone_type=rule.proposed_zone_type,
                confidence=rule.confidence,
                justification=rule.justification_text,
                trgs_reference=rule.trgs_reference,
            )
        return result

    def _default_proposal(self, atmosphere, release_grade) -> ZoneProposal:
        zone = '0' if release_grade == ReleaseGrade.CONTINUOUS else '1'
        if atmosphere == AtmosphereType.DUST:
            zone = str(int(zone) + 20)
        return ZoneProposal(
            zone_type=zone, confidence='low',
            justification='Konservativer Standardwert – manuelle Prüfung erforderlich',
            trgs_reference='TRGS 721, Tabelle 1',
        )
```

### 3.3 IgnitionSourceAutoFill

```python
# src/apps/explosionsschutz/services/ignition_prefill.py
from apps.explosionsschutz.models import ZoneDefinition, ZoneIgnitionSourceAssessment, Equipment

ALWAYS_PRESENT = {'hot_surfaces', 'friction_sparks', 'static_electricity'}

ALL_SOURCES = [
    ('hot_surfaces',       'Heiße Oberflächen'),
    ('flames_hot_gases',   'Flammen und heiße Gase'),
    ('mech_sparks',        'Mechanisch erzeugte Funken'),
    ('electrical_equip',   'Elektrische Betriebsmittel'),
    ('stray_currents',     'Ausgleichsströme/Kathodenschutz'),
    ('static_electricity', 'Statische Elektrizität'),
    ('lightning',          'Blitz'),
    ('em_radiation',       'Elektromagnetische Felder'),
    ('ionizing_radiation', 'Ionisierende Strahlung'),
    ('ultrasonics',        'Ultraschall'),
    ('adiabatic_compress', 'Adiabatische Kompression'),
    ('chemical_reaction',  'Exotherme chemische Reaktionen'),
    ('friction_sparks',    'Reibungsfunken'),
]


def prefill_ignition_sources(zone: ZoneDefinition) -> list[ZoneIgnitionSourceAssessment]:
    """
    Legt alle 13 Zündquellenarten (EN 1127-1) für eine Zone an.
    Setzt is_present=True für heuristische Quellen.
    """
    has_non_ex_electrical = Equipment.objects.filter(
        zone=zone, equipment_category='non_ex', is_active=True
    ).exists()

    assessments = []
    for source_key, source_name in ALL_SOURCES:
        is_present = source_key in ALWAYS_PRESENT
        if source_key == 'electrical_equip' and has_non_ex_electrical:
            is_present = True
        assessments.append(ZoneIgnitionSourceAssessment(
            zone=zone, ignition_source=source_key, source_name=source_name,
            is_present=is_present, auto_prefilled=True,
        ))
    ZoneIgnitionSourceAssessment.objects.bulk_create(assessments)
    return assessments
```

### 3.4 ExIntegrationService Erweiterung

```python
# src/apps/substances/services/ex_integration.py – Erweiterung
EXPLOSIVE_H_CODES = {
    'H220','H221','H222','H223','H224','H225','H226',
    'H240','H241','H242','H250','H261','H270','H271','H272',
}

@transaction.atomic
def handle_new_inventory_item(inventory_item_id: UUID) -> None:
    """Handler für outbox-Event: substances.inventory.created"""
    from apps.substances.models import SiteInventoryItem
    from apps.explosionsschutz.models import ExplosionConcept, Area

    item = SiteInventoryItem.objects.select_related('substance__current_sds').get(id=inventory_item_id)
    sds  = item.substance.current_sds
    if not sds:
        return

    h_codes = {h.h_code for h in sds.hazard_statements.all()}
    if not (h_codes & EXPLOSIVE_H_CODES):
        return

    area, _ = Area.objects.get_or_create(
        site_id=item.site_id, tenant_id=item.tenant_id, code='DEFAULT',
        defaults={'name': 'Allgemeiner Bereich (automatisch)'},
    )

    if not ExplosionConcept.objects.filter(
        area=area, substance=item.substance,
        status__in=['draft', 'in_progress', 'review'],
    ).exists():
        concept = ExplosionConcept.objects.create(
            tenant_id=item.tenant_id, area=area, substance=item.substance,
            title=f'Ex-Schutzkonzept – {item.substance.name}',
            status='draft', auto_draft_from_inventory=True,
        )
        OutboxMessage.objects.create(
            tenant_id=item.tenant_id,
            event_type='explosionsschutz.concept.auto_created',
            aggregate_type='ExplosionConcept', aggregate_id=concept.id,
            payload={
                'concept_id': str(concept.id),
                'substance': item.substance.name,
                'trigger': 'new_inventory_item',
                'h_codes': list(h_codes & EXPLOSIVE_H_CODES),
            },
        )
```

### 3.5 PDF-Service

```python
# src/apps/explosionsschutz/services/ex_document_pdf.py
from uuid import UUID
from weasyprint import HTML, CSS
from django.template.loader import render_to_string
from django.db import transaction
from apps.explosionsschutz.models import ExplosionConcept
from apps.documents.services import store_document_version
from apps.audit.services import emit_audit_event, AuditCategory
from apps.core.request_context import get_context


class ExDocumentPdfService:
    TEMPLATE = 'explosionsschutz/pdf/ex_schutzdokument.html'

    @transaction.atomic
    def generate(self, concept_id: UUID) -> 'DocumentVersion':
        """Generiert Ex-Schutzdokument-PDF, speichert in S3 via documents-App."""
        ctx     = get_context()
        concept = ExplosionConcept.objects.select_related(
            'area__site', 'substance',
        ).prefetch_related(
            'zones__ignition_assessments', 'measures__safety_function', 'equipment_set',
        ).get(id=concept_id, tenant_id=ctx.tenant_id)

        from django.utils.timezone import now
        html_string = render_to_string(self.TEMPLATE, {
            'concept':    concept,
            'sds_data':   concept.substance.ex_relevant_data,
            'zones':      concept.zones.all(),
            'measures':   concept.measures.all().order_by('category'),
            'equipment':  concept.equipment_set.filter(is_active=True),
            'generated_at': now(),
        })

        pdf_bytes   = HTML(string=html_string).write_pdf()
        doc_version = store_document_version(
            tenant_id=ctx.tenant_id,
            file_bytes=pdf_bytes,
            filename=f'Ex-Schutzdokument_{concept.title}_{concept.version}.pdf',
            content_type='application/pdf',
            entity_type='ExplosionConcept', entity_id=concept.id,
        )

        concept.pdf_document = doc_version
        concept.save(update_fields=['pdf_document'])

        emit_audit_event(
            tenant_id=ctx.tenant_id, category=AuditCategory.DOCUMENT,
            action='pdf_generated', entity_type='explosionsschutz.ExplosionConcept',
            entity_id=concept.id,
            payload={'version': concept.version, 'document_id': str(doc_version.id)},
        )
        return doc_version
```

### 3.6 Wizard-Flow (5 Schritte)

| Schritt | URL | HTMX-Target | Status-Transition |
|---------|-----|-------------|------------------|
| 1 | `/<pk>/wizard/step1/` | `#wizard-content` | `draft → in_progress` |
| 2 | `/<pk>/wizard/step2/` | `#zone-proposal` | (Preview) |
| 2b | `/<pk>/zones/<zid>/ignition/` | `#ignition-list` | (auto-prefill) |
| 3 | `/<pk>/wizard/step3/` | `#wizard-content` | (Zündquellen bestätigen) |
| 4 | `/<pk>/wizard/step4/` | `#wizard-content` | `in_progress → review` |
| 5 | `/<pk>/wizard/step5/` | `#wizard-content` | `review → validated` |

---

## 4 Migrationen & Rollout-Reihenfolge

Alle Migrationen sind **additiv** (keine Breaking Changes).

| # | Migration | App | Abhängigkeit | Breaking? |
|---|-----------|-----|-------------|-----------|
| 01 | `0001_create_gbu_reference_tables` | `gbu` | `substances` ✅ | Nein |
| 02 | `0002_create_gbu_activity` | `gbu` | `gbu` 0001, `tenancy` ✅ | Nein |
| 03 | `seed_hazard_categories` (mgmt cmd) | `gbu` | `gbu` 0001 | Nein |
| 04 | `seed_h_code_mappings` (mgmt cmd) | `gbu` | `gbu` 0002 | Nein |
| 05 | `0011_compliance_presets` | `compliance` | — | Nein |
| 06 | `0012_compliance_summary` | `compliance` | `compliance` 0011 | Nein |
| 07 | `0012_equipment_brandschutz_fields` | `explosionsschutz` | `compliance` 0011 | Nein |
| 08 | `seed_inspection_presets` (mgmt cmd) | `compliance` | `explosionsschutz` 0012 | Nein |
| 09 | `0013_zone_classification_rule` | `explosionsschutz` | — | Nein |
| 10 | `seed_zone_classification_rules` (mgmt cmd) | `explosionsschutz` | 0013 | Nein |
| 11 | `0014_ex_concept_auto_draft_field` | `explosionsschutz` | — | Nein |
| 12 | `0015_ignition_auto_prefilled_field` | `explosionsschutz` | — | Nein |

### 4.1 Celery Beat Ergänzungen (`config/celery.py`)

```python
# Ergänzungen in app.conf.beat_schedule:
'gbu-review-reminder': {
    'task': 'apps.gbu.tasks.check_gbu_reviews_due',
    'schedule': crontab(hour=6, minute=10),
},
'compliance-snapshot': {
    'task': 'apps.compliance.tasks.compliance_snapshot_task',
    'schedule': crontab(hour=5, minute=0),
},
'compliance-escalation': {
    'task': 'apps.compliance.tasks.escalation_task',
    'schedule': crontab(hour=6, minute=0),
},

# Task Queues:
'apps.gbu.tasks.*':        {'queue': 'reports'},
'apps.compliance.tasks.*': {'queue': 'default'},
```

### 4.2 `INSTALLED_APPS` Ergänzung

```python
# config/settings.py
INSTALLED_APPS = [
    # ... bestehend ...
    'apps.gbu',        # Modul 2: GBU-Automation
    'apps.compliance', # Modul 3: Compliance-Dashboard
    # apps.explosionsschutz bereits vorhanden (Modul 1: Erweiterung)
]
```

---

## 5 Teststrategie

| Ebene | Tool | Scope | Ort | Ziel-Coverage |
|-------|------|-------|-----|--------------|
| Unit | pytest + factory_boy | Services, Engine-Logik, Models | `tests/gbu/`, `tests/compliance/` | >90 % |
| Integration | pytest-django | DB-Queries, Service↔Model, Outbox | `tests/integration/` | alle happy paths |
| E2E | Playwright | Wizard-Flows, PDF-Download, HTMX | `tests/e2e/` | kritische User Journeys |
| Compliance | pytest parametrize | H-Code Mappings H200–H420 vollständig | `tests/gbu/test_h_codes.py` | 100 % H-Codes |
| PDF | pytest + WeasyPrint | PDF-Output valide, Pflichtfelder vorhanden | `tests/gbu/test_pdf.py` | Smoke-Tests |

### `conftest.py` Fixtures

```python
# tests/conftest.py – Ergänzungen
import pytest
from apps.gbu.models.reference import HazardCategoryRef


@pytest.fixture
def hazard_categories(db):
    fire = HazardCategoryRef.objects.create(
        code='fire_explosion', name='Brand/Explosion',
        category_type='fire_explosion', tops_level='T',
    )
    return {'fire': fire}

@pytest.fixture
def sds_with_h224(substances_factory, db):
    return substances_factory.sds_revision(h_codes=['H224', 'H302'])
```

---

## 6 Sprint-Plan (10 Wochen MVP)

| KW | Sprint-Ziel | Modul 2 (gbu/) | Modul 3 (compliance/) | Modul 1 (ex-Erw.) |
|----|------------|----------------|----------------------|-------------------|
| **1–2** | Datengrundlagen | Models + Migrations 01–04, alle H-Codes seeded | Models + Migrations 05–08, Presets seeded | `ZoneClassificationRule`-Model, Migration 09–10 |
| **3–4** | Core Services | `gbu_engine.py`: derive, risk_score, propose → Unit Tests >90 % | `compliance_query.py`, `DashboardView` Grundgerüst | `ZoneClassificationEngine` + `IgnitionSourceAutoFill` |
| **5–6** | HTMX UI | 5-Schritt-Wizard Schritt 1+2 mit HTMX-Partial | Compliance-Cockpit: KPI-Cards, Überfälligen-Liste | Wizard Step 1+2: Stoff-Auswahl + Zonen-Vorschlag |
| **7–8** | PDF + Async | WeasyPrint GBU + BA (GHS-SVG), Celery-Tasks | Celery: Snapshot + Eskalation + Action-Auto-Erstellung | WeasyPrint Ex-Schutzdokument, `ExDocumentPdfService` |
| **9–10** | Integration + Release | Approve-Flow, `next_review_date` → Compliance-Dashboard, E2E | M2-Integration, M1-Integration, CSV-Export | Wizard Step 3–5, Review+Freigabe, Integration Tests |

### Definition of Done (pro Sprint)

- [ ] Alle neuen Models haben Migrations (forwards + backwards getestet)
- [ ] Unit-Test-Coverage neuer Services ≥ 90 %
- [ ] HTMX-Partials im Browser getestet (Chrome + Firefox)
- [ ] Seed-Commands idempotent (mehrfaches Ausführen = keine Duplikate)
- [ ] Audit-Events für alle Create/Update/Approve-Aktionen vorhanden
- [ ] Outbox-Topics für async Benachrichtigungen definiert und getestet
- [ ] Permissions in `DEFAULT_PERMISSIONS` registriert
- [ ] Admin-Interface für neue Models registriert

### Deployment (kein Extra-Aufwand)

Alle drei Module deployen als Teil der bestehenden `risk-hub` App. Kein separater Service, kein neues Docker-Image.

- 3 neue Celery-Beat-Einträge in `celery.py`
- 2 neue `INSTALLED_APPS` Einträge in `settings.py`
- WeasyPrint bereits als Dependency vorhanden (`reporting`-App nutzt es bereits)
- GHS-Piktogramm-SVGs als Static Files einmalig hinzufügen (UNECE-Lizenz: frei verwendbar)
