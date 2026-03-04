# REVIEW: ADR-007 — Paketarchitektur Explosionsschutz/Brandschutz

| Feld | Wert |
|---|---|
| **Reviewer** | Claude (Automatisierter Architektur-Review) |
| **Reviewed** | ADR-007 v1.0 (Proposed), 2026-03-03 |
| **Review-Datum** | 2026-03-03 |
| **Vorgaben** | Django + HTMX + Postgres 16 + Hetzner VMs + Docker |
| **Gesamturteil** | ⚠️ **CONDITIONAL APPROVE** — 4 Blocker, 7 Major, 5 Minor |

---

## Gesamtbewertung

Die Architekturentscheidung selbst (eigenständiges `riskfw`-Package) ist **fachlich korrekt und
strategisch richtig**. Die Abgrenzung nl2cad = CAD-Ökosystem vs. riskfw = Safety-Berechnungen
ist klar und nachvollziehbar begründet. Die Schichtentrennung in Abschnitt 2.1 ist sauber.

**Kritische Probleme** existieren jedoch in den Implementierungsdetails:
primär rund um Compliance-Invarianten, Typ-Sicherheit und Migrationsrisiken.

---

## BLOCKER (müssen vor Approval behoben werden)

---

### B1 — CASCADE-FK bricht Unveränderlichkeits-Invariante

**Befund (Abschnitt 4.1, `ZoneCalculationResult.zone`)**

```python
# ADR-007, Zeile ~322 — FEHLERHAFT
zone = models.ForeignKey(
    "ZoneDefinition", on_delete=models.CASCADE,  # ← BLOCKER
    related_name="calculations"
)
```

Das Modell deklariert in seinem Docstring:
> "Unveränderlich nach Erstellung (kein Update, kein Delete)."

Gleichzeitig wird `on_delete=CASCADE` verwendet. Das bedeutet: Wenn eine
`ZoneDefinition` gelöscht wird (z.B. fehlerhafte Nutzeraktion, Admin-Skript),
werden alle archivierten Berechnungsnachweise **kaskadierend gelöscht** —
eine direkte Verletzung von **BetrSichV §§ 14–17** (Aufbewahrungspflicht
für Prüfnachweise).

**Risiko:** 🔴 KRITISCH — Compliance-Verletzung, potenzielle Haftung

**Empfehlung:**

```python
# KORREKT: Löschen einer ZoneDefinition VERBIETEN wenn Berechnungen existieren
zone = models.ForeignKey(
    "ZoneDefinition",
    on_delete=models.PROTECT,          # Verhindert Löschen der ZoneDefinition
    related_name="calculations",
)
```

Zusätzlich DB-Level-Absicherung via PostgreSQL-Constraint in der Migration:

```sql
-- Zusätzlich in der Migration: Row-Level-Schutz
-- (Django default_permissions reicht alleine nicht)
ALTER TABLE ex_zone_calculation_result
    ADD CONSTRAINT no_delete_check
    CHECK (TRUE);  -- Placeholder; echter Schutz via Row Security Policy:

-- In der Postgres-Konfiguration (via psql oder Ansible):
ALTER TABLE ex_zone_calculation_result ENABLE ROW LEVEL SECURITY;
CREATE POLICY no_delete_policy ON ex_zone_calculation_result
    FOR DELETE USING (FALSE);  -- Niemand darf löschen
```

---

### B2 — `vars(result)` statt `dataclasses.asdict()` für JSONField-Serialisierung

**Befund (Abschnitt 4.2, Service `calculate_and_store_zone`)**

```python
# ADR-007, Zeile ~392 — FEHLERHAFT
raw_result=vars(result),
```

`vars()` auf einem `@dataclass`-Objekt gibt das interne `__dict__` zurück.
Probleme:
1. Nested Dataclasses (z.B. `list[str]` warnings) werden nicht tief-serialisiert
2. Bei `@dataclass(frozen=True)` mit `__slots__` wirft `vars()` einen `TypeError`
3. Django's `JSONField` serialisiert zwar `dict`, aber `list[str]`-Felder
   werden als Python-Objekte serialisiert, nicht als JSON-Arrays

