"""Tenancy models."""

import uuid
from django.db import models


class Organization(models.Model):
    """Tenant organization."""
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant_id = models.UUIDField(unique=True, default=uuid.uuid4, editable=False)
    slug = models.SlugField(max_length=63, unique=True)
    name = models.CharField(max_length=200)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "tenancy_organization"

    def __str__(self) -> str:
        return self.name


class Site(models.Model):
    """Physical site/location within an organization."""
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant_id = models.UUIDField(db_index=True)
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name="sites")
    name = models.CharField(max_length=200)
    address = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "tenancy_site"
        constraints = [
            models.UniqueConstraint(fields=["tenant_id", "name"], name="uq_site_name_per_tenant"),
        ]

    def __str__(self) -> str:
        return self.name
