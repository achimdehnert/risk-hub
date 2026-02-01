# ADR-006: Audit & Compliance

| Metadaten | |
| --------- | --- |
| **Status** | ✅ APPROVED |
| **Version** | 1.0 |
| **Datum** | 2026-02-01 |
| **Autor** | Achim Dehnert (AI-unterstützt) |
| **Depends On** | ADR-003 (Tenant/RBAC), ADR-005 (Events) |

---

## 📋 Executive Summary

Dieses ADR definiert die **Audit- und Compliance-Architektur** für Risk-Hub. Ziel ist die Erfüllung regulatorischer Anforderungen (BetrSichV, ISO 27001, DSGVO) durch lückenlose, unveränderliche Protokollierung.

### Kernentscheidungen

| # | Entscheidung | Begründung |
| --- | ------------ | ---------- |
| 1 | Append-Only Audit Log | Unveränderlichkeit für Compliance |
| 2 | PostgreSQL + Partitionierung | Performance bei hohem Volumen |
| 3 | 10 Jahre Retention | BetrSichV §14 Anforderung |
| 4 | Strukturiertes JSON-Format | Maschinenlesbar, querybar |
| 5 | Automatische Erfassung via Middleware | Keine vergessenen Audits |

---

## 1. Kontext

Risk-Hub verwaltet sicherheitskritische Daten für Explosionsschutz und Gefahrstoffe. Regulatorische Anforderungen:

### 1.1 BetrSichV (Betriebssicherheitsverordnung)

- **§14**: Prüfungen dokumentieren und aufbewahren
- **§15**: Prüfbescheinigungen mindestens bis zur nächsten Prüfung
- **Anhang 2, Abschnitt 3**: Ex-Schutz-Dokumentation

### 1.2 ISO 27001

- **A.12.4.1**: Event Logging
- **A.12.4.2**: Protection of Log Information
- **A.12.4.3**: Administrator and Operator Logs
- **A.12.4.4**: Clock Synchronisation

### 1.3 DSGVO

- **Art. 5 (2)**: Rechenschaftspflicht (Accountability)
- **Art. 30**: Verzeichnis von Verarbeitungstätigkeiten
- **Art. 33**: Meldung von Datenschutzverletzungen

---

## 2. Architektur-Entscheidungen

### 2.1 Audit-Log-Schema

```sql
-- Partitionierte Audit-Tabelle (nach Monat)
CREATE TABLE audit_log (
    id UUID NOT NULL DEFAULT gen_random_uuid(),
    
    -- Context
    tenant_id UUID NOT NULL,
    user_id UUID,
    session_id UUID,
    request_id UUID,
    
    -- Action
    action VARCHAR(50) NOT NULL,
    action_category VARCHAR(50) NOT NULL,
    
    -- Target
    entity_type VARCHAR(100) NOT NULL,
    entity_id UUID,
    entity_name VARCHAR(500),
    
    -- Changes
    old_value JSONB,
    new_value JSONB,
    changed_fields TEXT[],
    
    -- Request Context
    ip_address INET,
    user_agent TEXT,
    http_method VARCHAR(10),
    http_path VARCHAR(2000),
    
    -- Metadata
    metadata JSONB DEFAULT '{}',
    
    -- Timestamp (partition key)
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    
    -- Constraints
    CONSTRAINT audit_action_chk CHECK (
        action IN (
            'create', 'read', 'update', 'delete',
            'login', 'logout', 'login_failed',
            'export', 'import', 'approve', 'reject',
            'assign', 'revoke', 'invite', 'suspend'
        )
    ),
    CONSTRAINT audit_category_chk CHECK (
        action_category IN (
            'data', 'auth', 'access', 'admin', 'system', 'compliance'
        )
    ),
    
    PRIMARY KEY (id, created_at)
) PARTITION BY RANGE (created_at);

-- Partitions erstellen (automatisch via pg_partman oder manuell)
CREATE TABLE audit_log_2026_01 PARTITION OF audit_log
    FOR VALUES FROM ('2026-01-01') TO ('2026-02-01');
CREATE TABLE audit_log_2026_02 PARTITION OF audit_log
    FOR VALUES FROM ('2026-02-01') TO ('2026-03-01');
-- ... weitere Partitions

-- Indexes
CREATE INDEX idx_audit_tenant_time ON audit_log(tenant_id, created_at DESC);
CREATE INDEX idx_audit_user_time ON audit_log(user_id, created_at DESC);
CREATE INDEX idx_audit_entity ON audit_log(entity_type, entity_id);
CREATE INDEX idx_audit_action ON audit_log(action, created_at DESC);
```

