# IMPL-008 · Phase 2A — GBU-App: Models, Migrations, Seed-Daten

**Typ:** Agent-führbares Implementierungskonzept  
**Bezug:** ADR-008 (Modul 2: GBU-Automation), Phase 2A  
**Datum:** 2026-03-03  
**Voraussetzung:** risk-hub läuft lokal, Tests grün

---

## Ziel dieser Phase

Am Ende von Phase 2A gilt:

- `src/gbu/` ist eine vollständige Django-App (registriert, migriert)
- 3 Referenz-Models: `HazardCategoryRef`, `HCodeCategoryMapping`, `MeasureTemplate`
- 1 Haupt-Model: `HazardAssessmentActivity` + `ActivityMeasure`
- Migrations angelegt und angewendet
- Seed-Daten: alle H200–H420 gemappt (min. 48 H-Codes → 10 Kategorien)
- Admin-Interface registriert
- Unit-Tests: ≥ 80% Coverage der Models
- CI grün (ruff + pytest)

---

## Schritt 1 — Verzeichnisstruktur anlegen

```
src/gbu/__init__.py
src/gbu/apps.py
src/gbu/admin.py
src/gbu/forms.py
src/gbu/views.py
src/gbu/urls.py
src/gbu/tasks.py
src/gbu/models/__init__.py
src/gbu/models/reference.py
src/gbu/models/activity.py
src/gbu/services/__init__.py
src/gbu/services/gbu_engine.py
src/gbu/services/pdf_service.py
src/gbu/migrations/__init__.py
src/gbu/templates/gbu/.gitkeep
src/gbu/fixtures/hazard_categories.json
src/gbu/fixtures/h_code_mappings.json
src/gbu/management/__init__.py
src/gbu/management/commands/__init__.py
src/gbu/management/commands/seed_hazard_categories.py
src/gbu/management/commands/seed_h_code_mappings.py
src/gbu/tests/__init__.py
src/gbu/tests/test_models.py
src/gbu/tests/test_services.py
```

---

## Schritt 2 — `apps.py`

```python
# src/gbu/apps.py
from django.apps import AppConfig


class GbuConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "gbu"
    verbose_name = "GBU-Automation"
```

---

## Schritt 3 — `models/reference.py`

```python
# src/gbu/models/reference.py
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
        db_index=True,
    )
    trgs_reference = models.CharField(max_length=50, blank=True, default="")
    description    = models.TextField(blank=True, default="")
    sort_order     = models.PositiveSmallIntegerField(default=0)

    class Meta:
        db_table = "gbu_hazard_category_ref"
        ordering = ["category_type", "sort_order", "name"]
        verbose_name = "Gefährdungskategorie"
        verbose_name_plural = "Gefährdungskategorien"

    def __str__(self) -> str:
        return f"{self.code} — {self.name}"


class HCodeCategoryMapping(models.Model):
    """H-Code → Gefährdungskategorie (n:m, admin-pflegbar)."""

    h_code     = models.CharField(max_length=10, db_index=True)
    category   = models.ForeignKey(
        HazardCategoryRef,
        on_delete=models.CASCADE,
        related_name="h_code_mappings",
    )
    annotation = models.TextField(blank=True, default="")

    class Meta:
        db_table        = "gbu_h_code_category_mapping"
        unique_together = [("h_code", "category")]
        ordering = ["h_code"]
        verbose_name = "H-Code Mapping"
        verbose_name_plural = "H-Code Mappings"

    def __str__(self) -> str:
        return f"{self.h_code} → {self.category.code}"


class MeasureTemplate(models.Model):
    """TOPS-Schutzmaßnahmen-Vorlage, verknüpft mit Gefährdungskategorie."""

    category     = models.ForeignKey(
        HazardCategoryRef,
        on_delete=models.CASCADE,
        related_name="measure_templates",
    )
    tops_type    = models.CharField(
        max_length=1,
        choices=[(t.value, t.name.title()) for t in TOPSType],
        db_index=True,
    )
    title        = models.CharField(max_length=300)
    description  = models.TextField(blank=True, default="")
    legal_basis  = models.CharField(max_length=200, blank=True, default="")
    is_mandatory = models.BooleanField(default=False)
    sort_order   = models.PositiveSmallIntegerField(default=0)

    class Meta:
        db_table = "gbu_measure_template"
        ordering = ["tops_type", "sort_order"]
        verbose_name = "Maßnahmen-Vorlage"
        verbose_name_plural = "Maßnahmen-Vorlagen"

    def __str__(self) -> str:
        return f"[{self.tops_type}] {self.title}"
```

---

## Schritt 4 — `models/activity.py`

