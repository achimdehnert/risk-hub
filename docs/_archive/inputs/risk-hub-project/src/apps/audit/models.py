"""
Audit Models
============

Audit Trail für alle risk-relevanten Operationen.
"""

import uuid

from django.db import models

from apps.core.models import TenantModel


class AuditEvent(TenantModel):
    """
    Audit Event für jeden risk-relevanten Write.
    
    Erfasst:
    - Was passiert ist (category, action)
    - Wer es getan hat (actor)
    - An welchem Objekt (entity)
    - Details (payload)
    - Wann (timestamp)
    - Kontext (request_id)
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # Actor
    actor_user_id = models.UUIDField(null=True, blank=True, db_index=True)
    actor_type = models.CharField(max_length=20, default="user")  # user, system, api
    
    # Event Classification
    category = models.CharField(max_length=80, db_index=True)  # z.B. "risk.assessment"
    action = models.CharField(max_length=80, db_index=True)    # z.B. "created", "approved"
    
    # Target Entity
    entity_type = models.CharField(max_length=120)  # z.B. "risk.Assessment"
    entity_id = models.UUIDField(db_index=True)
    
    # Details
    payload = models.JSONField(default=dict)
    
    # Context
    request_id = models.CharField(max_length=64, null=True, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)
    
    # Timestamp (override von TenantModel)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        db_table = "audit_event"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["tenant_id", "created_at"]),
            models.Index(fields=["entity_type", "entity_id"]),
            models.Index(fields=["actor_user_id", "created_at"]),
        ]

    def __str__(self):
        return f"{self.category}.{self.action} on {self.entity_type}:{self.entity_id}"
