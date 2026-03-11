"""Tests for create_trial management command."""

from __future__ import annotations

from io import StringIO

import pytest
from django.core.management import call_command
from django.core.management.base import CommandError


@pytest.mark.django_db
class TestCreateTrialCommand:
    def test_creates_trial_for_valid_slug(self):
        from django_tenancy.module_models import ModuleSubscription
        from tenancy.models import Organization

        org = Organization.objects.create(
            name="Trial Org",
            slug="trial-org",
            tenant_id="33333333-3333-3333-3333-333333333333",
        )
        out = StringIO()
        call_command(
            "create_trial",
            "--slug",
            "trial-org",
            "--plan",
            "starter",
            "--days",
            "14",
            stdout=out,
        )
        output = out.getvalue()
        assert "activated" in output
        assert ModuleSubscription.objects.filter(tenant_id=org.tenant_id, module="gbu").exists()

    def test_raises_for_unknown_slug(self):
        with pytest.raises(CommandError, match="not found"):
            call_command("create_trial", "--slug", "nonexistent-slug")

    def test_idempotent_second_run(self):
        from django_tenancy.module_models import ModuleSubscription
        from tenancy.models import Organization

        Organization.objects.create(
            name="Idempotent Org",
            slug="idempotent-org",
            tenant_id="44444444-4444-4444-4444-444444444444",
        )
        call_command("create_trial", "--slug", "idempotent-org", "--plan", "starter")
        call_command("create_trial", "--slug", "idempotent-org", "--plan", "starter")
        assert (
            ModuleSubscription.objects.filter(
                tenant_id="44444444-4444-4444-4444-444444444444"
            ).count()
            == 1
        )