### 2.2 Immutability Enforcement

```sql
-- Trigger: Verhindert UPDATE und DELETE
CREATE OR REPLACE FUNCTION audit_log_immutable()
RETURNS TRIGGER AS $$
BEGIN
    RAISE EXCEPTION 'Audit log is immutable. Operation % not allowed.', TG_OP;
    RETURN NULL;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER audit_log_no_update
    BEFORE UPDATE ON audit_log
    FOR EACH ROW EXECUTE FUNCTION audit_log_immutable();

CREATE TRIGGER audit_log_no_delete
    BEFORE DELETE ON audit_log
    FOR EACH ROW EXECUTE FUNCTION audit_log_immutable();

-- Revoke DELETE/UPDATE für normale Benutzer
REVOKE UPDATE, DELETE ON audit_log FROM PUBLIC;
REVOKE UPDATE, DELETE ON audit_log FROM app_user;
```

---

## 3. Django Implementation

### 3.1 Audit Model

```python
# audit/models.py
from django.db import models
from django.contrib.postgres.fields import ArrayField
import uuid


class AuditAction(models.TextChoices):
    CREATE = "create", "Create"
    READ = "read", "Read"
    UPDATE = "update", "Update"
    DELETE = "delete", "Delete"
    LOGIN = "login", "Login"
    LOGOUT = "logout", "Logout"
    LOGIN_FAILED = "login_failed", "Login Failed"
    EXPORT = "export", "Export"
    IMPORT = "import", "Import"
    APPROVE = "approve", "Approve"
    REJECT = "reject", "Reject"
    ASSIGN = "assign", "Assign"
    REVOKE = "revoke", "Revoke"
    INVITE = "invite", "Invite"
    SUSPEND = "suspend", "Suspend"


class AuditCategory(models.TextChoices):
    DATA = "data", "Data Change"
    AUTH = "auth", "Authentication"
    ACCESS = "access", "Access Control"
    ADMIN = "admin", "Administration"
    SYSTEM = "system", "System"
    COMPLIANCE = "compliance", "Compliance"


class AuditLog(models.Model):
    """Immutable audit log entry."""
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4)
    
    # Context
    tenant_id = models.UUIDField(db_index=True)
    user_id = models.UUIDField(null=True, blank=True, db_index=True)
    session_id = models.UUIDField(null=True, blank=True)
    request_id = models.UUIDField(null=True, blank=True)
    
    # Action
    action = models.CharField(max_length=50, choices=AuditAction.choices)
    action_category = models.CharField(max_length=50, choices=AuditCategory.choices)
    
    # Target
    entity_type = models.CharField(max_length=100, db_index=True)
    entity_id = models.UUIDField(null=True, blank=True)
    entity_name = models.CharField(max_length=500, blank=True, default="")
    
    # Changes
    old_value = models.JSONField(null=True, blank=True)
    new_value = models.JSONField(null=True, blank=True)
    changed_fields = ArrayField(
        models.CharField(max_length=100),
        null=True,
        blank=True,
    )
    
    # Request Context
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True, default="")
    http_method = models.CharField(max_length=10, blank=True, default="")
    http_path = models.CharField(max_length=2000, blank=True, default="")
    
    # Metadata
    metadata = models.JSONField(default=dict)
    
    # Timestamp
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    
    class Meta:
        db_table = "audit_log"
        ordering = ["-created_at"]
        
        # Prevent modifications
        managed = True
    
    def save(self, *args, **kwargs):
        if self.pk and AuditLog.objects.filter(pk=self.pk).exists():
            raise ValueError("Audit log entries cannot be modified")
        super().save(*args, **kwargs)
    
    def delete(self, *args, **kwargs):
        raise ValueError("Audit log entries cannot be deleted")
```

