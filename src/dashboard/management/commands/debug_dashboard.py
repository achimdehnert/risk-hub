"""Debug command: simulate dashboard KPI load and print traceback."""

import traceback

from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Debug dashboard 500 — simulate get_compliance_kpis for first org"

    def handle(self, *args, **options):
        from tenancy.models import Organization

        orgs = list(Organization.objects.all()[:5])
        self.stdout.write(f"Organizations found: {len(orgs)}")
        for org in orgs:
            self.stdout.write(f"  {org.slug} | tenant_id={org.tenant_id} | status={org.status}")

        if not orgs:
            self.stderr.write("No organizations found!")
            return

        org = orgs[0]
        tenant_id = org.tenant_id
        self.stdout.write(f"\nTesting with tenant_id={tenant_id}")

        try:
            from dashboard.services import get_compliance_kpis

            kpis = get_compliance_kpis(tenant_id)
            self.stdout.write(self.style.SUCCESS(f"get_compliance_kpis OK: {kpis}"))
        except Exception:
            self.stderr.write("get_compliance_kpis FAILED:")
            self.stderr.write(traceback.format_exc())

        try:
            from dashboard.services import get_recent_activities

            acts = get_recent_activities(tenant_id)
            self.stdout.write(self.style.SUCCESS(f"get_recent_activities OK: {len(acts)} entries"))
        except Exception:
            self.stderr.write("get_recent_activities FAILED:")
            self.stderr.write(traceback.format_exc())

        self.stdout.write("\nChecking migrations...")
        try:
            from django.db import connection

            with connection.cursor() as c:
                c.execute("SELECT name FROM django_migrations ORDER BY applied DESC LIMIT 20")
                rows = c.fetchall()
                for r in rows:
                    self.stdout.write(f"  {r[0]}")
        except Exception:
            self.stderr.write(traceback.format_exc())
