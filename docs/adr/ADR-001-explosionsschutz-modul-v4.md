# ADR-001: Explosionsschutz-Modul für Risk-Hub

| Metadaten | |
| --------- | --- |
| **Status** | ✅ APPROVED |
| **Version** | 4.0 |
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

---

## 1. Review-Feedback Integration (v4)

### 1.1 Umgesetzte Optimierungen

| Bereich | Review-Kritik | Umsetzung v4 |
| ------- | ------------- | ------------ |
| **SoC** | Redundante Substance-Daten | Nur FK zu `substances.Substance`, `@property` für SDS-Daten |
| **Equipment** | Nicht normalisiert | `EquipmentType` als Stammdatenkatalog |
| **ATEX** | `atex_marking` Freitext | Strukturierte Felder: `atex_category`, `temperature_class`, `protection_type` |
| **Measures** | `measure_type` gemischt | `SafetyFunction` als separate Entität für MSR |
| **Zones** | `trgs_reference` Freitext | `ReferenceStandard` Tabelle |
| **Naming** | `is_atex_certified` redundant | Entfernt (ableitbar aus Kategorie) |
| **Dynamik** | `has_explosion_hazard` DB-Feld | `@property` mit dynamischer Prüfung |

### 1.2 Neue Entitäten

```text
┌─────────────────────────────────────────────────────────────────────┐
│                    NEUE STAMMDATEN-ENTITÄTEN                        │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  ┌─────────────────┐   ┌─────────────────┐   ┌─────────────────┐   │
│  │ReferenceStandard│   │  MeasureCatalog │   │ SafetyFunction  │   │
│  │                 │   │                 │   │                 │   │
│  │ code (TRGS 720) │   │ title           │   │ name            │   │
│  │ title           │   │ default_type    │   │ performance_lvl │   │
│  │ category        │   │ description_tpl │   │ sil_level       │   │
│  │ url             │   │ is_global       │   │ monitoring_meth │   │
│  └─────────────────┘   └─────────────────┘   └─────────────────┘   │
│                                                                     │
│  ┌─────────────────┐   ┌─────────────────┐                         │
│  │  EquipmentType  │   │VerificationDoc  │                         │
│  │                 │   │                 │                         │
│  │ manufacturer    │   │ title           │                         │
│  │ model           │   │ document_type   │                         │
│  │ atex_category   │   │ file            │                         │
│  │ temperature_cls │   │ issued_at       │                         │
│  │ protection_type │   │ valid_until     │                         │
│  └─────────────────┘   └─────────────────┘                         │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 2. Optimiertes Datenmodell (ERD v4)

### 2.1 Vollständiges Entity-Relationship-Diagramm

```text
┌─────────────────────────────────────────────────────────────────────────────────┐
│                           EXPLOSIONSSCHUTZ ERD v4                               │
├─────────────────────────────────────────────────────────────────────────────────┤
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
│  ┌──────────────────────────────────────────────────────────────────────┐       │
│  │                      ExplosionConcept                                │       │
│  │  ┌─────────────────────────────────────────────────────────────┐    │       │
│  │  │ • area (FK)                                                  │    │       │
│  │  │ • substance (FK → substances.Substance)                      │    │       │
│  │  │ • assessment_id (optional FK → risk.Assessment)              │    │       │
│  │  │ • title, version, status                                     │    │       │
│  │  │ • is_validated, validated_by, validated_at                   │    │       │
│  │  │                                                              │    │       │
│  │  │ @property sds_data → H-Sätze, Piktogramme, CAS, etc.        │    │       │
│  │  │ @property completion_percentage                              │    │       │
│  │  └─────────────────────────────────────────────────────────────┘    │       │
│  └──────────────────────────────────────────────────────────────────────┘       │
│         │                                                                       │
│         ├─────────────────┬─────────────────┬─────────────────┐                 │
│         │ 1:N             │ 1:N             │ 1:N             │ 1:N             │
│         ▼                 ▼                 ▼                 ▼                 │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐         │
│  │ZoneDefinition│  │ Protection   │  │Verification  │  │  Equipment   │         │
│  │              │  │   Measure    │  │  Document    │  │              │         │
│  │ zone_type    │  │              │  │              │  │ equipment_   │         │
│  │ extent(JSON) │  │ category     │  │ document_type│  │ type (FK)    │         │
│  │ reference_   │  │ safety_      │  │ file         │  │ zone (FK)    │         │
│  │ standard(FK) │  │ function(FK) │  │ issued_at    │  │ serial_no    │         │
│  └──────────────┘  │ status       │  └──────────────┘  │ next_insp    │         │
│         │          │ catalog_     │                    └──────┬───────┘         │
│         │          │ reference(FK)│                           │ 1:N             │
│         │          └──────────────┘                           ▼                 │
│         │                 │                            ┌──────────────┐         │
│         │                 │                            │  Inspection  │         │
│         │                 ▼                            │              │         │
│         │          ┌──────────────┐                    │ type         │         │
│         │          │SafetyFunction│                    │ result       │         │
│         │          │              │                    │ inspector    │         │
│         │          │ perf_level   │                    │ certificate  │         │
│         │          │ sil_level    │                    └──────────────┘         │
│         │          │ monitoring   │                                             │
│         │          └──────────────┘                                             │
│         │                                                                       │
│         ▼                                                                       │
│  ┌──────────────┐                                                               │
│  │Reference     │                                                               │
│  │Standard      │                                                               │
│  │              │                                                               │
│  │ code         │  (TRGS 720, IEC 60079-10-1, etc.)                            │
│  │ title        │                                                               │
│  │ url          │                                                               │
│  └──────────────┘                                                               │
│                                                                                 │
│  ┌──────────────┐   ┌──────────────┐                                           │
│  │EquipmentType │   │MeasureCatalog│                                           │
│  │              │   │              │                                           │
│  │ manufacturer │   │ title        │  (Stammdaten - wiederverwendbar)          │
│  │ model        │   │ default_type │                                           │
│  │ atex_category│   │ description  │                                           │
│  │ temp_class   │   │ is_global    │                                           │
│  │ protection   │   └──────────────┘                                           │
│  │ ip_rating    │                                                               │
│  └──────────────┘                                                               │
│                                                                                 │
└─────────────────────────────────────────────────────────────────────────────────┘
```

### 2.2 Model-Übersicht

| Model | Beschreibung | Beziehungen |
| ----- | ------------ | ----------- |
| `ReferenceStandard` | TRGS, IEC, EN Regelwerke | → ZoneDefinition |
| `MeasureCatalog` | Maßnahmen-Vorlagen | → ProtectionMeasure |
| `SafetyFunction` | MSR-Bewertung (PLr/SIL) | → ProtectionMeasure |
| `Area` | Betriebsbereich | Site → Area → ExplosionConcept |
| `ExplosionConcept` | Ex-Konzept | → Substance, → Assessment |
| `ZoneDefinition` | ATEX-Zone | Concept → Zone |
| `ProtectionMeasure` | Schutzmaßnahme | → SafetyFunction, → MeasureCatalog |
| `EquipmentType` | Geräte-Stammdaten | → Equipment |
| `Equipment` | Konkretes Betriebsmittel | → Zone, → EquipmentType |
| `Inspection` | Prüfung nach BetrSichV | Equipment → Inspection |
| `VerificationDocument` | Nachweisdokumente | Concept → Documents |

---

## 3. Strukturierte ATEX-Kennzeichnung

### 3.1 Vorher (v3) vs. Nachher (v4)

```python
# v3 - Freitext (problematisch)
class Equipment(models.Model):
    atex_marking = models.CharField(max_length=100)  # "II 2G Ex d IIB T4"

