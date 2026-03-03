# ADR-007: Paketarchitektur für Explosionsschutz- und Brandschutz-Fachlogik

| Feld            | Wert                                                           |
|-----------------|----------------------------------------------------------------|
| **Status**      | **Proposed — zur externen Review**                             |
| **Datum**       | 2026-03-03                                                     |
| **Autor**       | Achim Dehnert                                                  |
| **PyPI-Account**| `iildehnert`                                                   |
| **Repos**       | `risk-hub` (Schutztat), `nl2cad`, neues Repo `riskfw`          |
| **Entscheider** | IT-Architekt, Explosionsschutz-SV, Brandschutz-SV              |
| **Review durch**| *(externe Sachverständige, bitte Kommentare in GitHub Issues)* |

---

## Zusammenfassung für Reviewer

Dieses ADR trifft eine grundlegende Architekturentscheidung über die Aufteilung von
Sicherheitsfachlogik auf Python-Packages:

> **`riskfw`** ist ein neues, eigenständiges PyPI-Package (kein CAD-Bezug),
> das Berechnungslogik für Explosionsschutz (TRGS 721/722, ATEX, EN 1127-1)
> als wiederverwendbare, Framework-agnostische Python-Library bereitstellt.
> Es ist **kein Teil des `nl2cad`-Ökosystems**, da `nl2cad` ausschließlich
> CAD-Dateiverarbeitung (IFC/DXF) adressiert.

**Kernfragen an Reviewer:**

1. Ist die fachliche Abgrenzung Explosionsschutz / Brandschutz korrekt getroffen?
2. Sind die Normbezüge (TRGS 721, EN 1127-1, IEC 60079-10-1) vollständig?
3. Fehlen sicherheitstechnisch relevante Berechnungsmodule?
4. Ist `riskfw` als Name für ein öffentliches PyPI-Package geeignet?

---

## 1. Kontext und Problemstellung

### 1.1 Ausgangslage

**risk-hub** (`Schutztat`) ist eine Multi-Tenant Django-App für Arbeitssicherheit.
Das Modul `explosionsschutz` enthält aktuell Berechnungslogik direkt in der App:

```
risk-hub/src/explosionsschutz/
├── calculations.py     ← Stoff-DB, TRGS 721 Zonenberechnung, ATEX-Check
├── models.py           ← Django-ORM: Konzepte, Zonen, Betriebsmittel
├── services.py         ← Service-Layer mit Audit-Trail
├── export_views.py     ← GAEB/PDF-Export (nutzt bereits nl2cad.gaeb)
└── schemas.py          ← Pydantic: ZoneExtent-Geometrie
```

**nl2cad** ist eine separate CAD-Analyse-Library:

```
nl2cad-core         → IFC/DXF Parsing, Dataclasses, Handler-Pipeline
nl2cad-brandschutz  → Erkennt Brandschutz-Elemente AUS DXF-Layern (ASR A2.3, DIN 4102)
nl2cad-areas        → Berechnet Flächen AUS IFC-Räumen (DIN 277, WoFlV)
nl2cad-gaeb         → Exportiert CAD-Daten nach GAEB XML/Excel
nl2cad-nlp          → Konvertiert natürliche Sprache → CAD-Befehle
```

### 1.2 Das Kernproblem

`calculations.py` in risk-hub enthält Fachlogik, die **keinen CAD-Bezug** hat:

| Funktion | Norm | CAD-Bezug? |
|---|---|---|
| `calculate_zone_extent()` | TRGS 721 | ❌ reine Physik/Mathematik |
| `calculate_ventilation_effectiveness()` | TRGS 722 | ❌ Strömungslehre |
| `check_equipment_suitability()` | ATEX 2014/34/EU | ❌ Kennzeichnungsprüfung |
| Stoff-Datenbank (GESTIS) | — | ❌ Chemie-Daten |
| Zündquellen-Bewertung | EN 1127-1 | ❌ Sicherheitstechnik |

Diese Logik gehört **nicht** in nl2cad (kein CAD-Bezug) und **nicht** dauerhaft
in risk-hub (nicht wiederverwendbar, schlechte Testbarkeit ohne Django).

