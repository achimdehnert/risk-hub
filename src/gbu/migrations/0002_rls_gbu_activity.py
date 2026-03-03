"""
RLS-Policies für tenant-scoped GBU-Tabellen.

Idempotent: CREATE POLICY IF NOT EXISTS.
Rollback: DROP POLICY + DISABLE ROW LEVEL SECURITY.
"""
from django.db import migrations

RLS_SQL = """
ALTER TABLE gbu_hazard_assessment_activity ENABLE ROW LEVEL SECURITY;
ALTER TABLE gbu_hazard_assessment_activity FORCE ROW LEVEL SECURITY;
CREATE POLICY IF NOT EXISTS tenant_isolation
    ON gbu_hazard_assessment_activity
    FOR ALL
    USING (tenant_id = current_setting('app.tenant_id', true)::uuid)
    WITH CHECK (tenant_id = current_setting('app.tenant_id', true)::uuid);

ALTER TABLE gbu_activity_measure ENABLE ROW LEVEL SECURITY;
ALTER TABLE gbu_activity_measure FORCE ROW LEVEL SECURITY;
CREATE POLICY IF NOT EXISTS tenant_isolation
    ON gbu_activity_measure
    FOR ALL
    USING (tenant_id = current_setting('app.tenant_id', true)::uuid)
    WITH CHECK (tenant_id = current_setting('app.tenant_id', true)::uuid);
"""

ROLLBACK_SQL = """
DROP POLICY IF EXISTS tenant_isolation ON gbu_hazard_assessment_activity;
ALTER TABLE gbu_hazard_assessment_activity DISABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS tenant_isolation ON gbu_activity_measure;
ALTER TABLE gbu_activity_measure DISABLE ROW LEVEL SECURITY;
"""


class Migration(migrations.Migration):
    dependencies = [
        ("gbu", "0001_initial"),
    ]
    operations = [
        migrations.RunSQL(sql=RLS_SQL, reverse_sql=ROLLBACK_SQL),
    ]
