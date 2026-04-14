"""Identity models."""

from django.contrib.auth.models import AbstractUser
from django.db import models
from django_tenancy.managers import TenantManager


class User(AbstractUser):
    """Custom user model with tenant association."""

    tenant_id = models.UUIDField(null=True, blank=True, db_index=True)

    class Meta:
        db_table = "identity_user"


class ApiKey(models.Model):
    tenant_id = models.UUIDField(db_index=True)
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="api_keys",
    )
    name = models.CharField(max_length=120, blank=True, default="")
    key_prefix = models.CharField(max_length=16, db_index=True)
    key_hash = models.CharField(max_length=64)
    created_at = models.DateTimeField(auto_now_add=True)
    revoked_at = models.DateTimeField(null=True, blank=True)
    last_used_at = models.DateTimeField(null=True, blank=True)

    objects = TenantManager()

    class Meta:
        db_table = "identity_api_key"
        constraints = [
            models.UniqueConstraint(
                fields=["key_prefix", "key_hash"],
                name="uq_api_key",
            ),
        ]
