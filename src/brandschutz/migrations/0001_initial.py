# Generated manually — initial migration for brandschutz app

import uuid

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        ("tenancy", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="FireProtectionConcept",
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
                ("tenant_id", models.UUIDField(db_index=True)),
                (
                    "site",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="fire_protection_concepts",
                        to="tenancy.site",
                    ),
                ),
                ("title", models.CharField(max_length=240)),
                (
                    "concept_type",
                    models.CharField(
                        choices=[
                            ("basic", "Basiskonzept (§14 MBO)"),
                            ("full", "Vollständiges Brandschutzkonzept"),
                            ("operational", "Betrieblicher Brandschutz"),
                        ],
                        default="basic",
                        max_length=20,
                    ),
                ),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("draft", "Entwurf"),
                            ("in_review", "In Prüfung"),
                            ("approved", "Freigegeben"),
                            ("outdated", "Veraltet"),
                        ],
                        db_index=True,
                        default="draft",
                        max_length=15,
                    ),
                ),
                ("description", models.TextField(blank=True, default="")),
                ("valid_from", models.DateField(blank=True, null=True)),
                ("valid_until", models.DateField(blank=True, null=True)),
                (
                    "responsible_user_id",
                    models.UUIDField(blank=True, null=True),
                ),
                ("approved_by_id", models.UUIDField(blank=True, null=True)),
                ("approved_at", models.DateTimeField(blank=True, null=True)),
                ("created_by_id", models.UUIDField(blank=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={
                "verbose_name": "Brandschutzkonzept",
                "verbose_name_plural": "Brandschutzkonzepte",
                "db_table": "brandschutz_concept",
                "ordering": ["-created_at"],
                "indexes": [
                    models.Index(
                        fields=["tenant_id", "status"],
                        name="ix_brandschutz_concept_tenant_status",
                    ),
                ],
                "constraints": [
                    models.CheckConstraint(
                        condition=models.Q(
                            status__in=["draft", "in_review", "approved", "outdated"]
                        ),
                        name="ck_brandschutz_concept_status",
                    ),
                ],
            },
        ),
        migrations.CreateModel(
            name="FireSection",
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
                ("tenant_id", models.UUIDField(db_index=True)),
                (
                    "concept",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="sections",
                        to="brandschutz.fireprotectionconcept",
                    ),
                ),
                ("name", models.CharField(max_length=200)),
                ("floor", models.CharField(blank=True, default="", max_length=50)),
                ("area_sqm", models.FloatField(blank=True, null=True)),
                (
                    "construction_class",
                    models.CharField(
                        blank=True,
                        choices=[
                            ("GK1", "GK1 — Freistehend, eingeschossig"),
                            ("GK2", "GK2 — bis 7 m, max. 2 Vollgeschosse"),
                            ("GK3", "GK3 — bis 7 m, mehr als 2 Vollgeschosse"),
                            ("GK4", "GK4 — bis 13 m Höhe"),
                            ("GK5", "GK5 — Hochhaus (>13 m)"),
                        ],
                        default="",
                        max_length=5,
                    ),
                ),
                ("max_occupancy", models.PositiveIntegerField(blank=True, null=True)),
                ("fire_load_mj_m2", models.FloatField(blank=True, null=True)),
                ("has_sprinkler", models.BooleanField(default=False)),
                ("has_smoke_detector", models.BooleanField(default=False)),
                ("notes", models.TextField(blank=True, default="")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
            ],
            options={
                "verbose_name": "Brandabschnitt",
                "verbose_name_plural": "Brandabschnitte",
                "db_table": "brandschutz_section",
                "ordering": ["concept", "floor", "name"],
                "constraints": [
                    models.UniqueConstraint(
                        fields=("concept", "name"),
                        name="uq_brandschutz_section_name_per_concept",
                    ),
                ],
            },
        ),
        migrations.CreateModel(
            name="EscapeRoute",
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
                ("tenant_id", models.UUIDField(db_index=True)),
                (
                    "section",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="escape_routes",
                        to="brandschutz.firesection",
                    ),
                ),
                (
                    "route_type",
                    models.CharField(
                        choices=[
                            ("primary", "Erster Fluchtweg"),
                            ("secondary", "Zweiter Fluchtweg"),
                            ("emergency_exit", "Notausgang"),
                            ("rescue_access", "Rettungszugang (Feuerwehr)"),
                        ],
                        max_length=20,
                    ),
                ),
                ("description", models.TextField()),
                ("length_m", models.FloatField(blank=True, null=True)),
                ("width_m", models.FloatField(blank=True, null=True)),
                ("door_width_m", models.FloatField(blank=True, null=True)),
                ("is_signposted", models.BooleanField(default=False)),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("ok", "In Ordnung"),
                            ("deficient", "Mängel vorhanden"),
                            ("blocked", "Blockiert"),
                        ],
                        db_index=True,
                        default="ok",
                        max_length=15,
                    ),
                ),
                (
                    "last_inspection_date",
                    models.DateField(blank=True, null=True),
                ),
                ("deficiency_notes", models.TextField(blank=True, default="")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={
                "verbose_name": "Flucht- und Rettungsweg",
                "verbose_name_plural": "Flucht- und Rettungswege",
                "db_table": "brandschutz_escape_route",
                "ordering": ["section", "route_type"],
            },
        ),
        migrations.CreateModel(
            name="FireExtinguisher",
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
                ("tenant_id", models.UUIDField(db_index=True)),
                (
                    "section",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="fire_extinguishers",
                        to="brandschutz.firesection",
                    ),
                ),
                (
                    "serial_number",
                    models.CharField(blank=True, default="", max_length=100),
                ),
                (
                    "extinguisher_type",
                    models.CharField(
                        choices=[
                            ("water", "Wasserlöscher"),
                            ("foam", "Schaumlöscher"),
                            ("co2", "CO₂-Löscher"),
                            ("dry_powder", "Pulverlöscher"),
                            ("wet_chemical", "Fettbrandlöscher"),
                            ("abc_powder", "ABC-Pulverlöscher"),
                        ],
                        max_length=20,
                    ),
                ),
                ("capacity_kg", models.FloatField()),
                (
                    "fire_class",
                    models.CharField(blank=True, default="", max_length=20),
                ),
                (
                    "location_description",
                    models.CharField(max_length=300),
                ),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("operational", "Betriebsbereit"),
                            ("inspection_due", "Prüfung fällig"),
                            ("defective", "Defekt"),
                            ("retired", "Ausgemustert"),
                        ],
                        db_index=True,
                        default="operational",
                        max_length=20,
                    ),
                ),
                (
                    "last_inspection_date",
                    models.DateField(blank=True, null=True),
                ),
                (
                    "next_inspection_date",
                    models.DateField(blank=True, null=True),
                ),
                ("installed_at", models.DateField(blank=True, null=True)),
                ("notes", models.TextField(blank=True, default="")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={
                "verbose_name": "Feuerlöscher",
                "verbose_name_plural": "Feuerlöscher",
                "db_table": "brandschutz_extinguisher",
                "ordering": ["section", "extinguisher_type"],
                "indexes": [
                    models.Index(
                        fields=["tenant_id", "status"],
                        name="ix_brandschutz_ext_tenant_status",
                    ),
                    models.Index(
                        fields=["tenant_id", "next_inspection_date"],
                        name="ix_brandschutz_ext_inspection",
                    ),
                ],
            },
        ),
        migrations.CreateModel(
            name="FireProtectionMeasure",
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
                ("tenant_id", models.UUIDField(db_index=True)),
                (
                    "concept",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="measures",
                        to="brandschutz.fireprotectionconcept",
                    ),
                ),
                (
                    "section",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="measures",
                        to="brandschutz.firesection",
                    ),
                ),
                (
                    "category",
                    models.CharField(
                        choices=[
                            ("structural", "Baulicher Brandschutz"),
                            ("technical", "Anlagentechnischer Brandschutz"),
                            ("organizational", "Organisatorischer Brandschutz"),
                        ],
                        db_index=True,
                        max_length=20,
                    ),
                ),
                ("title", models.CharField(max_length=300)),
                ("description", models.TextField(blank=True, default="")),
                (
                    "legal_basis",
                    models.CharField(blank=True, default="", max_length=200),
                ),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("open", "Offen"),
                            ("in_progress", "In Bearbeitung"),
                            ("implemented", "Umgesetzt"),
                            ("accepted", "Akzeptiertes Risiko"),
                        ],
                        db_index=True,
                        default="open",
                        max_length=15,
                    ),
                ),
                (
                    "responsible_user_id",
                    models.UUIDField(blank=True, null=True),
                ),
                ("due_date", models.DateField(blank=True, null=True)),
                (
                    "completed_at",
                    models.DateTimeField(blank=True, null=True),
                ),
                ("sort_order", models.PositiveSmallIntegerField(default=0)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={
                "verbose_name": "Brandschutzmaßnahme",
                "verbose_name_plural": "Brandschutzmaßnahmen",
                "db_table": "brandschutz_measure",
                "ordering": ["category", "sort_order", "title"],
                "indexes": [
                    models.Index(
                        fields=["tenant_id", "status"],
                        name="ix_brandschutz_measure_tenant_status",
                    ),
                ],
            },
        ),
    ]
