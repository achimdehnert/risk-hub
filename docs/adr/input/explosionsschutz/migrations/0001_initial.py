"""
Migration 0001: Initiale Explosionsschutz-Tabellen + RLS-Policies.

Abfolge:
  1. Tabellen anlegen
  2. RLS aktivieren
  3. Policies definieren (tenant-isolation)

HINWEIS: Diese Migration setzt voraus:
  - apps.tenancy (Tenant-Modell)
  - apps.documents (Document-FK in Equipment/Concept)
  - apps.substances (Substance-UUID in ExplosionConcept)
"""
from __future__ import annotations

import uuid

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ("documents", "0001_initial"),
    ]

    operations = [
        # ──────────────────────────────────────────────────────────────────
        # STAMMDATEN
        # ──────────────────────────────────────────────────────────────────
        migrations.CreateModel(
            name="ReferenceStandard",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True)),
                ("tenant_id", models.UUIDField(blank=True, db_index=True, null=True)),
                ("is_system", models.BooleanField(default=False)),
                ("code", models.CharField(max_length=80)),
                ("title", models.CharField(max_length=300)),
                ("category", models.CharField(max_length=20)),
                ("issue_date", models.CharField(blank=True, max_length=20)),
                ("url", models.URLField(blank=True)),
                ("is_active", models.BooleanField(default=True)),
            ],
            options={"db_table": "ex_reference_standard", "ordering": ["category", "code"]},
        ),
        migrations.AddConstraint(
            model_name="referencestandard",
            constraint=models.UniqueConstraint(
                fields=["tenant_id", "code"],
                name="uq_ex_reference_standard_code_per_tenant",
                nulls_distinct=False,
            ),
        ),
        migrations.CreateModel(
            name="MeasureCatalog",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True)),
                ("tenant_id", models.UUIDField(blank=True, db_index=True, null=True)),
                ("is_system", models.BooleanField(default=False)),
                ("title", models.CharField(max_length=200)),
                ("default_category", models.CharField(max_length=20)),
                ("description_template", models.TextField(blank=True)),
                ("trgs_reference", models.ForeignKey(
                    blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL,
                    related_name="+", to="explosionsschutz.referencestandard",
                )),
                ("is_active", models.BooleanField(default=True)),
            ],
            options={"db_table": "ex_measure_catalog", "ordering": ["default_category", "title"]},
        ),
        migrations.CreateModel(
            name="SafetyFunction",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True)),
                ("tenant_id", models.UUIDField(db_index=True)),
                ("name", models.CharField(max_length=200)),
                ("description", models.TextField(blank=True)),
                ("performance_level", models.CharField(blank=True, max_length=1, null=True)),
                ("sil_level", models.IntegerField(blank=True, null=True)),
                ("monitoring_method", models.TextField(blank=True)),
                ("test_interval_months", models.PositiveSmallIntegerField(blank=True, null=True)),
                ("trgs_reference", models.ForeignKey(
                    blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL,
                    related_name="+", to="explosionsschutz.referencestandard",
                )),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={"db_table": "ex_safety_function", "ordering": ["name"]},
        ),
        migrations.CreateModel(
            name="EquipmentType",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True)),
                ("tenant_id", models.UUIDField(blank=True, db_index=True, null=True)),
                ("is_system", models.BooleanField(default=False)),
                ("manufacturer", models.CharField(max_length=200)),
                ("model_name", models.CharField(max_length=200)),
                ("description", models.TextField(blank=True)),
                ("atex_group", models.CharField(blank=True, max_length=3)),
                ("atex_category", models.CharField(blank=True, max_length=3)),
                ("temperature_class", models.CharField(blank=True, max_length=2)),
                ("protection_type", models.CharField(blank=True, max_length=50)),
                ("explosion_group", models.CharField(blank=True, max_length=10)),
                ("default_inspection_interval_months", models.PositiveSmallIntegerField(blank=True, null=True)),
            ],
            options={"db_table": "ex_equipment_type", "ordering": ["manufacturer", "model_name"]},
        ),
        # ──────────────────────────────────────────────────────────────────
        # BETRIEBSBEREICH
        # ──────────────────────────────────────────────────────────────────
        migrations.CreateModel(
            name="Area",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True)),
                ("tenant_id", models.UUIDField(db_index=True)),
                ("site_id", models.UUIDField(db_index=True)),
                ("code", models.CharField(max_length=50)),
                ("name", models.CharField(max_length=200)),
                ("description", models.TextField(blank=True)),
                ("location_description", models.CharField(blank=True, max_length=500)),
                ("floor_plan", models.ForeignKey(
                    blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL,
                    related_name="area_floor_plans", to="documents.document",
                )),
                ("is_active", models.BooleanField(default=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
            ],
            options={"db_table": "ex_area", "ordering": ["code"]},
        ),
        migrations.AddConstraint(
            model_name="area",
            constraint=models.UniqueConstraint(
                fields=["tenant_id", "code"],
                name="uq_ex_area_code_per_tenant",
            ),
        ),
        # ──────────────────────────────────────────────────────────────────
        # KONZEPT
        # ──────────────────────────────────────────────────────────────────
        migrations.CreateModel(
            name="ExplosionConcept",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True)),
                ("tenant_id", models.UUIDField(db_index=True)),
                ("area", models.ForeignKey(
                    on_delete=django.db.models.deletion.PROTECT,
                    related_name="concepts", to="explosionsschutz.area",
                )),
                ("substance_id", models.UUIDField(blank=True, db_index=True, null=True)),
                ("title", models.CharField(max_length=300)),
                ("version", models.CharField(default="1.0", max_length=20)),
                ("document_number", models.CharField(blank=True, max_length=100)),
                ("is_current", models.BooleanField(default=True)),
                ("status", models.CharField(default="draft", max_length=20)),
                ("atmosphere_type", models.CharField(default="gas", max_length=10)),
                ("process_description", models.TextField(blank=True)),
                ("substitute_check_status", models.CharField(default="not_checked", max_length=30)),
                ("substitute_check_notes", models.TextField(blank=True)),
                ("release_source_type", models.CharField(default="vapor", max_length=10)),
                ("release_grade", models.CharField(blank=True, max_length=20)),
                ("release_description", models.TextField(blank=True)),
                ("explosion_impact_mitigation", models.TextField(blank=True)),
                ("responsible_id", models.UUIDField(blank=True, null=True)),
                ("responsible_name", models.CharField(blank=True, max_length=200)),
                ("author_id", models.UUIDField(blank=True, null=True)),
                ("author_name", models.CharField(blank=True, max_length=200)),
                ("approved_by_id", models.UUIDField(blank=True, null=True)),
                ("approved_by_name", models.CharField(blank=True, max_length=200)),
                ("approved_at", models.DateTimeField(blank=True, null=True)),
                ("approval_notes", models.TextField(blank=True)),
                ("next_review_date", models.DateField(blank=True, null=True)),
                ("pdf_document", models.ForeignKey(
                    blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL,
                    related_name="explosion_concept_pdfs", to="documents.document",
                )),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={"db_table": "ex_concept", "ordering": ["-created_at"]},
        ),
        migrations.AddConstraint(
            model_name="explosionconcept",
            constraint=models.CheckConstraint(
                check=models.Q(status__in=["draft", "review", "approved", "archived"]),
                name="ck_ex_concept_status_valid",
            ),
        ),
        # ──────────────────────────────────────────────────────────────────
        # ZONEN
        # ──────────────────────────────────────────────────────────────────
        migrations.CreateModel(
            name="ZoneDefinition",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True)),
                ("tenant_id", models.UUIDField(db_index=True)),
                ("concept", models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name="zones", to="explosionsschutz.explosionconcept",
                )),
                ("zone_type", models.CharField(max_length=4)),
                ("name", models.CharField(max_length=200)),
                ("location_in_area", models.CharField(blank=True, max_length=300)),
                ("extent_shape", models.CharField(default="custom", max_length=10)),
                ("extent_radius_m", models.DecimalField(blank=True, decimal_places=2, max_digits=6, null=True)),
                ("extent_height_m", models.DecimalField(blank=True, decimal_places=2, max_digits=6, null=True)),
                ("extent_length_m", models.DecimalField(blank=True, decimal_places=2, max_digits=6, null=True)),
                ("extent_width_m", models.DecimalField(blank=True, decimal_places=2, max_digits=6, null=True)),
                ("extent_description", models.TextField(blank=True)),
                ("trgs_reference", models.ForeignKey(
                    blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL,
                    related_name="+", to="explosionsschutz.referencestandard",
                )),
                ("justification", models.TextField()),
                ("ventilation_type", models.CharField(default="natural", max_length=20)),
                ("ventilation_notes", models.TextField(blank=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
            ],
            options={"db_table": "ex_zone_definition", "ordering": ["zone_type", "name"]},
        ),
        migrations.CreateModel(
            name="ZoneIgnitionSourceAssessment",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True)),
                ("tenant_id", models.UUIDField(db_index=True)),
                ("zone", models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name="ignition_assessments", to="explosionsschutz.zonedefinition",
                )),
                ("ignition_source", models.CharField(max_length=3)),
                ("is_present", models.BooleanField(default=False)),
                ("is_effective", models.BooleanField(default=False)),
                ("mitigation", models.TextField(blank=True)),
                ("residual_risk_acceptable", models.BooleanField(default=True)),
                ("assessed_by_id", models.UUIDField(blank=True, null=True)),
                ("assessed_at", models.DateTimeField(blank=True, null=True)),
            ],
            options={"db_table": "ex_zone_ignition_assessment"},
        ),
        migrations.AddConstraint(
            model_name="zoneignitionsourceassessment",
            constraint=models.UniqueConstraint(
                fields=["zone", "ignition_source"],
                name="uq_ex_zone_ignition_source",
            ),
        ),
        # ──────────────────────────────────────────────────────────────────
        # MASSNAHMEN
        # ──────────────────────────────────────────────────────────────────
        migrations.CreateModel(
            name="ProtectionMeasure",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True)),
                ("tenant_id", models.UUIDField(db_index=True)),
                ("concept", models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name="measures", to="explosionsschutz.explosionconcept",
                )),
                ("category", models.CharField(max_length=20)),
                ("catalog_reference", models.ForeignKey(
                    blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL,
                    related_name="+", to="explosionsschutz.measurecatalog",
                )),
                ("title", models.CharField(max_length=300)),
                ("description", models.TextField()),
                ("justification", models.TextField(blank=True)),
                ("safety_function", models.ForeignKey(
                    blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL,
                    related_name="measures", to="explosionsschutz.safetyfunction",
                )),
                ("responsible_id", models.UUIDField(blank=True, null=True)),
                ("responsible_name", models.CharField(blank=True, max_length=200)),
                ("due_date", models.DateField(blank=True, null=True)),
                ("status", models.CharField(default="done", max_length=20)),
                ("completion_date", models.DateField(blank=True, null=True)),
                ("completion_notes", models.TextField(blank=True)),
                ("standard_reference", models.ForeignKey(
                    blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL,
                    related_name="+", to="explosionsschutz.referencestandard",
                )),
                ("sort_order", models.PositiveSmallIntegerField(default=0)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
            ],
            options={"db_table": "ex_protection_measure", "ordering": ["category", "sort_order", "title"]},
        ),
        # ──────────────────────────────────────────────────────────────────
        # EQUIPMENT & INSPECTIONS
        # ──────────────────────────────────────────────────────────────────
        migrations.CreateModel(
            name="Equipment",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True)),
                ("tenant_id", models.UUIDField(db_index=True)),
                ("area", models.ForeignKey(
                    on_delete=django.db.models.deletion.PROTECT,
                    related_name="equipment", to="explosionsschutz.area",
                )),
                ("equipment_type", models.ForeignKey(
                    blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL,
                    related_name="equipment", to="explosionsschutz.equipmenttype",
                )),
                ("inventory_number", models.CharField(blank=True, max_length=100)),
                ("serial_number", models.CharField(blank=True, max_length=100)),
                ("name", models.CharField(max_length=300)),
                ("description", models.TextField(blank=True)),
                ("location_detail", models.CharField(blank=True, max_length=300)),
                ("atex_marking_override", models.CharField(blank=True, max_length=100)),
                ("manufacturer", models.CharField(blank=True, max_length=200)),
                ("year_of_manufacture", models.PositiveSmallIntegerField(blank=True, null=True)),
                ("year_of_installation", models.PositiveSmallIntegerField(blank=True, null=True)),
                ("first_inspection_date", models.DateField(blank=True, null=True)),
                ("next_inspection_date", models.DateField(blank=True, null=True)),
                ("inspection_interval_months", models.PositiveSmallIntegerField(blank=True, null=True)),
                ("is_active", models.BooleanField(default=True)),
                ("decommission_date", models.DateField(blank=True, null=True)),
                ("notes", models.TextField(blank=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={"db_table": "ex_equipment", "ordering": ["area", "name"]},
        ),
        migrations.AddField(
            model_name="equipment",
            name="zones",
            field=models.ManyToManyField(
                blank=True, related_name="equipment",
                to="explosionsschutz.zonedefinition",
            ),
        ),
        migrations.CreateModel(
            name="Inspection",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True)),
                ("tenant_id", models.UUIDField(db_index=True)),
                ("equipment", models.ForeignKey(
                    on_delete=django.db.models.deletion.PROTECT,
                    related_name="inspections", to="explosionsschutz.equipment",
                )),
                ("inspection_type", models.CharField(max_length=20)),
                ("scheduled_date", models.DateField()),
                ("performed_date", models.DateField(blank=True, null=True)),
                ("performed_by_id", models.UUIDField(blank=True, null=True)),
                ("performed_by_name", models.CharField(blank=True, max_length=200)),
                ("external_inspector", models.CharField(blank=True, max_length=200)),
                ("result", models.CharField(blank=True, max_length=30, null=True)),
                ("findings", models.TextField(blank=True)),
                ("corrective_actions", models.TextField(blank=True)),
                ("protocol", models.ForeignKey(
                    blank=True, null=True, on_delete=django.db.models.deletion.PROTECT,
                    related_name="inspection_protocols", to="documents.document",
                )),
                ("next_inspection_date", models.DateField(blank=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
            ],
            options={"db_table": "ex_inspection", "ordering": ["-scheduled_date"]},
        ),
        migrations.CreateModel(
            name="VerificationDocument",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True)),
                ("tenant_id", models.UUIDField(db_index=True)),
                ("concept", models.ForeignKey(
                    on_delete=django.db.models.deletion.PROTECT,
                    related_name="verification_documents", to="explosionsschutz.explosionconcept",
                )),
                ("title", models.CharField(max_length=300)),
                ("document_type", models.CharField(max_length=30)),
                ("document", models.ForeignKey(
                    on_delete=django.db.models.deletion.PROTECT,
                    related_name="verification_refs", to="documents.document",
                )),
                ("issuer", models.CharField(blank=True, max_length=200)),
                ("issued_at", models.DateField(blank=True, null=True)),
                ("valid_until", models.DateField(blank=True, null=True)),
                ("notes", models.TextField(blank=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
            ],
            options={"db_table": "ex_verification_document", "ordering": ["-issued_at"]},
        ),

        # ──────────────────────────────────────────────────────────────────
        # RLS: Row Level Security für alle Tenant-Tabellen
        # ──────────────────────────────────────────────────────────────────
        migrations.RunSQL(
            sql="""
            -- Aktiviere RLS auf allen tenant-isolierten Tabellen
            ALTER TABLE ex_area                         ENABLE ROW LEVEL SECURITY;
            ALTER TABLE ex_concept                      ENABLE ROW LEVEL SECURITY;
            ALTER TABLE ex_zone_definition              ENABLE ROW LEVEL SECURITY;
            ALTER TABLE ex_zone_ignition_assessment     ENABLE ROW LEVEL SECURITY;
            ALTER TABLE ex_protection_measure           ENABLE ROW LEVEL SECURITY;
            ALTER TABLE ex_safety_function              ENABLE ROW LEVEL SECURITY;
            ALTER TABLE ex_equipment                    ENABLE ROW LEVEL SECURITY;
            ALTER TABLE ex_inspection                   ENABLE ROW LEVEL SECURITY;
            ALTER TABLE ex_verification_document        ENABLE ROW LEVEL SECURITY;

            -- Policies: Tenant-Isolation (tenant_id = current_setting)
            CREATE POLICY ex_area_tenant_isolation ON ex_area
                USING (tenant_id = current_setting('app.tenant_id')::uuid);

            CREATE POLICY ex_concept_tenant_isolation ON ex_concept
                USING (tenant_id = current_setting('app.tenant_id')::uuid);

            CREATE POLICY ex_zone_tenant_isolation ON ex_zone_definition
                USING (tenant_id = current_setting('app.tenant_id')::uuid);

            CREATE POLICY ex_ignition_tenant_isolation ON ex_zone_ignition_assessment
                USING (tenant_id = current_setting('app.tenant_id')::uuid);

            CREATE POLICY ex_measure_tenant_isolation ON ex_protection_measure
                USING (tenant_id = current_setting('app.tenant_id')::uuid);

            CREATE POLICY ex_safety_fn_tenant_isolation ON ex_safety_function
                USING (tenant_id = current_setting('app.tenant_id')::uuid);

            CREATE POLICY ex_equipment_tenant_isolation ON ex_equipment
                USING (tenant_id = current_setting('app.tenant_id')::uuid);

            CREATE POLICY ex_inspection_tenant_isolation ON ex_inspection
                USING (tenant_id = current_setting('app.tenant_id')::uuid);

            CREATE POLICY ex_verification_tenant_isolation ON ex_verification_document
                USING (tenant_id = current_setting('app.tenant_id')::uuid);

            -- Hybrid-Isolation für Stammdaten (NULL = global, UUID = tenant-eigene)
            ALTER TABLE ex_reference_standard           ENABLE ROW LEVEL SECURITY;
            ALTER TABLE ex_measure_catalog              ENABLE ROW LEVEL SECURITY;
            ALTER TABLE ex_equipment_type               ENABLE ROW LEVEL SECURITY;

            CREATE POLICY ex_refstd_hybrid_read ON ex_reference_standard FOR SELECT
                USING (
                    tenant_id IS NULL
                    OR tenant_id = current_setting('app.tenant_id')::uuid
                );
            CREATE POLICY ex_refstd_tenant_write ON ex_reference_standard FOR ALL
                USING (
                    is_system = FALSE
                    AND tenant_id = current_setting('app.tenant_id')::uuid
                );

            CREATE POLICY ex_catalog_hybrid_read ON ex_measure_catalog FOR SELECT
                USING (
                    tenant_id IS NULL
                    OR tenant_id = current_setting('app.tenant_id')::uuid
                );
            CREATE POLICY ex_catalog_tenant_write ON ex_measure_catalog FOR ALL
                USING (
                    is_system = FALSE
                    AND tenant_id = current_setting('app.tenant_id')::uuid
                );

            CREATE POLICY ex_eqtype_hybrid_read ON ex_equipment_type FOR SELECT
                USING (
                    tenant_id IS NULL
                    OR tenant_id = current_setting('app.tenant_id')::uuid
                );
            CREATE POLICY ex_eqtype_tenant_write ON ex_equipment_type FOR ALL
                USING (
                    is_system = FALSE
                    AND tenant_id = current_setting('app.tenant_id')::uuid
                );
            """,
            reverse_sql="""
            DROP POLICY IF EXISTS ex_area_tenant_isolation ON ex_area;
            DROP POLICY IF EXISTS ex_concept_tenant_isolation ON ex_concept;
            DROP POLICY IF EXISTS ex_zone_tenant_isolation ON ex_zone_definition;
            DROP POLICY IF EXISTS ex_ignition_tenant_isolation ON ex_zone_ignition_assessment;
            DROP POLICY IF EXISTS ex_measure_tenant_isolation ON ex_protection_measure;
            DROP POLICY IF EXISTS ex_safety_fn_tenant_isolation ON ex_safety_function;
            DROP POLICY IF EXISTS ex_equipment_tenant_isolation ON ex_equipment;
            DROP POLICY IF EXISTS ex_inspection_tenant_isolation ON ex_inspection;
            DROP POLICY IF EXISTS ex_verification_tenant_isolation ON ex_verification_document;
            DROP POLICY IF EXISTS ex_refstd_hybrid_read ON ex_reference_standard;
            DROP POLICY IF EXISTS ex_refstd_tenant_write ON ex_reference_standard;
            DROP POLICY IF EXISTS ex_catalog_hybrid_read ON ex_measure_catalog;
            DROP POLICY IF EXISTS ex_catalog_tenant_write ON ex_measure_catalog;
            DROP POLICY IF EXISTS ex_eqtype_hybrid_read ON ex_equipment_type;
            DROP POLICY IF EXISTS ex_eqtype_tenant_write ON ex_equipment_type;
            """,
        ),
    ]
