-- Enable RLS for tenant-scoped tables (run after migrations)
-- IMPORTANT: For local dev, you may skip this. For prod/staging, enable it.

-- Tenancy
ALTER TABLE tenancy_organization ENABLE ROW LEVEL SECURITY;
ALTER TABLE tenancy_site ENABLE ROW LEVEL SECURITY;

-- Risk
ALTER TABLE risk_assessment ENABLE ROW LEVEL SECURITY;

-- Actions
ALTER TABLE actions_action_item ENABLE ROW LEVEL SECURITY;

-- Documents
ALTER TABLE documents_document ENABLE ROW LEVEL SECURITY;
ALTER TABLE documents_document_version ENABLE ROW LEVEL SECURITY;

-- Permissions
ALTER TABLE permissions_role ENABLE ROW LEVEL SECURITY;
ALTER TABLE permissions_scope ENABLE ROW LEVEL SECURITY;
ALTER TABLE permissions_assignment ENABLE ROW LEVEL SECURITY;

-- Reporting
ALTER TABLE reporting_export_job ENABLE ROW LEVEL SECURITY;

-- Audit & Outbox
ALTER TABLE bfagent_core_audit_event ENABLE ROW LEVEL SECURITY;
ALTER TABLE bfagent_core_outbox_message ENABLE ROW LEVEL SECURITY;

-- RLS Policies
CREATE POLICY tenant_isolation_org ON tenancy_organization
    USING (tenant_id = NULLIF(current_setting('app.current_tenant', true), '')::uuid);

CREATE POLICY tenant_isolation_site ON tenancy_site
    USING (tenant_id = NULLIF(current_setting('app.current_tenant', true), '')::uuid);

CREATE POLICY tenant_isolation_assessment ON risk_assessment
    USING (tenant_id = NULLIF(current_setting('app.current_tenant', true), '')::uuid);

CREATE POLICY tenant_isolation_action ON actions_action_item
    USING (tenant_id = NULLIF(current_setting('app.current_tenant', true), '')::uuid);

CREATE POLICY tenant_isolation_doc ON documents_document
    USING (tenant_id = NULLIF(current_setting('app.current_tenant', true), '')::uuid);

CREATE POLICY tenant_isolation_doc_ver ON documents_document_version
    USING (tenant_id = NULLIF(current_setting('app.current_tenant', true), '')::uuid);

CREATE POLICY tenant_isolation_role ON permissions_role
    USING (tenant_id = NULLIF(current_setting('app.current_tenant', true), '')::uuid);

CREATE POLICY tenant_isolation_scope ON permissions_scope
    USING (tenant_id = NULLIF(current_setting('app.current_tenant', true), '')::uuid);

CREATE POLICY tenant_isolation_assignment ON permissions_assignment
    USING (tenant_id = NULLIF(current_setting('app.current_tenant', true), '')::uuid);

CREATE POLICY tenant_isolation_export ON reporting_export_job
    USING (tenant_id = NULLIF(current_setting('app.current_tenant', true), '')::uuid);

CREATE POLICY tenant_isolation_audit ON bfagent_core_audit_event
    USING (tenant_id = NULLIF(current_setting('app.current_tenant', true), '')::uuid);

CREATE POLICY tenant_isolation_outbox ON bfagent_core_outbox_message
    USING (tenant_id = NULLIF(current_setting('app.current_tenant', true), '')::uuid);