# v4 - Strukturiert (normalisiert)
class EquipmentType(models.Model):
    atex_group = models.CharField(max_length=10)      # "II"
    atex_category = models.CharField(max_length=10)   # "2G"
    protection_type = models.CharField(max_length=50) # "Ex d"
    explosion_group = models.CharField(max_length=10) # "IIB"
    temperature_class = models.CharField(max_length=10) # "T4"
    ip_rating = models.CharField(max_length=10)       # "IP65"
    
    @property
    def full_atex_marking(self) -> str:
        """Vollständige ATEX-Kennzeichnung aus Einzelfeldern"""
        return f"{self.atex_group} {self.atex_category} {self.protection_type} ..."
```

### 3.2 Vorteile der Strukturierung

| Aspekt | Freitext | Strukturiert |
| ------ | -------- | ------------ |
| Validierung | ❌ Keine | ✅ Enum-basiert |
| Suche/Filter | ❌ Schwierig | ✅ Einfach per FK |
| Zonenzuordnung | ❌ Manuell | ✅ Automatisch |
| Reporting | ❌ Parsing nötig | ✅ Direkt nutzbar |

---

## 4. SafetyFunction für MSR-Bewertung

### 4.1 Entkopplung

```text
┌─────────────────────────────────────────────────────────────────┐
│                    MEASURE ARCHITECTURE v4                      │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  Einfache Maßnahme:                                            │
│  ┌────────────────────────────────────────────────────────┐    │
│  │ ProtectionMeasure                                      │    │
│  │   category: "secondary"                                │    │
│  │   title: "Erdung aller leitfähigen Teile"             │    │
│  │   safety_function: NULL                                │    │
│  └────────────────────────────────────────────────────────┘    │
│                                                                 │
│  MSR-Sicherheitsfunktion:                                      │
│  ┌────────────────────────────────────────────────────────┐    │
│  │ ProtectionMeasure                                      │    │
│  │   category: "secondary"                                │    │
│  │   title: "Gaswarnanlage mit Abschaltung"              │    │
│  │   safety_function: ──────────────────────────────────► │    │
│  └────────────────────────────────────────────────────────┘    │
│                               │                                 │
│                               ▼                                 │
│                    ┌──────────────────────┐                    │
│                    │   SafetyFunction     │                    │
│                    │                      │                    │
│                    │   name: "GW-001"     │                    │
│                    │   perf_level: "d"    │                    │
│                    │   sil_level: "2"     │                    │
│                    │   monitoring: "cont" │                    │
│                    └──────────────────────┘                    │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## 5. Integration mit Substances-Modul

