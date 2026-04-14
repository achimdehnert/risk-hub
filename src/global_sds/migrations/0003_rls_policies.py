"""
RLS-Policies für Global SDS Library (ADR-161 §3.2).

Globale Tabellen:
- SELECT: offen für alle authentifizierten DB-Verbindungen
- INSERT: nur via Service-Account (Upload-Pipeline, Migrations)
- UPDATE/DELETE: nie erlaubt (Immutabilität nach Anlage)

SdsUsage (tenant-scoped):
- SELECT/INSERT/UPDATE: nur für eigenen Tenant
- DELETE: nie erlaubt
"""

from django.db import migrations

# Globale Tabellen — kein tenant_id, Hybrid-RLS
GLOBAL_TABLES = [
    "global_sds_substance",
    "global_sds_sdsrevision",
    "global_sds_sdscomponent",
    "global_sds_sdsexposurelimit",
    "global_sds_revisiondiff",
]

# Tenant-scoped Tabelle
TENANT_TABLE = "global_sds_usage"


def apply_rls(apps, schema_editor):
    """Enable RLS on all global_sds tables."""
    with schema_editor.connection.cursor() as cursor:
        # ── Global tables: read-open, write-restricted ──
        for table in GLOBAL_TABLES:
            cursor.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY;")
            cursor.execute(f"ALTER TABLE {table} FORCE ROW LEVEL SECURITY;")

            # SELECT: global sichtbar
            cursor.execute(
                f"CREATE POLICY {table}_read ON {table} "
                f"FOR SELECT USING (true);"
            )

            # INSERT: nur Service-Account
            cursor.execute(
                f"CREATE POLICY {table}_insert ON {table} "
                f"FOR INSERT WITH CHECK ("
                f"    current_setting('app.is_service_account', true)::boolean = true"
                f");"
            )

            # UPDATE: nie erlaubt
            cursor.execute(
                f"CREATE POLICY {table}_no_update ON {table} "
                f"FOR UPDATE USING (false);"
            )

            # DELETE: nie erlaubt
            cursor.execute(
                f"CREATE POLICY {table}_no_delete ON {table} "
                f"FOR DELETE USING (false);"
            )

        # ── SdsUsage: tenant-scoped RLS ──
        cursor.execute(f"ALTER TABLE {TENANT_TABLE} ENABLE ROW LEVEL SECURITY;")
        cursor.execute(f"ALTER TABLE {TENANT_TABLE} FORCE ROW LEVEL SECURITY;")

        # SELECT: nur eigener Tenant
        cursor.execute(
            f"CREATE POLICY {TENANT_TABLE}_tenant_read ON {TENANT_TABLE} "
            f"FOR SELECT USING ("
            f"    tenant_id::text = current_setting('app.tenant_id', true)"
            f"    OR current_setting('app.is_service_account', true)::boolean = true"
            f");"
        )

        # INSERT: nur eigener Tenant
        cursor.execute(
            f"CREATE POLICY {TENANT_TABLE}_tenant_insert ON {TENANT_TABLE} "
            f"FOR INSERT WITH CHECK ("
            f"    tenant_id::text = current_setting('app.tenant_id', true)"
            f"    OR current_setting('app.is_service_account', true)::boolean = true"
            f");"
        )

        # UPDATE: nur eigener Tenant
        cursor.execute(
            f"CREATE POLICY {TENANT_TABLE}_tenant_update ON {TENANT_TABLE} "
            f"FOR UPDATE USING ("
            f"    tenant_id::text = current_setting('app.tenant_id', true)"
            f"    OR current_setting('app.is_service_account', true)::boolean = true"
            f");"
        )

        # DELETE: nie erlaubt
        cursor.execute(
            f"CREATE POLICY {TENANT_TABLE}_no_delete ON {TENANT_TABLE} "
            f"FOR DELETE USING (false);"
        )


def remove_rls(apps, schema_editor):
    """Remove all RLS policies (reverse migration)."""
    all_tables = GLOBAL_TABLES + [TENANT_TABLE]
    with schema_editor.connection.cursor() as cursor:
        for table in all_tables:
            # Drop all policies for this table
            cursor.execute(
                "SELECT policyname FROM pg_policies WHERE tablename = %s;",
                [table],
            )
            for row in cursor.fetchall():
                cursor.execute(f"DROP POLICY IF EXISTS {row[0]} ON {table};")

            cursor.execute(f"ALTER TABLE {table} DISABLE ROW LEVEL SECURITY;")


class Migration(migrations.Migration):
    dependencies = [
        ("global_sds", "0002_initial"),
    ]

    operations = [
        migrations.RunPython(apply_rls, remove_rls),
    ]
