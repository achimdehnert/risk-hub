"""Seed demo data for development."""

from django.core.management.base import BaseCommand
from tenancy.models import Organization, Site
from identity.models import User
from risk.models import Assessment, Hazard
from permissions.models import Permission, Role, Scope, Assignment
import uuid


class Command(BaseCommand):
    help = "Seed demo data for development"

    def handle(self, *args, **options):
        self.stdout.write("Seeding demo data...")
        
        # Create demo organization
        org, created = Organization.objects.get_or_create(
            slug="demo",
            defaults={
                "name": "Demo GmbH",
            }
        )
        if created:
            self.stdout.write(f"  Created organization: {org.name}")
        
        tenant_id = org.tenant_id
        
        # Create sites
        site1, _ = Site.objects.get_or_create(
            tenant_id=tenant_id,
            name="Hauptstandort",
            defaults={"organization": org, "address": "Musterstraße 1, 12345 Berlin"}
        )
        site2, _ = Site.objects.get_or_create(
            tenant_id=tenant_id,
            name="Lager Nord",
            defaults={"organization": org, "address": "Industrieweg 5, 22222 Hamburg"}
        )
        self.stdout.write(f"  Sites: {Site.objects.filter(tenant_id=tenant_id).count()}")
        
        # Create demo user
        user, created = User.objects.get_or_create(
            username="demo",
            defaults={
                "email": "demo@example.com",
                "tenant_id": tenant_id,
                "is_staff": True,
            }
        )
        if created:
            user.set_password("demo")
            user.save()
            self.stdout.write(f"  Created user: demo (password: demo)")
        
        # Create permissions
        permissions_data = [
            ("risk.assessment.read", "Gefährdungsbeurteilungen lesen"),
            ("risk.assessment.write", "Gefährdungsbeurteilungen bearbeiten"),
            ("risk.assessment.approve", "Gefährdungsbeurteilungen freigeben"),
            ("documents.read", "Dokumente lesen"),
            ("documents.write", "Dokumente hochladen"),
            ("actions.read", "Maßnahmen lesen"),
            ("actions.write", "Maßnahmen bearbeiten"),
        ]
        for code, desc in permissions_data:
            Permission.objects.get_or_create(code=code, defaults={"description": desc})
        self.stdout.write(f"  Permissions: {Permission.objects.count()}")
        
        # Create roles
        admin_role, _ = Role.objects.get_or_create(
            tenant_id=tenant_id,
            name="Administrator",
            defaults={"is_system": True}
        )
        admin_role.permissions.set(Permission.objects.all())
        
        reader_role, _ = Role.objects.get_or_create(
            tenant_id=tenant_id,
            name="Leser",
            defaults={"is_system": True}
        )
        reader_role.permissions.set(
            Permission.objects.filter(code__endswith=".read")
        )
        self.stdout.write(f"  Roles: {Role.objects.filter(tenant_id=tenant_id).count()}")
        
        # Create scope and assignment
        tenant_scope, _ = Scope.objects.get_or_create(
            tenant_id=tenant_id,
            scope_type=Scope.SCOPE_TENANT,
            defaults={}
        )
        Assignment.objects.get_or_create(
            tenant_id=tenant_id,
            user_id=user.id,
            role=admin_role,
            scope=tenant_scope,
        )
        
        # Create sample assessments
        assessment1, _ = Assessment.objects.get_or_create(
            tenant_id=tenant_id,
            title="Brandschutz Bürogebäude",
            defaults={
                "category": "brandschutz",
                "description": "Gefährdungsbeurteilung für das Hauptgebäude",
                "site_id": site1.id,
                "created_by_id": user.id,
            }
        )
        
        assessment2, _ = Assessment.objects.get_or_create(
            tenant_id=tenant_id,
            title="Arbeitssicherheit Lager",
            defaults={
                "category": "arbeitssicherheit",
                "description": "Gefährdungsbeurteilung für Lagertätigkeiten",
                "site_id": site2.id,
                "created_by_id": user.id,
            }
        )
        self.stdout.write(f"  Assessments: {Assessment.objects.filter(tenant_id=tenant_id).count()}")
        
        # Create sample hazards
        Hazard.objects.get_or_create(
            tenant_id=tenant_id,
            assessment=assessment1,
            title="Fehlende Brandmelder",
            defaults={
                "description": "In einigen Räumen fehlen Rauchmelder",
                "severity": 3,
                "probability": 2,
                "mitigation": "Installation von Rauchmeldern in allen Räumen",
            }
        )
        
        Hazard.objects.get_or_create(
            tenant_id=tenant_id,
            assessment=assessment2,
            title="Stolpergefahr durch Kabel",
            defaults={
                "description": "Lose Kabel auf dem Boden im Lagerbereich",
                "severity": 2,
                "probability": 4,
                "mitigation": "Kabelkanäle installieren",
            }
        )
        self.stdout.write(f"  Hazards: {Hazard.objects.filter(tenant_id=tenant_id).count()}")
        
        self.stdout.write(self.style.SUCCESS("Demo data seeded successfully!"))
        self.stdout.write(f"\nAccess: http://demo.localhost:8080/risk/assessments/")
        self.stdout.write(f"Login: demo / demo")
