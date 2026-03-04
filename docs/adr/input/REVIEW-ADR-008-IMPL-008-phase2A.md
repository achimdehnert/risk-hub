# REVIEW: ADR-008 & IMPL-008 Phase 2A — GBU-App

**Reviewer:** Senior Architecture Review (Production-Critical)  
**Datum:** 2026-03-03  
**Review-Typ:** Blocking Review  
**Dokumente:** `ADR-008-module-1-3-gbu-compliance-ex-dokument.md` · `IMPL-008-phase2A-gbu-app.md`  
**Plattform-Basis:** Django + HTMX + PostgreSQL 16 (Hetzner, Docker, ADR-022-konform)  
**Bewertung:** 🔴 ÜBERARBEITUNG ERFORDERLICH — 4 kritische, 4 hohe, 4 mittlere, 3 niedrige Befunde

---

## Executive Summary

Der strategische Ansatz (H-Code → GBU → BA, database-driven, service-layer-first) ist
korrekt und gut begründet. Die Dokumente enthalten jedoch **vier produktionskritische
Architekturverletzungen**, die auf dem lokalen Entwicklungssystem unsichtbar bleiben,
aber in der PostgreSQL-16-Produktion zu Datenverlust, RLS-Bypass oder nicht-idempotenten
Deployments führen.

**Merge freigeben erst nach:** Behebung aller 🔴 Kritischen und 🟠 Hohen Befunde.

---

## Schweregrade

| Symbol | Schwere | Bedeutung |
|--------|---------|-----------|
| 🔴 | KRITISCH | Produktions-Blocker, Dateninkonsistenz oder Security-Verletzung |
| 🟠 | HOCH | Compliance-Verletzung oder stiller Laufzeitfehler |
| 🟡 | MITTEL | Tech-Debt, schlechtere Testbarkeit oder Wartungsrisiko |
| 🔵 | NIEDRIG | Stil/Konvention, kein funktionaler Impact |

---

## 🔴 KRITISCHE BEFUNDE (Blocker)

---

### K1 — App-Pfad-Konflikt: `src/gbu/` vs. `src/apps/gbu/`

**Befund**

IMPL-008 §Schritt 1 legt `src/gbu/__init__.py` an.  
`apps.py` definiert `name = "gbu"`.  
IMPL-008 §Schritt 6 trägt `"gbu"` in `INSTALLED_APPS` ein.

Die gesamte Plattform liegt unter `src/apps/` (Architektur-Dokument):
```
src/apps/core/   apps.py → name = "apps.core"
src/apps/tenancy/ apps.py → name = "apps.tenancy"
src/apps/audit/   apps.py → name = "apps.audit"
```

ADR-008 §3.1 nennt selbst `src/apps/gbu/` — IMPL-008 weicht davon ab.

**Risiko**

- `python manage.py check` schlägt fehl oder findet die App nicht.
- `makemigrations gbu` erzeugt falsche Migrations-Labels.
- Import-Konflikte wenn Django beide Pfade sucht.
- `ruff` / `mypy` konfiguriert auf `src/apps/` — false positives.

**Empfehlung**

```
# Korrekte Verzeichnisstruktur
src/apps/gbu/__init__.py
src/apps/gbu/apps.py         # name = "apps.gbu"
src/apps/gbu/models/...
src/apps/gbu/services/...

# settings.py INSTALLED_APPS
"apps.gbu",   # nicht "gbu"

# config/urls.py
path("gbu/", include("apps.gbu.urls")),
```

---

### K2 — `h_statements` ist kein gültiger Related-Name (Runtime-Bug)

**Befund**

`gbu_engine.py` Zeile 859:
```python
revision = SdsRevision.objects.prefetch_related("h_statements").get(id=sds_revision_id)
h_codes  = list(revision.h_statements.values_list("h_code", flat=True))
```

Laut ADR-002 und `src/substances/models/sds.py` (project knowledge) heißt der
Related-Manager auf `SdsRevision`:

```python
class SdsHazardStatement(models.Model):
    sds_revision = models.ForeignKey(
        SdsRevision,
        on_delete=models.CASCADE,
        related_name="hazard_statements",   # ← korrekt
    )
```

`h_statements` existiert nicht. Der Zugriff wirft zur Laufzeit:
```
AttributeError: 'SdsRevision' object has no attribute 'h_statements'
```

Im Stub-Test (test_services.py Zeile 1104) wird dasselbe falsche Attribut gemockt:
```python
mock_revision.h_statements.values_list.return_value = []
```
→ Der Test ist grün, deckt den echten Bug aber nicht auf.

**Risiko**

Jeder Aufruf von `derive_hazard_categories()` schlägt in Produktion fehl.  
Der bestehende Test gibt fälschlicherweise grünes Licht.

**Empfehlung**

```python
# src/apps/gbu/services/gbu_engine.py
revision = SdsRevision.objects.prefetch_related(
    "hazard_statements"          # ← korrekter related_name aus ADR-002
).get(id=sds_revision_id)

h_codes = list(revision.hazard_statements.values_list("h_code", flat=True))
```

```python
# src/apps/gbu/tests/test_services.py — Test reparieren
mock_revision.hazard_statements.values_list.return_value = []

# Zusätzlich: Integrations-Test mit echter DB-Relation (pytest.mark.django_db)
@pytest.mark.django_db
def test_should_derive_categories_from_h_code_h224(sds_revision_factory, h_code_mapping_factory):
    sds = sds_revision_factory(h_codes=["H224"])
    h_code_mapping_factory(h_code="H224", category__code="fire_explosion")
    result = derive_hazard_categories(sds.id)
    assert len(result) == 1
    assert result[0].code == "fire_explosion"
```

---

### K3 — Seed-Commands sind nicht idempotent (Fixture mit Integer-PKs)