```python
# src/gbu/models/activity.py
import uuid
from enum import StrEnum

from django.conf import settings
from django.db import models

from gbu.models.reference import HazardCategoryRef, MeasureTemplate, TOPSType


class ActivityFrequency(StrEnum):
    DAILY      = "daily"
    WEEKLY     = "weekly"
    OCCASIONAL = "occasional"
    RARE       = "rare"


class QuantityClass(StrEnum):
    XS = "xs"
    S  = "s"
    M  = "m"
    L  = "l"


class RiskScore(StrEnum):
    LOW      = "low"
    MEDIUM   = "medium"
    HIGH     = "high"
    CRITICAL = "critical"


class ActivityStatus(StrEnum):
    DRAFT    = "draft"
    REVIEW   = "review"
    APPROVED = "approved"
    OUTDATED = "outdated"


class HazardAssessmentActivity(models.Model):
    """
    GBU-Tätigkeit mit Gefahrstoff — Kern-Entity Modul 2.

    Compliance: kein DELETE-Permission, SdsRevision PROTECT.
    """

    id                        = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant_id                 = models.UUIDField(db_index=True)
    site                      = models.ForeignKey("tenancy.Site", on_delete=models.PROTECT, related_name="gbu_activities")
    sds_revision              = models.ForeignKey("substances.SdsRevision", on_delete=models.PROTECT, related_name="gbu_activities")
    activity_description      = models.TextField()
    activity_frequency        = models.CharField(max_length=15, choices=[(f.value, f.name.title()) for f in ActivityFrequency])
    duration_minutes          = models.PositiveSmallIntegerField()
    quantity_class            = models.CharField(max_length=2, choices=[(q.value, q.name) for q in QuantityClass])
    substitution_checked      = models.BooleanField(default=False)
    substitution_notes        = models.TextField(blank=True, default="")
    derived_hazard_categories = models.ManyToManyField(HazardCategoryRef, blank=True, related_name="activities")
    risk_score                = models.CharField(max_length=10, choices=[(r.value, r.name.title()) for r in RiskScore], blank=True, default="")
    status                    = models.CharField(max_length=10, choices=[(s.value, s.name.title()) for s in ActivityStatus], default=ActivityStatus.DRAFT, db_index=True)
    approved_by               = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="+")
    approved_at               = models.DateTimeField(null=True, blank=True)
    next_review_date          = models.DateField(null=True, blank=True)
    gbu_document              = models.ForeignKey("documents.DocumentVersion", on_delete=models.SET_NULL, null=True, blank=True, related_name="+")
    ba_document               = models.ForeignKey("documents.DocumentVersion", on_delete=models.SET_NULL, null=True, blank=True, related_name="+")
    created_at                = models.DateTimeField(auto_now_add=True)
    updated_at                = models.DateTimeField(auto_now=True)
    created_by                = models.UUIDField(null=True, blank=True)

    class Meta:
        db_table            = "gbu_hazard_assessment_activity"
        default_permissions = ("add", "change", "view")
        ordering            = ["-created_at"]
        indexes             = [
            models.Index(fields=["tenant_id", "status"], name="ix_gbu_activity_tenant_status"),
            models.Index(fields=["tenant_id", "next_review_date"], name="ix_gbu_activity_review_date"),
        ]
        verbose_name        = "GBU-Tätigkeit"
        verbose_name_plural = "GBU-Tätigkeiten"

    def __str__(self) -> str:
        return f"{self.activity_description[:60]} ({self.status})"

    @property
    def is_approved(self) -> bool:
        return self.status == ActivityStatus.APPROVED


class ActivityMeasure(models.Model):
    """Konkrete Schutzmaßnahme einer GBU-Tätigkeit."""

    id           = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    activity     = models.ForeignKey(HazardAssessmentActivity, on_delete=models.PROTECT, related_name="measures")
    template     = models.ForeignKey(MeasureTemplate, on_delete=models.PROTECT, null=True, blank=True)
    tops_type    = models.CharField(max_length=1, choices=[(t.value, t.name.title()) for t in TOPSType])
    title        = models.CharField(max_length=300)
    description  = models.TextField(blank=True, default="")
    legal_basis  = models.CharField(max_length=200, blank=True, default="")
    is_confirmed = models.BooleanField(default=False)
    is_mandatory = models.BooleanField(default=False)
    sort_order   = models.PositiveSmallIntegerField(default=0)
    created_at   = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "gbu_activity_measure"
        ordering = ["tops_type", "sort_order"]
        verbose_name = "GBU-Schutzmaßnahme"
        verbose_name_plural = "GBU-Schutzmaßnahmen"

    def __str__(self) -> str:
        return f"[{self.tops_type}] {self.title}"
```