**Einzige Verbindung zu nl2cad:** `nl2cad-brandschutz` erkennt `ExBereich`-Objekte
aus DXF-Layer-Namen — diese werden als Ergebnis an risk-hub übergeben.
Das ist eine Konsumenten-Beziehung, kein Grund für eine Package-Zugehörigkeit.

### 1.3 Anforderungen der Stakeholder

**Explosionsschutz-Sachverständiger (Ex-SV):**

- Zonenausdehnung nach TRGS 721 berechnen mit revisionssicherem Nachweis
  (Zeitstempel, Norm-Referenz, ausführende Person, archiviertes Rohergebnis)
- Zündquellen-Bewertungsmatrix nach EN 1127-1 (alle 13 Quellen) als
  druckfertiges Prüfdokument exportieren
- ATEX-Kennzeichnung von Betriebsmitteln automatisch gegen Zone prüfen
- Ex-Zonen aus CAD-Plänen (DXF) importieren statt manuell erfassen
- Prüfberichte revisionssicher archivieren (BetrSichV §§ 14–17)

**Brandschutz-Sachverständiger (BS-SV):**

- IFC/DXF-Pläne automatisch auf Brandschutz-Elemente analysieren
  (Fluchtwege, Brandabschnitte, Rauchmelder, Sprinkler)
- ASR A2.3 / DIN 4102 Konformitätsprüfung mit Mängel-Protokoll
- Kombinierten Ex + Brand-Check: Zone 1 erfordert F60-Wand — vorhanden?
- Wiederkehrende Prüffristen verwalten und überwachen

**IT-Architekt:**

- Klares Package-Ökosystem: jede Library hat **einen** Zweck
- Framework-agnostische Fachlogik: testbar ohne Django, wiederverwendbar
- risk-hub enthält nur: Persistenz, Tenant-Isolation, UI, Audit-Trail
- Keine zirkulären Abhängigkeiten zwischen Packages
- PyPI-Releases unabhängig versionierbar

---

## 2. Entscheidung

### 2.1 Ziel-Architektur

```text
 ┌──────────────────────────────────────────────────────────────────┐
 │  SCHICHT 4: risk-hub (Django App)                                │
 │  Persistenz · Tenant-Isolation · UI/HTMX · Audit · Workflow     │
 │                                                                  │
 │  explosionsschutz/   brandschutz/   substances/                 │
 │  → delegiert Berechnung → speichert Ergebnis                    │
 ├────────────────────┬─────────────────────────────────────────────┤
 │  SCHICHT 3a:       │  SCHICHT 3b:                                │
 │  riskfw (NEU)      │  nl2cad-brandschutz (bestehend)             │
 │  PyPI: iildehnert  │  PyPI: achimdehnert                         │
 │                    │                                             │
 │  Ex-Schutz         │  CAD-Analyse                                │
 │  Fachlogik         │  Brandschutz                                │
 │  (kein CAD)        │  (aus IFC/DXF)                              │
 ├────────────────────┴─────────────────────────────────────────────┤
 │  SCHICHT 2: nl2cad-core (bestehend)                              │
 │  IFC/DXF Parsing · Dataclasses · Handler-Pipeline               │
 │  (Basis für nl2cad-brandschutz; riskfw hat KEINE Abhängigkeit)  │
 └──────────────────────────────────────────────────────────────────┘
```

### 2.2 Entschiedene Paket-Zugehörigkeit

#### Neues Package: `riskfw`

**Begründung für eigenständiges Package außerhalb von `nl2cad`:**

`nl2cad` = "Natural Language to CAD" — das Ökosystem verarbeitet CAD-Dateien.
`riskfw` = "Risk Framework" — berechnet physikalische und normative Kenngrößen
für Arbeitssicherheit. Kein einziges Modul in `riskfw` liest oder schreibt
eine IFC- oder DXF-Datei.

**Abhängigkeiten:** keine (pure Python, stdlib only)
**Kein** nl2cad-core, **kein** Django, **kein** httpx

