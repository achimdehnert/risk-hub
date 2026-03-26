# src/global_sds/migrations/0001_initial.py
"""
Initial migration for Global SDS Library (ADR-012).

Creates: GlobalSubstance, GlobalSdsRevision, GlobalSdsComponent,
GlobalSdsExposureLimit, SdsRevisionDiffRecord, SdsUsage.
"""

import uuid

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("substances", "0002_substance_gestis_fields"),
    ]

    operations = [
        # ── GlobalSubstance ──
        migrations.CreateModel(
            name="GlobalSubstance",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "uuid",
                    models.UUIDField(
                        default=uuid.uuid4,
                        editable=False,
                        unique=True,
                    ),
                ),
                (
                    "cas_number",
                    models.CharField(
                        blank=True,
                        help_text="CAS Registry Number (z.B. 111-76-2)",
                        max_length=20,
                        null=True,
                        unique=True,
                    ),
                ),
                (
                    "ec_number",
                    models.CharField(
                        blank=True,
                        default="",
                        help_text="EC/EINECS-Nummer",
                        max_length=20,
                    ),
                ),
                (
                    "name",
                    models.CharField(
                        help_text="IUPAC oder gebräuchlicher Name",
                        max_length=512,
                    ),
                ),
                (
                    "synonyms",
                    models.JSONField(
                        blank=True,
                        default=list,
                        help_text="Alternative Namen",
                    ),
                ),
                (
                    "chemical_formula",
                    models.CharField(
                        blank=True, default="", max_length=200,
                    ),
                ),
                (
                    "created_at",
                    models.DateTimeField(auto_now_add=True),
                ),
            ],
            options={
                "verbose_name": "Globale Substanz",
                "verbose_name_plural": "Globale Substanzen",
                "db_table": "global_sds_substance",
                "ordering": ["name"],
            },
        ),
        # ── GlobalSdsRevision ──
        migrations.CreateModel(
            name="GlobalSdsRevision",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "uuid",
                    models.UUIDField(
                        default=uuid.uuid4,
                        editable=False,
                        unique=True,
                    ),
                ),
                (
                    "source_hash",
                    models.CharField(
                        help_text="SHA-256 des Original-PDFs",
                        max_length=64,
                        unique=True,
                    ),
                ),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("PENDING", "Ausstehend (nur Uploader)"),
                            ("VERIFIED", "Verifiziert (global)"),
                            ("REJECTED", "Abgelehnt"),
                            ("SUPERSEDED", "Abgelöst"),
                        ],
                        default="PENDING",
                        max_length=20,
                    ),
                ),
                (
                    "uploaded_by_tenant_id",
                    models.UUIDField(db_index=True),
                ),
                (
                    "manufacturer_name",
                    models.CharField(
                        blank=True, default="", max_length=256,
                    ),
                ),
                (
                    "product_name",
                    models.CharField(max_length=512),
                ),
                (
                    "revision_date",
                    models.DateField(blank=True, null=True),
                ),
                (
                    "version_number",
                    models.CharField(
                        blank=True, default="", max_length=20,
                    ),
                ),
                (
                    "wgk",
                    models.PositiveSmallIntegerField(
                        blank=True, null=True,
                    ),
                ),
                (
                    "storage_class_trgs510",
                    models.CharField(
                        blank=True, default="", max_length=5,
                    ),
                ),
                (
                    "voc_percent",
                    models.DecimalField(
                        blank=True, decimal_places=3,
                        max_digits=6, null=True,
                    ),
                ),
                (
                    "voc_g_per_l",
                    models.DecimalField(
                        blank=True, decimal_places=2,
                        max_digits=8, null=True,
                    ),
                ),
                (
                    "flash_point_c",
                    models.DecimalField(
                        blank=True, decimal_places=2,
                        max_digits=7, null=True,
                    ),
                ),
                (
                    "ignition_temperature_c",
                    models.DecimalField(
                        blank=True, decimal_places=2,
                        max_digits=7, null=True,
                    ),
                ),
                (
                    "lower_explosion_limit",
                    models.DecimalField(
                        blank=True, decimal_places=3,
                        max_digits=6, null=True,
                    ),
                ),
                (
                    "upper_explosion_limit",
                    models.DecimalField(
                        blank=True, decimal_places=3,
                        max_digits=6, null=True,
                    ),
                ),
                (
                    "parse_confidence",
                    models.FloatField(blank=True, null=True),
                ),
                (
                    "llm_corrections",
                    models.JSONField(blank=True, default=list),
                ),
                (
                    "signal_word",
                    models.CharField(
                        blank=True, default="", max_length=20,
                    ),
                ),
                (
                    "created_at",
                    models.DateTimeField(auto_now_add=True),
                ),
                (
                    "updated_at",
                    models.DateTimeField(auto_now=True),
                ),
                (
                    "substance",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="revisions",
                        to="global_sds.globalsubstance",
                    ),
                ),
                (
                    "superseded_by",
                    models.OneToOneField(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="supersedes",
                        to="global_sds.globalsdsrevision",
                    ),
                ),
                (
                    "hazard_statements",
                    models.ManyToManyField(
                        blank=True,
                        related_name="global_sds_revisions",
                        to="substances.hazardstatementref",
                    ),
                ),
                (
                    "precautionary_statements",
                    models.ManyToManyField(
                        blank=True,
                        related_name="global_sds_revisions",
                        to="substances.precautionarystatementref",
                    ),
                ),
                (
                    "pictograms",
                    models.ManyToManyField(
                        blank=True,
                        related_name="global_sds_revisions",
                        to="substances.pictogramref",
                    ),
                ),
            ],
            options={
                "verbose_name": "Globale SDS-Revision",
                "verbose_name_plural": "Globale SDS-Revisionen",
                "db_table": "global_sds_sdsrevision",
                "ordering": ["-revision_date", "-created_at"],
            },
        ),
        # ── GlobalSdsComponent ──
        migrations.CreateModel(
            name="GlobalSdsComponent",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "chemical_name",
                    models.CharField(max_length=512),
                ),
                (
                    "cas_number",
                    models.CharField(
                        blank=True, db_index=True,
                        default="", max_length=20,
                    ),
                ),
                (
                    "ec_number",
                    models.CharField(
                        blank=True, default="", max_length=20,
                    ),
                ),
                (
                    "concentration_min",
                    models.DecimalField(
                        blank=True, decimal_places=4,
                        max_digits=7, null=True,
                    ),
                ),
                (
                    "concentration_max",
                    models.DecimalField(
                        blank=True, decimal_places=4,
                        max_digits=7, null=True,
                    ),
                ),
                (
                    "concentration_note",
                    models.CharField(
                        blank=True, default="", max_length=100,
                    ),
                ),
                (
                    "m_factor_acute",
                    models.PositiveSmallIntegerField(
                        blank=True, null=True,
                    ),
                ),
                (
                    "m_factor_chronic",
                    models.PositiveSmallIntegerField(
                        blank=True, null=True,
                    ),
                ),
                (
                    "sds_revision",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="components",
                        to="global_sds.globalsdsrevision",
                    ),
                ),
                (
                    "hazard_statements",
                    models.ManyToManyField(
                        blank=True,
                        related_name="global_sds_components",
                        to="substances.hazardstatementref",
                    ),
                ),
            ],
            options={
                "verbose_name": "SDS-Inhaltsstoff",
                "verbose_name_plural": "SDS-Inhaltsstoffe",
                "db_table": "global_sds_sdscomponent",
            },
        ),
        # ── GlobalSdsExposureLimit ──
        migrations.CreateModel(
            name="GlobalSdsExposureLimit",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "limit_type",
                    models.CharField(
                        choices=[
                            ("AGW", "Arbeitsplatzgrenzwert (TRGS 900)"),
                            ("STEL", "Kurzzeitgrenzwert"),
                            ("TWA", "Zeitgewichteter Mittelwert"),
                            ("BGW", "Biologischer Grenzwert (TRGS 903)"),
                            ("DNEL_W", "DNEL Arbeitnehmer"),
                            ("DNEL_C", "DNEL Verbraucher"),
                            ("PNEC", "PNEC Umwelt"),
                        ],
                        max_length=10,
                    ),
                ),
                (
                    "route",
                    models.CharField(
                        choices=[
                            ("INH", "Einatmung"),
                            ("DERM", "Haut"),
                            ("ORAL", "Oral"),
                            ("FW", "Süßwasser"),
                            ("MW", "Meerwasser"),
                            ("SOIL", "Boden"),
                            ("STP", "Abwasserkläranlage"),
                        ],
                        max_length=10,
                    ),
                ),
                (
                    "value",
                    models.DecimalField(
                        decimal_places=4, max_digits=12,
                    ),
                ),
                (
                    "unit",
                    models.CharField(max_length=40),
                ),
                (
                    "effect_type",
                    models.CharField(
                        blank=True, default="", max_length=100,
                    ),
                ),
                (
                    "basis",
                    models.CharField(
                        blank=True, default="", max_length=100,
                    ),
                ),
                (
                    "component",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="exposure_limits",
                        to="global_sds.globalsdscomponent",
                    ),
                ),
                (
                    "sds_revision",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="exposure_limits",
                        to="global_sds.globalsdsrevision",
                    ),
                ),
            ],
            options={
                "verbose_name": "Expositionsgrenzwert",
                "verbose_name_plural": "Expositionsgrenzwerte",
                "db_table": "global_sds_sdsexposurelimit",
            },
        ),
        # ── SdsRevisionDiffRecord ──
        migrations.CreateModel(
            name="SdsRevisionDiffRecord",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "overall_impact",
                    models.CharField(
                        choices=[
                            ("SAFETY_CRITICAL", "Safety Critical"),
                            ("REGULATORY", "Regulatory"),
                            ("INFORMATIONAL", "Informational"),
                        ],
                        max_length=20,
                    ),
                ),
                (
                    "field_diffs",
                    models.JSONField(),
                ),
                (
                    "added_h_codes",
                    models.JSONField(default=list),
                ),
                (
                    "removed_h_codes",
                    models.JSONField(default=list),
                ),
                (
                    "changed_components",
                    models.JSONField(default=list),
                ),
                (
                    "computed_at",
                    models.DateTimeField(auto_now_add=True),
                ),
                (
                    "old_revision",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="diffs_as_old",
                        to="global_sds.globalsdsrevision",
                    ),
                ),
                (
                    "new_revision",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="diffs_as_new",
                        to="global_sds.globalsdsrevision",
                    ),
                ),
            ],
            options={
                "verbose_name": "SDS-Revisions-Diff",
                "verbose_name_plural": "SDS-Revisions-Diffs",
                "db_table": "global_sds_revisiondiff",
            },
        ),
        # ── SdsUsage (tenant-scoped) ──
        migrations.CreateModel(
            name="SdsUsage",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "tenant_id",
                    models.UUIDField(db_index=True),
                ),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("ACTIVE", "Aktiv"),
                            ("PENDING_APPROVAL", "Wartet auf Freigabe"),
                            ("REVIEW_REQUIRED", "Überprüfung erforderlich"),
                            ("UPDATE_AVAILABLE", "Update verfügbar"),
                            ("SUPERSEDED", "Abgelöst"),
                            ("WITHDRAWN", "Zurückgezogen"),
                        ],
                        default="PENDING_APPROVAL",
                        max_length=20,
                    ),
                ),
                (
                    "approval_date",
                    models.DateTimeField(blank=True, null=True),
                ),
                (
                    "internal_note",
                    models.TextField(blank=True, default=""),
                ),
                (
                    "pending_update_impact",
                    models.CharField(
                        blank=True, default="", max_length=20,
                    ),
                ),
                (
                    "review_deadline",
                    models.DateField(blank=True, null=True),
                ),
                (
                    "update_deferred_reason",
                    models.TextField(blank=True, default=""),
                ),
                (
                    "update_deferred_until",
                    models.DateField(blank=True, null=True),
                ),
                (
                    "created_at",
                    models.DateTimeField(auto_now_add=True),
                ),
                (
                    "updated_at",
                    models.DateTimeField(auto_now=True),
                ),
                (
                    "sds_revision",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="usages",
                        to="global_sds.globalsdsrevision",
                    ),
                ),
                (
                    "pending_update_revision",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="pending_for_usages",
                        to="global_sds.globalsdsrevision",
                    ),
                ),
                (
                    "approved_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="approved_sds_usages",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "update_deferred_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="deferred_sds_updates",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "verbose_name": "SDS-Nutzung (Tenant)",
                "verbose_name_plural": "SDS-Nutzungen (Tenant)",
                "db_table": "global_sds_usage",
            },
        ),
        # ── Constraints ──
        migrations.AddConstraint(
            model_name="globalsdsrevision",
            constraint=models.CheckConstraint(
                check=models.Q(
                    ("superseded_by", models.F("id")),
                    _negated=True,
                ),
                name="chk_sdsrevision_no_self_supersession",
            ),
        ),
        migrations.AddConstraint(
            model_name="globalsdsexposurelimit",
            constraint=models.UniqueConstraint(
                fields=[
                    "sds_revision", "component",
                    "limit_type", "route",
                ],
                name="uq_exposure_limit_per_component_route",
            ),
        ),
        migrations.AddConstraint(
            model_name="sdsrevisiondiffrecord",
            constraint=models.UniqueConstraint(
                fields=["old_revision", "new_revision"],
                name="uq_diff_per_revision_pair",
            ),
        ),
        migrations.AddConstraint(
            model_name="sdsusage",
            constraint=models.UniqueConstraint(
                fields=["tenant_id", "sds_revision"],
                name="uq_sds_usage_per_tenant",
            ),
        ),
        migrations.AddConstraint(
            model_name="sdsusage",
            constraint=models.CheckConstraint(
                check=(
                    models.Q(("status", "ACTIVE"), _negated=True)
                    | models.Q(approved_by__isnull=False)
                ),
                name="chk_sds_usage_active_requires_approver",
            ),
        ),
        # ── Indexes ──
        migrations.AddIndex(
            model_name="globalsdsrevision",
            index=models.Index(
                fields=["source_hash"],
                name="ix_global_sds_source_hash",
            ),
        ),
        migrations.AddIndex(
            model_name="globalsdsrevision",
            index=models.Index(
                fields=["status", "uploaded_by_tenant_id"],
                name="ix_global_sds_status_tenant",
            ),
        ),
        migrations.AddIndex(
            model_name="sdsusage",
            index=models.Index(
                fields=["tenant_id", "status"],
                name="ix_sds_usage_tenant_status",
            ),
        ),
    ]
