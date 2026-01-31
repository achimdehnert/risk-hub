-- =============================================================================
-- Explosionsschutz-Modul: Row-Level Security (RLS) Policies
-- =============================================================================
-- Version: 5.0
-- Datum: 2026-01-31
-- Basis: ADR-001 v5 (Enterprise Edition)
--
-- Dieses Script aktiviert Row-Level Security für alle Explosionsschutz-Tabellen
-- und implementiert das Hybrid-Tenant-Isolation-Modell.
--
-- Ausführung: psql -d riskhub -f enable_rls_explosionsschutz.sql
-- =============================================================================

-- -----------------------------------------------------------------------------
-- 1. STAMMDATEN MIT HYBRID-ISOLATION
-- -----------------------------------------------------------------------------
-- Stammdaten-Tabellen erlauben:
-- - Lesen: Globale Daten (tenant_id IS NULL) + eigene Daten
-- - Schreiben: Nur eigene Daten (tenant_id = current_tenant)
-- - System-Daten (is_system = true) sind schreibgeschützt
-- -----------------------------------------------------------------------------

-- ReferenceStandard
ALTER TABLE ex_reference_standard ENABLE ROW LEVEL SECURITY;

CREATE POLICY tenant_read_reference_standard 
ON ex_reference_standard
FOR SELECT
USING (
    tenant_id IS NULL  -- Globale Daten
    OR tenant_id = current_setting('app.current_tenant', true)::uuid  -- Eigene Daten
);

CREATE POLICY tenant_insert_reference_standard 
ON ex_reference_standard
FOR INSERT
WITH CHECK (
    tenant_id = current_setting('app.current_tenant', true)::uuid
    AND NOT COALESCE(is_system, false)  -- Keine System-Daten via INSERT
);

CREATE POLICY tenant_update_reference_standard 
ON ex_reference_standard
FOR UPDATE
USING (
    tenant_id = current_setting('app.current_tenant', true)::uuid
    AND NOT COALESCE(is_system, false)  -- Keine System-Daten ändern
);

CREATE POLICY tenant_delete_reference_standard 
ON ex_reference_standard
FOR DELETE
USING (
    tenant_id = current_setting('app.current_tenant', true)::uuid
    AND NOT COALESCE(is_system, false)  -- Keine System-Daten löschen
);


-- MeasureCatalog
ALTER TABLE ex_measure_catalog ENABLE ROW LEVEL SECURITY;

CREATE POLICY tenant_read_measure_catalog 
ON ex_measure_catalog
FOR SELECT
USING (
    tenant_id IS NULL
    OR tenant_id = current_setting('app.current_tenant', true)::uuid
);

CREATE POLICY tenant_insert_measure_catalog 
ON ex_measure_catalog
FOR INSERT
WITH CHECK (
    tenant_id = current_setting('app.current_tenant', true)::uuid
    AND NOT COALESCE(is_system, false)
);

CREATE POLICY tenant_update_measure_catalog 
ON ex_measure_catalog
FOR UPDATE
USING (
    tenant_id = current_setting('app.current_tenant', true)::uuid
    AND NOT COALESCE(is_system, false)
);

CREATE POLICY tenant_delete_measure_catalog 
ON ex_measure_catalog
FOR DELETE
USING (
    tenant_id = current_setting('app.current_tenant', true)::uuid
    AND NOT COALESCE(is_system, false)
);


-- EquipmentType
ALTER TABLE ex_equipment_type ENABLE ROW LEVEL SECURITY;

CREATE POLICY tenant_read_equipment_type 
ON ex_equipment_type
FOR SELECT
USING (
    tenant_id IS NULL
    OR tenant_id = current_setting('app.current_tenant', true)::uuid
);

CREATE POLICY tenant_insert_equipment_type 
ON ex_equipment_type
FOR INSERT
WITH CHECK (
    tenant_id = current_setting('app.current_tenant', true)::uuid
    AND NOT COALESCE(is_system, false)
);

CREATE POLICY tenant_update_equipment_type 
ON ex_equipment_type
FOR UPDATE
USING (
    tenant_id = current_setting('app.current_tenant', true)::uuid
    AND NOT COALESCE(is_system, false)
);

CREATE POLICY tenant_delete_equipment_type 
ON ex_equipment_type
FOR DELETE
USING (
    tenant_id = current_setting('app.current_tenant', true)::uuid
    AND NOT COALESCE(is_system, false)
);


-- SafetyFunction
ALTER TABLE ex_safety_function ENABLE ROW LEVEL SECURITY;