---

## Schritt 5 — `models/__init__.py`

```python
# src/gbu/models/__init__.py
from gbu.models.reference import (
    HazardCategoryRef, HazardCategoryType,
    HCodeCategoryMapping, MeasureTemplate, TOPSType,
)
from gbu.models.activity import (
    ActivityFrequency, ActivityMeasure, ActivityStatus,
    HazardAssessmentActivity, QuantityClass, RiskScore,
)

__all__ = [
    "ActivityFrequency", "ActivityMeasure", "ActivityStatus",
    "HazardAssessmentActivity", "HazardCategoryRef", "HazardCategoryType",
    "HCodeCategoryMapping", "MeasureTemplate", "QuantityClass",
    "RiskScore", "TOPSType",
]
```

---

## Schritt 6 — `settings.py` anpassen

In `src/config/settings.py` in `INSTALLED_APPS` einfügen (nach `"dsb"`):

```python
"gbu",
```

In `MODULE_URL_MAP` ergänzen:

```python
"/gbu/": "gbu",
"/api/gbu/": "gbu",
```

---

## Schritt 7 — `urls.py` (Stub)

```python
# src/gbu/urls.py
from django.urls import path

app_name = "gbu"
urlpatterns = []
```

In `src/config/urls.py` einfügen:

```python
path("gbu/", include("gbu.urls")),
```

---

## Schritt 8 — `admin.py`

```python
# src/gbu/admin.py
from django.contrib import admin
from gbu.models.reference import HazardCategoryRef, HCodeCategoryMapping, MeasureTemplate
from gbu.models.activity import HazardAssessmentActivity, ActivityMeasure


@admin.register(HazardCategoryRef)
class HazardCategoryRefAdmin(admin.ModelAdmin):
    list_display  = ["code", "name", "category_type", "trgs_reference", "sort_order"]
    list_filter   = ["category_type"]
    search_fields = ["code", "name"]


@admin.register(HCodeCategoryMapping)
class HCodeCategoryMappingAdmin(admin.ModelAdmin):
    list_display  = ["h_code", "category", "annotation"]
    list_filter   = ["category__category_type"]
    search_fields = ["h_code"]
    ordering      = ["h_code"]


@admin.register(MeasureTemplate)
class MeasureTemplateAdmin(admin.ModelAdmin):
    list_display  = ["title", "tops_type", "category", "is_mandatory", "sort_order"]
    list_filter   = ["tops_type", "is_mandatory"]
    search_fields = ["title"]


class ActivityMeasureInline(admin.TabularInline):
    model  = ActivityMeasure
    extra  = 0
    fields = ["tops_type", "title", "is_confirmed", "is_mandatory"]


@admin.register(HazardAssessmentActivity)
class HazardAssessmentActivityAdmin(admin.ModelAdmin):
    list_display   = ["activity_description_short", "status", "risk_score", "tenant_id", "next_review_date"]
    list_filter    = ["status", "risk_score"]
    search_fields  = ["activity_description"]
    readonly_fields = ["id", "created_at", "updated_at", "approved_at"]
    inlines        = [ActivityMeasureInline]

    def activity_description_short(self, obj):
        return obj.activity_description[:60]
    activity_description_short.short_description = "Tätigkeit"
```

---

## Schritt 9 — Migration erstellen

```bash
DJANGO_SETTINGS_MODULE=config.settings_test PYTHONPATH=src \
  python src/manage.py makemigrations gbu --name initial_gbu_models
DJANGO_SETTINGS_MODULE=config.settings_test PYTHONPATH=src \
  python src/manage.py migrate
```

---

## Schritt 10 — Seed-Fixtures

### `fixtures/hazard_categories.json` — 10 Kategorien (TRGS 400 vollständig)

