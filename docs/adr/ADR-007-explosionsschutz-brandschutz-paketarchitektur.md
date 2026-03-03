# ADR-007: Paketarchitektur für Explosionsschutz und Brandschutz

| Feld            | Wert                                                                |
|-----------------|---------------------------------------------------------------------|
| **Status**      | Proposed                                                            |
| **Datum**       | 2026-03-03                                                          |
| **Autor**       | Achim Dehnert                                                       |
| **Kontext**     | risk-hub (Schutztat), nl2cad, neues PyPI-Package `nl2cad-exschutz` |
| **Entscheider** | IT-Architekt, Ex-Schutz-SV, Brandschutz-SV                         |

---

## 1. Kontext und Problemstellung

### 1.1 Ausgangslage

risk-hub implementiert aktuell Explosionsschutz- und Brandschutzlogik direkt in der Django-App:

- `explosionsschutz/calculations.py` — Stoffdatenbank (GESTIS-basiert), Zonenberechnung (TRGS 721), ATEX-Equipment-Prüfung
- `explosionsschutz/models.py` — Django-ORM für Zonen, Konzepte, Betriebsmittel, Zündquellen
- `explosionsschutz/export_views.py` — GAEB X84-Export via `nl2cad.gaeb` (bereits umgestellt)

nl2cad enthält parallel in `nl2cad-brandschutz`:

- `analyzer.py` — IFC/DXF Layer-Erkennung für Brandschutz
- `models.py` — `BrandschutzAnalyse`, `Fluchtweg`, `Brandabschnitt`, `ExBereich`
- `rules/` — ASR A2.3, DIN 4102 Regelwerk-Checks

**Kernproblem:** Es gibt keine klare Grenzziehung, welche Logik in Framework-agnostische
Python-Packages (nl2cad-*) und welche in die Django-App (risk-hub) gehört. Das führt zu:

- Duplikation (Stoff-Datenbank in `calculations.py` vs. potentiell nl2cad)
- Nicht-wiederverwendbarer Fachlogik (TRGS 721 Berechnung nur in risk-hub)
- Fehlender Trennung von Analyse (CAD/Normen) und Persistenz (Django)

### 1.2 Akteure und ihre Anforderungen

**Explosionsschutz-Sachverständiger (Ex-SV):**

- Berechnung Zonenausdehnung nach TRGS 721 mit Nachweisarchivierung (Zeitstempel, Norm, Berechner)
- Zündquellen-Bewertungsmatrix (alle 13 EN 1127-1 Quellen) als Prüfdokument
- ATEX-Kennzeichnungsprüfung bei Betriebsmittel-Erfassung
- Import von Ex-Zonen aus CAD-Plänen (DXF)
- Revisionssichere Prüfberichtserstellung

**Brandschutz-Sachverständiger (BS-SV):**

- Analyse von IFC/DXF-Plänen auf Brandschutz-Elemente (Fluchtwege, Brandabschnitte, Melder)
- ASR A2.3 / DIN 4102 Konformitätsprüfung mit Mangelprotokoll
- Kombination Ex-Zone + Brandschutz-Anforderungen (z.B. F60-Wand an Zone 1)
- Wiederkehrende Prüffristen-Verwaltung

**IT-Architekt:**

- Framework-agnostische Fachlogik in wiederverwendbaren PyPI-Packages
- Django-App enthält nur Persistenz, UI, Tenant-Isolation, Audit-Trail
- Klare Paket-Grenzen und Abhängigkeiten
- Keine zirkulären Abhängigkeiten zwischen Packages

---

## 2. Entscheidung

### 2.1 Ziel-Architektur: Vier-Schichten-Modell

