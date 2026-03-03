# ADR-007: Paketarchitektur für Explosionsschutz- und Brandschutz-Fachlogik

| Feld             | Wert                                                                |
|------------------|---------------------------------------------------------------------|
| **Status**       | **Accepted** (nach Review, 2026-03-03)                              |
| **Version**      | 2.0                                                                 |
| **Datum**        | 2026-03-03                                                          |
| **Autor**        | Achim Dehnert                                                       |
| **PyPI-Account** | `iildehnert`                                                        |
| **Repos**        | `risk-hub` (Schutztat), `nl2cad`, neues Repo `riskfw`               |
| **Entscheider**  | IT-Architekt, Explosionsschutz-SV, Brandschutz-SV                   |
| **Review**       | Architektur-Review 2026-03-03 — CONDITIONAL APPROVE                 |
| **Review-Quelle**| `docs/adr/input/REVIEW-ADR-007-explosionsschutz-brandschutz.md`     |

## Änderungshistorie

| Version | Datum | Änderung |
|---|---|---|
| 1.0 | 2026-03-03 | Initiales ADR — Proposed |
| 2.0 | 2026-03-03 | Alle Review-Befunde eingearbeitet: 4 Blocker, 7 Major, 5 Minor behoben |

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

`calculations.py` enthält Fachlogik **ohne CAD-Bezug**, die in risk-hub deplatziert ist:

| Funktion | Norm | CAD-Bezug? |
|---|---|---|
| `calculate_zone_extent()` | TRGS 721 | ❌ reine Physik/Mathematik |
| `calculate_ventilation_effectiveness()` | TRGS 722 | ❌ Strömungslehre |
| `check_equipment_suitability()` | ATEX 2014/34/EU | ❌ Kennzeichnungsprüfung |
| Stoff-Datenbank (GESTIS) | — | ❌ Chemie-Daten |
| Zündquellen-Bewertung | EN 1127-1 | ❌ Sicherheitstechnik |

**Einzige Verbindung zu nl2cad:** `nl2cad-brandschutz` erkennt `ExBereich`-Objekte
aus DXF-Layer-Namen. Das ist eine Konsumenten-Beziehung, kein Package-Zugehörigkeitsgrund.

### 1.3 Anforderungen der Stakeholder

**Explosionsschutz-Sachverständiger (Ex-SV):**
- Zonenausdehnung nach TRGS 721 mit revisionssicherem Nachweis (BetrSichV §§ 14–17)
- Zündquellen-Bewertungsmatrix EN 1127-1 (13 Quellen) als druckfertiges Prüfdokument
- ATEX-Kennzeichnungsprüfung bei Betriebsmittel-Erfassung
- Ex-Zonen-Import aus DXF-Plänen

**Brandschutz-Sachverständiger (BS-SV):**
- IFC/DXF-Analyse auf Fluchtwege, Brandabschnitte, Melder (ASR A2.3, DIN 4102)
- Kombinierten Ex + Brand-Check: Zone 1 erfordert F60-Wand

**IT-Architekt:**
- Framework-agnostische Fachlogik in wiederverwendbaren Packages
- risk-hub enthält nur: Persistenz, Tenant-Isolation, UI, Audit-Trail
- Keine zirkulären Abhängigkeiten, unabhängige PyPI-Releases

---

## 2. Entscheidung

### 2.1 Ziel-Architektur

```text
 ┌──────────────────────────────────────────────────────────────────┐
 │  SCHICHT 4: risk-hub (Django App)                                │
 │  Persistenz · Tenant-Isolation · UI/HTMX · Audit · Workflow     │
 │  → delegiert Berechnung → speichert Ergebnis                    │
 ├────────────────────┬─────────────────────────────────────────────┤
 │  SCHICHT 3a:       │  SCHICHT 3b:                                │
 │  riskfw (NEU)      │  nl2cad-brandschutz (bestehend)             │
 │  PyPI: iildehnert  │  PyPI: achimdehnert                         │
 │  Ex-Schutz Logik   │  CAD-Analyse Brandschutz (IFC/DXF)          │
 │  (KEIN CAD-Bezug)  │                                             │
 ├────────────────────┴─────────────────────────────────────────────┤
 │  SCHICHT 2: nl2cad-core (bestehend)                              │
 │  IFC/DXF Parsing — riskfw hat KEINE nl2cad-Abhängigkeit          │
 └──────────────────────────────────────────────────────────────────┘
```

