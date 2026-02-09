"""Load default permissions into the database (ADR-003 §3.4)."""

from __future__ import annotations

from django.core.management.base import BaseCommand

from permissions.models import Permission

DEFAULT_PERMISSIONS: list[dict[str, str]] = [
    # Tenant Management
    {"code": "tenant.view", "module": "tenant", "resource": "tenant", "action": "view"},
    {"code": "tenant.manage", "module": "tenant", "resource": "tenant", "action": "manage"},
    # User Management
    {"code": "user.view", "module": "user", "resource": "user", "action": "view"},
    {"code": "user.invite", "module": "user", "resource": "user", "action": "create"},
    {"code": "user.edit", "module": "user", "resource": "user", "action": "edit"},
    {"code": "user.delete", "module": "user", "resource": "user", "action": "delete"},
    # Site Management
    {"code": "site.view", "module": "site", "resource": "site", "action": "view"},
    {"code": "site.create", "module": "site", "resource": "site", "action": "create"},
    {"code": "site.edit", "module": "site", "resource": "site", "action": "edit"},
    {"code": "site.delete", "module": "site", "resource": "site", "action": "delete"},
    # Risk Assessment
    {"code": "risk.assessment.read", "module": "risk", "resource": "assessment", "action": "view"},
    {"code": "risk.assessment.write", "module": "risk", "resource": "assessment", "action": "create"},
    {"code": "risk.assessment.edit", "module": "risk", "resource": "assessment", "action": "edit"},
    {"code": "risk.assessment.approve", "module": "risk", "resource": "assessment", "action": "approve"},
    {"code": "risk.assessment.delete", "module": "risk", "resource": "assessment", "action": "delete"},
    # Explosionsschutz
    {"code": "ex_area.view", "module": "ex", "resource": "area", "action": "view"},
    {"code": "ex_area.create", "module": "ex", "resource": "area", "action": "create"},
    {"code": "ex_area.edit", "module": "ex", "resource": "area", "action": "edit"},
    {"code": "ex_concept.view", "module": "ex", "resource": "concept", "action": "view"},
    {"code": "ex_concept.create", "module": "ex", "resource": "concept", "action": "create"},
    {"code": "ex_concept.approve", "module": "ex", "resource": "concept", "action": "approve"},
    {"code": "ex_equipment.view", "module": "ex", "resource": "equipment", "action": "view"},
    {"code": "ex_equipment.create", "module": "ex", "resource": "equipment", "action": "create"},
    {"code": "ex_equipment.edit", "module": "ex", "resource": "equipment", "action": "edit"},
    {"code": "ex_inspection.view", "module": "ex", "resource": "inspection", "action": "view"},
    {"code": "ex_inspection.create", "module": "ex", "resource": "inspection", "action": "create"},
    # Substances
    {"code": "substance.view", "module": "substance", "resource": "substance", "action": "view"},
    {"code": "substance.create", "module": "substance", "resource": "substance", "action": "create"},
    {"code": "substance.edit", "module": "substance", "resource": "substance", "action": "edit"},
    {"code": "substance.delete", "module": "substance", "resource": "substance", "action": "delete"},
    # Documents (services use documents.read / documents.create)
    {"code": "documents.read", "module": "document", "resource": "document", "action": "view"},
    {"code": "documents.create", "module": "document", "resource": "document", "action": "create"},
    {"code": "documents.delete", "module": "document", "resource": "document", "action": "delete"},
    # Actions (services use actions.read / actions.write)
    {"code": "actions.read", "module": "action", "resource": "action_item", "action": "view"},
    {"code": "actions.write", "module": "action", "resource": "action_item", "action": "create"},
    {"code": "actions.edit", "module": "action", "resource": "action_item", "action": "edit"},
    # Audit
    {"code": "audit.view", "module": "audit", "resource": "audit", "action": "view"},
    {"code": "audit.export", "module": "audit", "resource": "audit", "action": "export"},
    # Reporting
    {"code": "report.view", "module": "report", "resource": "export_job", "action": "view"},
    {"code": "report.export", "module": "report", "resource": "export_job", "action": "export"},
]

SYSTEM_ROLES: dict[str, list[str]] = {
    "admin": [p["code"] for p in DEFAULT_PERMISSIONS],
    "manager": [
        p["code"] for p in DEFAULT_PERMISSIONS
        if p["action"] in ("view", "create", "edit", "export", "approve")
    ],
    "member": [
        p["code"] for p in DEFAULT_PERMISSIONS
        if p["action"] in ("view", "create", "edit")
    ],
    "viewer": [
        p["code"] for p in DEFAULT_PERMISSIONS
        if p["action"] == "view"
    ],
}


class Command(BaseCommand):
    help = "Load default permissions and system roles (ADR-003)"

    def add_arguments(self, parser):
        parser.add_argument(
            "--clear", action="store_true",
            help="Delete existing permissions before loading",
        )

    def handle(self, *args, **options):
        from permissions.models import Role, RolePermission

        if options["clear"]:
            Permission.objects.filter(is_system=True).delete()
            Role.objects.filter(is_system=True).delete()
            self.stdout.write("Cleared existing system permissions and roles.")

        created = 0
        for perm_data in DEFAULT_PERMISSIONS:
            _, was_created = Permission.objects.update_or_create(
                code=perm_data["code"],
                defaults={
                    "module": perm_data["module"],
                    "resource": perm_data["resource"],
                    "action": perm_data["action"],
                    "is_system": True,
                },
            )
            if was_created:
                created += 1

        self.stdout.write(
            f"Permissions: {created} created, "
            f"{len(DEFAULT_PERMISSIONS) - created} updated."
        )

        roles_created = 0
        for role_name, perm_codes in SYSTEM_ROLES.items():
            role, was_created = Role.objects.update_or_create(
                tenant_id=None,
                name=role_name,
                defaults={
                    "is_system": True,
                    "description": f"System role: {role_name}",
                },
            )
            if was_created:
                roles_created += 1

            perms = Permission.objects.filter(code__in=perm_codes)
            existing = set(
                RolePermission.objects.filter(role=role)
                .values_list("permission__code", flat=True)
            )
            new_perms = [p for p in perms if p.code not in existing]
            RolePermission.objects.bulk_create(
                [RolePermission(role=role, permission=p) for p in new_perms],
            )

        self.stdout.write(
            self.style.SUCCESS(
                f"Done: {len(DEFAULT_PERMISSIONS)} permissions, "
                f"{len(SYSTEM_ROLES)} system roles "
                f"({roles_created} new)."
            )
        )
