-- =============================================================================
-- RLS for Risk-Hub (ADR-003 §4)
-- Run AFTER migrations: psql -U app -d app -f scripts/enable_rls.sql
-- =============================================================================

-- Helper: session variable used by middleware (set_db_tenant)
-- Usage:  SET LOCAL app.tenant_id = '<uuid>';
-- Policy: tenant_id = current_setting('app.tenant_id', true)::uuid

-- =============================================================================
-- 1. ENABLE RLS on all tenant-scoped tables
-- =============================================================================

-- Tenancy
ALTER TABLE tenancy_site ENABLE ROW LEVEL SECURITY;
ALTER TABLE tenancy_site FORCE ROW LEVEL SECURITY;
ALTER TABLE tenancy_membership ENABLE ROW LEVEL SECURITY;
ALTER TABLE tenancy_membership FORCE ROW LEVEL SECURITY;

-- Risk
ALTER TABLE risk_assessment ENABLE ROW LEVEL SECURITY;
ALTER TABLE risk_assessment FORCE ROW LEVEL SECURITY;
ALTER TABLE risk_hazard ENABLE ROW LEVEL SECURITY;
ALTER TABLE risk_hazard FORCE ROW LEVEL SECURITY;

-- Actions
ALTER TABLE actions_action_item ENABLE ROW LEVEL SECURITY;
ALTER TABLE actions_action_item FORCE ROW LEVEL SECURITY;

-- Documents
ALTER TABLE documents_document ENABLE ROW LEVEL SECURITY;
ALTER TABLE documents_document FORCE ROW LEVEL SECURITY;
ALTER TABLE documents_document_version ENABLE ROW LEVEL SECURITY;
ALTER TABLE documents_document_version FORCE ROW LEVEL SECURITY;

-- Permissions
ALTER TABLE permissions_scope ENABLE ROW LEVEL SECURITY;
ALTER TABLE permissions_scope FORCE ROW LEVEL SECURITY;
ALTER TABLE permissions_assignment ENABLE ROW LEVEL SECURITY;
ALTER TABLE permissions_assignment FORCE ROW LEVEL SECURITY;
ALTER TABLE permissions_override ENABLE ROW LEVEL SECURITY;
ALTER TABLE permissions_override FORCE ROW LEVEL SECURITY;

-- Reporting
ALTER TABLE reporting_export_job ENABLE ROW LEVEL SECURITY;
ALTER TABLE reporting_export_job FORCE ROW LEVEL SECURITY;

-- Audit & Outbox
ALTER TABLE audit_event ENABLE ROW LEVEL SECURITY;
ALTER TABLE audit_event FORCE ROW LEVEL SECURITY;
ALTER TABLE outbox_message ENABLE ROW LEVEL SECURITY;
ALTER TABLE outbox_message FORCE ROW LEVEL SECURITY;

-- =============================================================================
-- 2. TENANT ISOLATION POLICIES
-- =============================================================================

-- Macro: tenant_id must match session variable
-- NULLIF handles empty string from current_setting default

CREATE POLICY tenant_iso ON tenancy_site
    FOR ALL USING (tenant_id = current_setting('app.tenant_id', true)::uuid)
    WITH CHECK (tenant_id = current_setting('app.tenant_id', true)::uuid);

CREATE POLICY tenant_iso ON tenancy_membership
    FOR ALL USING (tenant_id = current_setting('app.tenant_id', true)::uuid)
    WITH CHECK (tenant_id = current_setting('app.tenant_id', true)::uuid);

CREATE POLICY tenant_iso ON risk_assessment
    FOR ALL USING (tenant_id = current_setting('app.tenant_id', true)::uuid)
    WITH CHECK (tenant_id = current_setting('app.tenant_id', true)::uuid);

CREATE POLICY tenant_iso ON risk_hazard
    FOR ALL USING (tenant_id = current_setting('app.tenant_id', true)::uuid)
    WITH CHECK (tenant_id = current_setting('app.tenant_id', true)::uuid);

CREATE POLICY tenant_iso ON actions_action_item
    FOR ALL USING (tenant_id = current_setting('app.tenant_id', true)::uuid)
    WITH CHECK (tenant_id = current_setting('app.tenant_id', true)::uuid);

CREATE POLICY tenant_iso ON documents_document
    FOR ALL USING (tenant_id = current_setting('app.tenant_id', true)::uuid)
    WITH CHECK (tenant_id = current_setting('app.tenant_id', true)::uuid);

