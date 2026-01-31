# Explosionsschutz-Modul: Migrations-Dokumentation

| Version | Datum      | Autor       | Status     |
|---------|------------|-------------|------------|
| 5.0     | 2026-01-31 | System      | Draft      |

## Übersicht

Dieses Dokument beschreibt die Django-Migrationen für das Explosionsschutz-Modul
basierend auf ADR-001 v5.

## Voraussetzungen

### 1. Abhängige Module

Die folgenden Module müssen **vor** dem Explosionsschutz-Modul migriert werden:

| Modul | Tabellen | Beschreibung |
|-------|----------|--------------|
| `tenancy` | `tenancy_organization`, `tenancy_site` | Multi-Tenancy Basis |
| `identity` | `identity_user` | Benutzer für Audit-Trail |
| `substances` | `substances_substance` | Stoffdatenbank |
| `risk` | `risk_assessment` | Gefährdungsbeurteilungen |
| `documents` | `documents_document` | Dokumentenmanagement |
| `audit` | `audit_audit_event` | Audit-Trail (optional) |
| `outbox` | `outbox_outbox_message` | Event-Outbox (optional) |

### 2. PostgreSQL-Erweiterungen

```sql
-- UUID-Unterstützung (falls nicht vorhanden)
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
```

## Migrations-Reihenfolge

### Phase 1: Stammdaten-Tabellen

```bash
# Migration erstellen
python manage.py makemigrations explosionsschutz --name 0001_initial_masterdata

# Enthält:
# - ex_reference_standard
# - ex_measure_catalog
# - ex_safety_function
# - ex_equipment_type
```

**Tabellen:**

```sql
-- 1. Regelwerksreferenzen
CREATE TABLE ex_reference_standard (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID NULL,  -- NULL = global
    code VARCHAR(50) NOT NULL,
    title VARCHAR(255) NOT NULL,
    category VARCHAR(20) NOT NULL,
    url VARCHAR(500),
    valid_from DATE,
    valid_until DATE,
    is_system BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE UNIQUE INDEX uq_refstd_tenant_code 
ON ex_reference_standard (COALESCE(tenant_id, '00000000-0000-0000-0000-000000000000'), code);

-- 2. Maßnahmenkatalog
CREATE TABLE ex_measure_catalog (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID NULL,
    code VARCHAR(50) NOT NULL,
    title VARCHAR(255) NOT NULL,
    description TEXT,
    default_type VARCHAR(20) NOT NULL,
    is_system BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 3. MSR-Sicherheitsfunktionen
CREATE TABLE ex_safety_function (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID NULL,
    name VARCHAR(200) NOT NULL,
    description TEXT,
    performance_level VARCHAR(5),
    sil_level VARCHAR(5),
    monitoring_method VARCHAR(50),
    test_interval_months INTEGER,
    is_system BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 4. Betriebsmitteltypen
CREATE TABLE ex_equipment_type (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID NULL,
    manufacturer VARCHAR(200) NOT NULL,
    model VARCHAR(200) NOT NULL,
    description TEXT,
    atex_group VARCHAR(5) DEFAULT 'II',
    atex_category VARCHAR(5),
    protection_type VARCHAR(20),
    explosion_group VARCHAR(10),
    temperature_class VARCHAR(5),
    epl VARCHAR(5),
    ip_rating VARCHAR(10),
    ambient_temp_min DECIMAL(5,1),
    ambient_temp_max DECIMAL(5,1),
    default_inspection_interval_months INTEGER DEFAULT 12,
    datasheet_url VARCHAR(500),
    certificate_number VARCHAR(100),
    notified_body VARCHAR(200),
    is_system BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE UNIQUE INDEX uq_eqtype_tenant_mfr_model 
ON ex_equipment_type (COALESCE(tenant_id, '00000000-0000-0000-0000-000000000000'), manufacturer, model);
```

### Phase 2: Core-Tabellen

```bash
python manage.py makemigrations explosionsschutz --name 0002_core_entities

# Enthält:
# - ex_area
# - ex_concept
# - ex_zone_definition
# - ex_protection_measure
```

**Tabellen:**