### 3.2 Audit Service

```python
# audit/services.py
from typing import Any
from uuid import UUID
from django.db import transaction
from .models import AuditLog, AuditAction, AuditCategory


class AuditService:
    """Service for creating audit log entries."""
    
    def log(
        self,
        tenant_id: UUID,
        action: AuditAction,
        category: AuditCategory,
        entity_type: str,
        entity_id: UUID | None = None,
        entity_name: str = "",
        old_value: dict | None = None,
        new_value: dict | None = None,
        user_id: UUID | None = None,
        request_context: dict | None = None,
        metadata: dict | None = None,
    ) -> AuditLog:
        """Create an audit log entry."""
        
        changed_fields = None
        if old_value and new_value:
            changed_fields = self._calculate_changed_fields(old_value, new_value)
        
        request_context = request_context or {}
        
        return AuditLog.objects.create(
            tenant_id=tenant_id,
            user_id=user_id,
            session_id=request_context.get("session_id"),
            request_id=request_context.get("request_id"),
            action=action,
            action_category=category,
            entity_type=entity_type,
            entity_id=entity_id,
            entity_name=entity_name,
            old_value=old_value,
            new_value=new_value,
            changed_fields=changed_fields,
            ip_address=request_context.get("ip_address"),
            user_agent=request_context.get("user_agent", ""),
            http_method=request_context.get("http_method", ""),
            http_path=request_context.get("http_path", ""),
            metadata=metadata or {},
        )
    
    def _calculate_changed_fields(
        self,
        old_value: dict,
        new_value: dict,
    ) -> list[str]:
        """Calculate which fields changed between old and new values."""
        changed = []
        all_keys = set(old_value.keys()) | set(new_value.keys())
        
        for key in all_keys:
            old = old_value.get(key)
            new = new_value.get(key)
            if old != new:
                changed.append(key)
        
        return changed
    
    def log_data_change(
        self,
        tenant_id: UUID,
        action: AuditAction,
        entity_type: str,
        entity_id: UUID,
        entity_name: str = "",
        old_value: dict | None = None,
        new_value: dict | None = None,
        **kwargs,
    ) -> AuditLog:
        """Convenience method for data changes."""
        return self.log(
            tenant_id=tenant_id,
            action=action,
            category=AuditCategory.DATA,
            entity_type=entity_type,
            entity_id=entity_id,
            entity_name=entity_name,
            old_value=old_value,
            new_value=new_value,
            **kwargs,
        )
    
    def log_auth_event(
        self,
        tenant_id: UUID,
        action: AuditAction,
        user_id: UUID | None = None,
        success: bool = True,
        **kwargs,
    ) -> AuditLog:
        """Convenience method for auth events."""
        metadata = kwargs.pop("metadata", {})
        metadata["success"] = success
        
        return self.log(
            tenant_id=tenant_id,
            action=action,
            category=AuditCategory.AUTH,
            entity_type="User",
            entity_id=user_id,
            user_id=user_id,
            metadata=metadata,
            **kwargs,
        )


# Singleton
audit_service = AuditService()
```

### 3.3 Automatic Audit Middleware

```python
# audit/middleware.py
from django.utils.deprecation import MiddlewareMixin
from common.context import get_tenant_id, get_user_id, get_request_id


class AuditContextMiddleware(MiddlewareMixin):
    """Capture request context for audit logging."""
    
    def process_request(self, request):
        request.audit_context = {
            "request_id": get_request_id(),
            "session_id": request.session.session_key if hasattr(request, "session") else None,
            "ip_address": self._get_client_ip(request),
            "user_agent": request.headers.get("User-Agent", "")[:500],
            "http_method": request.method,
            "http_path": request.path[:2000],
        }
    
    def _get_client_ip(self, request) -> str | None:
        x_forwarded_for = request.headers.get("X-Forwarded-For")
        if x_forwarded_for:
            return x_forwarded_for.split(",")[0].strip()
        return request.META.get("REMOTE_ADDR")
```