CREATE POLICY tenant_read_safety_function 
ON ex_safety_function
FOR SELECT
USING (
    tenant_id IS NULL
    OR tenant_id = current_setting('app.current_tenant', true)::uuid
);

CREATE POLICY tenant_insert_safety_function 
ON ex_safety_function
FOR INSERT
WITH CHECK (
    tenant_id = current_setting('app.current_tenant', true)::uuid
    AND NOT COALESCE(is_system, false)
);

CREATE POLICY tenant_update_safety_function 
ON ex_safety_function
FOR UPDATE
USING (
    tenant_id = current_setting('app.current_tenant', true)::uuid
    AND NOT COALESCE(is_system, false)
);

CREATE POLICY tenant_delete_safety_function 
ON ex_safety_function
FOR DELETE
USING (
    tenant_id = current_setting('app.current_tenant', true)::uuid
    AND NOT COALESCE(is_system, false)
);


-- -----------------------------------------------------------------------------
-- 2. CORE ENTITIES MIT STRIKTER TENANT-ISOLATION
-- -----------------------------------------------------------------------------
-- Core-Tabellen erlauben nur Zugriff auf eigene Daten.
-- -----------------------------------------------------------------------------

-- Area
ALTER TABLE ex_area ENABLE ROW LEVEL SECURITY;

CREATE POLICY tenant_isolation_area 
ON ex_area
USING (tenant_id = current_setting('app.current_tenant', true)::uuid);

CREATE POLICY tenant_insert_area 
ON ex_area
FOR INSERT
WITH CHECK (tenant_id = current_setting('app.current_tenant', true)::uuid);


-- ExplosionConcept
ALTER TABLE ex_concept ENABLE ROW LEVEL SECURITY;

CREATE POLICY tenant_isolation_concept 
ON ex_concept
USING (tenant_id = current_setting('app.current_tenant', true)::uuid);

CREATE POLICY tenant_insert_concept 
ON ex_concept
FOR INSERT
WITH CHECK (tenant_id = current_setting('app.current_tenant', true)::uuid);


-- ZoneDefinition
ALTER TABLE ex_zone_definition ENABLE ROW LEVEL SECURITY;

CREATE POLICY tenant_isolation_zone 
ON ex_zone_definition
USING (tenant_id = current_setting('app.current_tenant', true)::uuid);

CREATE POLICY tenant_insert_zone 
ON ex_zone_definition
FOR INSERT
WITH CHECK (tenant_id = current_setting('app.current_tenant', true)::uuid);


-- ProtectionMeasure
ALTER TABLE ex_protection_measure ENABLE ROW LEVEL SECURITY;

CREATE POLICY tenant_isolation_measure 
ON ex_protection_measure
USING (tenant_id = current_setting('app.current_tenant', true)::uuid);

CREATE POLICY tenant_insert_measure 
ON ex_protection_measure
FOR INSERT
WITH CHECK (tenant_id = current_setting('app.current_tenant', true)::uuid);


-- Equipment
ALTER TABLE ex_equipment ENABLE ROW LEVEL SECURITY;

CREATE POLICY tenant_isolation_equipment 
ON ex_equipment
USING (tenant_id = current_setting('app.current_tenant', true)::uuid);

CREATE POLICY tenant_insert_equipment 
ON ex_equipment
FOR INSERT
WITH CHECK (tenant_id = current_setting('app.current_tenant', true)::uuid);


-- Inspection
ALTER TABLE ex_inspection ENABLE ROW LEVEL SECURITY;

CREATE POLICY tenant_isolation_inspection 
ON ex_inspection
USING (tenant_id = current_setting('app.current_tenant', true)::uuid);

CREATE POLICY tenant_insert_inspection 
ON ex_inspection
FOR INSERT
WITH CHECK (tenant_id = current_setting('app.current_tenant', true)::uuid);


-- VerificationDocument
ALTER TABLE ex_verification_document ENABLE ROW LEVEL SECURITY;

CREATE POLICY tenant_isolation_document 
ON ex_verification_document
USING (tenant_id = current_setting('app.current_tenant', true)::uuid);

CREATE POLICY tenant_insert_document 
ON ex_verification_document
FOR INSERT
WITH CHECK (tenant_id = current_setting('app.current_tenant', true)::uuid);


-- ZoneIgnitionSourceAssessment
ALTER TABLE ex_zone_ignition_assessment ENABLE ROW LEVEL SECURITY;

CREATE POLICY tenant_isolation_ignition 
ON ex_zone_ignition_assessment
USING (tenant_id = current_setting('app.current_tenant', true)::uuid);