CREATE POLICY tenant_iso ON documents_document_version
    FOR ALL USING (tenant_id = current_setting('app.tenant_id', true)::uuid)
    WITH CHECK (tenant_id = current_setting('app.tenant_id', true)::uuid);

CREATE POLICY tenant_iso ON permissions_scope
    FOR ALL USING (tenant_id = current_setting('app.tenant_id', true)::uuid)
    WITH CHECK (tenant_id = current_setting('app.tenant_id', true)::uuid);

CREATE POLICY tenant_iso ON permissions_assignment
    FOR ALL USING (tenant_id = current_setting('app.tenant_id', true)::uuid)
    WITH CHECK (tenant_id = current_setting('app.tenant_id', true)::uuid);

CREATE POLICY tenant_iso ON reporting_export_job
    FOR ALL USING (tenant_id = current_setting('app.tenant_id', true)::uuid)
    WITH CHECK (tenant_id = current_setting('app.tenant_id', true)::uuid);

CREATE POLICY tenant_iso ON audit_event
    FOR ALL USING (tenant_id = current_setting('app.tenant_id', true)::uuid)
    WITH CHECK (tenant_id = current_setting('app.tenant_id', true)::uuid);

CREATE POLICY tenant_iso ON outbox_message
    FOR ALL USING (tenant_id = current_setting('app.tenant_id', true)::uuid)
    WITH CHECK (tenant_id = current_setting('app.tenant_id', true)::uuid);

-- =============================================================================
-- 2b. EXPLOSIONSSCHUTZ TABLES
-- =============================================================================

-- Core tenant-scoped tables
ALTER TABLE ex_area ENABLE ROW LEVEL SECURITY;
ALTER TABLE ex_area FORCE ROW LEVEL SECURITY;
ALTER TABLE ex_concept ENABLE ROW LEVEL SECURITY;
ALTER TABLE ex_concept FORCE ROW LEVEL SECURITY;
ALTER TABLE ex_zone_definition ENABLE ROW LEVEL SECURITY;
ALTER TABLE ex_zone_definition FORCE ROW LEVEL SECURITY;
ALTER TABLE ex_protection_measure ENABLE ROW LEVEL SECURITY;
ALTER TABLE ex_protection_measure FORCE ROW LEVEL SECURITY;
ALTER TABLE ex_equipment ENABLE ROW LEVEL SECURITY;
ALTER TABLE ex_equipment FORCE ROW LEVEL SECURITY;
ALTER TABLE ex_inspection ENABLE ROW LEVEL SECURITY;
ALTER TABLE ex_inspection FORCE ROW LEVEL SECURITY;
ALTER TABLE ex_verification_document ENABLE ROW LEVEL SECURITY;
ALTER TABLE ex_verification_document FORCE ROW LEVEL SECURITY;
ALTER TABLE ex_zone_ignition_assessment ENABLE ROW LEVEL SECURITY;
ALTER TABLE ex_zone_ignition_assessment FORCE ROW LEVEL SECURITY;

-- Master data tables (hybrid isolation)
ALTER TABLE ex_reference_standard ENABLE ROW LEVEL SECURITY;
ALTER TABLE ex_reference_standard FORCE ROW LEVEL SECURITY;
ALTER TABLE ex_measure_catalog ENABLE ROW LEVEL SECURITY;
ALTER TABLE ex_measure_catalog FORCE ROW LEVEL SECURITY;
ALTER TABLE ex_safety_function ENABLE ROW LEVEL SECURITY;
ALTER TABLE ex_safety_function FORCE ROW LEVEL SECURITY;
ALTER TABLE ex_equipment_type ENABLE ROW LEVEL SECURITY;
ALTER TABLE ex_equipment_type FORCE ROW LEVEL SECURITY;

-- Standard tenant isolation policies
DROP POLICY IF EXISTS tenant_iso ON ex_area;
CREATE POLICY tenant_iso ON ex_area
    FOR ALL USING (tenant_id = current_setting('app.tenant_id', true)::uuid)
    WITH CHECK (tenant_id = current_setting('app.tenant_id', true)::uuid);

DROP POLICY IF EXISTS tenant_iso ON ex_concept;
CREATE POLICY tenant_iso ON ex_concept
    FOR ALL USING (tenant_id = current_setting('app.tenant_id', true)::uuid)
    WITH CHECK (tenant_id = current_setting('app.tenant_id', true)::uuid);

DROP POLICY IF EXISTS tenant_iso ON ex_zone_definition;
CREATE POLICY tenant_iso ON ex_zone_definition
    FOR ALL USING (tenant_id = current_setting('app.tenant_id', true)::uuid)
    WITH CHECK (tenant_id = current_setting('app.tenant_id', true)::uuid);