```json
[
  {"model": "gbu.hazardcategoryref", "pk": 1, "fields": {"code": "GK-BRAND", "name": "Brand- und Explosionsgefahr", "category_type": "fire_explosion", "trgs_reference": "TRGS 400 Abschnitt 5.3.1", "description": "H220-H225, H228, H240-H242", "sort_order": 10}},
  {"model": "gbu.hazardcategoryref", "pk": 2, "fields": {"code": "GK-AKUT-TOX", "name": "Akute Toxizität", "category_type": "acute_toxic", "trgs_reference": "TRGS 400 Abschnitt 5.3.2", "description": "H300, H301, H310, H311, H330, H331", "sort_order": 20}},
  {"model": "gbu.hazardcategoryref", "pk": 3, "fields": {"code": "GK-CHRON-TOX", "name": "Chronische Toxizität / Organtoxizität", "category_type": "chronic_toxic", "trgs_reference": "TRGS 400 Abschnitt 5.3.3", "description": "H370, H371, H372, H373", "sort_order": 30}},
  {"model": "gbu.hazardcategoryref", "pk": 4, "fields": {"code": "GK-HAUT", "name": "Ätz-/Reizwirkung Haut", "category_type": "skin_corrosion", "trgs_reference": "TRGS 400 Abschnitt 5.3.4", "description": "H314, H315", "sort_order": 40}},
  {"model": "gbu.hazardcategoryref", "pk": 5, "fields": {"code": "GK-AUGE", "name": "Augenschäden / Augenreizung", "category_type": "eye_damage", "trgs_reference": "TRGS 400 Abschnitt 5.3.5", "description": "H318, H319", "sort_order": 50}},
  {"model": "gbu.hazardcategoryref", "pk": 6, "fields": {"code": "GK-ATEM", "name": "Atemwegs-/Hautsensibilisierung", "category_type": "respiratory", "trgs_reference": "TRGS 400 Abschnitt 5.3.6", "description": "H334, H317", "sort_order": 60}},
  {"model": "gbu.hazardcategoryref", "pk": 7, "fields": {"code": "GK-CMR", "name": "CMR-Stoffe (Karzinogen/Mutagen/Reproduktionstoxisch)", "category_type": "cmr", "trgs_reference": "TRGS 400 Abschnitt 5.3.7 / TRGS 905", "description": "H340, H341, H350, H351, H360, H361", "sort_order": 70}},
  {"model": "gbu.hazardcategoryref", "pk": 8, "fields": {"code": "GK-UMWELT", "name": "Umweltgefährlichkeit", "category_type": "environment", "trgs_reference": "TRGS 400 Abschnitt 5.3.8", "description": "H400, H410, H411, H412", "sort_order": 80}},
  {"model": "gbu.hazardcategoryref", "pk": 9, "fields": {"code": "GK-ERSTICK", "name": "Erstickungsgefahr / Sauerstoffverdrängung", "category_type": "asphyxiant", "trgs_reference": "TRGS 400 Abschnitt 5.3.9", "description": "Gase ohne H-Satz", "sort_order": 90}},
  {"model": "gbu.hazardcategoryref", "pk": 10, "fields": {"code": "GK-HAUT-SENS", "name": "Hautsensibilisierung", "category_type": "skin_sens", "trgs_reference": "TRGS 400 Abschnitt 5.3.6", "description": "H317", "sort_order": 65}}
]
```

### `fixtures/h_code_mappings.json` — 48 H-Code-Mappings (H220–H412)

Siehe vollständige Liste in der lokalen Datei `docs/adr/IMPL-008-phase2A-gbu-app.md` Schritt 11.

---

## Schritt 11 — Management Commands

```python
# src/gbu/management/commands/seed_hazard_categories.py
from django.core.management.base import BaseCommand
from django.core.management import call_command

class Command(BaseCommand):
    help = "Seed GBU Gefährdungskategorien aus Fixture"
    def handle(self, *args, **options):
        call_command("loaddata", "gbu/fixtures/hazard_categories.json")
        from gbu.models.reference import HazardCategoryRef
        self.stdout.write(self.style.SUCCESS(f"OK: {HazardCategoryRef.objects.count()} Kategorien"))
```

```python
# src/gbu/management/commands/seed_h_code_mappings.py
from django.core.management.base import BaseCommand
from django.core.management import call_command

class Command(BaseCommand):
    help = "Seed GBU H-Code Mappings aus Fixture"
    def handle(self, *args, **options):
        call_command("loaddata", "gbu/fixtures/h_code_mappings.json")
        from gbu.models.reference import HCodeCategoryMapping
        self.stdout.write(self.style.SUCCESS(f"OK: {HCodeCategoryMapping.objects.count()} Mappings"))
```

---

## Schritt 12 — Tests: `tests/test_models.py`