### 3.4 Model Mixin for Auto-Auditing

```python
# audit/mixins.py
from django.db import models
from django.db.models.signals import post_save, post_delete, pre_save
from django.dispatch import receiver
from .services import audit_service
from .models import AuditAction, AuditCategory


class AuditableMixin(models.Model):
    """Mixin for automatic audit logging on model changes."""
    
    class Meta:
        abstract = True
    
    # Override in subclass
    audit_entity_type: str = None
    audit_fields: list[str] = None  # None = all fields
    audit_exclude_fields: list[str] = ["updated_at", "created_at"]
    
    def get_audit_name(self) -> str:
        """Return a human-readable name for audit logs."""
        return str(self)
    
    def to_audit_dict(self) -> dict:
        """Serialize model for audit log."""
        fields = self.audit_fields or [f.name for f in self._meta.fields]
        exclude = self.audit_exclude_fields or []
        
        data = {}
        for field in fields:
            if field not in exclude:
                value = getattr(self, field, None)
                if hasattr(value, "pk"):
                    value = str(value.pk)
                elif hasattr(value, "isoformat"):
                    value = value.isoformat()
                data[field] = value
        
        return data


def setup_audit_signals(model_class):
    """Register audit signals for a model."""
    
    @receiver(pre_save, sender=model_class)
    def capture_old_values(sender, instance, **kwargs):
        if instance.pk:
            try:
                instance._audit_old_values = sender.objects.get(pk=instance.pk).to_audit_dict()
            except sender.DoesNotExist:
                instance._audit_old_values = None
        else:
            instance._audit_old_values = None
    
    @receiver(post_save, sender=model_class)
    def audit_save(sender, instance, created, **kwargs):
        from common.context import get_tenant_id, get_user_id, get_request_context
        
        tenant_id = getattr(instance, "tenant_id", None) or get_tenant_id()
        if not tenant_id:
            return
        
        action = AuditAction.CREATE if created else AuditAction.UPDATE
        
        audit_service.log_data_change(
            tenant_id=tenant_id,
            action=action,
            entity_type=instance.audit_entity_type or sender.__name__,
            entity_id=instance.pk,
            entity_name=instance.get_audit_name(),
            old_value=getattr(instance, "_audit_old_values", None),
            new_value=instance.to_audit_dict(),
            user_id=get_user_id(),
            request_context=get_request_context(),
        )
    
    @receiver(post_delete, sender=model_class)
    def audit_delete(sender, instance, **kwargs):
        from common.context import get_tenant_id, get_user_id, get_request_context
        
        tenant_id = getattr(instance, "tenant_id", None) or get_tenant_id()
        if not tenant_id:
            return
        
        audit_service.log_data_change(
            tenant_id=tenant_id,
            action=AuditAction.DELETE,
            entity_type=instance.audit_entity_type or sender.__name__,
            entity_id=instance.pk,
            entity_name=instance.get_audit_name(),
            old_value=instance.to_audit_dict(),
            user_id=get_user_id(),
            request_context=get_request_context(),
        )
```

---

## 4. Entity-spezifische Audits

### 4.1 Ex-Konzept Audit

```python
# explosionsschutz/models.py
from audit.mixins import AuditableMixin, setup_audit_signals


class ExConcept(AuditableMixin, models.Model):
    """Explosionsschutzkonzept - requires detailed audit."""
    
    audit_entity_type = "ExConcept"
    audit_fields = [
        "id", "title", "status", "version",
        "approved_by", "approved_at", "site_id",
    ]
    
    # ... model fields ...
    
    def get_audit_name(self) -> str:
        return f"{self.title} v{self.version}"


# Register signals
setup_audit_signals(ExConcept)
```