```text
┌─────────────────────────────────────────────────────────────────┐
│  SCHICHT 4: risk-hub (Django)                                   │
│  Persistenz · Tenant-Isolation · UI · Audit · Prüf-Workflow     │
│                                                                 │
│  explosionsschutz/  brandschutz/  substances/                   │
│  ↓ delegiert an ↓                                               │
├─────────────────────────────────────────────────────────────────┤
│  SCHICHT 3: nl2cad-exschutz (NEU — PyPI)                        │
│  Ex-Schutz Fachlogik ohne Framework-Abhängigkeit                │
│                                                                 │
│  • Zonenberechnung TRGS 721/722                                 │
│  • ATEX-Equipment-Eignungsprüfung (2014/34/EU)                  │
│  • Zündquellen-Bewertung EN 1127-1 (13 Quellen)                 │
│  • Stoff-Datenbank (GESTIS-basiert, erweiterbar)                │
│  • ZoneExtent-Geometrie-Berechnung                              │
│  • IEC 60079-10-1 Lüftungseffektivität                          │
├─────────────────────────────────────────────────────────────────┤
│  SCHICHT 2: nl2cad-brandschutz (bestehend — PyPI)               │
│  Brandschutz-Analyse aus IFC/DXF                                │
│                                                                 │
│  • BrandschutzAnalyzer (IFC + DXF)                              │
│  • ASR A2.3 Fluchtweg-Validierung                               │
│  • DIN 4102 Feuerwiderstand-Checks                              │
│  • ExBereich-Erkennung (ATEX-Zonen aus CAD)                     │
│  • BrandschutzAnalyse Dataclass (Export-fähig)                  │
├─────────────────────────────────────────────────────────────────┤
│  SCHICHT 1: nl2cad-core (bestehend — PyPI)                      │
│  IFC/DXF Parsing · Dataclasses · Handler-Pipeline               │
└─────────────────────────────────────────────────────────────────┘
```

### 2.2 Neues Package: `nl2cad-exschutz`

**Begründung für eigenständiges Package (nicht in nl2cad-brandschutz):**

- Explosionsschutz (ATEX/BetrSichV) und Brandschutz (ASR/DIN 4102) sind **normativ getrennte Disziplinen**
- `nl2cad-brandschutz` analysiert CAD-Dateien; `nl2cad-exschutz` berechnet physikalische Kenngrößen
- Unterschiedliche Downstream-Konsumenten denkbar (risk-hub nutzt beide; ein reines Ex-Schutz-Tool nur `nl2cad-exschutz`)
- Stoff-Datenbank (GESTIS) ist eigenständige Ressource ohne CAD-Bezug

**PyPI-Name:** `nl2cad-exschutz`
**Abhängigkeiten:** nur `nl2cad-core>=0.1.0` (keine Django, keine httpx)

### 2.3 Funktionszuordnung

#### `nl2cad-exschutz` — Framework-agnostische Fachlogik

| Modul | Inhalt | Migriert aus |
|---|---|---|
| `substances/database.py` | Stoff-Datenbank (GESTIS), `SubstanceProperties` Dataclass | `risk-hub/calculations.py` |
| `substances/lookup.py` | `get_substance_properties()`, Alias-Auflösung, Fuzzy-Search | `risk-hub/calculations.py` |
| `zones/calculator.py` | `calculate_zone_extent()` nach TRGS 721 | `risk-hub/calculations.py` |
| `zones/ventilation.py` | `calculate_ventilation_effectiveness()` nach TRGS 722 | `risk-hub/calculations.py` |
| `zones/models.py` | `ZoneExtentResult`, `VentilationResult` Dataclasses | neu |
| `equipment/checker.py` | `check_equipment_suitability()` nach ATEX 2014/34/EU | `risk-hub/calculations.py` |
| `equipment/models.py` | `ATEXCheckResult` Dataclass | neu |
| `ignition/assessor.py` | `IgnitionSourceMatrix`, alle 13 EN 1127-1 Quellen | neu |
| `ignition/models.py` | `IgnitionAssessment`, `IgnitionRisk` Dataclasses | neu |
| `reports/pdf_builder.py` | `IgnitionAssessmentReport`, `ZoneCalculationReport` | neu |
| `constants.py` | ATEX-Kategorien, Explosionsgruppen, Temperaturklassen | `risk-hub/calculations.py` |

#### `nl2cad-brandschutz` — Erweiterungen (bestehend)