### 2.2 Paket-Zugehörigkeit

#### Neues Package: `riskfw` (pure Python, stdlib only)

`nl2cad` = CAD-Dateiverarbeitung. `riskfw` = Safety-Berechnungen.
Kein `riskfw`-Modul liest oder schreibt IFC/DXF.

**Abhängigkeiten:** keine (`difflib` für Fuzzy-Lookup via stdlib — siehe B4)

| Modul | Inhalt | Norm |
|---|---|---|
| `riskfw.substances` | GESTIS Stoff-DB (statisch, versioniert), `SubstanceProperties` | GESTIS/DGUV |
| `riskfw.zones.calculator` | `calculate_zone_extent()` | TRGS 721:2017-09 |
| `riskfw.zones.ventilation` | `calculate_ventilation_effectiveness()` | TRGS 722:2012-08 |
| `riskfw.zones.models` | `ZoneExtentResult`, `VentilationResult`, `ZoneType`, `ReleaseType` Enums | — |
| `riskfw.equipment.checker` | `check_equipment_suitability()` | ATEX 2014/34/EU |
| `riskfw.equipment.models` | `ATEXCheckResult` Dataclass | IEC 60079-0 |
| `riskfw.ignition.assessor` | `IgnitionSourceMatrix`, 13 Quellen EN 1127-1 | EN 1127-1:2019 |
| `riskfw.ignition.models` | `IgnitionAssessment`, `IgnitionRisk` (StrEnum) | — |
| `riskfw.reports` | `ZoneCalculationReport`, `IgnitionAssessmentReport` Dataclasses | — |
| `riskfw.constants` | ATEX-Kategorien, Normversionen (`NORM_TRGS_721 = "TRGS 721:2017-09"`) | IEC 60079 |
| `riskfw.exceptions` | `SubstanceNotFoundError`, `ZoneCalculationError` | — |

#### `nl2cad-brandschutz` — unverändert + eine Erweiterung (Phase 2)

| Modul | Status |
|---|---|
| `analyzer.py`, `models.py`, `rules/asr_a23.py`, `rules/din4102.py` | **unverändert** |
| `rules/combined.py` — Zone 1 + F60-Wand Check | **NEU (Phase 2)** |

#### `risk-hub` — nur Django-Schicht

| Verbleibend | Begründung |
|---|---|
| Alle Django ORM Models | Persistenz, Migrations, Tenant-Isolation |
| `ZoneCalculationResult` **(NEU)** | TRGS 721 Nachweisarchivierung (BetrSichV) |
| `create_*` / `update_*` Services | Audit, `@transaction.atomic` |
| `calculate_and_store_zone()` **(NEU)** | Delegiert an `riskfw`, persistiert |
| `import_zones_from_dxf()` **(NEU)** | Delegiert an `nl2cad-brandschutz` |
| `create_equipment()` mit ATEX-Check **(NEU)** | Explizit im Service, kein Signal (→ M6) |
| `calculations.py` | **DEPRECATE** in Phase 3 |

---

## 3. Spezifikation: `riskfw`

### 3.1 Package-Struktur