**Befund**

Beide Seed-Commands delegieren an `loaddata`:
```python
# seed_hazard_categories.py + seed_h_code_mappings.py
call_command("loaddata", "gbu/fixtures/hazard_categories.json", verbosity=1)
```

Die Fixture enthält **explizite Integer-PKs**:
```json
{"model": "gbu.hcodecategorymapping", "pk": 20, "fields": {"h_code": "H302", "category": 2, ...}}
```

`loaddata` auf PostgreSQL verhält sich bei bereits vorhandenen Daten wie folgt:
- Existiert `pk=20` → `UPDATE` (überschreibt manuelle Admin-Änderungen still)
- Existiert `pk=20` nicht → `INSERT`

Zweites Problem: `category: 2` referenziert den Integer-PK der `HazardCategoryRef`.
Wenn `seed_hazard_categories` auf einer leeren DB oder einer DB mit anderem Inhalt
läuft, wird PK=2 einer anderen Kategorie zugeordnet. Die Referenz ist **fragil**.

Qualitätskriterium „Idempotent: mehrfaches Ausführen darf nicht kaputt machen" —
**nicht erfüllt**.

**Risiko**

- Produktions-Seed überschreibt Admin-gepflegte Mappings still.
- Kategorien-FK-Referenzen in Fixtures korrelieren implizit mit Einfüge-Reihenfolge.
- PostgreSQL-Sequenz driftet (BigAutoField + explizite Integer-PKs = Sequenz muss
  manuell auf `max(pk)+1` gesetzt werden nach `loaddata`).

**Empfehlung**

Seed-Commands mit `update_or_create()` auf natürlichen Schlüsseln, **keine Fixtures**
für Referenzdaten:

```python
# src/apps/gbu/management/commands/seed_hazard_categories.py
"""
Seed-Command: GBU Gefährdungskategorien (HazardCategoryRef).

Idempotent: update_or_create auf naturalem Schlüssel 'code'.
Mehrfaches Ausführen ist sicher (CI, Post-Deploy, lokale Einrichtung).
"""
import logging

from django.core.management.base import BaseCommand
from django.db import transaction

from apps.gbu.models.reference import HazardCategoryRef, HazardCategoryType

logger = logging.getLogger(__name__)

# Referenzdaten: Quelle TRGS 400 (Stand 2024-09)
# Erweiterungen: neue Zeile hinzufügen, code ist natürlicher Schlüssel
HAZARD_CATEGORIES: list[dict] = [
    {
        "code":          "fire_explosion",
        "name":          "Brand und Explosion",
        "category_type": HazardCategoryType.FIRE_EXPLOSION,
        "trgs_reference": "TRGS 400 Abschnitt 5.3",
        "description":   "Entzündbare Flüssigkeiten, Gase, Feststoffe",
        "sort_order":    10,
    },
    {
        "code":          "acute_toxic",
        "name":          "Akute Toxizität",
        "category_type": HazardCategoryType.ACUTE_TOXIC,
        "trgs_reference": "TRGS 400 Abschnitt 5.4",
        "description":   "Akut giftig bei Einatmen, Hautkontakt oder Verschlucken",
        "sort_order":    20,
    },
    {
        "code":          "chronic_toxic",
        "name":          "Chronische Toxizität (STOT)",
        "category_type": HazardCategoryType.CHRONIC_TOXIC,
        "trgs_reference": "TRGS 400 Abschnitt 5.5",
        "description":   "Schädigung bei wiederholter Exposition (STOT SE/RE)",
        "sort_order":    30,
    },
    {
        "code":          "skin_corrosion",
        "name":          "Ätz-/Reizwirkung Haut",
        "category_type": HazardCategoryType.SKIN_CORROSION,
        "trgs_reference": "TRGS 401",
        "description":   "Verätzung oder Reizung der Haut",
        "sort_order":    40,
    },
    {
        "code":          "eye_damage",
        "name":          "Augenschäden",
        "category_type": HazardCategoryType.EYE_DAMAGE,
        "trgs_reference": "TRGS 400 Abschnitt 5.6",
        "description":   "Schwere Augenschäden oder Augenreizung",
        "sort_order":    50,
    },
    {
        "code":          "respiratory",
        "name":          "Atemwegssensibilisierung",
        "category_type": HazardCategoryType.RESPIRATORY,
        "trgs_reference": "TRGS 406",
        "description":   "Sensibilisierung der Atemwege (Berufsasthma)",
        "sort_order":    60,
    },
    {
        "code":          "skin_sens",
        "name":          "Hautsensibilisierung",
        "category_type": HazardCategoryType.SKIN_SENS,
        "trgs_reference": "TRGS 401",
        "description":   "Allergische Kontaktdermatitis",
        "sort_order":    70,
    },
    {
        "code":          "cmr",
        "name":          "CMR-Stoff (Karzinogen/Mutagen/Reproduktionstoxisch)",
        "category_type": HazardCategoryType.CMR,
        "trgs_reference": "TRGS 905, TRGS 906",
        "description":   "Krebserzeugend, keimzellmutagen oder reproduktionstoxisch",
        "sort_order":    80,
    },
    {
        "code":          "environment",
        "name":          "Umweltgefährlichkeit",
        "category_type": HazardCategoryType.ENVIRONMENT,
        "trgs_reference": "TRGS 400 Abschnitt 5.9",
        "description":   "Aquatische oder terrestrische Toxizität",
        "sort_order":    90,
    },
    {
        "code":          "asphyxiant",
        "name":          "Erstickungsgefahr",
        "category_type": HazardCategoryType.ASPHYXIANT,
        "trgs_reference": "TRGS 400 Abschnitt 5.10",
        "description":   "Sauerstoffverdrängung oder chemische Erstickung",
        "sort_order":    100,
    },
]


class Command(BaseCommand):
    help = "Seed GBU Gefährdungskategorien — idempotent via update_or_create(code)"

    @transaction.atomic
    def handle(self, *args, **options) -> None:
        created_count  = 0
        updated_count  = 0

        for data in HAZARD_CATEGORIES:
            code = data.pop("code")
            _, created = HazardCategoryRef.objects.update_or_create(
                code=code,
                defaults=data,
            )
            if created:
                created_count += 1
                self.stdout.write(f"  + Erstellt: {code}")
            else:
                updated_count += 1
                self.stdout.write(f"  ~ Aktualisiert: {code}")

        total = HazardCategoryRef.objects.count()
        self.stdout.write(
            self.style.SUCCESS(
                f"OK: {created_count} erstellt, {updated_count} aktualisiert "
                f"— {total} Kategorien gesamt"
            )
        )
```

