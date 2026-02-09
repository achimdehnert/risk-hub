"""Add lifecycle fields to Organization + Membership model."""

import uuid

import django.conf
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("tenancy", "0001_initial"),
        migrations.swappable_dependency(
            django.conf.settings.AUTH_USER_MODEL
        ),
    ]

    operations = [
        # --- Organization lifecycle columns ---
        migrations.AddField(
            model_name="organization",
            name="status",
            field=models.CharField(
                choices=[
                    ("trial", "Trial"),
                    ("active", "Active"),
                    ("suspended", "Suspended"),
                    ("deleted", "Deleted"),
                ],
                default="trial",
                max_length=20,
            ),
        ),
        migrations.AddField(
            model_name="organization",
            name="plan_code",
            field=models.CharField(default="free", max_length=50),
        ),
        migrations.AddField(
            model_name="organization",
            name="trial_ends_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="organization",
            name="suspended_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="organization",
            name="suspended_reason",
            field=models.TextField(blank=True, default=""),
        ),
        migrations.AddField(
            model_name="organization",
            name="deleted_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="organization",
            name="settings",
            field=models.JSONField(blank=True, default=dict),
        ),
        migrations.AddField(
            model_name="organization",
            name="updated_at",
            field=models.DateTimeField(auto_now=True),
        ),
        migrations.AddConstraint(
            model_name="organization",
            constraint=models.CheckConstraint(
                check=models.Q(
                    status__in=[
                        "trial", "active", "suspended", "deleted",
                    ],
                ),
                name="org_status_chk",
            ),
        ),
        migrations.AddIndex(
            model_name="organization",
            index=models.Index(
                fields=["status"], name="idx_org_status",
            ),
        ),
        # --- Site: add updated_at ---
        migrations.AddField(
            model_name="site",
            name="updated_at",
            field=models.DateTimeField(auto_now=True),
        ),
        # --- Membership model ---
        migrations.CreateModel(
            name="Membership",
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
                    "role",
                    models.CharField(
                        choices=[
                            ("owner", "Owner"),
                            ("admin", "Admin"),
                            ("member", "Member"),
                            ("viewer", "Viewer"),
                            ("external", "External"),
                        ],
                        default="member",
                        max_length=20,
                    ),
                ),
                (
                    "invited_at",
                    models.DateTimeField(blank=True, null=True),
                ),
                (
                    "accepted_at",
                    models.DateTimeField(blank=True, null=True),
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
                    "user",
                    models.ForeignKey(
                        on_delete=models.deletion.CASCADE,
                        related_name="memberships",
                        to=django.conf.settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "invited_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=models.deletion.SET_NULL,
                        related_name="+",
                        to=django.conf.settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "db_table": "tenancy_membership",
            },
        ),
        migrations.AddConstraint(
            model_name="membership",
            constraint=models.UniqueConstraint(
                fields=("tenant_id", "user"),
                name="membership_unique",
            ),
        ),
        migrations.AddConstraint(
            model_name="membership",
            constraint=models.CheckConstraint(
                check=models.Q(
                    role__in=[
                        "owner", "admin", "member",
                        "viewer", "external",
                    ],
                ),
                name="membership_role_chk",
            ),
        ),
        migrations.AddIndex(
            model_name="membership",
            index=models.Index(
                fields=["tenant_id", "role"],
                name="idx_membership_tenant_role",
            ),
        ),
    ]
