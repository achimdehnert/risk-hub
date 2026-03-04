"""
Migration: ZoneCalculationResult + EquipmentATEXCheck

BetrSichV §§ 14-17 Compliance:
- ZoneCalculationResult: PROTECT FK, no delete/change permission
- PostgreSQL RLS: DELETE wird auf DB-Ebene verhindert
- EquipmentATEXCheck: PROTECT FK, no delete/change permission
"""

import uuid

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("explosionsschutz", "0003_area_dxf_fields"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="ZoneCalculationResult",
            fields=[
                (
                    "id",
                    models.UUIDField(
                        primary_key=True,
                        default=uuid.uuid4,
                        editable=False,
                        serialize=False,
                    ),
                ),
                ("tenant_id", models.UUIDField(db_index=True)),
                (
                    "substance_name",
                    models.CharField(max_length=200),
                ),
                (
                    "release_rate_kg_s",
                    models.DecimalField(max_digits=12, decimal_places=6),
                ),
                (
                    "ventilation_rate_m3_s",
                    models.DecimalField(max_digits=12, decimal_places=4),
                ),
                (
                    "release_type",
                    models.CharField(
                        max_length=20,
                        choices=[
                            ("jet", "Strahl"),
                            ("pool", "Lache"),
                            ("diffuse", "Diffus"),
                        ],
                    ),
                ),
                (
                    "calculated_zone_type",
                    models.CharField(
                        max_length=5,
                        choices=[
                            ("0", "Zone 0"),
                            ("1", "Zone 1"),
                            ("2", "Zone 2"),
                        ],
                    ),
                ),
                (
                    "calculated_radius_m",
                    models.DecimalField(max_digits=8, decimal_places=3),
                ),
                (
                    "calculated_volume_m3",
                    models.DecimalField(max_digits=12, decimal_places=3),
                ),
                (
                    "basis_norm",
                    models.CharField(
                        max_length=100,
                        default="TRGS 721:2017-09",
                    ),
                ),
                (
                    "riskfw_version",
                    models.CharField(max_length=20),
                ),
                ("raw_result", models.JSONField()),
                (
                    "calculated_at",
                    models.DateTimeField(auto_now_add=True),
                ),
                (
                    "notes",
                    models.TextField(blank=True, default=""),
                ),
                (
                    "zone",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="calculations",
                        to="explosionsschutz.zonedefinition",
                        help_text=("PROTECT: Zone nicht loeschbar solange Nachweis existiert"),
                    ),
                ),
                (
                    "calculated_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="zone_calculations",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "db_table": "ex_zone_calculation_result",
                "verbose_name": "Zonenberechnungs-Nachweis",
                "verbose_name_plural": "Zonenberechnungs-Nachweise",
                "ordering": ["-calculated_at"],
                "default_permissions": ("add", "view"),
            },
        ),
        migrations.CreateModel(
            name="EquipmentATEXCheck",
            fields=[
                (
                    "id",
                    models.UUIDField(
                        primary_key=True,
                        default=uuid.uuid4,
                        editable=False,
                        serialize=False,
                    ),
                ),
                ("tenant_id", models.UUIDField(db_index=True)),
                ("is_suitable", models.BooleanField()),
                ("result", models.JSONField()),
                (
                    "riskfw_version",
                    models.CharField(max_length=20),
                ),
                (
                    "checked_at",
                    models.DateTimeField(auto_now_add=True),
                ),
                (
                    "equipment",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="atex_checks",
                        to="explosionsschutz.equipment",
                    ),
                ),
            ],
            options={
                "db_table": "ex_equipment_atex_check",
                "verbose_name": "ATEX-Eignungsprüfung",
                "verbose_name_plural": "ATEX-Eignungsprüfungen",
                "ordering": ["-checked_at"],
                "default_permissions": ("add", "view"),
            },
        ),
        # PostgreSQL RLS: Verhindert DELETE auf DB-Ebene (BetrSichV §§ 14-17)
        migrations.RunSQL(
            sql="""
                ALTER TABLE ex_zone_calculation_result
                    ENABLE ROW LEVEL SECURITY;

                DROP POLICY IF EXISTS no_delete_zone_calc
                    ON ex_zone_calculation_result;

                CREATE POLICY no_delete_zone_calc
                    ON ex_zone_calculation_result
                    FOR DELETE
                    USING (FALSE);

                ALTER TABLE ex_equipment_atex_check
                    ENABLE ROW LEVEL SECURITY;

                DROP POLICY IF EXISTS no_delete_atex_check
                    ON ex_equipment_atex_check;

                CREATE POLICY no_delete_atex_check
                    ON ex_equipment_atex_check
                    FOR DELETE
                    USING (FALSE);
            """,
            reverse_sql="""
                DROP POLICY IF EXISTS no_delete_zone_calc
                    ON ex_zone_calculation_result;
                ALTER TABLE ex_zone_calculation_result
                    DISABLE ROW LEVEL SECURITY;

                DROP POLICY IF EXISTS no_delete_atex_check
                    ON ex_equipment_atex_check;
                ALTER TABLE ex_equipment_atex_check
                    DISABLE ROW LEVEL SECURITY;
            """,
        ),
    ]