### 4.2 Equipment Inspection Audit

```python
# explosionsschutz/services.py
from audit.services import audit_service
from audit.models import AuditAction, AuditCategory


class EquipmentService:
    """Service for equipment management with compliance auditing."""
    
    def record_inspection(
        self,
        equipment: Equipment,
        inspection_type: str,
        inspector: User,
        result: str,
        notes: str,
        **kwargs,
    ) -> Inspection:
        """Record an equipment inspection with full audit trail."""
        
        inspection = Inspection.objects.create(
            equipment=equipment,
            inspection_type=inspection_type,
            inspector_id=inspector.id,
            result=result,
            notes=notes,
            **kwargs,
        )
        
        # Compliance audit entry
        audit_service.log(
            tenant_id=equipment.tenant_id,
            action=AuditAction.CREATE,
            category=AuditCategory.COMPLIANCE,
            entity_type="Inspection",
            entity_id=inspection.id,
            entity_name=f"Inspection: {equipment.name}",
            new_value={
                "equipment_id": str(equipment.id),
                "equipment_name": equipment.name,
                "inspection_type": inspection_type,
                "inspector_name": inspector.get_full_name(),
                "result": result,
                "notes": notes,
                "atex_category": equipment.atex_category,
            },
            user_id=inspector.id,
            metadata={
                "compliance_type": "BetrSichV_§14",
                "next_inspection_due": str(inspection.next_due_date),
            },
        )
        
        return inspection
```

---

## 5. Compliance Reports

### 5.1 Audit Export Service

```python
# audit/export.py
import csv
import io
from datetime import datetime
from typing import Iterator
from .models import AuditLog


class AuditExportService:
    """Export audit logs for compliance reporting."""
    
    def export_csv(
        self,
        tenant_id: UUID,
        start_date: datetime,
        end_date: datetime,
        entity_types: list[str] | None = None,
    ) -> Iterator[str]:
        """Export audit logs as CSV stream."""
        
        queryset = AuditLog.objects.filter(
            tenant_id=tenant_id,
            created_at__gte=start_date,
            created_at__lte=end_date,
        ).order_by("created_at")
        
        if entity_types:
            queryset = queryset.filter(entity_type__in=entity_types)
        
        output = io.StringIO()
        writer = csv.writer(output)
        
        # Header
        writer.writerow([
            "Timestamp", "User", "Action", "Category",
            "Entity Type", "Entity ID", "Entity Name",
            "Changed Fields", "IP Address",
        ])
        yield output.getvalue()
        output.seek(0)
        output.truncate(0)
        
        # Data rows
        for entry in queryset.iterator(chunk_size=1000):
            writer.writerow([
                entry.created_at.isoformat(),
                str(entry.user_id) if entry.user_id else "System",
                entry.action,
                entry.action_category,
                entry.entity_type,
                str(entry.entity_id) if entry.entity_id else "",
                entry.entity_name,
                ", ".join(entry.changed_fields or []),
                entry.ip_address or "",
            ])
            yield output.getvalue()
            output.seek(0)
            output.truncate(0)
    
    def export_json(
        self,
        tenant_id: UUID,
        start_date: datetime,
        end_date: datetime,
    ) -> Iterator[dict]:
        """Export audit logs as JSON stream."""
        
        queryset = AuditLog.objects.filter(
            tenant_id=tenant_id,
            created_at__gte=start_date,
            created_at__lte=end_date,
        ).order_by("created_at")
        
        for entry in queryset.iterator(chunk_size=1000):
            yield {
                "id": str(entry.id),
                "timestamp": entry.created_at.isoformat(),
                "tenant_id": str(entry.tenant_id),
                "user_id": str(entry.user_id) if entry.user_id else None,
                "action": entry.action,
                "category": entry.action_category,
                "entity": {
                    "type": entry.entity_type,
                    "id": str(entry.entity_id) if entry.entity_id else None,
                    "name": entry.entity_name,
                },
                "changes": {
                    "old": entry.old_value,
                    "new": entry.new_value,
                    "fields": entry.changed_fields,
                },
                "request": {
                    "ip": entry.ip_address,
                    "user_agent": entry.user_agent,
                    "method": entry.http_method,
                    "path": entry.http_path,
                },
                "metadata": entry.metadata,
            }
```