```sql
-- 5. Betriebsbereiche
CREATE TABLE ex_area (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID NOT NULL,
    site_id UUID,  -- FK zu tenancy_site
    code VARCHAR(50) NOT NULL,
    name VARCHAR(200) NOT NULL,
    description TEXT,
    has_explosion_hazard BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    CONSTRAINT uq_area_tenant_code UNIQUE (tenant_id, code)
);

CREATE INDEX ix_area_tenant_site ON ex_area (tenant_id, site_id);

-- 6. Explosionsschutzkonzepte
CREATE TABLE ex_concept (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID NOT NULL,
    area_id UUID NOT NULL REFERENCES ex_area(id),
    substance_id UUID NOT NULL,  -- FK zu substances_substance
    assessment_id UUID,  -- FK zu risk_assessment
    title VARCHAR(255) NOT NULL,
    version INTEGER NOT NULL DEFAULT 1,
    status VARCHAR(20) NOT NULL DEFAULT 'draft',
    is_validated BOOLEAN DEFAULT FALSE,
    validated_by_id UUID,
    validated_at TIMESTAMP WITH TIME ZONE,
    created_by_id UUID,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    CONSTRAINT uq_concept_tenant_area_version UNIQUE (tenant_id, area_id, version)
);

CREATE INDEX ix_concept_tenant_status ON ex_concept (tenant_id, status);

-- 7. Zonendefinitionen
CREATE TABLE ex_zone_definition (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID NOT NULL,
    concept_id UUID NOT NULL REFERENCES ex_concept(id) ON DELETE CASCADE,
    zone_type VARCHAR(10) NOT NULL,
    name VARCHAR(200) NOT NULL,
    extent JSONB,
    extent_horizontal_m DECIMAL(6,2),
    extent_vertical_m DECIMAL(6,2),
    justification TEXT,
    reference_standard_id UUID REFERENCES ex_reference_standard(id),
    reference_section VARCHAR(50),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX ix_zone_tenant_concept ON ex_zone_definition (tenant_id, concept_id);
CREATE INDEX ix_zone_type ON ex_zone_definition (zone_type);

-- 8. Schutzmaßnahmen
CREATE TABLE ex_protection_measure (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID NOT NULL,
    concept_id UUID NOT NULL REFERENCES ex_concept(id) ON DELETE CASCADE,
    category VARCHAR(20) NOT NULL,
    title VARCHAR(255) NOT NULL,
    description TEXT,
    catalog_reference_id UUID REFERENCES ex_measure_catalog(id),
    safety_function_id UUID REFERENCES ex_safety_function(id),
    status VARCHAR(20) NOT NULL DEFAULT 'open',
    responsible_user_id UUID,
    due_date DATE,
    verified_by_id UUID,
    verified_at TIMESTAMP WITH TIME ZONE,
    verification_notes TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX ix_measure_tenant_concept ON ex_protection_measure (tenant_id, concept_id);
CREATE INDEX ix_measure_status ON ex_protection_measure (status);
```

### Phase 3: Equipment und Inspections

```bash
python manage.py makemigrations explosionsschutz --name 0003_equipment_inspections

# Enthält:
# - ex_equipment
# - ex_inspection
# - ex_verification_document
```

**Tabellen:**

```sql
-- 9. Betriebsmittel
CREATE TABLE ex_equipment (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID NOT NULL,
    equipment_type_id UUID NOT NULL REFERENCES ex_equipment_type(id),
    area_id UUID NOT NULL REFERENCES ex_area(id),
    zone_id UUID REFERENCES ex_zone_definition(id),
    serial_number VARCHAR(100),
    asset_number VARCHAR(100),
    location_detail VARCHAR(255),
    status VARCHAR(20) NOT NULL DEFAULT 'active',
    installation_date DATE,
    last_inspection_date DATE,
    next_inspection_date DATE,
    inspection_interval_months INTEGER,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    CONSTRAINT uq_equipment_tenant_serial UNIQUE (tenant_id, serial_number)
);

CREATE INDEX ix_equipment_tenant_area ON ex_equipment (tenant_id, area_id);
CREATE INDEX ix_equipment_next_inspection ON ex_equipment (next_inspection_date);

-- 10. Prüfungen
CREATE TABLE ex_inspection (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID NOT NULL,
    equipment_id UUID NOT NULL REFERENCES ex_equipment(id) ON DELETE CASCADE,
    inspection_type VARCHAR(30) NOT NULL,
    inspection_date DATE NOT NULL,
    inspector_name VARCHAR(200) NOT NULL,
    inspector_qualification VARCHAR(100),
    result VARCHAR(20) NOT NULL,
    findings TEXT,
    recommendations TEXT,
    certificate_number VARCHAR(100),
    next_inspection_date DATE,
    created_by_id UUID,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX ix_inspection_tenant_equipment ON ex_inspection (tenant_id, equipment_id);
CREATE INDEX ix_inspection_date ON ex_inspection (inspection_date);

-- 11. Nachweisdokumente
CREATE TABLE ex_verification_document (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID NOT NULL,
    concept_id UUID NOT NULL REFERENCES ex_concept(id) ON DELETE CASCADE,
    document_id UUID,  -- FK zu documents_document
    title VARCHAR(255) NOT NULL,
    document_type VARCHAR(30) NOT NULL,
    issued_by VARCHAR(200),
    issued_at DATE,
    valid_until DATE,
    notes TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX ix_verdoc_tenant_concept ON ex_verification_document (tenant_id, concept_id);
```

