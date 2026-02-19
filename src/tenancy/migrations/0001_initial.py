# Rewritten: Organization + Membership now owned by django_tenancy package.
# The DB tables (tenancy_organization, tenancy_membership) are identical —
# django_tenancy.0001_initial creates them. This migration only owns Site.

import django.db.models.deletion
import uuid
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        # django_tenancy package owns Organization + Membership tables.
        ("django_tenancy", "0002_module_subscription_module_membership"),
    ]

    operations = [
        migrations.CreateModel(
            name="Site",
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
                ("name", models.CharField(max_length=200)),
                ("address", models.TextField(blank=True, default="")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "organization",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="sites",
                        to="django_tenancy.organization",
                    ),
                ),
            ],
            options={
                "db_table": "tenancy_site",
                "constraints": [
                    models.UniqueConstraint(
                        fields=("tenant_id", "name"),
                        name="uq_site_name_per_tenant",
                    ),
                ],
            },
        ),
    ]