```text
riskfw/
├── pyproject.toml               ← name="riskfw", requires-python=">=3.11"
├── README.md
├── CHANGELOG.md                 ← Versionsstrategie: MAJOR=Norm-Ausgabe, MINOR=neue Norm, PATCH=Bugfix
└── src/riskfw/
    ├── __init__.py              # __version__ = "0.1.0"
    ├── constants.py             # NORM_TRGS_721="TRGS 721:2017-09", ATEX_CATEGORIES, ...
    ├── exceptions.py            # SubstanceNotFoundError, ZoneCalculationError
    ├── substances/
    │   ├── __init__.py          # Public: get_substance_properties, fuzzy_lookup
    │   ├── database.py          # SUBSTANCE_DATABASE — Stand: 2026-03-01, Prüfung fällig: 2027-03-01
    │   └── lookup.py            # difflib.get_close_matches (stdlib, kein rapidfuzz)
    ├── zones/
    │   ├── __init__.py
    │   ├── models.py            # ZoneType(StrEnum), ReleaseType(StrEnum), ZoneExtentResult
    │   ├── calculator.py        # TRGS 721:2017-09
    │   └── ventilation.py       # TRGS 722:2012-08
    ├── equipment/
    │   ├── __init__.py
    │   ├── models.py            # ATEXCheckResult
    │   └── checker.py           # ATEX 2014/34/EU
    ├── ignition/
    │   ├── __init__.py
    │   ├── models.py            # IgnitionRisk(StrEnum), IgnitionAssessment
    │   └── assessor.py          # IgnitionSourceMatrix — 13 Quellen EN 1127-1:2019
    └── reports/
        ├── __init__.py
        └── builder.py           # ZoneCalculationReport, IgnitionAssessmentReport
```

### 3.2 Typsichere Enums (behebt M1, N2)

```python
# riskfw/zones/models.py
from enum import StrEnum
from dataclasses import dataclass, field


class ZoneType(StrEnum):
    ZONE_0 = "0"
    ZONE_1 = "1"
    ZONE_2 = "2"


class ReleaseType(StrEnum):
    JET = "jet"
    POOL = "pool"
    DIFFUSE = "diffuse"


@dataclass
class ZoneExtentResult:
    zone_type: ZoneType           # typsicher — kein raw str
    release_type: ReleaseType     # typsicher
    radius_m: float               # float64, TRGS 721: ±0.1m Genauigkeit ausreichend
    volume_m3: float
    dilution_factor: float
    safety_factor: float
    basis_norm: str = "TRGS 721:2017-09"   # immer mit Ausgabejahr
    warnings: list[str] = field(default_factory=list)


# riskfw/ignition/models.py
class IgnitionRisk(StrEnum):
    """Risikostufe nach EN 1127-1:2019."""
    NONE = "none"
    LOW = "low"
    HIGH = "high"


@dataclass
class IgnitionAssessment:
    source_id: str           # "S01" .. "S13"
    source_name: str
    is_present: bool
    is_effective: bool
    risk_level: IgnitionRisk  # typsicher
    mitigation: str = ""
    norm_reference: str = "EN 1127-1:2019"
```

### 3.3 Stoff-Lookup (behebt B4)

```python
# riskfw/substances/lookup.py — stdlib only, kein rapidfuzz
import difflib
from riskfw.substances.database import SUBSTANCE_DATABASE
from riskfw.exceptions import SubstanceNotFoundError


def get_substance_properties(name: str) -> "SubstanceProperties":
    key = name.lower().strip()
    if key in SUBSTANCE_DATABASE:
        return SUBSTANCE_DATABASE[key]
    # Fuzzy-Fallback: difflib.get_close_matches (stdlib, O(n) für n~100 ausreichend)
    matches = difflib.get_close_matches(key, list(SUBSTANCE_DATABASE.keys()), n=1, cutoff=0.6)
    if matches:
        return SUBSTANCE_DATABASE[matches[0]]
    raise SubstanceNotFoundError(
        f"Stoff '{name}' nicht in Datenbank. Bekannte Stoffe: {list(SUBSTANCE_DATABASE)[:10]}"
    )
```

### 3.4 Report-Dataclasses (behebt N5)

```python
# riskfw/reports/builder.py
from dataclasses import dataclass, field


@dataclass
class ZoneCalculationReport:
    """Vollständiger Prüfnachweis für eine TRGS 721 Zonenberechnung."""
    project_name: str
    zone_name: str
    substance_name: str
    substance_lel: float            # UEG in Vol%
    release_rate_kg_s: float
    ventilation_rate_m3_s: float
    release_type: str
    zone_type: str                  # "0" | "1" | "2"
    radius_m: float
    volume_m3: float
    basis_norm: str                 # "TRGS 721:2017-09"
    riskfw_version: str             # z.B. "0.1.0"
    warnings: list[str] = field(default_factory=list)


@dataclass
class IgnitionAssessmentReport:
    """Vollständige Zündquellen-Bewertungsmatrix nach EN 1127-1."""
    project_name: str
    zone_type: str
    assessments: list[IgnitionAssessment] = field(default_factory=list)
    basis_norm: str = "EN 1127-1:2019"
    riskfw_version: str = ""

    @property
    def has_unmitigated_high_risk(self) -> bool:
        return any(
            a.risk_level == IgnitionRisk.HIGH and not a.mitigation
            for a in self.assessments
        )
```