**Risiko:** 🔴 KRITISCH — Laufzeit-Fehler, korrupte Archivdaten

**Empfehlung:**

```python
import dataclasses
import json

# KORREKT: dataclasses.asdict() für tiefe Serialisierung
raw_result=dataclasses.asdict(result),

# Alternativ für explizite Kontrolle:
raw_result=json.loads(json.dumps(dataclasses.asdict(result))),
```

In `riskfw/zones/models.py` sollte `ZoneExtentResult` explizit mit
`@dataclass` (nicht `frozen=True`) definiert werden, sofern `vars()` erwartet
wird, oder der Contract muss auf `asdict()` umgestellt werden.

---

### B3 — Fehlende Stoff-Lookup-Fehlerbehandlung im kritischen Berechnungspfad

**Befund (Abschnitt 4.2)**

```python
# ADR-007 — kein Fehlerhandling
zone = ZoneDefinition.objects.get(id=cmd.zone_id, tenant_id=tenant_id)
substance_name = zone.concept.substance.name  # ← AttributeError wenn concept/substance None
```

Wenn `zone.concept` oder `zone.concept.substance` `None` ist, wirft Python
einen `AttributeError` **innerhalb einer `@transaction.atomic`-Transaktion**.
Django rollt die Transaktion zurück, aber der Fehler landet als unbehandelter
500er beim Nutzer — ohne sprechende Fehlermeldung, ohne Audit-Log-Eintrag.

**Risiko:** 🔴 KRITISCH — Produktionsfehler ohne Diagnose-Möglichkeit

**Empfehlung:**

```python
@transaction.atomic
def calculate_and_store_zone(
    cmd: CalculateZoneCmd,
    tenant_id: UUID,
    user_id: UUID | None = None,
) -> ZoneCalculationResult:
    from riskfw.zones import calculate_zone_extent
    from riskfw.exceptions import SubstanceNotFoundError

    try:
        zone = ZoneDefinition.objects.select_related(
            "concept__substance"               # N+1 vermeiden
        ).get(id=cmd.zone_id, tenant_id=tenant_id)
    except ZoneDefinition.DoesNotExist:
        raise ValueError(f"ZoneDefinition {cmd.zone_id} not found for tenant")

    if zone.concept is None:
        raise ValueError(f"ZoneDefinition {cmd.zone_id} hat kein ExplConcept")
    if zone.concept.substance is None:
        raise ValueError(f"Concept {zone.concept_id} hat keinen Stoff")

    substance_name = zone.concept.substance.name
    # ... rest of function
```

---

### B4 — `riskfw` "keine Abhängigkeiten" widerspricht "Fuzzy-Search" in `substances/lookup.py`

**Befund (Abschnitte 2.2, 3.1)**

Das ADR deklariert in Abschnitt 2.2:
> "**Abhängigkeiten:** keine (pure Python, stdlib only)"

Gleichzeitig benennt die Package-Struktur (3.1):
> `substances/lookup.py  # Alias-Auflösung, Fuzzy-Search`

Fuzzy-String-Matching in Python stdlib (`difflib`) ist funktionsfähig aber
in Produktionsqualität üblicherweise unzureichend (Levenshtein-Distanz ist
O(n²)). Wenn `rapidfuzz` oder `fuzzywuzzy` gemeint ist, ist das eine externe
Abhängigkeit und widerspricht dem "stdlib only"-Versprechen.

**Risiko:** 🟠 MAJOR — falsche Erwartungshaltung bei Nutzern, PyPI-Veröffentlichung
mit versteckten Abhängigkeiten

**Empfehlung:**

Option A (empfohlen): `difflib.SequenceMatcher` aus stdlib verwenden —
für GESTIS-Stoff-Lookup mit ~100 Einträgen vollkommen ausreichend:

```python
# substances/lookup.py — stdlib only, korrekt
import difflib

def fuzzy_lookup(name: str, threshold: float = 0.6) -> str | None:
    """Findet nächsten Stoff-Namen via stdlib difflib."""
    candidates = list(SUBSTANCE_DATABASE.keys())
    matches = difflib.get_close_matches(name.lower(), candidates, n=1, cutoff=threshold)
    return matches[0] if matches else None
```

