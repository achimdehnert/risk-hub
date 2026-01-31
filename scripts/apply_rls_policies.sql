-- scripts/apply_rls_policies.sql
-- Run this AFTER initial migrations: psql -d app -f scripts/apply_rls_policies.sql

-- Enable RLS on all tables
ALTER TABLE ex_reference_standard ENABLE ROW LEVEL SECURITY;
ALTER TABLE ex_measure_catalog ENABLE ROW LEVEL SECURITY;
ALTER TABLE ex_safety_function ENABLE ROW LEVEL SECURITY;
ALTER TABLE ex_equipment_type ENABLE ROW LEVEL SECURITY;
ALTER TABLE ex_area ENABLE ROW LEVEL SECURITY;
ALTER TABLE ex_concept ENABLE ROW LEVEL SECURITY;
ALTER TABLE ex_zone_definition ENABLE ROW LEVEL SECURITY;
ALTER TABLE ex_protection_measure ENABLE ROW LEVEL SECURITY;
ALTER TABLE ex_equipment ENABLE ROW LEVEL SECURITY;
ALTER TABLE ex_inspection ENABLE ROW LEVEL SECURITY;
ALTER TABLE ex_verification_document ENABLE ROW LEVEL SECURITY;
ALTER TABLE ex_zone_ignition_assessment ENABLE ROW LEVEL SECURITY;

-- Hybrid isolation for master data (global + tenant)
CREATE POLICY IF NOT EXISTS ex_std_iso ON ex_reference_standard FOR ALL
USING (tenant_id = current_setting('app.tenant_id', true)::uuid
       OR tenant_id IS NULL OR is_system = true);

CREATE POLICY IF NOT EXISTS ex_cat_iso ON ex_measure_catalog FOR ALL
USING (tenant_id = current_setting('app.tenant_id', true)::uuid
       OR tenant_id IS NULL OR is_system = true);

CREATE POLICY IF NOT EXISTS ex_sf_iso ON ex_safety_function FOR ALL
USING (tenant_id = current_setting('app.tenant_id', true)::uuid
       OR tenant_id IS NULL OR is_system = true);

CREATE POLICY IF NOT EXISTS ex_et_iso ON ex_equipment_type FOR ALL
USING (tenant_id = current_setting('app.tenant_id', true)::uuid
       OR tenant_id IS NULL OR is_system = true);

-- Strict isolation for core entities
CREATE POLICY IF NOT EXISTS ex_area_iso ON ex_area FOR ALL
USING (tenant_id = current_setting('app.tenant_id', true)::uuid);

CREATE POLICY IF NOT EXISTS ex_concept_iso ON ex_concept FOR ALL
USING (tenant_id = current_setting('app.tenant_id', true)::uuid);

CREATE POLICY IF NOT EXISTS ex_zone_iso ON ex_zone_definition FOR ALL
USING (tenant_id = current_setting('app.tenant_id', true)::uuid);

CREATE POLICY IF NOT EXISTS ex_measure_iso ON ex_protection_measure FOR ALL
USING (tenant_id = current_setting('app.tenant_id', true)::uuid);

CREATE POLICY IF NOT EXISTS ex_equip_iso ON ex_equipment FOR ALL
USING (tenant_id = current_setting('app.tenant_id', true)::uuid);

CREATE POLICY IF NOT EXISTS ex_insp_iso ON ex_inspection FOR ALL
USING (tenant_id = current_setting('app.tenant_id', true)::uuid);

CREATE POLICY IF NOT EXISTS ex_doc_iso ON ex_verification_document FOR ALL
USING (tenant_id = current_setting('app.tenant_id', true)::uuid);

CREATE POLICY IF NOT EXISTS ex_ign_iso ON ex_zone_ignition_assessment FOR ALL
USING (tenant_id = current_setting('app.tenant_id', true)::uuid);

SELECT 'RLS policies applied successfully' AS status;
