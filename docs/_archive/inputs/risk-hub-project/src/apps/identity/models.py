"""
Identity Models
===============

User und Authentication.
"""

import uuid

from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    """
    Custom User Model mit Tenant-Zuordnung.
    
    User können mehreren Tenants zugeordnet sein (über Assignments).
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # Optional: Primary Tenant (für Default-Kontext)
    tenant_id = models.UUIDField(null=True, blank=True, db_index=True)
    
    # Profile
    phone = models.CharField(max_length=50, blank=True)
    job_title = models.CharField(max_length=100, blank=True)
    department = models.CharField(max_length=100, blank=True)
    
    # Preferences
    language = models.CharField(max_length=10, default="de")
    timezone = models.CharField(max_length=50, default="Europe/Berlin")

    class Meta:
        db_table = "identity_user"
        verbose_name = "User"
        verbose_name_plural = "Users"

    def __str__(self):
        return self.get_full_name() or self.username