Option B: `rapidfuzz` als explizite optionale Abhängigkeit deklarieren:

```toml
# pyproject.toml
[project.optional-dependencies]
fuzzy = ["rapidfuzz>=3.0"]
```

---

## MAJOR (sollten vor Go-Live behoben werden)

---

### M1 — Fehlende Typ-Sicherheit bei `zone_type`, `release_type`, `risk_level`

**Befund (Abschnitte 3.3, 4.2)**

Mehrere kritische Felder verwenden `str` statt typsicherer Alternativen:

```python
# AKTUELL — unsicher
zone_type: str      # "0" | "1" | "2" — dokumentiert, aber nicht erzwungen
release_type: str   # "jet" | "pool" | "diffuse"
risk_level: str     # "none" | "low" | "high"
```

Ein falsch getippter Wert (z.B. `"Zone 1"` statt `"1"`) landet
lautlos in der DB und im PDF-Nachweis.

**Risiko:** 🟠 MAJOR — Datenbankkorruption, falscher Prüfnachweis

**Empfehlung:**

```python
# riskfw/zones/models.py
from enum import StrEnum

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
    zone_type: ZoneType          # ← typsicher
    release_type: ReleaseType    # ← typsicher
    radius_m: float
    # ...

# Entsprechend in risk-hub models.py:
calculated_zone_type = models.CharField(
    max_length=5,
    choices=[(z.value, z.value) for z in ZoneType],
)
```

`StrEnum` (Python 3.11+) ist kompatibel mit `str`, d.h. Serialisierung nach
JSON/DB funktioniert ohne Änderungen.

---

### M2 — DXF-Import ohne Input-Validierung und Größenbeschränkung

**Befund (Abschnitt 4.3, `import_zones_from_dxf`)**

```python
def import_zones_from_dxf(
    concept_id: UUID,
    dxf_bytes: bytes,    # ← keine Größenprüfung, keine Validierung
    ...
) -> int:
    analyse = BrandschutzAnalyzer().analyze_dxf(ezdxf.read(io.BytesIO(dxf_bytes)))
```

Probleme:
1. Kein maximales Dateigrößen-Limit → DoS durch 100MB-DXF
2. `ezdxf.read()` kann für syntaktisch korrupte Dateien unvorhersehbare
   Exceptions werfen — diese sind nicht gefangen
3. `ezdxf` ist nicht in den deklarierten risk-hub-Abhängigkeiten genannt

**Risiko:** 🟠 MAJOR — DoS-Angriff, unbehandelte Exceptions, fehlende Abhängigkeit

**Empfehlung:**

```python
# Konstante in risk-hub/explosionsschutz/constants.py
DXF_MAX_BYTES = 50 * 1024 * 1024  # 50 MB

@transaction.atomic
def import_zones_from_dxf(
    concept_id: UUID,
    dxf_bytes: bytes,
    tenant_id: UUID,
    user_id: UUID | None = None,
) -> int:
    import io
    import ezdxf
    from ezdxf.lldxf.const import DXFError
    from nl2cad.brandschutz.analyzer import BrandschutzAnalyzer

    # Größenprüfung
    if len(dxf_bytes) > DXF_MAX_BYTES:
        raise ValueError(
            f"DXF-Datei zu groß: {len(dxf_bytes)} Bytes (max {DXF_MAX_BYTES})"
        )

    # Geparste Ausnahmen statt nackter Exception
    try:
        doc = ezdxf.read(io.BytesIO(dxf_bytes))
    except DXFError as exc:
        raise ValueError(f"Ungültige DXF-Datei: {exc}") from exc

    concept = ExplosionConcept.objects.get(id=concept_id, tenant_id=tenant_id)
    analyse = BrandschutzAnalyzer().analyze_dxf(doc)
    # ...
```

In `requirements.txt` / `pyproject.toml` (risk-hub) explizit ergänzen:
```
ezdxf>=1.1,<2.0
```