```python
# src/apps/gbu/management/commands/seed_h_code_mappings.py
"""
Seed-Command: GBU H-Code-Kategorie-Mappings.

Idempotent: get_or_create auf (h_code, category). Bestehende Mappings
werden nicht überschrieben (Admin-Pflege bleibt erhalten).
Annotation-Update via update_or_create wenn gewünscht: --force Flag.
"""
import logging

from django.core.management.base import BaseCommand, CommandParser
from django.db import transaction

from apps.gbu.models.reference import HazardCategoryRef, HCodeCategoryMapping

logger = logging.getLogger(__name__)

# Quelle: GHS-Verordnung (CLP-VO EG 1272/2008), TRGS 400 (Stand 2024-09)
# Format: (h_code, category_code, annotation)
# category_code referenziert HazardCategoryRef.code (natürlicher Schlüssel)
H_CODE_MAPPINGS: list[tuple[str, str, str]] = [
    # ── Brand / Explosion ────────────────────────────────────────────────────
    ("H220", "fire_explosion", "Extrem entzündbares Gas — Zone 0/20 prüfen (TRGS 720)"),
    ("H221", "fire_explosion", "Entzündbares Gas"),
    ("H222", "fire_explosion", "Extrem entzündbares Aerosol"),
    ("H223", "fire_explosion", "Entzündbares Aerosol"),
    ("H224", "fire_explosion", "Flüss. Flammpunkt < 23°C, Siedepunkt ≤ 35°C — Kat. 1"),
    ("H225", "fire_explosion", "Leichtentzündbare Flüssigkeit — Flammpunkt 23–60°C"),
    ("H226", "fire_explosion", "Entzündbare Flüssigkeit — Flammpunkt 60–93°C"),
    ("H228", "fire_explosion", "Entzündbarer Feststoff"),
    ("H240", "fire_explosion", "Explosionsgefährlich bei Erwärmung"),
    ("H241", "fire_explosion", "Entzündbar oder explosionsgefährlich bei Erwärmung"),
    ("H242", "fire_explosion", "Entzündbar bei Erwärmung"),
    ("H250", "fire_explosion", "Entzündet sich in Berührung mit Luft selbst"),
    ("H251", "fire_explosion", "Selbsterhitzungsfähig in großen Mengen"),
    ("H252", "fire_explosion", "Selbsterhitzungsfähig in großen Mengen — Brandgefahr"),
    ("H260", "fire_explosion", "Entzündbares Gas bei Wasserkontakt"),
    ("H261", "fire_explosion", "Entzündbares Gas bei Wasserkontakt"),
    ("H270", "fire_explosion", "Kann Brand verursachen oder verstärken (Oxidationsmittel)"),
    ("H271", "fire_explosion", "Kann Brand oder Explosion verursachen"),
    ("H272", "fire_explosion", "Kann Brand verstärken — Oxidationsmittel"),
    # ── Akute Toxizität ──────────────────────────────────────────────────────
    ("H300", "acute_toxic",   "Lebensgefahr bei Verschlucken — Kat. 1/2"),
    ("H301", "acute_toxic",   "Giftig bei Verschlucken — Kat. 3"),
    ("H302", "acute_toxic",   "Gesundheitsschädlich bei Verschlucken — Kat. 4"),
    ("H304", "acute_toxic",   "Kann bei Verschlucken und Eindringen in Atemwege tödlich sein"),
    ("H310", "acute_toxic",   "Lebensgefahr bei Hautkontakt — Kat. 1/2"),
    ("H311", "acute_toxic",   "Giftig bei Hautkontakt — Kat. 3"),
    ("H312", "acute_toxic",   "Gesundheitsschädlich bei Hautkontakt — Kat. 4"),
    ("H330", "acute_toxic",   "Lebensgefahr bei Einatmen — Kat. 1/2"),
    ("H331", "acute_toxic",   "Giftig bei Einatmen — Kat. 3"),
    ("H332", "acute_toxic",   "Gesundheitsschädlich bei Einatmen — Kat. 4"),
    # ── Chronische Toxizität (STOT) ──────────────────────────────────────────
    ("H370", "chronic_toxic", "Schädigt die Organe — STOT SE Kat. 1"),
    ("H371", "chronic_toxic", "Kann die Organe schädigen — STOT SE Kat. 2"),
    ("H372", "chronic_toxic", "Schädigt Organe bei längerer Exposition — STOT RE Kat. 1"),
    ("H373", "chronic_toxic", "Kann Organe schädigen bei längerer Exposition — STOT RE Kat. 2"),
    # ── Haut ────────────────────────────────────────────────────────────────
    ("H314", "skin_corrosion", "Schwere Verätzungen der Haut und Augenschäden — Kat. 1"),
    ("H315", "skin_corrosion", "Verursacht Hautreizungen — Kat. 2"),
    # ── Augen ────────────────────────────────────────────────────────────────
    ("H318", "eye_damage",    "Verursacht schwere Augenschäden — Kat. 1"),
    ("H319", "eye_damage",    "Verursacht schwere Augenreizung — Kat. 2"),
    # ── Atemwegssensibilisierung ─────────────────────────────────────────────
    ("H334", "respiratory",   "Kann bei Einatmen Allergie/Asthma/Atemnot verursachen"),
    # ── Hautsensibilisierung ─────────────────────────────────────────────────
    ("H317", "skin_sens",     "Kann allergische Hautreaktionen verursachen"),
    # ── CMR ──────────────────────────────────────────────────────────────────
    ("H340", "cmr",           "Kann genetische Defekte verursachen — Mutagen Kat. 1"),
    ("H341", "cmr",           "Kann vermutlich genetische Defekte verursachen — Kat. 2"),
    ("H350", "cmr",           "Kann Krebs erzeugen — Karzinogen Kat. 1A/1B"),
    ("H351", "cmr",           "Kann vermutlich Krebs erzeugen — Kat. 2"),
    ("H360", "cmr",           "Kann Fruchtbarkeit/ungeborenes Kind schädigen — Kat. 1A/1B"),
    ("H361", "cmr",           "Kann vermutlich Fruchtbarkeit beeinträchtigen — Kat. 2"),
    ("H362", "cmr",           "Kann Säuglinge über Muttermilch schädigen"),
    # ── Umwelt ───────────────────────────────────────────────────────────────
    ("H400", "environment",   "Sehr giftig für Wasserorganismen — Kat. Akut 1"),
    ("H410", "environment",   "Sehr giftig für Wasserorganismen mit langfristiger Wirkung — Chr. 1"),
    ("H411", "environment",   "Giftig für Wasserorganismen mit langfristiger Wirkung — Chr. 2"),
    ("H412", "environment",   "Schädlich für Wasserorganismen mit langfristiger Wirkung — Chr. 3"),
    ("H413", "environment",   "Kann für Wasserorganismen schädlich sein — Chr. 4"),
    # ── Erstickung ───────────────────────────────────────────────────────────
    ("H280", "asphyxiant",    "Enthält Gas unter Druck — Erwärmen kann Explosion verursachen"),
    ("H281", "asphyxiant",    "Enthält tiefgekühltes Gas — Kälteverbrennungen"),
    ("H290", "asphyxiant",    "Kann gegenüber Metallen korrosiv sein"),
]


class Command(BaseCommand):
    help = (
        "Seed GBU H-Code-Mappings — idempotent via get_or_create(h_code, category).\n"
        "Nutze --force um Annotationen bestehender Einträge zu überschreiben."
    )

    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument(
            "--force",
            action="store_true",
            default=False,
            help="Annotationen bestehender Mappings überschreiben",
        )

    @transaction.atomic
    def handle(self, *args, **options) -> None:
        force          = options["force"]
        created_count  = 0
        skipped_count  = 0
        error_count    = 0

        for h_code, category_code, annotation in H_CODE_MAPPINGS:
            # Kategorie per natürlichem Schlüssel laden — schlägt explizit fehl
            try:
                category = HazardCategoryRef.objects.get(code=category_code)
            except HazardCategoryRef.DoesNotExist:
                self.stderr.write(
                    self.style.ERROR(
                        f"  ERROR: Kategorie '{category_code}' nicht gefunden "
                        f"(H-Code: {h_code}). seed_hazard_categories zuerst ausführen."
                    )
                )
                error_count += 1
                continue

            if force:
                _, created = HCodeCategoryMapping.objects.update_or_create(
                    h_code=h_code,
                    category=category,
                    defaults={"annotation": annotation},
                )
            else:
                _, created = HCodeCategoryMapping.objects.get_or_create(
                    h_code=h_code,
                    category=category,
                    defaults={"annotation": annotation},
                )

            if created:
                created_count += 1
            else:
                skipped_count += 1

        if error_count > 0:
            self.stderr.write(
                self.style.ERROR(f"FEHLER: {error_count} Mappings konnten nicht angelegt werden.")
            )
            raise SystemExit(1)   # Exit-Code 1 für CI

        total = HCodeCategoryMapping.objects.count()
        self.stdout.write(
            self.style.SUCCESS(
                f"OK: {created_count} erstellt, {skipped_count} übersprungen "
                f"— {total} Mappings gesamt"
            )
        )
```