| Modul | Inhalt | Norm |
|---|---|---|
| `riskfw.substances` | GESTIS Stoff-Datenbank, `SubstanceProperties` | GESTIS/DGUV |
| `riskfw.zones.calculator` | `calculate_zone_extent()` | TRGS 721 |
| `riskfw.zones.ventilation` | `calculate_ventilation_effectiveness()` | TRGS 722 |
| `riskfw.zones.models` | `ZoneExtentResult`, `VentilationResult` Dataclasses | — |
| `riskfw.equipment.checker` | `check_equipment_suitability()` | ATEX 2014/34/EU |
| `riskfw.equipment.models` | `ATEXCheckResult` Dataclass | IEC 60079-0 |
| `riskfw.ignition.assessor` | `IgnitionSourceMatrix`, 13 Quellen | EN 1127-1 |
| `riskfw.ignition.models` | `IgnitionAssessment`, `IgnitionRisk` Dataclasses | — |
| `riskfw.reports` | `ZoneCalculationReport`, `IgnitionAssessmentReport` | — |
| `riskfw.constants` | ATEX-Kategorien, Explosionsgruppen, Temperaturklassen | IEC 60079 |

#### `nl2cad-brandschutz` — unverändert + eine Erweiterung

| Modul | Status |
|---|---|
| `analyzer.py` — IFC/DXF Analyse | **unverändert** |
| `models.py` — `ExBereich`, `Fluchtweg`, `Brandabschnitt` | **unverändert** |
| `rules/asr_a23.py`, `rules/din4102.py` | **unverändert** |
| `rules/combined.py` — Zone 1 + F60-Wand Check | **NEU (P2)** |

#### `risk-hub` — nur Django-Schicht

| Verbleibend | Begründung |
|---|---|
| `models.py` — alle Django ORM Models | Persistenz, Migrations, Tenant-Isolation |
| `models.py` — `ZoneCalculationResult` **(NEU)** | TRGS 721 Nachweisarchivierung |
| `services.py` — alle `create_*` / `update_*` | Audit, `@transaction.atomic` |
| `services.py` — `calculate_and_store_zone()` **(NEU)** | Delegiert an `riskfw`, persistiert |
| `services.py` — `import_zones_from_dxf()` **(NEU)** | Delegiert an `nl2cad-brandschutz` |
| `export_views.py` — PDF/GAEB Export | WeasyPrint, nl2cad.gaeb |
| `export_views.py` — `IgnitionAssessmentExportView` **(NEU)** | PDF via WeasyPrint |
| `calculations.py` | **→ DEPRECATE** nach Phase 3, auf riskfw delegieren |
| `schemas.py` — `ZoneExtent` | Bleibt als Pydantic-Validierung für Forms/API |

---

## 3. Spezifikation: `riskfw`

### 3.1 Package-Struktur

```text
riskfw/                          ← eigenständiges Git-Repo
├── pyproject.toml               ← name = "riskfw", PyPI: iildehnert
├── README.md
├── CHANGELOG.md
└── src/riskfw/
    ├── __init__.py              # __version__ = "0.1.0"
    ├── constants.py             # ATEX_CATEGORIES, TEMP_CLASSES, EXP_GROUPS
    ├── substances/
    │   ├── __init__.py          # Public: get_substance_properties, list_substances
    │   ├── database.py          # SUBSTANCE_DATABASE (GESTIS-basiert)
    │   └── lookup.py            # Alias-Auflösung, Fuzzy-Search
    ├── zones/
    │   ├── __init__.py          # Public: calculate_zone_extent, ...
    │   ├── models.py            # ZoneExtentResult, VentilationResult
    │   ├── calculator.py        # TRGS 721 Zonenberechnung
    │   └── ventilation.py       # TRGS 722 Lüftungseffektivität
    ├── equipment/
    │   ├── __init__.py          # Public: check_equipment_suitability
    │   ├── models.py            # ATEXCheckResult
    │   └── checker.py           # ATEX 2014/34/EU Eignungsprüfung
    ├── ignition/
    │   ├── __init__.py          # Public: IgnitionSourceMatrix
    │   ├── models.py            # IgnitionAssessment, IgnitionRisk
    │   └── assessor.py          # 13 Zündquellen nach EN 1127-1
    └── reports/
        ├── __init__.py          # Public: ZoneCalculationReport, ...
        └── builder.py           # Report-Strukturen als Dataclasses
```

### 3.2 Public API