---

### M3 — Fragile Zone-Typ-Extraktion aus DXF-Layer-Namen

**Befund (Abschnitt 4.3)**

```python
# ADR-007, Zeile ~435 — FRAGIL
zone_type=ex_bereich.zone.value.replace("Zone ", ""),
```

Wenn `nl2cad-brandschutz` intern die Enum-Werte ändert (z.B. von `"Zone 1"`
zu `"EX_ZONE_1"` oder `"zone-1"`), erzeugt dieser Code lautlos falsche
Zonen-Typen in der DB — ohne Exception, ohne Fehlermeldung.

**Risiko:** 🟠 MAJOR — stiller Datenfehler, falscher Prüfnachweis

**Empfehlung:** Das ADR sollte einen stabilen Konvertierungs-Contract definieren.
Entweder exportiert `nl2cad-brandschutz` bereits den `ZoneType` als Enum, oder
der Parser wird explizit abgesichert:

```python
# In risk-hub: expliziter Mapping-Contract
_ZONE_VALUE_MAP = {
    "Zone 0": "0",
    "Zone 1": "1",
    "Zone 2": "2",
    "EX_ZONE_0": "0",  # Fallback für nl2cad-Format-Änderungen
    "EX_ZONE_1": "1",
    "EX_ZONE_2": "2",
}

def _parse_zone_type(raw_value: str) -> str:
    """Konvertiert nl2cad-Zonenwert zu riskfw-ZoneType."""
    result = _ZONE_VALUE_MAP.get(raw_value)
    if result is None:
        raise ValueError(
            f"Unbekannter Zonen-Wert aus DXF-Import: {raw_value!r}. "
            f"Erlaubt: {list(_ZONE_VALUE_MAP)}"
        )
    return result
```

---

### M4 — `basis_norm` ohne Norm-Version/Ausgabejahr

**Befund (Abschnitt 4.1, `ZoneCalculationResult`)**

```python
basis_norm = models.CharField(max_length=50, default="TRGS 721")
```

TRGS 721 wurde zuletzt 2017 überarbeitet. Wenn eine neue Ausgabe erscheint
und der Berechnungsalgorithmus in `riskfw` aktualisiert wird, kann man
**nicht mehr feststellen**, nach welcher Normausgabe eine historische
Berechnung durchgeführt wurde. Dies widerspricht BetrSichV § 14 (revisionssichere
Dokumentation).

**Risiko:** 🟠 MAJOR — Compliance-Lücke bei Betriebsprüfung

**Empfehlung:**

```python
# Im ZoneCalculationResult-Modell:
basis_norm = models.CharField(max_length=100, default="TRGS 721:2017-09")
riskfw_version = models.CharField(max_length=20)  # NEU: z.B. "0.1.0"

# Im Service:
import riskfw
calc = ZoneCalculationResult.objects.create(
    ...
    basis_norm=result.basis_norm,        # aus riskfw: "TRGS 721:2017-09"
    riskfw_version=riskfw.__version__,   # "0.1.0"
)
```

In `riskfw/constants.py` die Normversionen explizit benennen:
```python
NORM_TRGS_721 = "TRGS 721:2017-09"
NORM_TRGS_722 = "TRGS 722:2012-08"
NORM_EN_1127_1 = "EN 1127-1:2019"
```

---

### M5 — PyPI-Dependency für Produktionscode: Supply-Chain-Risiko

**Befund (Abschnitt 6, Phase 1)**

```
5. riskfw==0.1.0 nach PyPI publishen
6. riskfw in risk-hub/requirements.txt aufnehmen
```

Produktionskritische Sicherheits-Berechnungslogik (TRGS 721, ATEX) als
öffentliches PyPI-Package bereitzustellen und davon abzuhängen, schafft
ein Supply-Chain-Risiko: PyPI-Typosquatting, Account-Kompromittierung
(Account `iildehnert` muss 2FA haben), Paket-Yanking.

**Risiko:** 🟠 MAJOR — Supply-Chain-Angriff auf Sicherheitsberechnungen