```python
# src/gbu/tests/test_models.py
import pytest
from gbu.models.reference import HazardCategoryRef, HazardCategoryType, HCodeCategoryMapping, MeasureTemplate, TOPSType
from gbu.models.activity import ActivityStatus, HazardAssessmentActivity, RiskScore, QuantityClass


def test_should_hazard_category_type_be_str_compatible():
    assert HazardCategoryType.FIRE_EXPLOSION == "fire_explosion"
    assert isinstance(HazardCategoryType.CMR, str)

def test_should_tops_type_be_str_compatible():
    assert TOPSType.SUBSTITUTION == "S"
    assert TOPSType.PERSONAL == "P"

def test_should_activity_status_be_str_compatible():
    assert ActivityStatus.DRAFT == "draft"
    assert ActivityStatus.APPROVED == "approved"

def test_should_risk_score_cover_all_emkg_classes():
    assert RiskScore.LOW == "low"
    assert RiskScore.CRITICAL == "critical"

def test_should_activity_have_no_delete_permission():
    perms = HazardAssessmentActivity._meta.default_permissions
    assert "delete" not in perms
    assert "add" in perms and "view" in perms and "change" in perms

def test_should_models_have_correct_db_tables():
    assert HazardCategoryRef._meta.db_table == "gbu_hazard_category_ref"
    assert HCodeCategoryMapping._meta.db_table == "gbu_h_code_category_mapping"
    assert HazardAssessmentActivity._meta.db_table == "gbu_hazard_assessment_activity"

@pytest.mark.django_db
def test_should_create_hazard_category_ref():
    cat = HazardCategoryRef.objects.create(
        code="TEST-FIRE", name="Test Brand",
        category_type=HazardCategoryType.FIRE_EXPLOSION,
    )
    assert cat.pk is not None
    assert str(cat) == "TEST-FIRE — Test Brand"

@pytest.mark.django_db
def test_should_create_h_code_mapping():
    cat = HazardCategoryRef.objects.create(code="TEST-CMR", name="CMR", category_type=HazardCategoryType.CMR)
    m = HCodeCategoryMapping.objects.create(h_code="H350", category=cat, annotation="Karzinogen")
    assert str(m) == "H350 → TEST-CMR"

@pytest.mark.django_db
def test_should_enforce_unique_h_code_per_category():
    from django.db import IntegrityError
    cat = HazardCategoryRef.objects.create(code="TEST-U", name="U", category_type=HazardCategoryType.ACUTE_TOXIC)
    HCodeCategoryMapping.objects.create(h_code="H300", category=cat)
    with pytest.raises(IntegrityError):
        HCodeCategoryMapping.objects.create(h_code="H300", category=cat)

@pytest.mark.django_db
def test_should_create_measure_template():
    cat = HazardCategoryRef.objects.create(code="TEST-PSA", name="PSA", category_type=HazardCategoryType.SKIN_CORROSION)
    t = MeasureTemplate.objects.create(category=cat, tops_type=TOPSType.PERSONAL, title="Handschuhe", is_mandatory=True)
    assert t.is_mandatory is True
    assert "[P]" in str(t)
```

---

## Ausführungsreihenfolge für den Agent

```bash
# 1. Alle Dateien gemäß Schritt 1-12 anlegen

# 2. Migration
DJANGO_SETTINGS_MODULE=config.settings_test PYTHONPATH=src \
  python src/manage.py makemigrations gbu --name initial_gbu_models
DJANGO_SETTINGS_MODULE=config.settings_test PYTHONPATH=src \
  python src/manage.py migrate

# 3. System-Check
DJANGO_SETTINGS_MODULE=config.settings_test PYTHONPATH=src \
  python src/manage.py check

# 4. Tests
DJANGO_SETTINGS_MODULE=config.settings_test PYTHONPATH=src \
  python -m pytest src/gbu/tests/ -v --tb=short

# 5. Ruff
ruff check src/gbu/

# 6. Seed (auf Server nach Deploy)
python src/manage.py seed_hazard_categories
python src/manage.py seed_h_code_mappings
```

---

## Abnahmekriterien (Definition of Done Phase 2A)

| # | Kriterium | Prüfung |
|---|-----------|----------|
| 1 | `manage.py check` ohne Fehler | Shell |
| 2 | Migration `0001_initial_gbu_models.py` existiert | Datei |
| 3 | Alle 5 Tabellen angelegt (`gbu_*`) | `\dt gbu_*` |
| 4 | `pytest src/gbu/tests/` → 0 failures | Test-Output |
| 5 | `default_permissions` kein `delete` | Test #5 grün |
| 6 | `ruff check src/gbu/` → 0 Errors | Ruff |
| 7 | Admin zeigt alle 4 Models | Browser |
| 8 | Seed: 10 Kategorien, 48 Mappings | Command-Output |
| 9 | CI Pipeline grün | GitHub Actions |

---

## Was Phase 2A NICHT enthält (kommt Phase 2B)

- `calculate_risk_score()` (EMKG-Matrix)
- `approve_activity()` mit Audit-Event
- HTMX-Views und Templates
- Celery-Tasks für PDF
- `ExposureRiskMatrix`-Model

---

*IMPL-008 Phase 2A · 2026-03-03 · Bereit zur Agent-Ausführung*
