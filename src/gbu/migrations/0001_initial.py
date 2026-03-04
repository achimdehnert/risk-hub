import uuid

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        ("documents", "0001_initial"),
        ("substances", "0001_initial"),
        ("tenancy", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="HazardCategoryRef",
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
                ("code", models.CharField(max_length=30, unique=True)),
                ("name", models.CharField(max_length=200)),
                (
                    "category_type",
                    models.CharField(
                        choices=[
                            ("fire_explosion", "fire_explosion"),
                            ("acute_toxic", "acute_toxic"),
                            ("chronic_toxic", "chronic_toxic"),
                            ("skin_corrosion", "skin_corrosion"),
                            ("eye_damage", "eye_damage"),
                            ("respiratory", "respiratory"),
                            ("skin_sens", "skin_sens"),
                            ("cmr", "cmr"),
                            ("environment", "environment"),
                            ("asphyxiant", "asphyxiant"),
                        ],
                        db_index=True,
                        max_length=30,
                    ),
                ),
                (
                    "trgs_reference",
                    models.CharField(
                        blank=True,
                        default="",
                        max_length=50,
                        help_text="z.B. 'TRGS 400 Abschnitt 5.3'",
                    ),
                ),
                ("description", models.TextField(blank=True, default="")),
                ("sort_order", models.PositiveSmallIntegerField(default=0)),
            ],
            options={
                "verbose_name": "Gefährdungskategorie",
                "verbose_name_plural": "Gefährdungskategorien",
                "db_table": "gbu_hazard_category_ref",
                "ordering": ["category_type", "sort_order", "name"],
            },
        ),
        migrations.CreateModel(
            name="MeasureTemplate",
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
                    "tops_type",
                    models.CharField(
                        choices=[
                            ("S", "Substitution"),
                            ("T", "Technical"),
                            ("O", "Organisational"),
                            ("P", "Personal"),
                        ],
                        db_index=True,
                        max_length=1,
                    ),
                ),
                ("title", models.CharField(max_length=300)),
                ("description", models.TextField(blank=True, default="")),
                (
                    "legal_basis",
                    models.CharField(
                        blank=True,
                        default="",
                        max_length=200,
                        help_text="z.B. 'GefStoffV §7, TRGS 500'",
                    ),
                ),
                (
                    "is_mandatory",
                    models.BooleanField(
                        default=False,
                        help_text="Pflichtmaßnahme (keine Ablehnung möglich)",
                    ),
                ),
                ("sort_order", models.PositiveSmallIntegerField(default=0)),
                (
                    "category",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="measure_templates",
                        to="gbu.hazardcategoryref",
                    ),
                ),
            ],
            options={
                "verbose_name": "Maßnahmen-Vorlage",
                "verbose_name_plural": "Maßnahmen-Vorlagen",
                "db_table": "gbu_measure_template",
                "ordering": ["tops_type", "sort_order"],
            },
        ),
        migrations.CreateModel(
            name="HCodeCategoryMapping",
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
                    "h_code",
                    models.CharField(
                        db_index=True,
                        max_length=10,
                        help_text="z.B. 'H220', 'H301'",
                    ),
                ),
                (
                    "annotation",
                    models.TextField(
                        blank=True,
                        default="",
                        help_text="Begründung / TRGS-Verweis",
                    ),
                ),
                (
                    "category",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="h_code_mappings",
                        to="gbu.hazardcategoryref",
                    ),
                ),
            ],
            options={
                "verbose_name": "H-Code Mapping",
                "verbose_name_plural": "H-Code Mappings",
                "db_table": "gbu_h_code_category_mapping",
                "ordering": ["h_code"],
            },
        ),
        migrations.AlterUniqueTogether(
            name="hcodecategorymapping",
            unique_together={("h_code", "category")},
        ),
        migrations.CreateModel(
            name="HazardAssessmentActivity",
            fields=[
                (
                    "id",
                    models.UUIDField(
                        default=uuid.uuid4,
                        editable=False,
                        primary_key=True,
                        serialize=False,
                    ),
                ),
                (
                    "tenant_id",
                    models.UUIDField(
                        db_index=True,
                        help_text="Tenant-ID für Mandantentrennung",
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("created_by", models.UUIDField(blank=True, null=True)),
                (
                    "activity_description",
                    models.TextField(
                        help_text="Tätigkeitsbeschreibung (was wird gemacht, womit, wie lange)",
                    ),
                ),
                (
                    "activity_frequency",
                    models.CharField(
                        choices=[
                            ("daily", "Daily"),
                            ("weekly", "Weekly"),
                            ("occasional", "Occasional"),
                            ("rare", "Rare"),
                        ],
                        max_length=15,
                    ),
                ),
                (
                    "duration_minutes",
                    models.PositiveSmallIntegerField(
                        help_text="Expositionsdauer in Minuten pro Vorgang",
                    ),
                ),
                (
                    "quantity_class",
                    models.CharField(
                        choices=[("xs", "XS"), ("s", "S"), ("m", "M"), ("l", "L")],
                        help_text="Mengenkategorie nach EMKG",
                        max_length=2,
                    ),
                ),
                (
                    "substitution_checked",
                    models.BooleanField(
                        default=False,
                        help_text="Substitutionsprüfung nach §7 GefStoffV durchgeführt",
                    ),
                ),
                ("substitution_notes", models.TextField(blank=True, default="")),
                (
                    "risk_score",
                    models.CharField(
                        blank=True,
                        choices=[
                            ("low", "Low"),
                            ("medium", "Medium"),
                            ("high", "High"),
                            ("critical", "Critical"),
                        ],
                        default="",
                        help_text="EMKG-Risikostufe (berechnet)",
                        max_length=10,
                    ),
                ),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("draft", "Draft"),
                            ("review", "Review"),
                            ("approved", "Approved"),
                            ("outdated", "Outdated"),
                        ],
                        db_index=True,
                        default="draft",
                        max_length=10,
                    ),
                ),
                (
                    "approved_by_id",
                    models.UUIDField(
                        blank=True,
                        db_index=True,
                        null=True,
                        help_text="UUID der freigebenden Person (unveränderlich nach Freigabe)",
                    ),
                ),
                (
                    "approved_by_name",
                    models.CharField(
                        blank=True,
                        default="",
                        max_length=200,
                        help_text="Vollname der freigebenden Person (Snapshot, immutable)",
                    ),
                ),
                ("approved_at", models.DateTimeField(blank=True, null=True)),
                (
                    "next_review_date",
                    models.DateField(
                        blank=True,
                        null=True,
                        help_text="Nächste Überprüfung (GefStoffV §6)",
                    ),
                ),
                (
                    "ba_document",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="+",
                        to="documents.documentversion",
                        help_text="Generierte Betriebsanweisung (TRGS 555)",
                    ),
                ),
                (
                    "derived_hazard_categories",
                    models.ManyToManyField(
                        blank=True,
                        help_text="Auto-abgeleitete Gefährdungskategorien (via H-Code-Mapping)",
                        related_name="activities",
                        to="gbu.hazardcategoryref",
                    ),
                ),
                (
                    "gbu_document",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="+",
                        to="documents.documentversion",
                        help_text="Generiertes GBU-PDF",
                    ),
                ),
                (
                    "sds_revision",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="gbu_activities",
                        to="substances.sdsrevision",
                    ),
                ),
                (
                    "site",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="gbu_activities",
                        to="tenancy.site",
                    ),
                ),
            ],
            options={
                "verbose_name": "GBU-Tätigkeit",
                "verbose_name_plural": "GBU-Tätigkeiten",
                "db_table": "gbu_hazard_assessment_activity",
                "ordering": ["-created_at"],
                "default_permissions": ("add", "change", "view"),
            },
        ),
        migrations.AddIndex(
            model_name="hazardassessmentactivity",
            index=models.Index(
                fields=["tenant_id", "status"],
                name="ix_gbu_activity_tenant_status",
            ),
        ),
        migrations.AddIndex(
            model_name="hazardassessmentactivity",
            index=models.Index(
                fields=["tenant_id", "next_review_date"],
                name="ix_gbu_activity_review_date",
            ),
        ),
        migrations.CreateModel(
            name="ActivityMeasure",
            fields=[
                (
                    "id",
                    models.UUIDField(
                        default=uuid.uuid4,
                        editable=False,
                        primary_key=True,
                        serialize=False,
                    ),
                ),
                (
                    "tenant_id",
                    models.UUIDField(
                        db_index=True,
                        help_text="Denormalisiert von HazardAssessmentActivity.tenant_id (ADR-003)",
                    ),
                ),
                (
                    "tops_type",
                    models.CharField(
                        choices=[
                            ("S", "Substitution"),
                            ("T", "Technical"),
                            ("O", "Organisational"),
                            ("P", "Personal"),
                        ],
                        max_length=1,
                    ),
                ),
                ("title", models.CharField(max_length=300)),
                ("description", models.TextField(blank=True, default="")),
                ("legal_basis", models.CharField(blank=True, default="", max_length=200)),
                (
                    "is_confirmed",
                    models.BooleanField(
                        default=False,
                        help_text="Vom Nutzer bestätigt (nicht nur Vorlage)",
                    ),
                ),
                ("is_mandatory", models.BooleanField(default=False)),
                ("sort_order", models.PositiveSmallIntegerField(default=0)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "activity",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="measures",
                        to="gbu.hazardassessmentactivity",
                    ),
                ),
                (
                    "template",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.PROTECT,
                        to="gbu.measuretemplate",
                        help_text="Vorlage aus der Datenbank (optional)",
                    ),
                ),
            ],
            options={
                "verbose_name": "GBU-Schutzmaßnahme",
                "verbose_name_plural": "GBU-Schutzmaßnahmen",
                "db_table": "gbu_activity_measure",
                "ordering": ["tops_type", "sort_order"],
            },
        ),
    ]
