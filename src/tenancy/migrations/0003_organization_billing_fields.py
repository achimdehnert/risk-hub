"""Add ADR-118 billing fields to Organization (is_readonly, deactivation_reason, gdpr_delete_at)."""

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("tenancy", "0002_module_subscriptions_data"),
    ]

    operations = [
        migrations.AddField(
            model_name="organization",
            name="is_readonly",
            field=models.BooleanField(
                default=False,
                help_text=(
                    "True when subscription ended "
                    "\u2014 read-only access until gdpr_delete_at"
                ),
            ),
        ),
        migrations.AddField(
            model_name="organization",
            name="deactivation_reason",
            field=models.TextField(
                blank=True,
                default="",
                help_text="Reason provided by billing-hub on deactivation",
            ),
        ),
        migrations.AddField(
            model_name="organization",
            name="gdpr_delete_at",
            field=models.DateTimeField(
                null=True,
                blank=True,
                help_text=(
                    "Scheduled hard-delete date "
                    "(90 days after deactivation, GDPR)"
                ),
            ),
        ),
    ]