**Empfehlung:**

Option A (Kurzfristig): Pinnen via SHA-Hash in `requirements.txt`:

```
riskfw==0.1.0 --hash=sha256:<hash-aus-pypi>
```

Option B (Mittelfristig, empfohlen): Private PyPI-Registry auf Hetzner:

```bash
# docker-compose für Hetzner-internen PyPI-Mirror (devpi)
services:
  devpi:
    image: muccg/devpi:latest
    volumes:
      - devpi_data:/data
    ports:
      - "3141:3141"
```

```toml
# pyproject.toml risk-hub
[tool.pip]
index-url = "https://pypi.intern.schutztat.de/simple/"
extra-index-url = "https://pypi.org/simple/"
```

Option C: Direkte Git-Dependency (akzeptabel für frühe Phasen):
```
riskfw @ git+https://github.com/iildehnert/riskfw@v0.1.0#egg=riskfw
```

---

### M6 — `post_save`-Signal für ATEX-Check undokumentiert und riskant

**Befund (Abschnitt 6, Phase 2, Punkt 4)**

> "Equipment `post_save`-Signal: ATEX-Check via `riskfw`"

Django-Signals für Business-Logik sind bekanntermaßen problematisch:
- Signals laufen auch bei Fixtures, `bulk_create`, `loaddata` — unerwünschte
  ATEX-Checks bei Datenmigration
- Fehler im Signal-Handler können ORM-Saves unerwartet fehlschlagen lassen
- Kein Tenant-Kontext automatisch verfügbar im Signal

**Risiko:** 🟠 MAJOR — unvorhergesehene Seiteneffekte bei Migrations/Loaddata

**Empfehlung:** ATEX-Check explizit im Service-Layer statt via Signal:

```python
# services.py — EXPLIZIT statt Signal
@transaction.atomic
def create_equipment(cmd: CreateEquipmentCmd, tenant_id: UUID, user_id: UUID) -> Equipment:
    equipment = Equipment.objects.create(...)
    # Expliziter ATEX-Check — kein magisches Signal-Verhalten
    atex_result = check_equipment_suitability(
        ex_marking=equipment.atex_marking,
        zone=equipment.target_zone,
    )
    EquipmentATEXCheck.objects.create(
        equipment=equipment,
        result=dataclasses.asdict(atex_result),
    )
    return equipment
```

---

### M7 — N+1-Query-Problem im kritischen Pfad

**Befund (Abschnitt 4.2)**

```python
zone = ZoneDefinition.objects.get(id=cmd.zone_id, tenant_id=tenant_id)
substance_name = zone.concept.substance.name  # 2 zusätzliche Queries
```

Jeder Aufruf von `calculate_and_store_zone()` erzeugt mindestens 3 DB-Queries
(zone + concept + substance) ohne `select_related`.

**Risiko:** 🟡 MINOR (hier) aber Signal für ein Muster das sich im gesamten
Service-Layer wiederholen wird.

**Empfehlung:**

```python
zone = ZoneDefinition.objects.select_related(
    "concept__substance"
).get(id=cmd.zone_id, tenant_id=tenant_id)
```

---

## MINOR

---

### N1 — `audit_id` in Import-Service zeigt auf falsches Entity

**Befund (Abschnitt 4.3)**

```python
emit_audit_event(
    ...
    entity_type="ZoneDefinition",
    entity_id=concept_id,    # ← Das ist die Concept-ID, NICHT die ZoneDefinition-ID!
    ...
)
```

Der Audit-Event referenziert `entity_type="ZoneDefinition"` aber
`entity_id=concept_id`. Ein Audit-Trail, der auf das falsche Objekt zeigt,
ist bei einer Betriebsprüfung wertlos.

**Empfehlung:** Entweder `entity_type="ExplosionConcept"` oder die IDs der
erstellten `ZoneDefinition`-Instanzen im Audit loggen.

---

### N2 — `IgnitionRisk` Dataclass im ADR nicht definiert, aber referenziert

**Befund (Abschnitte 3.1 und 3.3)**