### 5.2 Compliance Report View

```python
# audit/views.py
from django.http import StreamingHttpResponse
from django.views import View
from permissions.decorators import require_permission


class AuditExportView(View):
    """Export audit logs for compliance."""
    
    @require_permission("audit.export")
    def get(self, request):
        tenant_id = request.tenant_id
        start_date = request.GET.get("start")
        end_date = request.GET.get("end")
        format = request.GET.get("format", "csv")
        
        export_service = AuditExportService()
        
        # Log the export itself
        audit_service.log(
            tenant_id=tenant_id,
            action=AuditAction.EXPORT,
            category=AuditCategory.COMPLIANCE,
            entity_type="AuditLog",
            user_id=request.user.id,
            metadata={
                "start_date": start_date,
                "end_date": end_date,
                "format": format,
            },
            request_context=request.audit_context,
        )
        
        if format == "csv":
            response = StreamingHttpResponse(
                export_service.export_csv(tenant_id, start_date, end_date),
                content_type="text/csv",
            )
            response["Content-Disposition"] = f'attachment; filename="audit_log_{start_date}_{end_date}.csv"'
        else:
            response = StreamingHttpResponse(
                export_service.export_json(tenant_id, start_date, end_date),
                content_type="application/json",
            )
            response["Content-Disposition"] = f'attachment; filename="audit_log_{start_date}_{end_date}.json"'
        
        return response
```

---

## 6. Retention & Archival

### 6.1 Retention Policy

| Datentyp | Retention | Begründung |
| -------- | --------- | ---------- |
| **Ex-Konzept Änderungen** | 10 Jahre | BetrSichV |
| **Prüfprotokolle** | Bis nächste Prüfung + 5 Jahre | BetrSichV §14 |
| **Login/Logout** | 2 Jahre | ISO 27001 |
| **Datenänderungen** | 5 Jahre | DSGVO |
| **Systemevents** | 1 Jahr | Operational |

### 6.2 Archival Strategy

```python
# audit/tasks.py
from celery import shared_task
from datetime import timedelta
from django.utils import timezone


@shared_task
def archive_old_audit_logs():
    """
    Archive audit logs older than retention period to cold storage.
    
    Runs monthly via Celery Beat.
    """
    retention_config = {
        "compliance": timedelta(days=365 * 10),  # 10 years
        "data": timedelta(days=365 * 5),          # 5 years
        "auth": timedelta(days=365 * 2),          # 2 years
        "system": timedelta(days=365),            # 1 year
    }
    
    for category, retention in retention_config.items():
        cutoff_date = timezone.now() - retention
        
        # Export to S3/Archive before deletion
        logs_to_archive = AuditLog.objects.filter(
            action_category=category,
            created_at__lt=cutoff_date,
        )
        
        if logs_to_archive.exists():
            # Archive to S3 (compliance bucket with legal hold)
            archive_to_s3(logs_to_archive, category, cutoff_date)
            
            # Drop old partition (safer than DELETE)
            drop_partition_before(cutoff_date)
```

### 6.3 Partition Management

```sql
-- Automatische Partition-Erstellung (pg_partman)
SELECT partman.create_parent(
    p_parent_table := 'public.audit_log',
    p_control := 'created_at',
    p_type := 'native',
    p_interval := '1 month',
    p_premake := 3
);

-- Retention: Partitions älter als 10 Jahre archivieren
SELECT partman.run_maintenance(
    p_parent_table := 'public.audit_log',
    p_retention := '10 years',
    p_retention_keep_table := true  -- Nicht löschen, nur detachen
);
```

