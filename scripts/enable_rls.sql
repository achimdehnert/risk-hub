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