---

### K4 — `HazardAssessmentActivity` erbt nicht von `TenantModel`

**Befund**

`activity.py` erbt von `models.Model` und deklariert `created_at`, `updated_at`,
`id` und `tenant_id` manuell.

Die Plattform stellt exakt diese Felder via `TenantModel` (aus `apps.core.models`)
bereit:

```python
# src/apps/core/models.py (project knowledge, implementiert)
class TenantModel(TimestampedModel):
    id        = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant_id = models.UUIDField(db_index=True)

    class Meta:
        abstract = True

    def save(self, *args, **kwargs):
        if not self.tenant_id:
            ctx = get_context()
            if ctx.tenant_id:
                self.tenant_id = ctx.tenant_id
            else:
                raise ValueError("tenant_id required but not in context")
        super().save(*args, **kwargs)
```

Die manuelle Wiederholung:
1. Verletzt DRY
2. Fehlt `TenantQuerySet.for_tenant()` — alle Queries müssen `tenant_id=...` manuell
   filtern, Plattform-Manager steht nicht zur Verfügung
3. Verletzt ADR-003 §2 „Model-Basis: UUID PK, tenant_id, TimestampedModel"

`ActivityMeasure` ist betroffen: es hat kein `tenant_id` überhaupt — Queries können
cross-tenant lecken wenn über `activity_id` direkt zugegriffen wird.