---

## 7. Security

### 7.1 Access Control

```python
# Permissions für Audit-Zugriff
AUDIT_PERMISSIONS = [
    {"code": "audit.view", "description": "View audit logs"},
    {"code": "audit.export", "description": "Export audit logs"},
    {"code": "audit.search", "description": "Search audit logs"},
]

# Nur Admins und Compliance Officers
AUDIT_ROLES = {
    "admin": ["audit.view", "audit.export", "audit.search"],
    "compliance_officer": ["audit.view", "audit.export", "audit.search"],
    "safety_manager": ["audit.view"],
    "member": [],  # Kein Zugriff
}
```

### 7.2 Data Masking

```python
# audit/masking.py
import re

SENSITIVE_PATTERNS = {
    "password": r".*password.*",
    "token": r".*token.*",
    "secret": r".*secret.*",
    "api_key": r".*api.?key.*",
}


def mask_sensitive_data(data: dict) -> dict:
    """Mask sensitive fields before logging."""
    if not data:
        return data
    
    masked = {}
    for key, value in data.items():
        key_lower = key.lower()
        is_sensitive = any(
            re.match(pattern, key_lower)
            for pattern in SENSITIVE_PATTERNS.values()
        )
        
        if is_sensitive:
            masked[key] = "[REDACTED]"
        elif isinstance(value, dict):
            masked[key] = mask_sensitive_data(value)
        else:
            masked[key] = value
    
    return masked
```

---

## 8. Monitoring & Alerting

### 8.1 Anomaly Detection

```python
# audit/monitoring.py
from prometheus_client import Counter, Gauge

# Metrics
audit_events_total = Counter(
    "riskhub_audit_events_total",
    "Total audit events",
    ["action", "category", "tenant_id"],
)

failed_logins_total = Counter(
    "riskhub_failed_logins_total",
    "Failed login attempts",
    ["tenant_id"],
)

# Alert: Zu viele fehlgeschlagene Logins
FAILED_LOGIN_THRESHOLD = 10  # pro Minute


@shared_task
def check_security_anomalies():
    """Check for security anomalies and alert."""
    from datetime import timedelta
    
    # Failed logins in last 5 minutes
    recent_failures = AuditLog.objects.filter(
        action=AuditAction.LOGIN_FAILED,
        created_at__gte=timezone.now() - timedelta(minutes=5),
    ).values("tenant_id", "ip_address").annotate(count=Count("id"))
    
    for entry in recent_failures:
        if entry["count"] > FAILED_LOGIN_THRESHOLD:
            send_security_alert(
                tenant_id=entry["tenant_id"],
                alert_type="brute_force_attempt",
                details={
                    "ip_address": entry["ip_address"],
                    "attempt_count": entry["count"],
                },
            )
```

---

## 9. Konsequenzen

### Positiv

- ✅ **Compliance-Ready**: BetrSichV, ISO 27001, DSGVO
- ✅ **Unveränderlich**: DB-Trigger verhindern Manipulation
- ✅ **Performant**: Partitionierung für hohe Volumina
- ✅ **Auswertbar**: JSON + Indexes für Ad-hoc Queries

### Negativ

- ❌ **Storage-Kosten**: 10 Jahre Retention = viel Speicher
- ❌ **Performance-Impact**: Jede Änderung = Audit-Insert
- ❌ **Komplexität**: Partition-Management erforderlich

---

## 10. Referenzen

- [BetrSichV §14](https://www.gesetze-im-internet.de/betrsichv_2015/__14.html)
- [ISO 27001 A.12.4](https://www.iso.org/standard/27001)
- [DSGVO Art. 5](https://dsgvo-gesetz.de/art-5-dsgvo/)
- [PostgreSQL Partitioning](https://www.postgresql.org/docs/current/ddl-partitioning.html)
- [pg_partman](https://github.com/pgpartman/pg_partman)

---

**Erstellt:** 2026-02-01  
**Version:** 1.0
