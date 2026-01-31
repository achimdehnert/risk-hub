# Explosionsschutz-Modul: Entity-Relationship-Diagramm (v5)

> **Version:** 5.0  
> **Datum:** 2026-01-31  
> **Basis:** ADR-001 v5 (Enterprise Edition)

---

## 1. Übersicht

```text
┌─────────────────────────────────────────────────────────────────────────────────┐
│                           EXPLOSIONSSCHUTZ ERD v5                               │
│                                                                                 │
│   ┌──────────────────────────────────────────────────────────────────────────┐  │
│   │                        EXTERNE MODULE                                    │  │
│   │  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐   │  │
│   │  │ tenancy  │  │ identity │  │substances│  │   risk   │  │documents │   │  │
│   │  │          │  │          │  │          │  │          │  │          │   │  │
│   │  │ Org/Site │  │   User   │  │Substance │  │Assessment│  │ Document │   │  │
│   │  └────┬─────┘  └────┬─────┘  └────┬─────┘  └────┬─────┘  └────┬─────┘   │  │
│   │       │             │             │             │             │         │  │
│   └───────┼─────────────┼─────────────┼─────────────┼─────────────┼─────────┘  │
│           │             │             │             │             │            │
│   ┌───────┼─────────────┼─────────────┼─────────────┼─────────────┼─────────┐  │
│   │       ▼             ▼             ▼             ▼             ▼         │  │
│   │                   EXPLOSIONSSCHUTZ MODULE                               │  │
│   │                                                                         │  │
│   │  ┌─────────────────────────────────────────────────────────────────┐   │  │
│   │  │                    STAMMDATEN (Reference)                       │   │  │
│   │  │                                                                 │   │  │
│   │  │  ┌────────────────┐  ┌────────────────┐  ┌────────────────┐    │   │  │
│   │  │  │ReferenceStandard│  │ MeasureCatalog │  │ EquipmentType  │    │   │  │
│   │  │  │                │  │                │  │                │    │   │  │
│   │  │  │ • code         │  │ • title        │  │ • manufacturer │    │   │  │
│   │  │  │ • title        │  │ • default_type │  │ • model        │    │   │  │
│   │  │  │ • category     │  │ • description  │  │ • atex_category│    │   │  │
│   │  │  │ • url          │  │ • is_global    │  │ • temp_class   │    │   │  │
│   │  │  └────────────────┘  └────────────────┘  │ • protection   │    │   │  │
│   │  │                                          │ • ip_rating    │    │   │  │
│   │  │  ┌────────────────┐                      └────────────────┘    │   │  │
│   │  │  │ SafetyFunction │                                            │   │  │
│   │  │  │                │                                            │   │  │
│   │  │  │ • name         │                                            │   │  │
│   │  │  │ • perf_level   │                                            │   │  │
│   │  │  │ • sil_level    │                                            │   │  │
│   │  │  │ • monitoring   │                                            │   │  │
│   │  │  └────────────────┘                                            │   │  │
│   │  └─────────────────────────────────────────────────────────────────┘   │  │
│   │                                                                         │  │
│   │  ┌─────────────────────────────────────────────────────────────────┐   │  │
│   │  │                    CORE ENTITIES                                │   │  │
│   │  │                                                                 │   │  │
│   │  │              ┌────────────────┐                                 │   │  │
│   │  │              │      Area      │                                 │   │  │
│   │  │              │                │                                 │   │  │
│   │  │              │ • site_id (FK) │                                 │   │  │
│   │  │              │ • name, code   │                                 │   │  │
│   │  │              │ • @has_ex_haz  │                                 │   │  │
│   │  │              └───────┬────────┘                                 │   │  │
│   │  │                      │ 1:N                                      │   │  │
│   │  │                      ▼                                          │   │  │
│   │  │  ┌───────────────────────────────────────────────────────────┐  │   │  │
│   │  │  │                  ExplosionConcept                         │  │   │  │
│   │  │  │                                                           │  │   │  │
│   │  │  │  • area (FK)           • substance (FK → substances)      │  │   │  │
│   │  │  │  • assessment_id       • title, version, status           │  │   │  │
│   │  │  │  • is_validated        • validated_by, validated_at       │  │   │  │
│   │  │  │                                                           │  │   │  │
│   │  │  │  @property sds_data    @property completion_percentage    │  │   │  │
│   │  │  └───────────────────────────────────────────────────────────┘  │   │  │
│   │  │              │           │           │           │              │   │  │
│   │  │              │ 1:N       │ 1:N       │ 1:N       │ 1:N         │   │  │
│   │  │              ▼           ▼           ▼           ▼              │   │  │
│   │  │  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐ ┌────────┐  │   │  │
│   │  │  │ZoneDefinition│ │Protection    │ │Verification  │ │Equipm. │  │   │  │
│   │  │  │              │ │Measure       │ │Document      │ │        │  │   │  │
│   │  │  │ • zone_type  │ │              │ │              │ │ • type │  │   │  │
│   │  │  │ • extent     │ │ • category   │ │ • doc_type   │ │ • zone │  │   │  │
│   │  │  │ • ref_std FK │ │ • safety_fn  │ │ • file       │ │ • serial│  │   │  │
│   │  │  └──────────────┘ │ • catalog FK │ │ • issued_at  │ └───┬────┘  │   │  │
│   │  │                   │ • status     │ └──────────────┘     │ 1:N   │   │  │
│   │  │                   └──────────────┘                      ▼       │   │  │
│   │  │                                                   ┌──────────┐  │   │  │
│   │  │                                                   │Inspection│  │   │  │
│   │  │                                                   │          │  │   │  │
│   │  │                                                   │ • type   │  │   │  │
│   │  │                                                   │ • result │  │   │  │
│   │  │                                                   │ • date   │  │   │  │
│   │  │                                                   └──────────┘  │   │  │
│   │  └─────────────────────────────────────────────────────────────────┘   │  │
│   └─────────────────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────────────────┘
```