**Risiko**

- `ActivityMeasure` ohne `tenant_id` ist ein RLS-Leck: ein Angreifer mit gültigem
  `activity_id` einer anderen Firma kann Maßnahmen lesen.
- Fehlende `TenantManager` verhindert `HazardAssessmentActivity.objects.for_tenant()`.

**Empfehlung**

```python
# src/apps/gbu/models/activity.py
from apps.core.models import TenantModel   # UUID PK + tenant_id + Timestamps

class HazardAssessmentActivity(TenantModel):
    """GBU-Tätigkeit mit Gefahrstoff.
    
    Erbt von TenantModel:
        id (UUID PK), tenant_id (UUID, db_index), created_at, updated_at
    
    Compliance: kein delete (default_permissions), SdsRevision PROTECT.
    """
    # ── NICHT WIEDERHOLEN: id, tenant_id, created_at, updated_at ────────────
    site              = models.ForeignKey("tenancy.Site", on_delete=models.PROTECT, ...)
    sds_revision      = models.ForeignKey("substances.SdsRevision", on_delete=models.PROTECT, ...)
    # ... restliche Felder ...

    class Meta(TenantModel.Meta):
        db_table            = "gbu_hazard_assessment_activity"
        default_permissions = ("add", "change", "view")
        # ...


class ActivityMeasure(models.Model):
    """Schutzmaßnahme einer GBU-Tätigkeit.
    
    tenant_id wird denormalisiert mitgeführt (RLS, direkte Queries).
    """
    id         = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant_id  = models.UUIDField(db_index=True)   # ← PFLICHT (ADR-003)
    activity   = models.ForeignKey(HazardAssessmentActivity, on_delete=models.PROTECT, ...)
    # ...
```

---

## 🟠 HOHE BEFUNDE

---

### H1 — Keine RLS-Policy in der Migration

**Befund**

`gbu_hazard_assessment_activity` hat `tenant_id`, aber kein einziges Migrations-File
enthält die RLS-Aktivierung. ADR-003 §4.2 definiert das RLS-Template als **Pflicht**
für jede tenant-scoped Tabelle:

```sql
ALTER TABLE <table> ENABLE ROW LEVEL SECURITY;
ALTER TABLE <table> FORCE ROW LEVEL SECURITY;
CREATE POLICY tenant_isolation ON <table>
    FOR ALL
    USING (tenant_id = current_setting('app.tenant_id', true)::uuid)
    WITH CHECK (tenant_id = current_setting('app.tenant_id', true)::uuid);
```

**Risiko**

PostgreSQL 16 ohne RLS-Policy erlaubt Superuser-Queries cross-tenant. Wenn
pgbouncer in Pool-Mode läuft (session-Variablen nicht isoliert), können in
Ausnahmesituationen Queries aus Tenant A Daten von Tenant B sehen.

**Empfehlung**

RLS in separater Post-Migration (nach `0001_initial_gbu_models.py`):

```python
# src/apps/gbu/migrations/0002_rls_gbu_activity.py
"""
Migration: RLS-Policies für tenant-scoped GBU-Tabellen.

Muss nach 0001_initial_gbu_models.py ausgeführt werden.
Idempotent: IF NOT EXISTS auf Policies.
"""
from django.db import migrations


RLS_SQL = """
-- gbu_hazard_assessment_activity
ALTER TABLE gbu_hazard_assessment_activity ENABLE ROW LEVEL SECURITY;
ALTER TABLE gbu_hazard_assessment_activity FORCE ROW LEVEL SECURITY;

CREATE POLICY IF NOT EXISTS tenant_isolation
    ON gbu_hazard_assessment_activity
    FOR ALL
    USING (tenant_id = current_setting('app.tenant_id', true)::uuid)
    WITH CHECK (tenant_id = current_setting('app.tenant_id', true)::uuid);

-- gbu_activity_measure (denormalisiertes tenant_id nach K4-Fix)
ALTER TABLE gbu_activity_measure ENABLE ROW LEVEL SECURITY;
ALTER TABLE gbu_activity_measure FORCE ROW LEVEL SECURITY;

CREATE POLICY IF NOT EXISTS tenant_isolation
    ON gbu_activity_measure
    FOR ALL
    USING (tenant_id = current_setting('app.tenant_id', true)::uuid)
    WITH CHECK (tenant_id = current_setting('app.tenant_id', true)::uuid);
"""

ROLLBACK_SQL = """
DROP POLICY IF EXISTS tenant_isolation ON gbu_hazard_assessment_activity;
ALTER TABLE gbu_hazard_assessment_activity DISABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS tenant_isolation ON gbu_activity_measure;
ALTER TABLE gbu_activity_measure DISABLE ROW LEVEL SECURITY;
"""


class Migration(migrations.Migration):
    dependencies = [
        ("gbu", "0001_initial_gbu_models"),
    ]
    operations = [
        migrations.RunSQL(sql=RLS_SQL, reverse_sql=ROLLBACK_SQL),
    ]
```

**Hinweis pgbouncer:** Bei `transaction`-Pool-Mode werden `SET LOCAL`-Variablen
mit dem Ende der Transaktion zurückgesetzt — kein Problem. Bei `session`-Pool-Mode
**muss** `RESET app.tenant_id` am Ende jeder Request-Verarbeitung aufgerufen werden.
Middleware-Code prüfen.

---

### H2 — `create_activity()` ohne `emit_audit_event` (Compliance-Verletzung)

**Befund**

Phase-2A-Stub `create_activity()` legt eine `HazardAssessmentActivity` an, ohne
`emit_audit_event()` aufzurufen. ADR-003 §3 und ADR-006 verlangen Audit-Events für
alle Compliance-kritischen Aktionen. Eine GBU ist ein Rechtsdokument nach GefStoffV §6.