| Modul | Ergänzung | Priorität |
|---|---|---|
| `analyzer.py` | `analyze_dxf()` gibt `ex_bereiche` bereits zurück — **unverändert** | — |
| `models.py` | `ExBereich` bereits definiert — **unverändert** | — |
| `rules/combined.py` | `CombinedExBrandCheck`: Zone 1 + F60-Wand Prüfung (NEU) | P2 |

#### `risk-hub/explosionsschutz` — Nur Django-Schicht

| Verbleibend in risk-hub | Begründung |
|---|---|
| `models.py` — alle Django-ORM Models | Persistenz, Tenant-Isolation, Migrations |
| `models.py` — `ZoneCalculationResult` (NEU) | TRGS 721 Ergebnis archivieren (Nachweispflicht) |
| `services.py` — alle `create_*` / `update_*` Funktionen | Audit-Trail, `@transaction.atomic`, Permissions |
| `services.py` — `calculate_and_store_zone()` (NEU) | Delegiert an `nl2cad-exschutz`, speichert Ergebnis |
| `services.py` — `import_zones_from_dxf()` (NEU) | Delegiert an `nl2cad-brandschutz`, erstellt DB-Records |
| `export_views.py` — alle Export-Views | UI-Schicht, WeasyPrint, GAEB |
| `export_views.py` — `IgnitionAssessmentExportView` (NEU) | PDF-Export via WeasyPrint |
| `calculations.py` | **DEPRECATE** → schrittweise leeren, auf nl2cad-exschutz delegieren |
| `schemas.py` — `ZoneExtent` | Bleibt als Pydantic-Validierung für Django Forms/API |

---

## 3. Detailspezifikation: `nl2cad-exschutz`

### 3.1 Package-Struktur

```text
packages/nl2cad-exschutz/
├── pyproject.toml
├── README.md
└── src/nl2cad/exschutz/
    ├── __init__.py
    ├── constants.py
    ├── substances/
    │   ├── __init__.py
    │   ├── database.py       # SubstanceProperties + SUBSTANCE_DATABASE
    │   └── lookup.py         # get_substance_properties()
    ├── zones/
    │   ├── __init__.py
    │   ├── models.py         # ZoneExtentResult, VentilationResult
    │   ├── calculator.py     # calculate_zone_extent() — TRGS 721
    │   └── ventilation.py    # calculate_ventilation_effectiveness() — TRGS 722
    ├── equipment/
    │   ├── __init__.py
    │   ├── models.py         # ATEXCheckResult
    │   └── checker.py        # check_equipment_suitability()
    ├── ignition/
    │   ├── __init__.py
    │   ├── models.py         # IgnitionAssessment, IgnitionRisk
    │   └── assessor.py       # IgnitionSourceMatrix, 13 EN 1127-1 Quellen
    └── reports/
        ├── __init__.py
        └── pdf_builder.py    # ReportSection, export_to_dict()
```

### 3.2 Public API

```python
# Stoff-Lookup
from nl2cad.exschutz.substances import get_substance_properties, list_substances

# Zonenberechnung
from nl2cad.exschutz.zones import calculate_zone_extent, calculate_ventilation_effectiveness

# ATEX-Prüfung
from nl2cad.exschutz.equipment import check_equipment_suitability

# Zündquellen-Bewertung
from nl2cad.exschutz.ignition import IgnitionSourceMatrix, IgnitionSource

# Report-Strukturen
from nl2cad.exschutz.reports import ZoneCalculationReport, IgnitionAssessmentReport
```

### 3.3 Zentrale Dataclasses

```python
# zones/models.py
@dataclass
class ZoneExtentResult:
    zone_type: str           # "0", "1", "2"
    radius_m: float
    volume_m3: float
    dilution_factor: float
    safety_factor: float
    release_type: str        # "jet" | "pool" | "diffuse"
    basis_norm: str = "TRGS 721"
    warnings: list[str] = field(default_factory=list)


# equipment/models.py
@dataclass
class ATEXCheckResult:
    is_suitable: bool
    equipment_marking: str
    target_zone: str
    detected_category: str | None
    detected_temp_class: str | None
    detected_exp_group: str | None
    issues: list[str] = field(default_factory=list)
    recommendations: list[str] = field(default_factory=list)
    basis_norm: str = "ATEX 2014/34/EU"


# ignition/models.py
@dataclass
class IgnitionAssessment:
    ignition_source: str     # "S1" .. "S13"
    is_present: bool
    is_effective: bool
    risk_level: str          # "none" | "low" | "high"
    mitigation: str = ""
    norm_reference: str = "EN 1127-1"
```