```python
# Stoff-Lookup
from riskfw.substances import get_substance_properties, list_substances

props = get_substance_properties("ethanol")
# → SubstanceProperties(name="Ethanol", lel=3.1, uel=27.7, ...)

# Zonenberechnung TRGS 721
from riskfw.zones import calculate_zone_extent

result = calculate_zone_extent(
    release_rate_kg_s=0.1,
    ventilation_rate_m3_s=2.0,
    substance_name="ethanol",
    release_type="jet",
)
# → ZoneExtentResult(zone_type="1", radius_m=2.3, basis_norm="TRGS 721")

# ATEX-Eignungsprüfung
from riskfw.equipment import check_equipment_suitability

check = check_equipment_suitability(
    ex_marking="II 2G Ex d IIB T4",
    zone="1",
)
# → ATEXCheckResult(is_suitable=True, detected_category="2G", ...)

# Zündquellen-Bewertung EN 1127-1
from riskfw.ignition import IgnitionSourceMatrix

matrix = IgnitionSourceMatrix()
assessment = matrix.assess("S01_heisse_oberflaechen", is_present=True,
                            is_effective=False, mitigation="Hitzeschild")
# → IgnitionAssessment(risk_level="low", norm_reference="EN 1127-1")
```

### 3.3 Zentrale Dataclasses

```python
# zones/models.py
@dataclass
class ZoneExtentResult:
    zone_type: str           # "0" | "1" | "2"
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
    detected_category: str | None    # "1G" | "2G" | "3G" | "1D" | ...
    detected_temp_class: str | None  # "T1" .. "T6"
    detected_exp_group: str | None   # "IIA" | "IIB" | "IIC"
    issues: list[str] = field(default_factory=list)
    recommendations: list[str] = field(default_factory=list)
    basis_norm: str = "ATEX 2014/34/EU"


# ignition/models.py
@dataclass
class IgnitionAssessment:
    source_id: str           # "S01" .. "S13"
    source_name: str         # "Heiße Oberflächen"
    is_present: bool
    is_effective: bool
    risk_level: str          # "none" | "low" | "high"
    mitigation: str = ""
    norm_reference: str = "EN 1127-1"
```

---

## 4. Spezifikation: risk-hub Erweiterungen

### 4.1 Neues Modell `ZoneCalculationResult`

```python
class ZoneCalculationResult(models.Model):
    """
    Archivierte TRGS 721 Zonenberechnung.
    Nachweispflicht nach BetrSichV §§ 14–17.
    Unveränderlich nach Erstellung (kein Update, kein Delete).
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant_id = models.UUIDField(db_index=True)

    zone = models.ForeignKey(
        "ZoneDefinition", on_delete=models.CASCADE, related_name="calculations"
    )
    substance_name = models.CharField(max_length=200)    # denorm. für Archiv
    release_rate_kg_s = models.DecimalField(max_digits=12, decimal_places=6)
    ventilation_rate_m3_s = models.DecimalField(max_digits=12, decimal_places=4)
    release_type = models.CharField(max_length=20)       # jet | pool | diffuse
    calculated_zone_type = models.CharField(max_length=5)
    calculated_radius_m = models.DecimalField(max_digits=8, decimal_places=3)
    calculated_volume_m3 = models.DecimalField(max_digits=12, decimal_places=3)
    basis_norm = models.CharField(max_length=50, default="TRGS 721")
    raw_result = models.JSONField()                      # vollständiges ZoneExtentResult
    calculated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True
    )
    calculated_at = models.DateTimeField(auto_now_add=True)
    notes = models.TextField(blank=True, default="")

    class Meta:
        db_table = "ex_zone_calculation_result"
        ordering = ["-calculated_at"]
        # Compliance: kein Löschen erlaubt
        default_permissions = ("add", "view")
```

### 4.2 Service `calculate_and_store_zone()`