Der Stub endet ohne jedweden Audit-Hook:
```python
logger.info("[GBUEngine] Tätigkeit erstellt: %s (tenant=%s)", activity.id, tenant_id)
return activity
```

**Risiko**

- Fehlende Audit-Spur für `created`-Events schon in Phase 2A.
- Phase 2B baut auf dem Stub auf — Audit wird strukturell nicht nachgerüstet.
- Compliance-Verstöße GefStoffV §6(4): Nachvollziehbarkeit der GBU-Erstellung fehlt.

**Empfehlung**

```python
# src/apps/gbu/services/gbu_engine.py — create_activity() Ergänzung
from apps.audit.services import emit_audit_event, AuditCategory

@transaction.atomic
def create_activity(cmd: CreateActivityCmd, tenant_id: UUID, user_id: UUID | None = None):
    activity = HazardAssessmentActivity.objects.create(
        tenant_id=tenant_id,
        site_id=cmd.site_id,
        sds_revision_id=cmd.sds_revision_id,
        activity_description=cmd.activity_description.strip(),
        activity_frequency=cmd.activity_frequency,
        duration_minutes=cmd.duration_minutes,
        quantity_class=cmd.quantity_class,
        substitution_checked=cmd.substitution_checked,
        substitution_notes=cmd.substitution_notes,
        status=ActivityStatus.DRAFT,
        created_by=user_id,
    )

    # Audit-Event — Pflicht nach ADR-006 für Compliance-kritische Erstellung
    emit_audit_event(
        tenant_id=tenant_id,
        category=AuditCategory.COMPLIANCE,
        action="created",
        entity_type="gbu.HazardAssessmentActivity",
        entity_id=activity.id,
        user_id=user_id,
        payload={
            "site_id":         str(cmd.site_id),
            "sds_revision_id": str(cmd.sds_revision_id),
            "status":          ActivityStatus.DRAFT,
        },
    )

    logger.info("[GBUEngine] Tätigkeit erstellt: %s (tenant=%s)", activity.id, tenant_id)
    return activity
```

---

### H3 — ADR-008 §5 schlägt `post_save`-Signal vor (verletzt eigenen Constraint §1.2)

**Befund**

ADR-008 §1.2 definiert als verbindlichen Constraint:

> „Kein `post_save`-Signal für Business-Logik —
> Explizite Service-Calls statt Magic-Signals (Migration/Loaddata-Schutz)"

Im Implementierungskonzept (aus dem der ADR entstammt) findet sich folgender Code:
```python
@receiver(post_save, sender=SiteInventoryItem)
def auto_create_ex_concept(sender, instance, created, **kwargs):
    ...
```

Dieses Muster ist im ADR unter §8 „Abgelehnte Alternativen" explizit als abgelehnt
gelistet. Trotzdem wird es für Modul 1 (Ex-Schutzdokument) im gleichen Dokument
zitiert ohne zu vermerken, dass es der Constraint-Auflistung widerspricht.

**Risiko**

- Signals laufen bei `loaddata` / `dumpdata` / Fixtures — erzeugen ungewollte
  `ExplosionConcept`-Drafts beim Seed.
- Kein Tenant-Kontext verfügbar in Signal-Handler → `get_context()` gibt `None`.
- Inconsistentes Verhalten in Unit-Tests (Signals müssen explizit disabled werden).

**Empfehlung**

ADR-008 §5.5 korrigieren:

```python
# NICHT:
@receiver(post_save, sender=SiteInventoryItem)
def auto_create_ex_concept(sender, instance, created, **kwargs): ...

# SONDERN — expliziter Service-Call im Inventory-Service (ADR-002):
# src/apps/substances/services/inventory_service.py

@transaction.atomic
def add_to_inventory(cmd: AddInventoryCmd, tenant_id: UUID, user_id: UUID) -> SiteInventoryItem:
    item = SiteInventoryItem.objects.create(...)
    
    # Expliziter Hook nach ADR-008 §1.2 (kein Signal!)
    from apps.explosionsschutz.services.ex_integration import check_and_create_ex_draft
    check_and_create_ex_draft(
        tenant_id=tenant_id,
        site_id=item.site_id,
        substance=item.substance,
        user_id=user_id,
    )
    
    emit_audit_event(...)
    return item
```

ADR-008 §5 (Modul 1) mit Verweis auf diesen Service-Call aktualisieren.

---

### H4 — `approved_by` als FK auf `AUTH_USER_MODEL` (Compliance-Daten-Verlust)

**Befund**

```python
approved_by = models.ForeignKey(
    settings.AUTH_USER_MODEL,
    on_delete=models.SET_NULL,   # ← Problem
    null=True, blank=True,
    related_name="+",
)
```

`SET_NULL` bedeutet: wird der User gelöscht (z.B. Mitarbeiter verlässt Unternehmen),
geht die Information **wer** die GBU freigegeben hat verloren.

GefStoffV §6(4): „Der Arbeitgeber hat die Gefährdungsbeurteilung zu dokumentieren."
Das schließt die freigebende Person ein. Datenverlust verletzt die Aufbewahrungspflicht.

**Empfehlung**

```python
# Unveränderlicher UUID-Wert (kein FK — FK-Invariante schützt Compliance-Nachweis)
approved_by_id   = models.UUIDField(
    null=True, blank=True,
    help_text="UUID der freigebenden Person (unveränderlich nach Freigabe)",
    db_index=True,
)
approved_by_name = models.CharField(
    max_length=200,
    blank=True,
    default="",
    help_text="Vollname der freigebenden Person (Snapshot, immutable nach Freigabe)",
)
```

Analog zu ADR-008 §5.4 `calculated_by_id = models.UUIDField(null=True)` für
`ZoneCalculationResult` — das gleiche Muster wurde dort korrekt gewählt.

