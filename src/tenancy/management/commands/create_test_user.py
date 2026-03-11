"""Management command: create_test_user.

Creates a user with all modules subscribed (business plan) for testing.
Idempotent — safe to run multiple times.

Usage:
    python manage.py create_test_user --username ad.risk --email ad.risk@dehnert.team --password <pw>
    python manage.py create_test_user --username ad.risk --email ad.risk@dehnert.team --password <pw> --org schutztat
"""

from __future__ import annotations

import secrets

from django.core.management.base import BaseCommand
from django.utils import timezone
from django_tenancy.module_models import ModuleMembership, ModuleSubscription

from billing.constants import PLAN_MODULES
from identity.models import User
from tenancy.models import Membership, Organization

ALL_MODULES = PLAN_MODULES.get("business", [])


class Command(BaseCommand):
    help = "Create a test user with all modules (business plan) for an organization."

    def add_arguments(self, parser):
        parser.add_argument("--username", required=True)
        parser.add_argument("--email", required=True)
        parser.add_argument(
            "--password",
            default=None,
            help="Password (auto-generated if omitted)",
        )
        parser.add_argument(
            "--org",
            default=None,
            help="Organization slug (uses first org if omitted)",
        )
        parser.add_argument(
            "--staff",
            action="store_true",
            default=True,
            help="Make user is_staff (default: True)",
        )

    def handle(self, *args, **options):
        username = options["username"]
        email = options["email"]
        password = options["password"] or secrets.token_urlsafe(16)
        org_slug = options["org"]
        is_staff = options["staff"]

        # Resolve organization
        if org_slug:
            try:
                org = Organization.objects.get(slug=org_slug)
            except Organization.DoesNotExist:
                self.stderr.write(f"Organization '{org_slug}' not found.")
                self.stderr.write(
                    "Available: " + ", ".join(Organization.objects.values_list("slug", flat=True))
                )
                return
        else:
            org = Organization.objects.filter(status=Organization.Status.ACTIVE).first()
            if not org:
                org = Organization.objects.first()
            if not org:
                self.stderr.write("No organization found. Create one first.")
                return

        tenant_id = org.tenant_id
        self.stdout.write(f"Organization: {org.name} (slug={org.slug}, tenant_id={tenant_id})")

        # Create or update user
        user, created = User.objects.get_or_create(
            username=username,
            defaults={
                "email": email,
                "tenant_id": tenant_id,
                "is_staff": is_staff,
                "is_active": True,
            },
        )
        if created:
            user.set_password(password)
            user.save()
            self.stdout.write(self.style.SUCCESS(f"Created user: {username}"))
        else:
            user.email = email
            user.tenant_id = tenant_id
            user.is_staff = is_staff
            user.set_password(password)
            user.save()
            self.stdout.write(f"Updated user: {username}")

        # Ensure Membership in org
        membership, mem_created = Membership.objects.get_or_create(
            tenant_id=tenant_id,
            organization=org,
            user=user,
            defaults={
                "role": "admin",
                "invited_by": user,
                "invited_at": timezone.now(),
                "accepted_at": timezone.now(),
            },
        )
        if mem_created:
            self.stdout.write("  Created org membership (role=admin)")

        # Activate all business modules for the org
        for module in ALL_MODULES:
            ModuleSubscription.objects.update_or_create(
                tenant_id=tenant_id,
                module=module,
                defaults={
                    "organization": org,
                    "status": ModuleSubscription.Status.ACTIVE,
                    "plan_code": "business",
                    "activated_at": timezone.now(),
                },
            )

        self.stdout.write(f"  Module subscriptions active: {', '.join(ALL_MODULES)}")

        # Grant user ModuleMembership (admin) for all modules
        for module in ALL_MODULES:
            ModuleMembership.objects.update_or_create(
                tenant_id=tenant_id,
                user=user,
                module=module,
                defaults={"role": ModuleMembership.Role.ADMIN},
            )

        self.stdout.write(f"  Module memberships granted: {', '.join(ALL_MODULES)}")

        self.stdout.write(
            self.style.SUCCESS(
                f"\nUser ready!\n"
                f"  Username : {username}\n"
                f"  Password : {password}\n"
                f"  E-Mail   : {email}\n"
                f"  Org      : {org.name} ({org.slug})\n"
                f"  Modules  : {', '.join(ALL_MODULES)}\n"
                f"  Login    : https://schutztat.de/accounts/login/"
            )
        )
