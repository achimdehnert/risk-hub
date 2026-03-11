"""No-op: Organization and Membership are now owned by the tenancy app.

This migration is kept as a placeholder so the dependency chain
(django_tenancy.0001 → tenancy.0001 → django_tenancy.0002) remains valid.
Previously-applied instances are harmless — Django won't re-run them.
"""

from django.db import migrations


class Migration(migrations.Migration):
    initial = True

    dependencies = []

    operations = []
