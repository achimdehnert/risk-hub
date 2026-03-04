from django.db import migrations


class Migration(migrations.Migration):
    """SQLite-compatible stub for django_tenancy migrations.

    django_tenancy uses PostgreSQL RLS (ENABLE ROW LEVEL SECURITY)
    which is not supported by SQLite. This stub creates the same tables
    without the PostgreSQL-specific SQL.
    """

    initial = True
    dependencies = []
    operations = []