---

## 4. Detailspezifikation: risk-hub Erweiterungen

### 4.1 Neues Modell: `ZoneCalculationResult`

```python
class ZoneCalculationResult(models.Model):
    """Archivierte TRGS 721 Zonenberechnung — Nachweispflicht nach BetrSichV."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant_id = models.UUIDField(db_index=True)
    zone = models.ForeignKey(
        ZoneDefinition, on_delete=models.CASCADE, related_name="calculations"
    )
    substance_name = models.CharField(max_length=200)  # Denormalisiert für Archiv
    release_rate_kg_s = models.DecimalField(max_digits=12, decimal_places=6)
    ventilation_rate_m3_s = models.DecimalField(max_digits=12, decimal_places=4)
    release_type = models.CharField(max_length=20)    # jet | pool | diffuse
    calculated_zone_type = models.CharField(max_length=5)   # "0", "1", "2"
    calculated_radius_m = models.DecimalField(max_digits=8, decimal_places=3)
    calculated_volume_m3 = models.DecimalField(max_digits=12, decimal_places=3)
    basis_norm = models.CharField(max_length=50, default="TRGS 721")
    raw_result = models.JSONField()    # Vollständiges ZoneExtentResult
    calculated_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    calculated_at = models.DateTimeField(auto_now_add=True)
    notes = models.TextField(blank=True, default="")

    class Meta:
        db_table = "ex_zone_calculation_result"
        ordering = ["-calculated_at"]
```

### 4.2 Neuer Service: `calculate_and_store_zone()`

```python
# services.py
@dataclass(frozen=True)
class CalculateZoneCmd:
    zone_id: UUID
    release_rate_kg_s: float
    ventilation_rate_m3_s: float
    release_type: str  # "jet" | "pool" | "diffuse"
    notes: str = ""


@transaction.atomic
def calculate_and_store_zone(
    cmd: CalculateZoneCmd,
    tenant_id: UUID,
    user_id: UUID | None = None,
) -> ZoneCalculationResult:
    """
    Delegiert Berechnung an nl2cad-exschutz, persistiert Ergebnis.
    Audit: explosionsschutz.zone.calculated
    """
    from nl2cad.exschutz.zones import calculate_zone_extent

    zone = ZoneDefinition.objects.get(id=cmd.zone_id, tenant_id=tenant_id)
    substance_name = zone.concept.substance.name

    result = calculate_zone_extent(
        release_rate_kg_s=cmd.release_rate_kg_s,
        ventilation_rate_m3_s=cmd.ventilation_rate_m3_s,
        substance_name=substance_name,
        release_type=cmd.release_type,
    )

    calc = ZoneCalculationResult.objects.create(
        tenant_id=tenant_id,
        zone=zone,
        substance_name=substance_name,
        release_rate_kg_s=cmd.release_rate_kg_s,
        ventilation_rate_m3_s=cmd.ventilation_rate_m3_s,
        release_type=cmd.release_type,
        calculated_zone_type=result.zone_type,
        calculated_radius_m=result.radius_m,
        calculated_volume_m3=result.volume_m3,
        basis_norm=result.basis_norm,
        raw_result=vars(result),
        calculated_by_id=user_id,
        notes=cmd.notes,
    )
    emit_audit_event(
        tenant_id=tenant_id,
        category=AuditCategory.ZONE,
        action="calculated",
        entity_type="ZoneCalculationResult",
        entity_id=calc.id,
        payload={"zone_type": result.zone_type, "radius_m": result.radius_m},
        user_id=user_id,
    )
    return calc
```

### 4.3 Neuer Service: `import_zones_from_dxf()`