In `riskfw/ignition/models.py` wird `IgnitionRisk` als Dataclass aufgelistet
(Zeile ~163), aber im Abschnitt 3.3 (Zentrale Dataclasses) nur `IgnitionAssessment`
spezifiziert. Unklar: Ist `IgnitionRisk` ein Enum (`low/high/none`) oder ein
separater Dataclass-Container?

**Empfehlung:** Im ADR explizit definieren:

```python
# Option A: StrEnum
class IgnitionRisk(StrEnum):
    NONE = "none"
    LOW = "low"
    HIGH = "high"

# Option B: Dataclass (falls mehr Kontext needed)
@dataclass
class IgnitionRisk:
    level: str          # "none" | "low" | "high"
    justification: str
    norm_clause: str    # z.B. "EN 1127-1 Abschnitt 6.1"
```

---

### N3 — Keine CHANGELOG.md-Strategie für Norm-Updates

**Befund (Abschnitt 3.1)**

Das ADR benennt `CHANGELOG.md` als Datei in `riskfw/`, definiert aber keine
Strategie für norm-getriebene Breaking Changes. Wenn TRGS 721 überarbeitet wird,
ist unklar ob das ein Major-, Minor- oder Patch-Release ist.

**Empfehlung:** Im ADR eine Versionierungsstrategie festlegen:

```
MAJOR: Norm-Ausgabe ändert sich (TRGS 721:2017 → TRGS 721:202x)
MINOR: Neue Norm-Unterstützung hinzugefügt (z.B. TRGS 753)
PATCH: Bugfix ohne normative Auswirkung
```

---

### N4 — Fehlende Precision-Spezifikation bei physikalischen Berechnungen

**Befund (Abschnitte 3.3, 4.1)**

Der Service übergibt `release_rate_kg_s: float` an `riskfw`, das Modell
speichert `DecimalField(max_digits=12, decimal_places=6)`. Floating-Point-
Berechnungen in Python können bei physikalischen Sicherheitsberechnungen
zu unerwarteten Rundungsfehlern führen.

**Empfehlung:** In `riskfw` explizit dokumentieren welche Präzision (Signifikante
Stellen) die Berechnungen liefern, und ob `Decimal` statt `float` verwendet
werden soll. Für TRGS 721 (Zonenausdehnung auf ±0.1m genau) ist `float64`
ausreichend — aber das sollte im ADR stehen.

---

### N5 — `reports/builder.py` ohne Spezifikation

**Befund (Abschnitt 3.1)**

Das Modul `riskfw/reports/builder.py` ist im Package-Baum aufgeführt und im
Public-API-Export in `3.2` referenziert (`ZoneCalculationReport`,
`IgnitionAssessmentReport`), aber nirgendwo im ADR inhaltlich spezifiziert.
Welche Felder enthalten diese Report-Dataclasses? Sind sie identisch mit den
`ZoneExtentResult`-Daten plus Metadaten?

**Empfehlung:** Report-Dataclasses im ADR spezifizieren oder explizit verweisen,
dass die Spezifikation in einem separaten ADR-008 folgt.

---

## Offene Architektur-Fragen (nicht Blocker, aber ADR sollte Position nehmen)

---

### F1 — GESTIS-Stoff-Datenbank: Statisch vs. API

**Befund (Abschnitt 8, Offene Fragen)**

Die Entscheidung ist im ADR als offen markiert. Als Reviewer empfehle ich:

**Statisch (empfohlen für v1):** GESTIS-Daten als statische Python-Datei in
`riskfw`, versioniert über `riskfw`-Releases. Begründung: Die GESTIS-API der
DGUV ist nicht SLA-gesichert für Produktionseinsatz. Statische Daten sind
offline-fähig, auditierbar, und funktionieren ohne Netzwerk-Dependency.

Pflege-Prozess:
```
# riskfw/substances/database.py — Header-Kommentar
# Quelle: GESTIS Stoffdatenbank, https://gestis.dguv.de/
# Stand: 2026-03-01 (manuell geprüft)
# Nächste Prüfung fällig: 2027-03-01
# Änderungsprotokoll: CHANGELOG.md -> "Substances"
```