```python
# services.py — delegiert an riskfw, persistiert Ergebnis
@dataclass(frozen=True)
class CalculateZoneCmd:
    zone_id: UUID
    release_rate_kg_s: float
    ventilation_rate_m3_s: float
    release_type: str   # "jet" | "pool" | "diffuse"
    notes: str = ""


@transaction.atomic
def calculate_and_store_zone(
    cmd: CalculateZoneCmd,
    tenant_id: UUID,
    user_id: UUID | None = None,
) -> ZoneCalculationResult:
    """
    Delegiert an riskfw.zones.calculate_zone_extent(),
    archiviert Ergebnis in DB.
    Audit: explosionsschutz.zone.calculated
    """
    from riskfw.zones import calculate_zone_extent

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

### 4.3 Service `import_zones_from_dxf()`

```python
@transaction.atomic
def import_zones_from_dxf(
    concept_id: UUID,
    dxf_bytes: bytes,
    tenant_id: UUID,
    user_id: UUID | None = None,
) -> int:
    """
    DXF-Upload → nl2cad-brandschutz erkennt ExBereich-Objekte
    → ZoneDefinition-Records in risk-hub DB anlegen.
    riskfw wird hier NICHT verwendet (das ist CAD-Analyse).
    """
    import io
    import ezdxf
    from nl2cad.brandschutz.analyzer import BrandschutzAnalyzer

    concept = ExplosionConcept.objects.get(id=concept_id, tenant_id=tenant_id)
    analyse = BrandschutzAnalyzer().analyze_dxf(ezdxf.read(io.BytesIO(dxf_bytes)))

    count = 0
    for ex_bereich in analyse.ex_bereiche:
        ZoneDefinition.objects.create(
            tenant_id=tenant_id,
            concept=concept,
            zone_type=ex_bereich.zone.value.replace("Zone ", ""),
            name=ex_bereich.name or f"Import: {ex_bereich.zone.value}",
            justification=f"DXF-Import, Layer: {ex_bereich.layer}",
        )
        count += 1

    emit_audit_event(
        tenant_id=tenant_id, category=AuditCategory.ZONE, action="imported",
        entity_type="ZoneDefinition", entity_id=concept_id,
        payload={"count": count, "source": "dxf"}, user_id=user_id,
    )
    return count
```

---

## 5. Abhängigkeitsmatrix

```text
                    ┌─────────────────────────────┐
                    │         risk-hub             │
                    │         (Django)             │
                    └──────┬──────────┬────────────┘
                           │          │
                           ↓          ↓
              ┌────────────┐    ┌─────────────────┐
              │  riskfw    │    │ nl2cad-brandschutz│
              │  (NEU)     │    │  (bestehend)     │
              │            │    └────────┬─────────┘
              │ KEINE      │             ↓
              │ nl2cad-    │    ┌─────────────────┐
              │ Abhängigkeit│   │   nl2cad-core   │
              └────────────┘    └─────────────────┘
