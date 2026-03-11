"""Setup PostgreSQL roles for RLS (ADR-137 Phase 2.3).

Creates a separate app-user role that is NOT the table owner,
so RLS policies apply to it. The migrations-user (table owner)
remains RLS-exempt without needing FORCE ROW LEVEL SECURITY.

Usage::

    python manage.py setup_rls_roles --dry-run
    python manage.py setup_rls_roles
"""

from __future__ import annotations

import logging

from django.conf import settings
from django.core.management.base import BaseCommand
from django.db import connection

logger = logging.getLogger(__name__)


def _build_statements(app_user: str, app_password: str, db_name: str) -> list[str]:
    """Return a list of individual SQL statements for RLS role setup."""
    return [
        # 1. Create app role (if not exists) — DO block must be a single statement
        (
            f"DO $$ BEGIN "
            f"IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = '{app_user}') THEN "
            f"CREATE ROLE {app_user} LOGIN PASSWORD '{app_password}'; "
            f"END IF; "
            f"END $$"
        ),
        # 2. Grant connect + usage
        f"GRANT CONNECT ON DATABASE {db_name} TO {app_user}",
        f"GRANT USAGE ON SCHEMA public TO {app_user}",
        # 3. Grant DML on all existing tables
        (
            f"GRANT SELECT, INSERT, UPDATE, DELETE "
            f"ON ALL TABLES IN SCHEMA public TO {app_user}"
        ),
        # 4. Grant usage on sequences
        (
            f"GRANT USAGE, SELECT "
            f"ON ALL SEQUENCES IN SCHEMA public TO {app_user}"
        ),
        # 5. Default privileges for future tables
        (
            f"ALTER DEFAULT PRIVILEGES IN SCHEMA public "
            f"GRANT SELECT, INSERT, UPDATE, DELETE "
            f"ON TABLES TO {app_user}"
        ),
        (
            f"ALTER DEFAULT PRIVILEGES IN SCHEMA public "
            f"GRANT USAGE, SELECT "
            f"ON SEQUENCES TO {app_user}"
        ),
    ]


class Command(BaseCommand):
    help = "Setup PostgreSQL roles for RLS (ADR-137)."

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Show SQL without executing.",
        )
        parser.add_argument(
            "--app-user",
            type=str,
            default=None,
            help="App-user role name (default: <db_name>_app).",
        )
        parser.add_argument(
            "--app-password",
            type=str,
            default=None,
            help="Password for app-user role.",
        )

    def handle(self, *args, **options):
        dry_run = options["dry_run"]

        if connection.vendor != "postgresql":
            self.stderr.write(
                self.style.ERROR(f"RLS roles require PostgreSQL. Current: {connection.vendor}")
            )
            return

        db_settings = settings.DATABASES["default"]
        db_name = db_settings["NAME"]
        migrations_user = db_settings["USER"]

        app_user = options["app_user"] or f"{db_name}_app"
        app_password = options["app_password"] or f"{app_user}_rls"

        statements = _build_statements(app_user, app_password, db_name)

        self.stdout.write(
            self.style.MIGRATE_HEADING(f"RLS Role Setup{' (DRY RUN)' if dry_run else ''}")
        )
        self.stdout.write(
            f"  Database:        {db_name}\n"
            f"  Migrations-user: {migrations_user} "
            f"(table owner, RLS-exempt)\n"
            f"  App-user:        {app_user} "
            f"(RLS applies)\n"
        )

        if dry_run:
            for stmt in statements:
                self.stdout.write(self.style.SQL_KEYWORD(f"{stmt};"))
            self.stdout.write(
                self.style.WARNING(
                    "\nAfter running this command:\n"
                    f"  1. Update DATABASE_URL to use "
                    f"'{app_user}' for gunicorn/celery\n"
                    f"  2. Keep '{migrations_user}' for "
                    f"migrate/createsuperuser\n"
                    f"  3. Run: python manage.py enable_rls"
                )
            )
        else:
            with connection.cursor() as cursor:
                for stmt in statements:
                    try:
                        cursor.execute(stmt)
                    except Exception as exc:
                        self.stderr.write(self.style.ERROR(f"  ERROR: {exc}"))
                        logger.exception("RLS role setup failed")
            self.stdout.write(self.style.SUCCESS(f"\nRole '{app_user}' created/updated."))