---

## 🟡 MITTLERE BEFUNDE

---

### M1 — Test-Mock verwendet falschen Import-Pfad (Grüner Test mit latentem Bug)

**Befund**

```python
# test_services.py Zeile 1105-1108
mocker.patch(
    "substances.models.SdsRevision.objects.prefetch_related"
).return_value.get.return_value = mock_revision
```

`unittest.mock.patch()` muss den Pfad mocken **wie er im zu testenden Modul
importiert wird**, nicht wo das Objekt definiert ist.

`gbu_engine.py` importiert:
```python
from substances.models import SdsRevision   # importiert in gbu_engine
```

Korrekt wäre:
```python
mocker.patch("gbu.services.gbu_engine.SdsRevision.objects.prefetch_related")
# oder nach K1-Fix:
mocker.patch("apps.gbu.services.gbu_engine.SdsRevision.objects.prefetch_related")
```

Der Test ist grün weil `substances.models.SdsRevision` nie aufgerufen wird — der
Mock-Pfad greift ins Leere, und die echte Funktion läuft nicht bis zur DB-Abfrage
(leere Liste wegen falschem `h_statements` related_name).

**Empfehlung**

```python
@pytest.mark.django_db
def test_should_derive_hazard_categories_return_empty_for_no_h_codes(mocker):
    from apps.gbu.models.reference import HazardCategoryRef
    rev_id = uuid.uuid4()

    mock_revision = mocker.MagicMock()
    # Korrekte hazard_statements related_name (siehe K2)
    mock_revision.hazard_statements.values_list.return_value = []

    # Korrekter Mock-Pfad: wo das Modul es importiert
    mocker.patch(
        "apps.gbu.services.gbu_engine.SdsRevision.objects.prefetch_related"
    ).return_value.get.return_value = mock_revision

    result = derive_hazard_categories(rev_id)
    assert result == []
```

---

### M2 — Test-DB: SQLite statt PostgreSQL 16 (Divergenz zu Produktion)

**Befund**

```python
# settings_test.py
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": ":memory:",
    }
}
```

Folgende Plattform-Features funktionieren auf SQLite anders oder gar nicht:
- `unique_together` Constraint-Handling (keine deferrable constraints)
- `models.Index` mit `name=` Parameter: SQLite ignoriert Indexnamen
- RLS-Policies: existieren auf SQLite nicht
- `UUIDField` als PK: SQLite speichert als TEXT, PostgreSQL als native UUID
- `JSONField`: SQLite nutzt TEXT, PostgreSQL JSONB (Operator-Unterschiede)
- `PositiveSmallIntegerField`: SQLite hat keine Integer-Range-Checks

**Risiko**

Migrations die auf SQLite passen, können auf PostgreSQL 16 fehlschlagen (K1-Pfad-
Problem bleibt unsichtbar, Integer-PK-Fixture-Sequence-Drift unentdeckt).

**Empfehlung**

```python
# src/config/settings_test.py
"""
Test-Settings — PostgreSQL 16 (identisch zu Produktion).

Voraussetzung: lokale PG-Instanz oder docker-compose.yml postgres-Service.
DJANGO_TEST_DB_URL kann überschrieben werden für CI.
"""
import os
from config.settings import *  # noqa: F401, F403  (Test-Override erlaubt)

DATABASES = {
    "default": {
        "ENGINE":   "django.db.backends.postgresql",
        "NAME":     os.environ.get("DJANGO_TEST_DB_NAME", "risk_hub_test"),
        "USER":     os.environ.get("DJANGO_TEST_DB_USER", "app"),
        "PASSWORD": os.environ.get("DJANGO_TEST_DB_PASSWORD", "app"),
        "HOST":     os.environ.get("DJANGO_TEST_DB_HOST", "localhost"),
        "PORT":     os.environ.get("DJANGO_TEST_DB_PORT", "5432"),
        "TEST":     {"NAME": "risk_hub_test"},
    }
}
```

```yaml
# pytest.ini oder pyproject.toml — Marker registrieren
[pytest]
DJANGO_SETTINGS_MODULE = config.settings_test
addopts = --strict-markers
markers =
    django_db: Tests mit DB-Zugriff
    integration: Integration-Tests (langsamer, PostgreSQL)
```

---

### M3 — `ApproveActivityCmd.next_review_date: str` (Typ-Unsicherheit)

**Befund**

```python
@dataclass(frozen=True)
class ApproveActivityCmd:
    activity_id: UUID
    next_review_date: str     # ISO-Date: "2027-03-01"
```

Das Feld ist als `str` typisiert mit einem Inline-Kommentar. Django speichert
`DateField` als `datetime.date`. Wenn `"2027-03-01"` direkt übergeben wird, akzeptiert
Django das — aber `"01.03.2027"` (deutsches Format) ebenfalls ohne Fehler bis zum
SQL-Insert.

**Empfehlung**

```python
import datetime

@dataclass(frozen=True)
class ApproveActivityCmd:
    activity_id:      UUID
    next_review_date: datetime.date   # ← typsicher, kein Parsing-Fehler möglich

# Service-Aufruf:
cmd = ApproveActivityCmd(
    activity_id=uuid.UUID(activity_id_str),
    next_review_date=datetime.date.fromisoformat(date_str),   # explizit, wirft ValueError
)
```

---

### M4 — `HazardCategoryRef` ohne `db_index` auf `category_type`

**Befund**

In IMPL-008 `reference.py`:
```python
category_type = models.CharField(
    max_length=30,
    choices=[(t.value, t.value) for t in HazardCategoryType],
    db_index=True,    # ← korrekt in IMPL-008
)
```