### 3.5 Normversionen in `constants.py` (behebt M4 partiell)

```python
# riskfw/constants.py
NORM_TRGS_721 = "TRGS 721:2017-09"
NORM_TRGS_722 = "TRGS 722:2012-08"
NORM_EN_1127_1 = "EN 1127-1:2019"
NORM_IEC_60079_10_1 = "IEC 60079-10-1:2015"
NORM_ATEX = "ATEX 2014/34/EU"
```

### 3.6 Versionsstrategie für Norm-Updates (behebt N3)

```
MAJOR: Norm-Ausgabe ändert sich und beeinflusst Berechnungsergebnis
       Beispiel: TRGS 721:2017-09 → TRGS 721:202x
MINOR: Neue Norm hinzugefügt (z.B. TRGS 753 Ammoniak)
PATCH: Bugfix ohne normative Auswirkung, neue Stoffe in Datenbank
```

### 3.7 Deployment: Git-Dependency für Phase 1 (behebt M5)

```
# risk-hub/requirements.txt — Phase 1 (vor PyPI-Veröffentlichung)
riskfw @ git+https://github.com/iildehnert/riskfw@v0.1.0#egg=riskfw

# Phase 2 (nach PyPI-Veröffentlichung mit SHA-Pin)
riskfw==0.1.0 --hash=sha256:<hash-aus-pypi>
```

PyPI-Account `iildehnert` **muss 2FA aktiviert haben** vor dem ersten Release.

---

## 4. Spezifikation: risk-hub Erweiterungen

### 4.1 Modell `ZoneCalculationResult` (behebt B1, M4)

```python
class ZoneCalculationResult(models.Model):
    """
    Archivierter TRGS 721 Zonenberechnungs-Nachweis.
    Nachweispflicht nach BetrSichV §§ 14–17.
    INVARIANTE: Unveränderlich und unlöschbar nach Erstellung.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant_id = models.UUIDField(db_index=True)

    zone = models.ForeignKey(
        "ZoneDefinition",
        on_delete=models.PROTECT,          # B1: CASCADE → PROTECT (BetrSichV-Compliance)
        related_name="calculations",
    )
    substance_name = models.CharField(max_length=200)
    release_rate_kg_s = models.DecimalField(max_digits=12, decimal_places=6)
    ventilation_rate_m3_s = models.DecimalField(max_digits=12, decimal_places=4)
    release_type = models.CharField(
        max_length=20,
        choices=[("jet", "Strahl"), ("pool", "Lache"), ("diffuse", "Diffus")],
    )
    calculated_zone_type = models.CharField(
        max_length=5,
        choices=[("0", "Zone 0"), ("1", "Zone 1"), ("2", "Zone 2")],  # M1: choices
    )
    calculated_radius_m = models.DecimalField(max_digits=8, decimal_places=3)
    calculated_volume_m3 = models.DecimalField(max_digits=12, decimal_places=3)
    basis_norm = models.CharField(max_length=100, default="TRGS 721:2017-09")  # M4: mit Ausgabejahr
    riskfw_version = models.CharField(max_length=20)                            # M4: Package-Version
    raw_result = models.JSONField()
    calculated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True
    )
    calculated_at = models.DateTimeField(auto_now_add=True)
    notes = models.TextField(blank=True, default="")

    class Meta:
        db_table = "ex_zone_calculation_result"
        ordering = ["-calculated_at"]
        default_permissions = ("add", "view")   # kein "change", kein "delete"
```

**PostgreSQL Row-Level-Security** (in der Migration via `RunSQL`):

