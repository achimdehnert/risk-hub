"""Tenancy models for risk-hub.

Organization and Membership are provided by the django_tenancy platform
package (ADR-035). This module re-exports them for backwards compatibility
and adds the risk-hub-specific Site model.
"""

from __future__ import annotations

import uuid

from django.db import models

from django_tenancy.models import Membership, Organization

__all__ = ["Membership", "Organization", "Site"]


class Site(models.Model):
    """Physical site/location within an organization."""

    id = models.UUIDField(
        primary_key=True, default=uuid.uuid4, editable=False,
    )
    tenant_id = models.UUIDField(db_index=True)
    organization = models.ForeignKey(
        Organization, on_delete=models.CASCADE, related_name="sites",
    )
    name = models.CharField(max_length=200)
    address = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "tenancy_site"
        constraints = [
            models.UniqueConstraint(
                fields=["tenant_id", "name"],
                name="uq_site_name_per_tenant",
            ),
        ]

    def __str__(self) -> str:
        return self.name