### 5.1 Keine Redundanz - Nur FK

```python
class ExplosionConcept(models.Model):
    # NICHT: substance_name, formula, ignition_temp (Redundanz!)
    # SONDERN:
    substance = models.ForeignKey(
        "substances.Substance",
        on_delete=models.PROTECT
    )
    
    @property
    def sds_data(self) -> dict:
        """Ex-relevante Daten aus aktuellem SDS (read-only)"""
        sds = self.substance.current_sds
        if not sds:
            return {}
        return {
            "substance_name": self.substance.name,
            "cas_number": self.substance.cas_number,
            "h_statements": [h.code for h in sds.hazard_statements.all()],
            "pictograms": [p.code for p in sds.pictograms.all()],
            # ... weitere SDS-Daten
        }
```

### 5.2 Dynamische Ex-Gefährdungsprüfung

```python
class Area(models.Model):
    # NICHT: has_explosion_hazard = models.BooleanField()
    # SONDERN:
    
    @property
    def has_explosion_hazard(self) -> bool:
        """Dynamisch: Prüft ob Ex-relevante Stoffe im Bereich"""
        EXPLOSIVE_H_CODES = {"H220", "H221", "H222", "H223", "H224", "H225", "H226"}
        
        inventory = SiteInventoryItem.objects.filter(
            site_id=self.site_id,
            storage_area=self.code
        )
        
        for item in inventory:
            sds = item.substance.current_sds
            if sds:
                h_codes = set(h.code for h in sds.hazard_statements.all())
                if h_codes & EXPLOSIVE_H_CODES:
                    return True
        return False
```

---

## 6. Implementierungsplan (aktualisiert)

### Voraussetzung: substances-Modul (SDS)

> **WICHTIG:** Das `explosionsschutz`-Modul setzt das `substances`-Modul voraus.