```sql
-- Migration: ex_zone_calculation_result ist unveränderlich auf DB-Ebene
ALTER TABLE ex_zone_calculation_result ENABLE ROW LEVEL SECURITY;
CREATE POLICY no_delete_policy ON ex_zone_calculation_result
    FOR DELETE USING (FALSE);
```

### 4.2 Service `calculate_and_store_zone()` (behebt B2, B3, M4, M7)

```python
import dataclasses
import riskfw
from riskfw.zones import calculate_zone_extent
from riskfw.exceptions import SubstanceNotFoundError


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
    Delegiert an riskfw.zones.calculate_zone_extent(), archiviert Ergebnis.
    Audit: explosionsschutz.zone.calculated
    """
    # B3 + M7: select_related verhindert N+1, Null-Guards vor Berechnung
    try:
        zone = ZoneDefinition.objects.select_related(
            "concept__substance"
        ).get(id=cmd.zone_id, tenant_id=tenant_id)
    except ZoneDefinition.DoesNotExist:
        raise ValueError(f"ZoneDefinition {cmd.zone_id} nicht gefunden (tenant={tenant_id})")

    if zone.concept is None:
        raise ValueError(f"ZoneDefinition {cmd.zone_id} hat kein ExplConcept")
    if zone.concept.substance is None:
        raise ValueError(f"Concept {zone.concept_id} hat keinen Stoff zugewiesen")

    substance_name = zone.concept.substance.name

    try:
        result = calculate_zone_extent(
            release_rate_kg_s=cmd.release_rate_kg_s,
            ventilation_rate_m3_s=cmd.ventilation_rate_m3_s,
            substance_name=substance_name,
            release_type=cmd.release_type,
        )
    except SubstanceNotFoundError as exc:
        raise ValueError(f"Stoff '{substance_name}' nicht in riskfw-Datenbank: {exc}") from exc

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
        riskfw_version=riskfw.__version__,           # M4: Version archivieren
        raw_result=dataclasses.asdict(result),       # B2: asdict() statt vars()
        calculated_by_id=user_id,
        notes=cmd.notes,
    )
    emit_audit_event(
        tenant_id=tenant_id,
        category=AuditCategory.ZONE,
        action="calculated",
        entity_type="ZoneCalculationResult",
        entity_id=calc.id,
        payload={"zone_type": str(result.zone_type), "radius_m": result.radius_m},
        user_id=user_id,
    )
    return calc
```

### 4.3 Service `import_zones_from_dxf()` (behebt M2, M3, N1)

