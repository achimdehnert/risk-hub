"""Initial migration for billing app."""

from __future__ import annotations

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
            name="StripeCustomer",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False)),
                ("stripe_customer_id", models.CharField(max_length=100, unique=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "organization",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="stripe_customer",
                        to="tenancy.organization",
                    ),
                ),
            ],
            options={"db_table": "billing_stripe_customer"},
        ),
        migrations.CreateModel(
            name="StripeSubscription",
            fields=[
                (
                    "id",
                    models.UUIDField(
                        default=uuid.uuid4, editable=False, primary_key=True, serialize=False
                    ),
                ),
                ("stripe_subscription_id", models.CharField(max_length=100, unique=True)),
                ("stripe_price_id", models.CharField(max_length=100)),
                (
                    "plan_code",
                    models.CharField(
                        help_text="starter / professional / business / enterprise", max_length=50
                    ),
                ),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("trialing", "Trial"),
                            ("active", "Aktiv"),
                            ("past_due", "Zahlung überfällig"),
                            ("canceled", "Gekündigt"),
                            ("unpaid", "Unbezahlt"),
                            ("incomplete", "Unvollständig"),
                        ],
                        default="trialing",
                        max_length=30,
                    ),
                ),
                ("current_period_start", models.DateTimeField(blank=True, null=True)),
                ("current_period_end", models.DateTimeField(blank=True, null=True)),
                ("cancel_at_period_end", models.BooleanField(default=False)),
                ("canceled_at", models.DateTimeField(blank=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "organization",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="stripe_subscriptions",
                        to="tenancy.organization",
                    ),
                ),
            ],
            options={"db_table": "billing_stripe_subscription", "ordering": ["-created_at"]},
        ),
        migrations.CreateModel(
            name="BillingEvent",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False)),
                ("stripe_event_id", models.CharField(max_length=100, unique=True)),
                ("event_type", models.CharField(max_length=100)),
                ("payload", models.JSONField()),
                ("processed", models.BooleanField(default=False)),
                ("error", models.TextField(blank=True, default="")),
                ("received_at", models.DateTimeField(auto_now_add=True)),
            ],
            options={"db_table": "billing_event", "ordering": ["-received_at"]},
        ),
    ]
