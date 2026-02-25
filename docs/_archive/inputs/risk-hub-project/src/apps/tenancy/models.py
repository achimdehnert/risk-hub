"""
Tenancy Models
==============

Multi-Tenancy Kern:
- Organization (Mandant)
- Site (Standort)
"""

import uuid

from django.db import models


class Organization(models.Model):
    """
    Mandant / Tenant.
    
    Jeder Mandant hat:
    - Eindeutige tenant_id (für alle Referenzen)
    - Eindeutigen slug (für Subdomain)
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant_id = models.UUIDField(unique=True, default=uuid.uuid4, editable=False)
    slug = models.SlugField(max_length=63, unique=True, help_text="Subdomain identifier")
    name = models.CharField(max_length=200)

    # Kontakt
    email = models.EmailField(blank=True)
    phone = models.CharField(max_length=50, blank=True)

    # Adresse
    street = models.CharField(max_length=200, blank=True)
    city = models.CharField(max_length=100, blank=True)
    postal_code = models.CharField(max_length=20, blank=True)
    country = models.CharField(max_length=2, default="DE")

    # Status
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # Subscription (später für Billing)
    # plan = models.CharField(max_length=50, default="trial")
    # trial_ends_at = models.DateTimeField(null=True)

    class Meta:
        db_table = "tenancy_organization"
        verbose_name = "Organization"
        verbose_name_plural = "Organizations"

    def __str__(self):
        return self.name


class Site(models.Model):
    """
    Standort innerhalb eines Mandanten.
    
    Für Berechtigungen auf Site-Ebene.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant_id = models.UUIDField(db_index=True)
    organization = models.ForeignKey(
        Organization, on_delete=models.CASCADE, related_name="sites"
    )

    name = models.CharField(max_length=200)
    code = models.CharField(max_length=50, blank=True, help_text="Interner Code")

    # Adresse
    street = models.CharField(max_length=200, blank=True)
    city = models.CharField(max_length=100, blank=True)
    postal_code = models.CharField(max_length=20, blank=True)
    country = models.CharField(max_length=2, default="DE")

    # Status
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "tenancy_site"
        verbose_name = "Site"
        verbose_name_plural = "Sites"
        constraints = [
            models.UniqueConstraint(
                fields=["tenant_id", "name"], name="uq_site_name_per_tenant"
            ),
            models.UniqueConstraint(
                fields=["tenant_id", "code"],
                name="uq_site_code_per_tenant",
                condition=models.Q(code__gt=""),
            ),
        ]

    def __str__(self):
        return f"{self.name} ({self.organization.name})"

    def save(self, *args, **kwargs):
        # tenant_id von Organization übernehmen
        if not self.tenant_id:
            self.tenant_id = self.organization.tenant_id
        super().save(*args, **kwargs)