```python
# explosionsschutz/constants.py
DXF_MAX_BYTES = 50 * 1024 * 1024   # 50 MB


# Stabiler Mapping-Contract für nl2cad-brandschutz ExBereich-Zonen-Werte (behebt M3)
_ZONE_VALUE_MAP: dict[str, str] = {
    "Zone 0": "0",
    "Zone 1": "1",
    "Zone 2": "2",
    "EX_ZONE_0": "0",    # Fallback für nl2cad-Formatänderungen
    "EX_ZONE_1": "1",
    "EX_ZONE_2": "2",
}


def _parse_ex_zone_type(raw_value: str) -> str:
    result = _ZONE_VALUE_MAP.get(raw_value)
    if result is None:
        raise ValueError(
            f"Unbekannter Ex-Zonen-Wert aus DXF: {raw_value!r}. "
            f"Erlaubt: {list(_ZONE_VALUE_MAP)}"
        )
    return result


@transaction.atomic
def import_zones_from_dxf(
    concept_id: UUID,
    dxf_bytes: bytes,
    tenant_id: UUID,
    user_id: UUID | None = None,
) -> int:
    """
    DXF → nl2cad-brandschutz.BrandschutzAnalyzer → ExBereich-Liste
    → ZoneDefinition-Records anlegen.
    riskfw wird hier NICHT verwendet (das ist CAD-Analyse via nl2cad).
    """
    import io
    import ezdxf
    from ezdxf.lldxf.const import DXFError
    from nl2cad.brandschutz.analyzer import BrandschutzAnalyzer

    # M2: Größenprüfung vor Verarbeitung
    if len(dxf_bytes) > DXF_MAX_BYTES:
        raise ValueError(
            f"DXF-Datei zu groß: {len(dxf_bytes):,} Bytes (max {DXF_MAX_BYTES:,})"
        )

    # M2: Spezifische Exception statt nackter Exception
    try:
        doc = ezdxf.read(io.BytesIO(dxf_bytes))
    except DXFError as exc:
        raise ValueError(f"Ungültige DXF-Datei: {exc}") from exc

    concept = ExplosionConcept.objects.get(id=concept_id, tenant_id=tenant_id)
    analyse = BrandschutzAnalyzer().analyze_dxf(doc)

    created_ids: list[UUID] = []
    for ex_bereich in analyse.ex_bereiche:
        zone = ZoneDefinition.objects.create(
            tenant_id=tenant_id,
            concept=concept,
            zone_type=_parse_ex_zone_type(ex_bereich.zone.value),   # M3: stabiles Mapping
            name=ex_bereich.name or f"Import: {ex_bereich.zone.value}",
            justification=f"DXF-Import via nl2cad-brandschutz, Layer: {ex_bereich.layer}",
        )
        created_ids.append(zone.id)

    # N1: entity_type korrekt auf ExplosionConcept, IDs der Zonen im Payload
    emit_audit_event(
        tenant_id=tenant_id,
        category=AuditCategory.ZONE,
        action="imported",
        entity_type="ExplosionConcept",        # N1: war falsch (ZoneDefinition/concept_id)
        entity_id=concept_id,
        payload={"count": len(created_ids), "zone_ids": [str(i) for i in created_ids], "source": "dxf"},
        user_id=user_id,
    )
    return len(created_ids)
```

### 4.4 Service `create_equipment()` mit ATEX-Check (behebt M6)

```python
# M6: Kein post_save-Signal — explizit im Service-Layer
import dataclasses
from riskfw.equipment import check_equipment_suitability


@dataclass(frozen=True)
class CreateEquipmentCmd:
    concept_id: UUID
    name: str
    atex_marking: str
    target_zone: str    # "0" | "1" | "2"
    serial_number: str = ""


@transaction.atomic
def create_equipment(
    cmd: CreateEquipmentCmd,
    tenant_id: UUID,
    user_id: UUID | None = None,
) -> Equipment:
    """
    Erstellt Betriebsmittel und führt sofort ATEX-Check durch.
    Kein post_save-Signal — explizit und deterministisch.
    """
    equipment = Equipment.objects.create(
        tenant_id=tenant_id,
        concept_id=cmd.concept_id,
        name=cmd.name,
        atex_marking=cmd.atex_marking,
        target_zone=cmd.target_zone,
        serial_number=cmd.serial_number,
    )
    atex_result = check_equipment_suitability(
        ex_marking=cmd.atex_marking,
        zone=cmd.target_zone,
    )
    EquipmentATEXCheck.objects.create(
        tenant_id=tenant_id,
        equipment=equipment,
        is_suitable=atex_result.is_suitable,
        result=dataclasses.asdict(atex_result),   # B2-Muster: asdict()
        riskfw_version=riskfw.__version__,
    )
    emit_audit_event(
        tenant_id=tenant_id,
        category=AuditCategory.EQUIPMENT,
        action="created",
        entity_type="Equipment",
        entity_id=equipment.id,
        payload={"atex_suitable": atex_result.is_suitable, "marking": cmd.atex_marking},
        user_id=user_id,
    )
    return equipment
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
              ┌────────────┐    ┌──────────────────┐
              │  riskfw    │    │ nl2cad-brandschutz│
              │  (NEU)     │    │  (bestehend)      │
              │ stdlib only│    └────────┬──────────┘
              │ KEINE      │             ↓
              │ nl2cad-Dep.│    ┌─────────────────┐
              └────────────┘    │   nl2cad-core   │
                                └─────────────────┘
```

**Verbote:**

| Von | Nach | Grund |
|---|---|---|
| `riskfw` | `nl2cad-*` | kein CAD-Bezug |
| `riskfw` | Django / httpx | Framework-agnostisch |
| `nl2cad-brandschutz` | `riskfw` | keine Querabhängigkeit |
| risk-hub Services | Django Signals für Business-Logik | explizit statt magisch (M6) |