### Phase 4: Zündquellenbewertung

```bash
python manage.py makemigrations explosionsschutz --name 0004_ignition_assessment

# Enthält:
# - ex_zone_ignition_assessment
```

**Tabellen:**

```sql
-- 12. Zündquellenbewertung
CREATE TABLE ex_zone_ignition_assessment (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID NOT NULL,
    zone_id UUID NOT NULL REFERENCES ex_zone_definition(id) ON DELETE CASCADE,
    ignition_source VARCHAR(30) NOT NULL,
    is_present BOOLEAN NOT NULL DEFAULT FALSE,
    is_effective BOOLEAN NOT NULL DEFAULT FALSE,
    mitigation TEXT,
    assessed_by_id UUID,
    assessed_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    CONSTRAINT uq_ignition_zone_source UNIQUE (tenant_id, zone_id, ignition_source)
);

CREATE INDEX ix_ignition_zone ON ex_zone_ignition_assessment (zone_id);
```

### Phase 5: M2M-Tabellen

```bash
python manage.py makemigrations explosionsschutz --name 0005_m2m_relations
```

**Tabellen:**

```sql
-- M2M: Maßnahmenkatalog <-> Regelwerke
CREATE TABLE ex_measure_catalog_reference_standards (
    id SERIAL PRIMARY KEY,
    measurecatalog_id UUID NOT NULL REFERENCES ex_measure_catalog(id),
    referencestandard_id UUID NOT NULL REFERENCES ex_reference_standard(id),
    UNIQUE (measurecatalog_id, referencestandard_id)
);

-- M2M: Sicherheitsfunktionen <-> Regelwerke
CREATE TABLE ex_safety_function_reference_standards (
    id SERIAL PRIMARY KEY,
    safetyfunction_id UUID NOT NULL REFERENCES ex_safety_function(id),
    referencestandard_id UUID NOT NULL REFERENCES ex_reference_standard(id),
    UNIQUE (safetyfunction_id, referencestandard_id)
);
```

## RLS aktivieren

Nach erfolgreicher Migration:

```bash
psql -d riskhub -f scripts/enable_rls_explosionsschutz.sql
```

## Seed-Daten laden

```bash
python manage.py loaddata explosionsschutz/fixtures/reference_standards.json
python manage.py loaddata explosionsschutz/fixtures/measure_catalog.json
python manage.py loaddata explosionsschutz/fixtures/equipment_types.json
```

## Rollback

Bei Problemen einzelne Migrationen zurücksetzen:

```bash
# Letzte Migration zurücksetzen
python manage.py migrate explosionsschutz 0004_ignition_assessment

# Alle Explosionsschutz-Migrationen zurücksetzen
python manage.py migrate explosionsschutz zero
```

## Migrations-Befehle

```bash
# Migrations-Status prüfen
python manage.py showmigrations explosionsschutz

# Alle Migrationen ausführen
python manage.py migrate explosionsschutz

# SQL anzeigen (ohne Ausführung)
python manage.py sqlmigrate explosionsschutz 0001_initial_masterdata
```

## Checkliste

- [ ] Abhängige Module migriert (tenancy, identity, substances)
- [ ] UUID-Extension aktiviert
- [ ] Migrationen erstellt (`makemigrations`)
- [ ] Migrationen ausgeführt (`migrate`)
- [ ] RLS aktiviert (`enable_rls_explosionsschutz.sql`)
- [ ] Seed-Daten geladen (Reference Standards, Measure Catalog)
- [ ] Tests ausgeführt (`pytest explosionsschutz/`)
- [ ] Admin-Interface getestet
