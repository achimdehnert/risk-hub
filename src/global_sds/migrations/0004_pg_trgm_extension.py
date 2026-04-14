"""
Enable pg_trgm extension for fuzzy matching (ADR-161 §P0.4).

Required by SdsIdentityResolver for trigram-based similarity search.
"""

from django.contrib.postgres.operations import TrigramExtension
from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("global_sds", "0003_rls_policies"),
    ]

    operations = [
        TrigramExtension(),
    ]