```python
@transaction.atomic
def import_zones_from_dxf(
    concept_id: UUID,
    dxf_bytes: bytes,
    tenant_id: UUID,
    user_id: UUID | None = None,
) -> int:
    """
    DXF → nl2cad-brandschutz.BrandschutzAnalyzer
    → ExBereich-Liste → ZoneDefinition-Records in DB.
    Gibt Anzahl importierter Zonen zurück.
    """
    import io

    import ezdxf
    from nl2cad.brandschutz.analyzer import BrandschutzAnalyzer

    concept = ExplosionConcept.objects.get(id=concept_id, tenant_id=tenant_id)
    doc = ezdxf.read(io.BytesIO(dxf_bytes))
    analyse = BrandschutzAnalyzer().analyze_dxf(doc)

    count = 0
    for ex_bereich in analyse.ex_bereiche:
        zone_type = ex_bereich.zone.value.replace("Zone ", "")  # "Zone 1" → "1"
        ZoneDefinition.objects.create(
            tenant_id=tenant_id,
            concept=concept,
            zone_type=zone_type,
            name=ex_bereich.name or f"Import: {ex_bereich.zone.value}",
            justification=(
                f"DXF-Import via nl2cad-brandschutz, Layer: {ex_bereich.layer}"
            ),
        )
        count += 1

    emit_audit_event(
        tenant_id=tenant_id,
        category=AuditCategory.ZONE,
        action="imported",
        entity_type="ZoneDefinition",
        entity_id=concept_id,
        payload={"count": count, "source": "dxf"},
        user_id=user_id,
    )
    return count
```

### 4.4 Neuer Export: `IgnitionAssessmentExportView`

```python
# export_views.py
class IgnitionAssessmentExportView(View):
    """PDF-Export der Zündquellen-Bewertungsmatrix nach EN 1127-1."""

    def get(self, request: HttpRequest, pk) -> HttpResponse:
        from nl2cad.exschutz.ignition import IgnitionSourceMatrix  # noqa: F401
        from nl2cad.exschutz.reports import IgnitionAssessmentReport
        from weasyprint import HTML

        tenant_id = getattr(request, "tenant_id", None)
        concept = get_object_or_404(
            ExplosionConcept.objects.filter(tenant_id=tenant_id), pk=pk
        )
        assessments = ZoneIgnitionSourceAssessment.objects.filter(
            zone__concept=concept
        ).select_related("zone")

        # nl2cad-exschutz baut Report-Struktur (framework-agnostisch)
        report = IgnitionAssessmentReport.from_assessments(
            project_name=concept.title,
            assessments=[vars(a) for a in assessments],
        )

        # risk-hub rendert via WeasyPrint
        html = render_to_string(
            "explosionsschutz/reports/ignition_matrix.html",
            {"report": report},
        )
        pdf_bytes = HTML(string=html).write_pdf()
        buf = io.BytesIO(pdf_bytes)
        filename = f"Zuendquellen_{concept.title[:30]}_v{concept.version}.pdf"
        return FileResponse(buf, as_attachment=True, filename=filename,
                            content_type="application/pdf")
```

---

## 5. Abhängigkeitsmatrix

```text
nl2cad-core
    ↑
nl2cad-brandschutz   nl2cad-exschutz (NEU)
         ↑                  ↑
         └──────────────────┘
                  risk-hub (Django)
```

**Verbotene Abhängigkeiten:**

| Von | Nach | Verboten |
|---|---|---|
| `nl2cad-exschutz` | Django | ✗ kein ORM, kein request |
| `nl2cad-exschutz` | `nl2cad-brandschutz` | ✗ keine Querabhängigkeit |
| `nl2cad-brandschutz` | `nl2cad-exschutz` | ✗ keine Querabhängigkeit |
| `risk-hub` | `calculations.py` direkt | ✗ nach Migration (Phase 3) |

---

## 6. Migrationspfad

### Phase 1 — nl2cad-exschutz Grundgerüst (Sprint 1)