### F2 — BetrSichV §§ 14-17 Prüffristen: risk-hub oder riskfw?

Die ADR-Entscheidung (BetrSichV in risk-hub, nicht riskfw) ist **korrekt**,
sollte aber explizit begründet werden: Prüffristen-Berechnung hängt von
Tenant-Daten (letzte Prüfung, Aufstellungsort) ab und hat deshalb Django-ORM-Kontext.
Reine Fristberechnung (z.B. `calculate_next_inspection_date()`) könnte
optional in riskfw landen, aber der Mehrwert ist gering.

---

## Zusammenfassung der Befunde

| ID | Typ | Bereich | Befund | Risiko |
|---|---|---|---|---|
| B1 | 🔴 BLOCKER | risk-hub Model | CASCADE-FK bricht Compliance-Invariante | BetrSichV-Verletzung |
| B2 | 🔴 BLOCKER | risk-hub Service | `vars()` statt `dataclasses.asdict()` | Korrupte Archivdaten |
| B3 | 🔴 BLOCKER | risk-hub Service | Kein Null-Check für `concept.substance` | Unbehandelte Exceptions |
| B4 | 🔴 BLOCKER | riskfw Package | "stdlib only" ≠ "Fuzzy-Search" | Falsche Abhängigkeitserklärung |
| M1 | 🟠 MAJOR | riskfw Dataclasses | `str` statt `StrEnum` für kritische Werte | Stille Datenfehler |
| M2 | 🟠 MAJOR | risk-hub Service | DXF ohne Size-Limit und Exception-Handling | DoS-Angriff möglich |
| M3 | 🟠 MAJOR | risk-hub Service | Fragiles `str.replace()` für Zone-Typ-Mapping | Stille Datenfehler |
| M4 | 🟠 MAJOR | risk-hub Model | `basis_norm` ohne Norm-Ausgabejahr | Compliance-Lücke |
| M5 | 🟠 MAJOR | Deployment | PyPI-Dependency Supply-Chain-Risiko | Sicherheitsrisiko |
| M6 | 🟠 MAJOR | risk-hub Architektur | `post_save`-Signal für Business-Logik | Seiteneffekte bei Migration |
| M7 | 🟠 MAJOR | risk-hub Service | N+1 im Berechnungspfad | Performance |
| N1 | 🟡 MINOR | Audit | Falsches Entity in Audit-Log | Audit-Qualität |
| N2 | 🟡 MINOR | riskfw Spec | `IgnitionRisk` undefiniert | Implementierungsambiguität |
| N3 | 🟡 MINOR | riskfw Prozess | Keine Norm-Update-Versionsstrategie | Prozessrisiko |
| N4 | 🟡 MINOR | riskfw Spec | Precision-Anforderungen nicht spezifiziert | Berechnungsqualität |
| N5 | 🟡 MINOR | riskfw Spec | `reports/builder.py` unspezifiziert | Implementierungsambiguität |

---

## Positiv-Befunde (zur Dokumentation)

- ✅ Architekturentscheidung (Option C: `riskfw`) ist fachlich korrekt und begründet
- ✅ Schichten-Diagramm (Abschnitt 2.1) ist klar und korrekt
- ✅ `@transaction.atomic` konsequent verwendet
- ✅ Tenant-Isolation in allen Services (`tenant_id=tenant_id` in `.get()`)
- ✅ `default_permissions = ("add", "view")` für unveränderliches Modell — guter Ansatz
- ✅ `raw_result = models.JSONField()` für vollständige Ergebnis-Archivierung — korrekt
- ✅ `select_related` wird in Services nicht vergessen (wenn ergänzt)
- ✅ Normbezüge in Abschnitt 9 vollständig und korrekt zugeordnet
- ✅ Migrationspfad in 3 Phasen ist realistisch und klein-schrittig
- ✅ Abhängigkeitsmatrix (Abschnitt 5) mit expliziten Verboten — Best Practice

---

*Review erstellt: 2026-03-03 | Status: Zur Überarbeitung durch ADR-Autor*