DROP POLICY IF EXISTS tenant_iso ON ex_protection_measure;
CREATE POLICY tenant_iso ON ex_protection_measure
    FOR ALL USING (tenant_id = current_setting('app.tenant_id', true)::uuid)
    WITH CHECK (tenant_id = current_setting('app.tenant_id', true)::uuid);

DROP POLICY IF EXISTS tenant_iso ON ex_equipment;
CREATE POLICY tenant_iso ON ex_equipment
    FOR ALL USING (tenant_id = current_setting('app.tenant_id', true)::uuid)
    WITH CHECK (tenant_id = current_setting('app.tenant_id', true)::uuid);

DROP POLICY IF EXISTS tenant_iso ON ex_inspection;
CREATE POLICY tenant_iso ON ex_inspection
    FOR ALL USING (tenant_id = current_setting('app.tenant_id', true)::uuid)
    WITH CHECK (tenant_id = current_setting('app.tenant_id', true)::uuid);

DROP POLICY IF EXISTS tenant_iso ON ex_verification_document;
CREATE POLICY tenant_iso ON ex_verification_document
    FOR ALL USING (tenant_id = current_setting('app.tenant_id', true)::uuid)
    WITH CHECK (tenant_id = current_setting('app.tenant_id', true)::uuid);

DROP POLICY IF EXISTS tenant_iso ON ex_zone_ignition_assessment;
CREATE POLICY tenant_iso ON ex_zone_ignition_assessment
    FOR ALL USING (tenant_id = current_setting('app.tenant_id', true)::uuid)
    WITH CHECK (tenant_id = current_setting('app.tenant_id', true)::uuid);

-- Hybrid isolation: global (tenant_id IS NULL) + tenant-specific
DROP POLICY IF EXISTS hybrid_iso ON ex_reference_standard;
CREATE POLICY hybrid_iso ON ex_reference_standard
    FOR ALL USING (
        tenant_id IS NULL
        OR tenant_id = current_setting('app.tenant_id', true)::uuid
    );

DROP POLICY IF EXISTS hybrid_iso ON ex_measure_catalog;
CREATE POLICY hybrid_iso ON ex_measure_catalog
    FOR ALL USING (
        tenant_id IS NULL
        OR tenant_id = current_setting('app.tenant_id', true)::uuid
    );

DROP POLICY IF EXISTS hybrid_iso ON ex_safety_function;
CREATE POLICY hybrid_iso ON ex_safety_function
    FOR ALL USING (
        tenant_id IS NULL
        OR tenant_id = current_setting('app.tenant_id', true)::uuid
    );

DROP POLICY IF EXISTS hybrid_iso ON ex_equipment_type;
CREATE POLICY hybrid_iso ON ex_equipment_type
    FOR ALL USING (
        tenant_id IS NULL
        OR tenant_id = current_setting('app.tenant_id', true)::uuid
    );

-- =============================================================================
-- 2c. SUBSTANCES TABLES
-- =============================================================================

ALTER TABLE substances_party ENABLE ROW LEVEL SECURITY;
ALTER TABLE substances_party FORCE ROW LEVEL SECURITY;
ALTER TABLE substances_substance ENABLE ROW LEVEL SECURITY;
ALTER TABLE substances_substance FORCE ROW LEVEL SECURITY;
ALTER TABLE substances_identifier ENABLE ROW LEVEL SECURITY;
ALTER TABLE substances_identifier FORCE ROW LEVEL SECURITY;
ALTER TABLE substances_sdsrevision ENABLE ROW LEVEL SECURITY;
ALTER TABLE substances_sdsrevision FORCE ROW LEVEL SECURITY;
ALTER TABLE substances_siteinventoryitem ENABLE ROW LEVEL SECURITY;
ALTER TABLE substances_siteinventoryitem FORCE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS tenant_iso ON substances_party;
CREATE POLICY tenant_iso ON substances_party
    FOR ALL USING (tenant_id = current_setting('app.tenant_id', true)::uuid)
    WITH CHECK (tenant_id = current_setting('app.tenant_id', true)::uuid);

DROP POLICY IF EXISTS tenant_iso ON substances_substance;
CREATE POLICY tenant_iso ON substances_substance
    FOR ALL USING (tenant_id = current_setting('app.tenant_id', true)::uuid)
    WITH CHECK (tenant_id = current_setting('app.tenant_id', true)::uuid);