---

## 6. Migrationspfad

### Phase 1 — `riskfw` erstellen (~1 Woche)

1. GitHub-Repo `riskfw` unter Account `iildehnert` anlegen
2. `substances/` aus `risk-hub/calculations.py` migrieren + Tests
3. `zones/calculator.py` migrieren + Tests (TRGS 721 Referenzfälle mit bekannten Ergebnissen)
4. `equipment/checker.py` migrieren + Tests (ATEX-Kategorien-Matrix)
5. `riskfw @ git+https://github.com/iildehnert/riskfw@v0.1.0` in risk-hub `requirements.txt`
6. **2FA auf PyPI-Account `iildehnert` aktivieren** vor erstem Release

### Phase 2 — risk-hub Integration (~1 Woche)

1. `ZoneCalculationResult` Modell + Migration (inkl. PostgreSQL RLS via `RunSQL`)
2. `calculate_and_store_zone()` + `import_zones_from_dxf()` Services
3. `create_equipment()` Service mit explizitem ATEX-Check (kein Signal)
4. `IgnitionAssessmentExportView` + WeasyPrint-Template

### Phase 3 — Konsolidierung (~3 Tage)

1. `ignition/` in `riskfw` implementieren (EN 1127-1:2019, 13 Quellen)
2. `calculations.py` leeren — nur noch Delegation an `riskfw`
3. `CombinedExBrandCheck` in `nl2cad-brandschutz` (Zone 1 + F60-Wand)
4. End-to-End-Test: DXF-Upload → Zonen-Import → Berechnung → PDF-Nachweis
5. `riskfw==0.1.0` auf PyPI publishen mit SHA-Hash-Pin in requirements.txt

---

## 7. Bewertung der Alternativen

### Option A: Status quo (`calculations.py` in risk-hub)
- ✅ Kein Aufwand
- ❌ Nicht wiederverwendbar, schlechte Testbarkeit, wachsende Tech Debt

### Option B: `nl2cad-exschutz` (abgelehnt)
- ❌ Fachlich falsch — nl2cad ist CAD-Library, Ex-Schutz hat keinen CAD-Bezug
- ❌ Irreführend für nl2cad-Nutzer ohne Ex-Schutz-Bedarf

### Option C: `riskfw` ✅ (diese Entscheidung)
- ✅ Klare Identität: Safety-Berechnungen, kein CAD
- ✅ Testbar ohne Django, wiederverwendbar
- ✅ nl2cad bleibt sauber als CAD-Ökosystem

---

## 8. Konsequenzen

### Positiv
- `calculations.py` wird Tech Debt abgebaut (Phase 3)
- `riskfw` als eigenständige Safety-Library auf PyPI
- Testbarkeit ohne Django-Setup
- Norm-Updates durch MAJOR-Versioning klar kommuniziert

### Negativ / Risiken
- Neues Git-Repo + PyPI-Release-Prozess nötig
- GESTIS-Stoff-DB statisch → manuelle Pflege bei DGUV-Updates
- 2 externe Dependencies in risk-hub (`riskfw` + `nl2cad-brandschutz`)

### Entschiedene offene Fragen (aus v1.0)

| Frage | Entscheidung | Begründung |
|---|---|---|
| GESTIS-API vs. statisch | **Statisch** für v1 | DGUV-API kein SLA, statisch offline-fähig und auditierbar |
| BetrSichV Prüffristen in riskfw? | **Nein, in risk-hub** | Hängt von Tenant-Daten ab (ORM-Kontext) |
| Brandschutz-Berechnungen in riskfw? | **Nein, in nl2cad-brandschutz** | Untrennbar von CAD-Analyse |
| Package-Name `riskfw`? | **Ja, beibehalten** | Klar, kurz, auf PyPI frei |

---

## 9. Normbezüge