CREATE POLICY tenant_insert_ignition 
ON ex_zone_ignition_assessment
FOR INSERT
WITH CHECK (tenant_id = current_setting('app.current_tenant', true)::uuid);


-- -----------------------------------------------------------------------------
-- 3. BYPASS FÜR ADMIN/MIGRATION
-- -----------------------------------------------------------------------------
-- Der Postgres-Superuser und spezielle Rollen umgehen RLS.
-- -----------------------------------------------------------------------------

-- Bypass-Rolle für Migrationen
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'riskhub_admin') THEN
        CREATE ROLE riskhub_admin NOLOGIN;
    END IF;
END
$$;

-- RLS-Bypass für Admin-Rolle
ALTER TABLE ex_reference_standard FORCE ROW LEVEL SECURITY;
ALTER TABLE ex_measure_catalog FORCE ROW LEVEL SECURITY;
ALTER TABLE ex_equipment_type FORCE ROW LEVEL SECURITY;
ALTER TABLE ex_safety_function FORCE ROW LEVEL SECURITY;
ALTER TABLE ex_area FORCE ROW LEVEL SECURITY;
ALTER TABLE ex_concept FORCE ROW LEVEL SECURITY;
ALTER TABLE ex_zone_definition FORCE ROW LEVEL SECURITY;
ALTER TABLE ex_protection_measure FORCE ROW LEVEL SECURITY;
ALTER TABLE ex_equipment FORCE ROW LEVEL SECURITY;
ALTER TABLE ex_inspection FORCE ROW LEVEL SECURITY;
ALTER TABLE ex_verification_document FORCE ROW LEVEL SECURITY;
ALTER TABLE ex_zone_ignition_assessment FORCE ROW LEVEL SECURITY;

-- Admin darf alles
GRANT ALL ON ex_reference_standard TO riskhub_admin;
GRANT ALL ON ex_measure_catalog TO riskhub_admin;
GRANT ALL ON ex_equipment_type TO riskhub_admin;
GRANT ALL ON ex_safety_function TO riskhub_admin;
GRANT ALL ON ex_area TO riskhub_admin;
GRANT ALL ON ex_concept TO riskhub_admin;
GRANT ALL ON ex_zone_definition TO riskhub_admin;
GRANT ALL ON ex_protection_measure TO riskhub_admin;
GRANT ALL ON ex_equipment TO riskhub_admin;
GRANT ALL ON ex_inspection TO riskhub_admin;
GRANT ALL ON ex_verification_document TO riskhub_admin;
GRANT ALL ON ex_zone_ignition_assessment TO riskhub_admin;


-- -----------------------------------------------------------------------------
-- 4. HELPER FUNCTION FÜR TENANT-CONTEXT
-- -----------------------------------------------------------------------------
-- Diese Funktion setzt den Tenant-Context für die aktuelle Session.
-- Sollte von der Django-Middleware aufgerufen werden.
-- -----------------------------------------------------------------------------

CREATE OR REPLACE FUNCTION set_current_tenant(p_tenant_id uuid)
RETURNS void AS $$
BEGIN
    PERFORM set_config('app.current_tenant', p_tenant_id::text, false);
END;
$$ LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION get_current_tenant()
RETURNS uuid AS $$
BEGIN
    RETURN current_setting('app.current_tenant', true)::uuid;
EXCEPTION
    WHEN OTHERS THEN
        RETURN NULL;
END;
$$ LANGUAGE plpgsql;


-- -----------------------------------------------------------------------------
-- 5. VERIFICATION
-- -----------------------------------------------------------------------------
-- Prüft ob RLS korrekt aktiviert ist.
-- -----------------------------------------------------------------------------

DO $$
DECLARE
    tbl record;
    rls_enabled boolean;
BEGIN
    FOR tbl IN 
        SELECT tablename 
        FROM pg_tables 
        WHERE schemaname = 'public' 
        AND tablename LIKE 'ex_%'
    LOOP
        SELECT relrowsecurity INTO rls_enabled
        FROM pg_class
        WHERE relname = tbl.tablename;
        
        IF NOT rls_enabled THEN
            RAISE WARNING 'RLS nicht aktiviert für: %', tbl.tablename;
        ELSE
            RAISE NOTICE 'RLS aktiviert für: %', tbl.tablename;
        END IF;
    END LOOP;
END
$$;

-- Ausgabe
SELECT 
    schemaname,
    tablename,
    rowsecurity as rls_enabled
FROM pg_tables t
JOIN pg_class c ON c.relname = t.tablename
WHERE t.schemaname = 'public'
AND t.tablename LIKE 'ex_%'
ORDER BY t.tablename;