---

## 2. Detaillierte Beziehungen

### 2.1 Hierarchie

```text
Organization (tenancy)
    │
    └──► Site (tenancy)
            │
            └──► Area (explosionsschutz)
                    │
                    ├──► ExplosionConcept ──► Substance (substances)
                    │         │
                    │         ├──► ZoneDefinition ──► ReferenceStandard
                    │         │
                    │         ├──► ProtectionMeasure ──► SafetyFunction
                    │         │                     └──► MeasureCatalog
                    │         │
                    │         └──► VerificationDocument
                    │
                    └──► Equipment ──► EquipmentType
                            │
                            └──► Inspection
```

### 2.2 Kardinalitäten

| Von | Zu | Kardinalität | Beschreibung |
| --- | -- | ------------ | ------------ |
| Site | Area | 1:N | Ein Standort hat mehrere Bereiche |
| Area | ExplosionConcept | 1:N | Ein Bereich kann mehrere Konzepte haben (Versionen) |
| ExplosionConcept | Substance | N:1 | Jedes Konzept bezieht sich auf einen Stoff |
| ExplosionConcept | ZoneDefinition | 1:N | Ein Konzept definiert mehrere Zonen |
| ExplosionConcept | ProtectionMeasure | 1:N | Ein Konzept hat mehrere Maßnahmen |
| ExplosionConcept | VerificationDocument | 1:N | Mehrere Nachweisdokumente |
| ZoneDefinition | ReferenceStandard | N:1 | Zone referenziert ein Regelwerk |
| ProtectionMeasure | SafetyFunction | N:1 | Maßnahme kann Sicherheitsfunktion haben |
| ProtectionMeasure | MeasureCatalog | N:1 | Maßnahme kann aus Katalog stammen |
| Area | Equipment | 1:N | Bereich enthält Betriebsmittel |
| Equipment | EquipmentType | N:1 | Gerät hat einen Typ |
| Equipment | ZoneDefinition | N:1 | Gerät ist einer Zone zugeordnet |
| Equipment | Inspection | 1:N | Gerät hat mehrere Prüfungen |

---

## 3. Tabellen-Übersicht

### 3.1 Stammdaten (tenant-übergreifend möglich)

| Tabelle | PK | Wichtige Felder | Tenant |
| ------- | -- | --------------- | ------ |
| `ex_reference_standard` | UUID | code, title, category, url | Optional |
| `ex_measure_catalog` | UUID | title, default_type, is_global | Optional |
| `ex_safety_function` | UUID | name, perf_level, sil_level | Ja |
| `ex_equipment_type` | UUID | manufacturer, model, atex_* | Optional |