In ADR-008 §3.2.1 fehlt `db_index=True` auf `category_type`. Da Queries nach
`category_type` für die Dashboard-Filterung häufig sind, ist der Index notwendig.

**Befund:** IMPL-008 hat es korrekt, ADR-008 nicht. ADR muss auf IMPL angepasst
werden (ADR ist die Wahrheitsquelle — Abweichung verwirrt künftige Reviewer).

---

## 🔵 NIEDRIGE BEFUNDE

---

### N1 — `MODULE_URL_MAP` in `settings.py` undokumentiert

**Befund**

IMPL-008 §Schritt 6 schreibt:
```python
MODULE_URL_MAP = {
    "/gbu/":     "gbu",
    "/api/gbu/": "gbu",
}
```

`MODULE_URL_MAP` taucht weder im kanonischen `settings.py` (project knowledge) noch
in ADR-003/004 auf. Unbekannte Settings-Schlüssel sind stilles Verhalten.

**Empfehlung:** Entweder dokumentieren (welche Middleware liest dieses Dict?) oder
entfernen.

---

### N2 — `settings_test.py` wildcard import verletzt ruff F403

**Befund**

```python
from config.settings import *  # noqa: F401, F403
```

Das `noqa` ist ein Kommentar zur Unterdrückung, keine Lösung. Ruff F403 (star-import)
ist in der Plattform-weiten `ruff.toml` aktiviert.

**Empfehlung**

```python
# Explizite Override-Technik (Django-Standard für Test-Settings):
from config.settings import (   # noqa: F401 — explizite Overrides folgen
    INSTALLED_APPS,
    MIDDLEWARE,
    SECRET_KEY,
    # ... alle genutzten Settings
)
DATABASES = { ... }   # Override
```

Oder: `settings_test.py` als reines Override-File mit `os.environ` Manipulation.

---

### N3 — `BigAutoField` in `GbuConfig.apps.py` inkonsistent mit UUID-Strategy

**Befund**

```python
class GbuConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
```

`HazardAssessmentActivity` und `ActivityMeasure` nutzen explizite UUID PKs.
`HazardCategoryRef`, `HCodeCategoryMapping` und `MeasureTemplate` haben keinen
expliziten PK → `BigAutoField` greift. Integer-PKs für Referenzdaten sind
akzeptabel, aber der Fixture-Ansatz (K3) macht Integer-PKs fragil.

Nach K3-Fix (natürliche Schlüssel statt Integer-PKs in Fixtures) ist dies kein
Problem mehr. Als Reminder stehen lassen.

---

## Review-Zusammenfassung

| # | Befund | Schwere | Datei | Blocking |
|---|--------|---------|-------|----------|
| K1 | App-Pfad `src/gbu/` statt `src/apps/gbu/`, `name="gbu"` statt `"apps.gbu"` | 🔴 | IMPL §1–7 | ✅ |
| K2 | `h_statements` → `hazard_statements` (AttributeError in Produktion) | 🔴 | IMPL §14 + Test §16 | ✅ |
| K3 | Seed nicht idempotent: `loaddata` mit Integer-PKs | 🔴 | IMPL §12–13 | ✅ |
| K4 | `TenantModel` nicht geerbt; `ActivityMeasure` ohne `tenant_id` | 🔴 | IMPL §4 | ✅ |
| H1 | RLS-Policy fehlt für `gbu_hazard_assessment_activity` | 🟠 | IMPL (fehlt) | ✅ |
| H2 | `create_activity()` ohne `emit_audit_event` | 🟠 | IMPL §14 | ✅ |
| H3 | `post_save`-Signal in ADR §5 (verletzt eigenen Constraint §1.2) | 🟠 | ADR §5 | ✅ |
| H4 | `approved_by FK SET_NULL` — Compliance-Datenverlust | 🟠 | IMPL §4 | ✅ |
| M1 | Test-Mock falscher Pfad — grüner Test, latenter Bug | 🟡 | IMPL §16 | — |
| M2 | SQLite statt PostgreSQL 16 in Tests | 🟡 | IMPL §17 | — |
| M3 | `next_review_date: str` statt `datetime.date` | 🟡 | IMPL §14 | — |
| M4 | `db_index=True` fehlt auf `category_type` in ADR-008 §3.2.1 | 🟡 | ADR §3.2.1 | — |
| N1 | `MODULE_URL_MAP` undokumentiert | 🔵 | IMPL §6 | — |
| N2 | wildcard import in `settings_test.py` | 🔵 | IMPL §17 | — |
| N3 | `BigAutoField` + Integer-PK-Fixtures (nach K3-Fix obsolet) | 🔵 | IMPL §2 | — |

### Definition of Done (vor Merge)

- [ ] K1: Verzeichnis nach `src/apps/gbu/` verschoben, `name = "apps.gbu"`
- [ ] K2: `hazard_statements` überall konsistent, Test-Mock korrigiert
- [ ] K3: Seed-Commands auf `update_or_create`/`get_or_create` umgestellt
- [ ] K4: `TenantModel` geerbt, `ActivityMeasure.tenant_id` ergänzt
- [ ] H1: Migration `0002_rls_gbu_activity.py` mit RLS-Policies
- [ ] H2: `emit_audit_event` in `create_activity()` (Phase-2A-Stub)
- [ ] H3: ADR-008 §5 Signal-Code durch Service-Call ersetzt
- [ ] H4: `approved_by_id = UUIDField`, `approved_by_name = CharField`
- [ ] `python manage.py check` fehlerfrei
- [ ] `ruff check src/apps/gbu/` — 0 Errors
- [ ] `pytest src/apps/gbu/tests/ -v` — 0 failures auf PostgreSQL

---

*REVIEW-ADR-008-IMPL-008 · 2026-03-03 · Blocking — Überarbeitung erforderlich*