```

**Verbote:**

| Von | Nach | Grund |
|---|---|---|
| `riskfw` | `nl2cad-*` | kein CAD-Bezug, kein gemeinsames Ökosystem |
| `riskfw` | Django | Framework-agnostisch |
| `nl2cad-brandschutz` | `riskfw` | keine Querabhängigkeit |
| `risk-hub` | `calculations.py` (direkt) | nach Phase 3 obsolet |

---

## 6. Migrationspfad

### Phase 1 — `riskfw` erstellen (Sprint 1, ~1 Woche)

1. Neues Git-Repo `riskfw` anlegen, PyPI-Account `iildehnert`
2. `substances/` aus `calculations.py` migrieren + Tests
3. `zones/calculator.py` migrieren + Tests (TRGS 721 Referenzfälle)
4. `equipment/checker.py` migrieren + Tests (ATEX-Kategorien)
5. `riskfw==0.1.0` nach PyPI publishen
6. `riskfw` in `risk-hub/requirements.txt` aufnehmen

### Phase 2 — risk-hub Integration (Sprint 2, ~1 Woche)

1. `ZoneCalculationResult` Modell + Migration
2. `calculate_and_store_zone()` + `import_zones_from_dxf()` Services
3. `IgnitionAssessmentExportView` + WeasyPrint-Template
4. Equipment `post_save`-Signal: ATEX-Check via `riskfw`

### Phase 3 — Konsolidierung (Sprint 3, ~3 Tage)

1. `ignition/` in `riskfw` implementieren (EN 1127-1, 13 Quellen)
2. `calculations.py` leeren — nur noch Delegation an `riskfw`
3. `CombinedExBrandCheck` in `nl2cad-brandschutz` (Zone + F60-Wand)
4. End-to-End-Test: DXF-Upload → Zonen-Import → Berechnung → PDF-Nachweis

---

## 7. Bewertung der Alternativen

### Option A: Alles in `risk-hub/calculations.py` belassen (Status quo)

- ✅ Kein Aufwand
- ❌ Fachlogik nicht wiederverwendbar außerhalb risk-hub
- ❌ Tests erfordern Django-Setup
- ❌ Wachsende Kopplung, zunehmende technische Schuld

### Option B: Logik in `nl2cad-exschutz` (abgelehnt)

- ❌ **Fachlich falsch**: nl2cad ist eine CAD-Library, kein Safety-Framework
- ❌ Irreführend für externe Nutzer von nl2cad
- ❌ Explosionsschutz-Berechnung hat keinen CAD-Datei-Bezug

### Option C: `riskfw` als eigenständiges Package ✅ (diese Entscheidung)

- ✅ Klare fachliche Identität: Safety-Berechnungen ohne CAD-Bezug
- ✅ Unabhängig testbar, unabhängig versionierbar
- ✅ Wiederverwendbar in anderen Apps (MCP-Tools, future SafetyHub)
- ✅ nl2cad bleibt sauber als CAD-Ökosystem

---

## 8. Konsequenzen

### Positiv

- `calculations.py` wird mittelfristig zur dünnen Delegation (Tech Debt abgebaut)
- `riskfw` auf PyPI als eigenständige Safety-Library verfügbar (`iildehnert`)
- Testbarkeit: `pytest` ohne Django, schnell und isoliert
- Klare Kommunikation nach außen: nl2cad = CAD, riskfw = Safety-Berechnungen

### Negativ / Risiken

- Neues Git-Repo und PyPI-Release-Prozess notwendig
- Stoff-Datenbank (GESTIS) ist statisch — benötigt manuelle Pflege bei Updates
- Zwei externe Dependencies in risk-hub: `riskfw` + `nl2cad-brandschutz`

### Offene Fragen für Reviewer

- [ ] **Stoff-Datenbank:** Statisch in Package (aktuell 13 Stoffe) oder
      externe GESTIS-API-Anbindung? Letzteres würde httpx erfordern und
      das Package komplexer machen.
- [ ] **Normerweiterung:** Soll `riskfw` auch BetrSichV §§ 14–17
      Prüffristen-Berechnung enthalten? Oder bleibt das in risk-hub?
- [ ] **Brandschutz in riskfw:** Soll `riskfw` auch Brandschutz-Berechnungen
      (z.B. Feuerwiderstandsdauer) enthalten — oder bleibt das vollständig
      in `nl2cad-brandschutz` (CAD-seitig)?
- [ ] **Package-Name:** Ist `riskfw` eindeutig genug oder besser
      `safetycalc`, `exschutz-py`, `atex-tools`?

---

## 9. Normbezüge

| Norm | Titel | Modul in riskfw |
|---|---|---|
| TRGS 721 | Gefährliche explosionsfähige Atmosphäre — Beurteilung | `zones.calculator` |
| TRGS 722 | Vermeidung gefährlicher explosionsfähiger Atmosphären | `zones.ventilation` |
| EN 1127-1 | Explosionsfähige Atmosphären — Grundlagen und Methodik | `ignition.assessor` |
| IEC 60079-10-1 | Klassifizierung von Bereichen (Gas) | `zones.calculator` |
| ATEX 2014/34/EU | Geräte in explosionsgefährdeten Bereichen | `equipment.checker` |
| IEC 60079-0 | Allgemeine Anforderungen Ex-Geräte | `equipment.models` |
| BetrSichV §§ 14–17 | Prüfpflichten überwachungsbedürftige Anlagen | risk-hub (nicht riskfw) |
| ASR A2.3 | Fluchtwege und Notausgänge | nl2cad-brandschutz (nicht riskfw) |
| DIN 4102 | Brandverhalten von Baustoffen | nl2cad-brandschutz (nicht riskfw) |

---

## 10. Verweise

- `ADR-001` risk-hub: Explosionsschutz-Modul und Domain-Modell
- `ADR-003` risk-hub: Multi-Tenant RBAC Architektur
- `ADR-006` risk-hub: Audit und Compliance
- `AGENTS.md` nl2cad: Package-Übersicht und Coding-Konventionen
- GitHub risk-hub: <https://github.com/achimdehnert/risk-hub>
- PyPI Account: `iildehnert`