### 3.2 Core Entities (tenant-gebunden)

| Tabelle | PK | Wichtige FKs | Tenant |
| ------- | -- | ------------ | ------ |
| `ex_area` | UUID | site_id | Ja |
| `ex_concept` | UUID | area, substance, assessment_id | Ja |
| `ex_zone_definition` | UUID | concept, reference_standard | Ja |
| `ex_protection_measure` | UUID | concept, safety_function, catalog | Ja |
| `ex_verification_document` | UUID | concept | Ja |
| `ex_equipment` | UUID | equipment_type, area, zone | Ja |
| `ex_inspection` | UUID | equipment | Ja |

---

## 4. Indizes

```sql
-- Performance-relevante Indizes

-- Area
CREATE INDEX ix_area_tenant_site ON ex_area (tenant_id, site_id);

-- ExplosionConcept
CREATE INDEX ix_concept_tenant_status ON ex_concept (tenant_id, status);
CREATE INDEX ix_concept_substance ON ex_concept (substance_id);

-- Equipment
CREATE INDEX ix_equipment_tenant_next_insp ON ex_equipment (tenant_id, next_inspection_date);
CREATE INDEX ix_equipment_zone ON ex_equipment (zone_id);

-- Inspection
CREATE INDEX ix_inspection_equipment ON ex_inspection (equipment_id);
CREATE INDEX ix_inspection_date ON ex_inspection (inspection_date DESC);
```

---

## 5. Constraints

```sql
-- Unique Constraints
ALTER TABLE ex_area ADD CONSTRAINT uq_area_code_per_site 
    UNIQUE (tenant_id, site_id, code) WHERE code != '';

ALTER TABLE ex_equipment_type ADD CONSTRAINT uq_equipment_type_mfr_model 
    UNIQUE (manufacturer, model);

-- Check Constraints
ALTER TABLE ex_concept ADD CONSTRAINT ck_concept_status_valid 
    CHECK (status IN ('draft', 'in_review', 'approved', 'archived'));

ALTER TABLE ex_zone_definition ADD CONSTRAINT ck_zone_type_valid 
    CHECK (zone_type IN ('0', '1', '2', '20', '21', '22', 'non_ex'));

ALTER TABLE ex_inspection ADD CONSTRAINT ck_inspection_result_valid 
    CHECK (result IN ('passed', 'passed_notes', 'failed', 'pending'));
```

---

## 6. Externe Abhängigkeiten

```text
┌─────────────────────────────────────────────────────────────────┐
│                    MODULE DEPENDENCIES                          │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  explosionsschutz                                               │
│       │                                                         │
│       ├───────► substances.Substance (REQUIRED)                │
│       │              └── substances.SdsRevision                │
│       │              └── substances.SdsHazardStatement         │
│       │                                                         │
│       ├───────► tenancy.Site (REQUIRED)                        │
│       │              └── tenancy.Organization                  │
│       │                                                         │
│       ├───────► identity.User (REQUIRED)                       │
│       │                                                         │
│       ├───────► risk.Assessment (OPTIONAL)                     │
│       │                                                         │
│       ├───────► documents.Document (OPTIONAL)                  │
│       │                                                         │
│       └───────► audit.AuditEvent (RECOMMENDED)                 │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## 7. Migrations-Reihenfolge

```text
1. 0001_reference_data.py
   - ReferenceStandard
   - MeasureCatalog

2. 0002_safety_function.py
   - SafetyFunction

3. 0003_equipment_type.py
   - EquipmentType

4. 0004_area.py
   - Area

5. 0005_concept.py
   - ExplosionConcept

6. 0006_zones_measures.py
   - ZoneDefinition
   - ProtectionMeasure

7. 0007_verification.py
   - VerificationDocument

8. 0008_equipment.py
   - Equipment

9. 0009_inspection.py
   - Inspection

10. 0010_fixtures.py
    - ReferenceStandard (TRGS 720-725, IEC 60079)
    - MeasureCatalog (Default-Vorlagen)
```