| Norm | Titel | Modul |
|---|---|---|
| TRGS 721:2017-09 | Gefährliche explosionsfähige Atmosphäre | `riskfw.zones.calculator` |
| TRGS 722:2012-08 | Vermeidung gefährlicher expl. Atmosphären | `riskfw.zones.ventilation` |
| EN 1127-1:2019 | Explosionsfähige Atmosphären — Grundlagen | `riskfw.ignition.assessor` |
| IEC 60079-10-1:2015 | Klassifizierung von Bereichen (Gas) | `riskfw.zones.calculator` |
| ATEX 2014/34/EU | Geräte in explosionsgefährdeten Bereichen | `riskfw.equipment.checker` |
| IEC 60079-0 | Allgemeine Anforderungen Ex-Geräte | `riskfw.equipment.models` |
| BetrSichV §§ 14–17 | Prüfpflichten überwachungsbedürftige Anlagen | risk-hub |
| ASR A2.3 | Fluchtwege und Notausgänge | nl2cad-brandschutz |
| DIN 4102 | Brandverhalten von Baustoffen | nl2cad-brandschutz |

---

## 10. Review-Befunde: Behoben in v2.0

| ID | Typ | Befund | Behebung in v2.0 |
|---|---|---|---|
| B1 | 🔴 BLOCKER | `CASCADE` → Compliance-Verletzung | `PROTECT` + PostgreSQL RLS |
| B2 | 🔴 BLOCKER | `vars()` → korrupte JSON-Archivdaten | `dataclasses.asdict()` durchgängig |
| B3 | 🔴 BLOCKER | Kein Null-Check `concept.substance` | Explizite Guards + `select_related` |
| B4 | 🔴 BLOCKER | "stdlib only" ≠ Fuzzy-Search-Dep | `difflib.get_close_matches` (stdlib) |
| M1 | 🟠 MAJOR | `str` für `zone_type`, `release_type` | `ZoneType(StrEnum)`, `ReleaseType(StrEnum)` |
| M2 | 🟠 MAJOR | DXF ohne Größenlimit + Exception | `DXF_MAX_BYTES=50MB`, `DXFError` gefangen |
| M3 | 🟠 MAJOR | Fragiles `str.replace()` Zone-Mapping | `_ZONE_VALUE_MAP` + `_parse_ex_zone_type()` |
| M4 | 🟠 MAJOR | `basis_norm` ohne Ausgabejahr | `"TRGS 721:2017-09"` + `riskfw_version` Feld |
| M5 | 🟠 MAJOR | PyPI Supply-Chain-Risiko | Git-Dep Phase 1, SHA-Pin Phase 3, 2FA-Pflicht |
| M6 | 🟠 MAJOR | `post_save`-Signal für ATEX-Check | Explizit in `create_equipment()` Service |
| M7 | 🟠 MAJOR | N+1 im Berechnungspfad | `select_related("concept__substance")` |
| N1 | 🟡 MINOR | Falsches Entity in Audit-Log | `entity_type="ExplosionConcept"` korrekt |
| N2 | 🟡 MINOR | `IgnitionRisk` undefiniert | `IgnitionRisk(StrEnum)` spezifiziert |
| N3 | 🟡 MINOR | Keine Norm-Versionsstrategie | MAJOR/MINOR/PATCH Strategie in Abschnitt 3.6 |
| N4 | 🟡 MINOR | Precision nicht spezifiziert | `float64`, TRGS 721: ±0.1m ausreichend |
| N5 | 🟡 MINOR | `reports/builder.py` unspezifiziert | Vollständige Dataclass-Spec in Abschnitt 3.4 |

---

## 11. Verweise

- `ADR-001` risk-hub: Explosionsschutz-Modul und Domain-Modell
- `ADR-003` risk-hub: Multi-Tenant RBAC Architektur
- `ADR-006` risk-hub: Audit und Compliance
- `docs/adr/input/REVIEW-ADR-007-explosionsschutz-brandschutz.md` — Quell-Review
- `AGENTS.md` nl2cad: Package-Übersicht und Coding-Konventionen
- GitHub: <https://github.com/achimdehnert/risk-hub>
- Raw ADR: <https://raw.githubusercontent.com/achimdehnert/risk-hub/main/docs/adr/ADR-007-explosionsschutz-brandschutz-paketarchitektur.md>
