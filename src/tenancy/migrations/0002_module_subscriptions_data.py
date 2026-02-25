"""Data migration: seed ModuleSubscription + ModuleMembership for existing tenants.

For every existing Organization:
  - Creates active ModuleSubscriptions for "risk", "dsb", "ex"
  - Creates ModuleMemberships for all existing Memberships:
      owner/admin  → module role "admin"
      member       → module role "member"
      viewer       → module role "viewer"
      external     → module role "viewer"
"""

from django.db import migrations


MODULES = ["risk", "dsb", "ex"]

ROLE_MAP = {
    "owner": "admin",
    "admin": "admin",
    "member": "member",
    "viewer": "viewer",
    "external": "viewer",
}


def seed_module_access(apps, schema_editor):
    Organization = apps.get_model("django_tenancy", "Organization")
    Membership = apps.get_model("django_tenancy", "Membership")
    ModuleSubscription = apps.get_model("django_tenancy", "ModuleSubscription")
    ModuleMembership = apps.get_model("django_tenancy", "ModuleMembership")

    for org in Organization.objects.all():
        for module in MODULES:
            ModuleSubscription.objects.get_or_create(
                tenant_id=org.tenant_id,
                module=module,
                defaults={
                    "organization_id": org.pk,
                    "status": "active",
                    "plan_code": "free",
                },
            )

        for membership in Membership.objects.filter(tenant_id=org.tenant_id):
            module_role = ROLE_MAP.get(membership.role, "viewer")
            for module in MODULES:
                ModuleMembership.objects.get_or_create(
                    tenant_id=org.tenant_id,
                    user_id=membership.user_id,
                    module=module,
                    defaults={"role": module_role},
                )


def reverse_seed(apps, schema_editor):
    pass  # Non-destructive reverse — leave data in place.


class Migration(migrations.Migration):

    dependencies = [
        ("tenancy", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(seed_module_access, reverse_code=reverse_seed),
    ]
