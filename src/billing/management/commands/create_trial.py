"""Management command: create_trial.

Activates a 14-day Professional trial for a given organization (by slug or tenant_id).
Idempotent: safe to run multiple times.

Usage:
    python manage.py create_trial --slug acme-gmbh
    python manage.py create_trial --slug acme-gmbh --plan starter --days 30
"""

from __future__ import annotations

import logging
from datetime import timedelta

from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone
from django_tenancy.models import Organization
from django_tenancy.module_models import ModuleSubscription

from billing.constants import PLAN_MODULES

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Activate a trial ModuleSubscription for an organization."

    def add_arguments(self, parser):
        parser.add_argument("--slug", required=True, help="Organization slug")
        parser.add_argument(
            "--plan",
            default="professional",
            choices=list(PLAN_MODULES.keys()),
            help="Plan code (default: professional)",
        )
        parser.add_argument(
            "--days",
            type=int,
            default=14,
            help="Trial duration in days (default: 14)",
        )

    def handle(self, *args, **options):
        slug = options["slug"]
        plan = options["plan"]
        days = options["days"]

        try:
            org = Organization.objects.get(slug=slug)
        except Organization.DoesNotExist:
            raise CommandError(f"Organization with slug '{slug}' not found.")

        modules = PLAN_MODULES.get(plan, [])
        if not modules:
            raise CommandError(f"Plan '{plan}' has no modules configured.")

        trial_end = timezone.now() + timedelta(days=days)
        created_count = 0
        updated_count = 0

        for module in modules:
            _, created = ModuleSubscription.objects.update_or_create(
                organization=org,
                tenant_id=org.tenant_id,
                module=module,
                defaults={
                    "status": ModuleSubscription.Status.TRIAL,
                    "plan_code": plan,
                    "activated_at": timezone.now(),
                    "expires_at": trial_end,
                },
            )
            if created:
                created_count += 1
            else:
                updated_count += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"Trial '{plan}' ({days} days) activated for '{org.name}'.\n"
                f"  Modules: {', '.join(modules)}\n"
                f"  Created: {created_count} | Updated: {updated_count}\n"
                f"  Expires: {trial_end.strftime('%Y-%m-%d %H:%M UTC')}"
            )
        )
        logger.info(
            "[billing] Trial %s activated for org %s (plan=%s days=%d)",
            modules,
            org.pk,
            plan,
            days,
        )