1. Package anlegen: `uv new packages/nl2cad-exschutz`
2. `substances/` migrieren aus `calculations.py` → Tests schreiben
3. `zones/calculator.py` migrieren → Tests: TRGS 721 Fälle
4. `equipment/checker.py` migrieren → Tests: ATEX-Kategorien
5. `nl2cad-exschutz` in risk-hub `requirements.txt` aufnehmen

### Phase 2 — risk-hub Integration (Sprint 2)

1. `ZoneCalculationResult` Modell + Migration
2. `calculate_and_store_zone()` Service
3. `import_zones_from_dxf()` Service
4. `IgnitionAssessmentExportView` + Template
5. Equipment-ATEX-Check-Signal bei `post_save`

### Phase 3 — Konsolidierung (Sprint 3)

1. `calculations.py` deprecaten: Funktionen auf `nl2cad-exschutz` delegieren
2. `ignition/assessor.py` in `nl2cad-exschutz` implementieren
3. `CombinedExBrandCheck` in `nl2cad-brandschutz` (Zone + F60-Prüfung)
4. End-to-End-Tests: DXF-Upload → Zonen → Berechnung → PDF-Report

---

## 7. Bewertung der Alternativen

### Alternative A: Alles in risk-hub belassen

- ❌ Fachlogik nicht wiederverwendbar
- ❌ Tests nur mit Django-Setup möglich
- ❌ Wachsende Kopplung zwischen Berechnung und ORM

### Alternative B: Alles in nl2cad-brandschutz

- ❌ Explosionsschutz ≠ Brandschutz — fachlich falsch
- ❌ Package würde zu groß und zu viele Normen abdecken
- ❌ ATEX/BetrSichV hat keine CAD-Abhängigkeit

### Alternative C: nl2cad-exschutz (diese Entscheidung) ✅

- ✅ Klare fachliche Trennung (Ex ≠ Brand)
- ✅ Unabhängig testbar ohne Django
- ✅ Wiederverwendbar in anderen Apps (z.B. cad-hub ATEX-Analyse)
- ✅ risk-hub bleibt schlank — nur Persistenz und UI

---

## 8. Konsequenzen

### Positiv

- `calculations.py` kann mittelfristig geleert werden (Tech Debt abgebaut)
- `nl2cad-exschutz` ist eigenständig über PyPI verteilbar
- Sachverständigen-Funktionen (PDF-Reports, Nachweise) klar lokalisiert
- Testbarkeit: `pytest packages/nl2cad-exschutz/` ohne Django-Overhead

### Negativ / Risiken

- Initial-Aufwand für Package-Erstellung (~2 Sprints)
- Zwei Abhängigkeiten in risk-hub (`nl2cad-brandschutz` + `nl2cad-exschutz`)
- Stoff-Datenbank muss gepflegt werden (GESTIS-Updates)

### Offene Fragen

- [ ] Stoff-Datenbank: statisch in Package oder externe GESTIS-API?
- [ ] `nl2cad-exschutz` Versionierung: gleiches Release-Cadence wie andere nl2cad-Packages?
- [ ] `ZoneExtent` Pydantic-Schema: in `nl2cad-exschutz` oder in risk-hub bleiben?

---

## 9. Verweise

- TRGS 721: Gefährliche explosionsfähige Atmosphäre — Beurteilung der Explosionsgefährlichkeit
- TRGS 722: Vermeidung oder Einschränkung gefährlicher explosionsfähiger Atmosphären
- EN 1127-1: Explosionsfähige Atmosphären — Grundlagen und Methodik
- IEC 60079-10-1: Klassifizierung von Bereichen bei gasförmigen Brennstoffen
- ATEX-Richtlinie 2014/34/EU: Geräte und Schutzsysteme in explosionsgefährdeten Bereichen
- BetrSichV §§ 14–17: Prüfpflichten für überwachungsbedürftige Anlagen
- ASR A2.3: Fluchtwege und Notausgänge
- DIN 4102: Brandverhalten von Baustoffen und Bauteilen
- `ADR-001` risk-hub: Multi-Tenant-Architektur und Domain-Modell
- `AGENTS.md` nl2cad: Package-Übersicht und Coding-Konventionen