```text
Phase 0: SDS-Modul Basis (Sprint 1-4)
├── Substance + Party + Identifier Models
├── SdsRevision + Classification Models
├── H-/P-Sätze + Piktogramme
├── SiteInventoryItem
└── Referenztabellen (H-/P-Satz-Texte)

Phase 1: Ex-Stammdaten (Sprint 5)
├── ReferenceStandard Model + Fixtures (TRGS 720-725)
├── MeasureCatalog Model + Default-Vorlagen
├── SafetyFunction Model
├── EquipmentType Model
└── Admin Interfaces

Phase 2: Ex-Core Models (Sprint 6-7)
├── Area Model + @property has_explosion_hazard
├── ExplosionConcept Model + Substance-FK
├── ZoneDefinition Model + ReferenceStandard-FK
├── ProtectionMeasure Model + SafetyFunction-FK
├── Signal: SiteInventoryItem → Ex-Review-Trigger
└── Unit Tests

Phase 3: Equipment & Inspections (Sprint 8-9)
├── Equipment Model + EquipmentType-FK
├── Inspection Model + Prüfprotokoll
├── VerificationDocument Model
├── Prüffristenlogik (auto next_inspection)
├── Benachrichtigungsservice (Outbox)
└── Unit Tests

Phase 4: UI/UX (Sprint 10-12)
├── Concept CRUD Views
├── Substance-Selector (aus SDS-Modul)
├── Zone Editor (HTMX)
├── Measure Management (HTMX)
├── Equipment Views mit Zonen-Zuordnungsvalidierung
├── SDS-Daten-Anzeige (read-only)
└── E2E Tests (Playwright)

Phase 5: PDF & Integration (Sprint 13)
├── PDF Template Explosionsschutzdokument
├── WeasyPrint Integration
├── Assessment-Verknüpfung
├── SDS-Daten im PDF (H-Sätze, Piktogramme)
└── API Documentation

Phase 6: QA & Release (Sprint 14-15)
├── Security Review
├── Performance Tests
├── User Documentation
└── Production Deployment
```

---

## 7. Konsequenzen

### 7.1 Positive Konsequenzen

| # | Konsequenz | Nutzen |
| --- | ---------- | ------ |
| 1 | Normalisierte ATEX-Daten | Validierung, Filterung, Reporting |
| 2 | Entkoppelte MSR-Bewertung | Klare Trennung einfach vs. komplex |
| 3 | Dynamische Ex-Prüfung | Immer aktuell, keine Inkonsistenzen |
| 4 | Stammdatenkataloge | Wiederverwendbarkeit, Konsistenz |
| 5 | SDS-Integration ohne Redundanz | Single Source of Truth |

### 7.2 Negative Konsequenzen

| # | Konsequenz | Mitigation |
| --- | ---------- | ---------- |
| 1 | Komplexeres Schema (+4 Models) | Saubere Dokumentation, ERD |
| 2 | Mehr JOINs für Abfragen | Indexierung, select_related() |
| 3 | SDS-Modul als Voraussetzung | Klare Dependency-Dokumentation |

---

## 8. Referenzen

| Dokument | Link |
| -------- | ---- |
| ATEX 114 Richtlinie | [EUR-Lex](https://eur-lex.europa.eu/legal-content/DE/TXT/?uri=CELEX:32014L0034) |
| TRGS 720-725 | [BAuA](https://www.baua.de/DE/Angebote/Regelwerk/TRGS/TRGS.html) |
| BetrSichV | [Gesetze im Internet](https://www.gesetze-im-internet.de/betrsichv_2015/) |
| IEC 60079-10-1 | [IEC Webstore](https://webstore.iec.ch/publication/63327) |
| Schutzbar SDS Konzept | [Schutzbar_SDS_Implementierungskonzept.md](../concepts/Schutzbar_SDS_Implementierungskonzept.md) |
| models.py | [src/explosionsschutz/models.py](../../src/explosionsschutz/models.py) |

---

## 9. Änderungshistorie

| Version | Datum | Autor | Änderung |
| ------- | ----- | ----- | -------- |
| 1.0 | 2026-01-31 | Cascade | Initial Draft |
| 2.0 | 2026-01-31 | Cascade | Review-Ready Version |
| 3.0 | 2026-01-31 | Cascade | SDS-Integration |
| 4.0 | 2026-01-31 | Cascade | **Review-Feedback** - Normalisierung, SoC, strukturierte ATEX |

---

## 10. Approval

| Rolle | Name | Datum | Signatur |
| ----- | ---- | ----- | -------- |
| Autor | Achim Dehnert | 2026-01-31 | ✅ |
| Technical Review | AI Review | 2026-01-31 | ✅ |
| Architecture | _ausstehend_ | | |

**Nächster Schritt:** Phase 0 (SDS-Modul) parallel starten, dann Phase 1 (Stammdaten)
