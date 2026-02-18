"""
Seed Demo Command
=================

Erstellt Demo-Tenant und Beispieldaten.

Usage:
    python manage.py seed_demo
"""

from django.core.management.base import BaseCommand
from django.db import transaction

from apps.tenancy.models import Organization, Site
from apps.permissions.services import setup_default_roles


class Command(BaseCommand):
    help = "Create demo tenant and sample data"

    def add_arguments(self, parser):
        parser.add_argument(
            "--slug",
            default="demo",
            help="Tenant slug (default: demo)",
        )
        parser.add_argument(
            "--name",
            default="Demo Organization",
            help="Organization name",
        )

    @transaction.atomic
    def handle(self, *args, **options):
        slug = options["slug"]
        name = options["name"]

        self.stdout.write(f"Creating tenant: {slug}")

        # Organization erstellen
        org, created = Organization.objects.get_or_create(
            slug=slug,
            defaults={"name": name},
        )

        if created:
            self.stdout.write(self.style.SUCCESS(f"✓ Created organization: {org.name}"))
        else:
            self.stdout.write(f"  Organization already exists: {org.name}")

        # Default Sites erstellen
        sites_data = [
            {"name": "Hauptstandort Berlin", "code": "BER", "city": "Berlin"},
            {"name": "Standort München", "code": "MUC", "city": "München"},
            {"name": "Standort Hamburg", "code": "HAM", "city": "Hamburg"},
        ]

        for site_data in sites_data:
            site, site_created = Site.objects.get_or_create(
                tenant_id=org.tenant_id,
                organization=org,
                name=site_data["name"],
                defaults={
                    "code": site_data["code"],
                    "city": site_data["city"],
                    "country": "DE",
                },
            )
            if site_created:
                self.stdout.write(self.style.SUCCESS(f"  ✓ Created site: {site.name}"))

        # Default Roles und Permissions
        self.stdout.write("Setting up default roles and permissions...")
        setup_default_roles(org.tenant_id)
        self.stdout.write(self.style.SUCCESS("  ✓ Default roles created"))

        # S3 Bucket erstellen (falls MinIO läuft)
        try:
            from apps.documents.services import ensure_bucket
            ensure_bucket()
            self.stdout.write(self.style.SUCCESS("  ✓ S3 bucket ready"))
        except Exception as e:
            self.stdout.write(self.style.WARNING(f"  ⚠ S3 bucket setup failed: {e}"))

        # Summary
        self.stdout.write("")
        self.stdout.write(self.style.SUCCESS("=" * 50))
        self.stdout.write(self.style.SUCCESS("Demo tenant ready!"))
        self.stdout.write(self.style.SUCCESS("=" * 50))
        self.stdout.write(f"  Slug:      {org.slug}")
        self.stdout.write(f"  Tenant ID: {org.tenant_id}")
        self.stdout.write(f"  URL:       http://{org.slug}.localhost:8080/")
        self.stdout.write("")
        self.stdout.write("Don't forget to add to /etc/hosts:")
        self.stdout.write(f"  127.0.0.1 {org.slug}.localhost")