DROP POLICY IF EXISTS tenant_iso ON substances_identifier;
CREATE POLICY tenant_iso ON substances_identifier
    FOR ALL USING (tenant_id = current_setting('app.tenant_id', true)::uuid)
    WITH CHECK (tenant_id = current_setting('app.tenant_id', true)::uuid);

DROP POLICY IF EXISTS tenant_iso ON substances_sdsrevision;
CREATE POLICY tenant_iso ON substances_sdsrevision
    FOR ALL USING (tenant_id = current_setting('app.tenant_id', true)::uuid)
    WITH CHECK (tenant_id = current_setting('app.tenant_id', true)::uuid);

DROP POLICY IF EXISTS tenant_iso ON substances_siteinventoryitem;
CREATE POLICY tenant_iso ON substances_siteinventoryitem
    FOR ALL USING (tenant_id = current_setting('app.tenant_id', true)::uuid)
    WITH CHECK (tenant_id = current_setting('app.tenant_id', true)::uuid);

-- =============================================================================
-- 3. ADMIN BYPASS (for migrations, management commands)
-- =============================================================================

CREATE POLICY admin_bypass ON tenancy_site FOR ALL TO postgres USING (true);
CREATE POLICY admin_bypass ON tenancy_membership FOR ALL TO postgres USING (true);
CREATE POLICY admin_bypass ON risk_assessment FOR ALL TO postgres USING (true);
CREATE POLICY admin_bypass ON risk_hazard FOR ALL TO postgres USING (true);
CREATE POLICY admin_bypass ON actions_action_item FOR ALL TO postgres USING (true);
CREATE POLICY admin_bypass ON documents_document FOR ALL TO postgres USING (true);
CREATE POLICY admin_bypass ON documents_document_version FOR ALL TO postgres USING (true);
CREATE POLICY admin_bypass ON permissions_scope FOR ALL TO postgres USING (true);
CREATE POLICY admin_bypass ON permissions_assignment FOR ALL TO postgres USING (true);
CREATE POLICY admin_bypass ON permissions_override FOR ALL TO postgres USING (true);
CREATE POLICY admin_bypass ON reporting_export_job FOR ALL TO postgres USING (true);
CREATE POLICY admin_bypass ON audit_event FOR ALL TO postgres USING (true);
CREATE POLICY admin_bypass ON outbox_message FOR ALL TO postgres USING (true);

-- Explosionsschutz admin bypass
CREATE POLICY admin_bypass ON ex_area FOR ALL TO postgres USING (true);
CREATE POLICY admin_bypass ON ex_concept FOR ALL TO postgres USING (true);
CREATE POLICY admin_bypass ON ex_zone_definition FOR ALL TO postgres USING (true);
CREATE POLICY admin_bypass ON ex_protection_measure FOR ALL TO postgres USING (true);
CREATE POLICY admin_bypass ON ex_equipment FOR ALL TO postgres USING (true);
CREATE POLICY admin_bypass ON ex_inspection FOR ALL TO postgres USING (true);
CREATE POLICY admin_bypass ON ex_verification_document FOR ALL TO postgres USING (true);
CREATE POLICY admin_bypass ON ex_zone_ignition_assessment FOR ALL TO postgres USING (true);
CREATE POLICY admin_bypass ON ex_reference_standard FOR ALL TO postgres USING (true);
CREATE POLICY admin_bypass ON ex_measure_catalog FOR ALL TO postgres USING (true);
CREATE POLICY admin_bypass ON ex_safety_function FOR ALL TO postgres USING (true);
CREATE POLICY admin_bypass ON ex_equipment_type FOR ALL TO postgres USING (true);

-- Substances admin bypass
CREATE POLICY admin_bypass ON substances_party FOR ALL TO postgres USING (true);
CREATE POLICY admin_bypass ON substances_substance FOR ALL TO postgres USING (true);
CREATE POLICY admin_bypass ON substances_identifier FOR ALL TO postgres USING (true);
CREATE POLICY admin_bypass ON substances_sdsrevision FOR ALL TO postgres USING (true);
CREATE POLICY admin_bypass ON substances_siteinventoryitem FOR ALL TO postgres USING (true);

-- =============================================================================
-- 4. SPECIAL: permissions_override uses membership FK, not direct tenant_id
--    Policy via JOIN to membership.tenant_id
-- =============================================================================

CREATE POLICY tenant_iso ON permissions_override
    FOR ALL USING (
        EXISTS (
            SELECT 1 FROM tenancy_membership m
            WHERE m.id = permissions_override.membership_id
            AND m.tenant_id = current_setting('app.tenant_id', true)::uuid
        )
    );
