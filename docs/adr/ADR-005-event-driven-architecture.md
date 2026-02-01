# ADR-005: Event-Driven Architecture

| Metadaten | |
| --------- | --- |
| **Status** | ✅ APPROVED |
| **Version** | 1.0 |
| **Datum** | 2026-02-01 |
| **Autor** | Achim Dehnert (AI-unterstützt) |
| **Depends On** | ADR-003 (Tenant/RBAC) |

---

## 📋 Executive Summary

Dieses ADR definiert die **Event-Driven Architecture** für Risk-Hub. Ziel ist die Entkopplung von Modulen, zuverlässige asynchrone Verarbeitung und Integration mit externen Systemen via Webhooks.

### Kernentscheidungen

| # | Entscheidung | Begründung |
| --- | ------------ | ---------- |
| 1 | Transactional Outbox Pattern | Garantierte Event-Delivery ohne 2PC |
| 2 | Domain Events in Python | Explizite, typisierte Events |
| 3 | Celery + Redis für Async | Bewährter Stack, Retry-Mechanismus |
| 4 | Webhook-Subscriptions pro Tenant | Self-Service Integrationen |

---

## 1. Kontext

Risk-Hub benötigt asynchrone Verarbeitung für:

- **PDF-Generierung**: Ex-Konzepte, Berichte (zeitintensiv)
- **Benachrichtigungen**: E-Mail, Push, Slack
- **Externe Integrationen**: ERP-Systeme, Behörden-Schnittstellen
- **Audit-Trail**: Asynchrones Logging ohne Latenz-Impact
- **Modul-Entkopplung**: Substances ↔ Explosionsschutz

### 1.1 Aktueller Stand

```
src/outbox/
├── models.py      # OutboxMessage Model (existiert)
└── ...
```

Das `outbox`-Modul existiert bereits, benötigt aber Standardisierung.

---

## 2. Architektur-Entscheidungen

### 2.1 Transactional Outbox Pattern

```
┌─────────────────────────────────────────────────────────────────┐
│                    TRANSACTIONAL OUTBOX                          │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌──────────────┐     ┌──────────────┐     ┌──────────────┐     │
│  │   Service    │────►│  Transaction │────►│   Database   │     │
│  │              │     │              │     │              │     │
│  │ create_area()│     │ 1. Area      │     │ ex_area      │     │
│  │              │     │ 2. Outbox    │     │ outbox_msg   │     │
│  └──────────────┘     └──────────────┘     └──────┬───────┘     │
│                                                    │             │
│                                            Poll/CDC│             │
│                                                    ▼             │
│  ┌──────────────┐     ┌──────────────┐     ┌──────────────┐     │
│  │   Webhook    │◄────│    Celery    │◄────│   Relay      │     │
│  │   Endpoint   │     │    Worker    │     │   Process    │     │
│  └──────────────┘     └──────────────┘     └──────────────┘     │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

**Vorteile:**
- Atomare Transaktion (Event + Business-Daten)
- Keine Lost Events
- Retry ohne Duplikate (Idempotenz)

### 2.2 Outbox-Schema

```sql
CREATE TABLE outbox_message (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL,
    
    -- Event Metadata
    event_type VARCHAR(100) NOT NULL,
    event_version VARCHAR(10) NOT NULL DEFAULT '1.0',
    aggregate_type VARCHAR(100) NOT NULL,
    aggregate_id UUID NOT NULL,
    
    -- Payload
    payload JSONB NOT NULL,
    metadata JSONB DEFAULT '{}',
    
    -- Processing State
    status VARCHAR(20) NOT NULL DEFAULT 'pending',
    retry_count INTEGER NOT NULL DEFAULT 0,
    max_retries INTEGER NOT NULL DEFAULT 5,
    
    -- Timestamps
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    processed_at TIMESTAMPTZ,
    scheduled_for TIMESTAMPTZ,
    
    -- Error Tracking
    last_error TEXT,
    
    CONSTRAINT outbox_status_chk CHECK (
        status IN ('pending', 'processing', 'completed', 'failed', 'dead_letter')
    )
);

CREATE INDEX idx_outbox_pending ON outbox_message(status, scheduled_for)
    WHERE status IN ('pending', 'processing');
CREATE INDEX idx_outbox_tenant ON outbox_message(tenant_id, created_at);
CREATE INDEX idx_outbox_aggregate ON outbox_message(aggregate_type, aggregate_id);
```

### 2.3 Django Model

```python
# outbox/models.py
from django.db import models
from enum import Enum
import uuid


class OutboxStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    DEAD_LETTER = "dead_letter"


class OutboxMessage(models.Model):
    """Transactional outbox for reliable event delivery."""
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4)
    tenant_id = models.UUIDField(db_index=True)
    
    # Event Metadata
    event_type = models.CharField(max_length=100, db_index=True)
    event_version = models.CharField(max_length=10, default="1.0")
    aggregate_type = models.CharField(max_length=100)
    aggregate_id = models.UUIDField()
    
    # Payload
    payload = models.JSONField()
    metadata = models.JSONField(default=dict)
    
    # Processing State
    status = models.CharField(
        max_length=20,
        choices=[(s.value, s.name) for s in OutboxStatus],
        default=OutboxStatus.PENDING.value,
        db_index=True,
    )
    retry_count = models.IntegerField(default=0)
    max_retries = models.IntegerField(default=5)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    processed_at = models.DateTimeField(null=True, blank=True)
    scheduled_for = models.DateTimeField(null=True, blank=True)
    
    # Error Tracking
    last_error = models.TextField(blank=True, default="")
    
    class Meta:
        db_table = "outbox_message"
        indexes = [
            models.Index(
                fields=["status", "scheduled_for"],
                name="idx_outbox_pending",
                condition=models.Q(status__in=["pending", "processing"]),
            ),
        ]
```

---

## 3. Domain Events

### 3.1 Event-Katalog

| Event | Aggregate | Trigger |
| ----- | --------- | ------- |
| `area.created` | ExArea | Neuer Ex-Bereich angelegt |
| `area.updated` | ExArea | Ex-Bereich geändert |
| `area.deleted` | ExArea | Ex-Bereich gelöscht |
| `concept.created` | ExConcept | Neues Ex-Konzept |
| `concept.approved` | ExConcept | Ex-Konzept freigegeben |
| `concept.rejected` | ExConcept | Ex-Konzept abgelehnt |
| `equipment.created` | Equipment | Neues Betriebsmittel |
| `equipment.inspection_due` | Equipment | Prüfung fällig |
| `substance.created` | Substance | Neuer Gefahrstoff |
| `substance.sds_updated` | Substance | SDS aktualisiert |
| `inventory.low_stock` | Inventory | Bestand unter Minimum |
| `document.uploaded` | Document | Neues Dokument |
| `user.invited` | User | User eingeladen |
| `user.joined` | User | User beigetreten |

### 3.2 Event-Struktur

```python
# events/base.py
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any
from uuid import UUID, uuid4


@dataclass(frozen=True)
class DomainEvent:
    """Base class for all domain events."""
    
    event_id: UUID = field(default_factory=uuid4)
    event_type: str = field(init=False)
    event_version: str = "1.0"
    occurred_at: datetime = field(default_factory=datetime.utcnow)
    
    # Context
    tenant_id: UUID = field(default=None)
    user_id: UUID | None = field(default=None)
    correlation_id: UUID | None = field(default=None)
    
    # Aggregate
    aggregate_type: str = field(init=False)
    aggregate_id: UUID = field(default=None)
    
    def to_dict(self) -> dict[str, Any]:
        """Serialize event to dictionary."""
        return {
            "event_id": str(self.event_id),
            "event_type": self.event_type,
            "event_version": self.event_version,
            "occurred_at": self.occurred_at.isoformat(),
            "tenant_id": str(self.tenant_id) if self.tenant_id else None,
            "user_id": str(self.user_id) if self.user_id else None,
            "correlation_id": str(self.correlation_id) if self.correlation_id else None,
            "aggregate_type": self.aggregate_type,
            "aggregate_id": str(self.aggregate_id) if self.aggregate_id else None,
            "payload": self._payload(),
        }
    
    def _payload(self) -> dict[str, Any]:
        """Override in subclasses for event-specific payload."""
        return {}
```

### 3.3 Konkrete Events

```python
# events/explosionsschutz.py
from dataclasses import dataclass, field
from uuid import UUID
from .base import DomainEvent


@dataclass(frozen=True)
class AreaCreated(DomainEvent):
    """Fired when a new Ex-Area is created."""
    
    event_type: str = field(default="area.created", init=False)
    aggregate_type: str = field(default="ExArea", init=False)
    
    # Event-specific data
    area_id: UUID = None
    area_name: str = ""
    zone_classification: str = ""
    site_id: UUID = None
    
    def _payload(self) -> dict:
        return {
            "area_id": str(self.area_id),
            "area_name": self.area_name,
            "zone_classification": self.zone_classification,
            "site_id": str(self.site_id) if self.site_id else None,
        }


@dataclass(frozen=True)
class ConceptApproved(DomainEvent):
    """Fired when an Ex-Concept is approved."""
    
    event_type: str = field(default="concept.approved", init=False)
    aggregate_type: str = field(default="ExConcept", init=False)
    
    concept_id: UUID = None
    concept_title: str = ""
    approved_by: UUID = None
    approval_comment: str = ""
    
    def _payload(self) -> dict:
        return {
            "concept_id": str(self.concept_id),
            "concept_title": self.concept_title,
            "approved_by": str(self.approved_by) if self.approved_by else None,
            "approval_comment": self.approval_comment,
        }


@dataclass(frozen=True)
class EquipmentInspectionDue(DomainEvent):
    """Fired when equipment inspection is due."""
    
    event_type: str = field(default="equipment.inspection_due", init=False)
    aggregate_type: str = field(default="Equipment", init=False)
    
    equipment_id: UUID = None
    equipment_name: str = ""
    inspection_type: str = ""
    due_date: str = ""
    days_until_due: int = 0
    
    def _payload(self) -> dict:
        return {
            "equipment_id": str(self.equipment_id),
            "equipment_name": self.equipment_name,
            "inspection_type": self.inspection_type,
            "due_date": self.due_date,
            "days_until_due": self.days_until_due,
        }
```

---

## 4. Event Publishing

### 4.1 Event Publisher Service

```python
# events/publisher.py
from django.db import transaction
from outbox.models import OutboxMessage
from .base import DomainEvent


class EventPublisher:
    """Publishes domain events to the outbox."""
    
    def publish(self, event: DomainEvent) -> OutboxMessage:
        """
        Publish event to outbox within current transaction.
        
        MUST be called within a database transaction to ensure
        atomicity with business data.
        """
        event_dict = event.to_dict()
        
        return OutboxMessage.objects.create(
            tenant_id=event.tenant_id,
            event_type=event.event_type,
            event_version=event.event_version,
            aggregate_type=event.aggregate_type,
            aggregate_id=event.aggregate_id,
            payload=event_dict["payload"],
            metadata={
                "correlation_id": event_dict.get("correlation_id"),
                "user_id": event_dict.get("user_id"),
            },
        )
    
    def publish_many(self, events: list[DomainEvent]) -> list[OutboxMessage]:
        """Publish multiple events in a single transaction."""
        return [self.publish(event) for event in events]


# Singleton instance
event_publisher = EventPublisher()
```

### 4.2 Service-Integration

```python
# explosionsschutz/services.py
from django.db import transaction
from events.publisher import event_publisher
from events.explosionsschutz import AreaCreated


class AreaService:
    """Service for Ex-Area management."""
    
    @transaction.atomic
    def create_area(
        self,
        tenant_id: UUID,
        user_id: UUID,
        site_id: UUID,
        name: str,
        zone_classification: str,
        **kwargs,
    ) -> Area:
        """Create a new Ex-Area with event publishing."""
        
        # 1. Create the area
        area = Area.objects.create(
            tenant_id=tenant_id,
            site_id=site_id,
            name=name,
            zone_classification=zone_classification,
            **kwargs,
        )
        
        # 2. Publish event (same transaction!)
        event_publisher.publish(
            AreaCreated(
                tenant_id=tenant_id,
                user_id=user_id,
                aggregate_id=area.id,
                area_id=area.id,
                area_name=area.name,
                zone_classification=area.zone_classification,
                site_id=site_id,
            )
        )
        
        return area
```

---

## 5. Event Processing (Celery)

### 5.1 Outbox Relay Task

```python
# outbox/tasks.py
from celery import shared_task
from django.db import transaction
from django.utils import timezone
from .models import OutboxMessage, OutboxStatus


@shared_task(bind=True, max_retries=3)
def process_outbox_messages(self):
    """
    Poll outbox and dispatch pending messages.
    
    Runs every 5 seconds via Celery Beat.
    """
    batch_size = 100
    
    # Select pending messages
    messages = OutboxMessage.objects.filter(
        status=OutboxStatus.PENDING.value,
        scheduled_for__lte=timezone.now(),
    ).select_for_update(skip_locked=True)[:batch_size]
    
    for message in messages:
        try:
            with transaction.atomic():
                # Mark as processing
                message.status = OutboxStatus.PROCESSING.value
                message.save(update_fields=["status"])
                
                # Dispatch to handlers
                dispatch_event.delay(str(message.id))
                
        except Exception as e:
            message.status = OutboxStatus.FAILED.value
            message.last_error = str(e)
            message.retry_count += 1
            message.save()


@shared_task(bind=True, max_retries=5, default_retry_delay=60)
def dispatch_event(self, message_id: str):
    """Dispatch a single event to all handlers."""
    
    try:
        message = OutboxMessage.objects.get(id=message_id)
        
        # 1. Internal handlers
        handle_internal_event(message)
        
        # 2. Webhook delivery
        deliver_webhooks(message)
        
        # Mark completed
        message.status = OutboxStatus.COMPLETED.value
        message.processed_at = timezone.now()
        message.save()
        
    except Exception as e:
        message = OutboxMessage.objects.get(id=message_id)
        message.retry_count += 1
        message.last_error = str(e)
        
        if message.retry_count >= message.max_retries:
            message.status = OutboxStatus.DEAD_LETTER.value
        else:
            message.status = OutboxStatus.PENDING.value
            message.scheduled_for = timezone.now() + timedelta(
                seconds=60 * (2 ** message.retry_count)  # Exponential backoff
            )
        
        message.save()
        raise self.retry(exc=e)
```

### 5.2 Celery Beat Schedule

```python
# config/celery.py
from celery.schedules import crontab

CELERY_BEAT_SCHEDULE = {
    "process-outbox": {
        "task": "outbox.tasks.process_outbox_messages",
        "schedule": 5.0,  # Every 5 seconds
    },
    "cleanup-completed-outbox": {
        "task": "outbox.tasks.cleanup_completed",
        "schedule": crontab(hour=2, minute=0),  # Daily at 2 AM
        "kwargs": {"retention_days": 30},
    },
    "check-equipment-inspections": {
        "task": "explosionsschutz.tasks.check_inspection_due",
        "schedule": crontab(hour=6, minute=0),  # Daily at 6 AM
    },
}
```

---

## 6. Webhook Subscriptions

### 6.1 Webhook-Schema

```sql
CREATE TABLE webhook_subscription (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL REFERENCES tenancy_organization(tenant_id),
    
    -- Configuration
    name VARCHAR(200) NOT NULL,
    url VARCHAR(2000) NOT NULL,
    secret VARCHAR(200) NOT NULL,
    
    -- Event Filter
    event_types TEXT[] NOT NULL,  -- ['area.*', 'concept.approved']
    
    -- State
    is_active BOOLEAN NOT NULL DEFAULT true,
    failure_count INTEGER NOT NULL DEFAULT 0,
    last_triggered_at TIMESTAMPTZ,
    last_success_at TIMESTAMPTZ,
    last_failure_at TIMESTAMPTZ,
    last_error TEXT,
    
    -- Metadata
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    created_by_user_id UUID
);

CREATE TABLE webhook_delivery (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    subscription_id UUID NOT NULL REFERENCES webhook_subscription(id),
    outbox_message_id UUID NOT NULL REFERENCES outbox_message(id),
    
    -- Request/Response
    request_headers JSONB,
    request_body JSONB,
    response_status INTEGER,
    response_body TEXT,
    
    -- Timing
    duration_ms INTEGER,
    attempted_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    
    -- Status
    success BOOLEAN NOT NULL
);

CREATE INDEX idx_webhook_delivery_sub ON webhook_delivery(subscription_id, attempted_at DESC);
```

### 6.2 Webhook Delivery

```python
# webhooks/delivery.py
import hmac
import hashlib
import httpx
from datetime import datetime


class WebhookDeliveryService:
    """Delivers webhooks to subscribers."""
    
    def __init__(self, timeout: float = 10.0):
        self.timeout = timeout
    
    def deliver(
        self,
        subscription: WebhookSubscription,
        message: OutboxMessage,
    ) -> WebhookDelivery:
        """Deliver a webhook with HMAC signature."""
        
        payload = {
            "event_id": str(message.id),
            "event_type": message.event_type,
            "event_version": message.event_version,
            "timestamp": message.created_at.isoformat(),
            "tenant_id": str(message.tenant_id),
            "data": message.payload,
        }
        
        body = json.dumps(payload, default=str)
        signature = self._sign(body, subscription.secret)
        
        headers = {
            "Content-Type": "application/json",
            "X-Webhook-Signature": f"sha256={signature}",
            "X-Webhook-Event": message.event_type,
            "X-Webhook-Delivery-ID": str(uuid.uuid4()),
            "User-Agent": "RiskHub-Webhooks/1.0",
        }
        
        start = datetime.utcnow()
        
        try:
            response = httpx.post(
                subscription.url,
                content=body,
                headers=headers,
                timeout=self.timeout,
            )
            
            success = 200 <= response.status_code < 300
            
            return WebhookDelivery.objects.create(
                subscription=subscription,
                outbox_message=message,
                request_headers=headers,
                request_body=payload,
                response_status=response.status_code,
                response_body=response.text[:10000],
                duration_ms=int((datetime.utcnow() - start).total_seconds() * 1000),
                success=success,
            )
            
        except Exception as e:
            return WebhookDelivery.objects.create(
                subscription=subscription,
                outbox_message=message,
                request_headers=headers,
                request_body=payload,
                response_status=0,
                response_body=str(e),
                duration_ms=int((datetime.utcnow() - start).total_seconds() * 1000),
                success=False,
            )
    
    def _sign(self, payload: str, secret: str) -> str:
        """Create HMAC-SHA256 signature."""
        return hmac.new(
            secret.encode(),
            payload.encode(),
            hashlib.sha256,
        ).hexdigest()
```

---

## 7. Event Handlers (Internal)

### 7.1 Handler Registry

```python
# events/handlers/registry.py
from typing import Callable
from collections import defaultdict


class EventHandlerRegistry:
    """Registry for internal event handlers."""
    
    def __init__(self):
        self._handlers: dict[str, list[Callable]] = defaultdict(list)
    
    def register(self, event_type: str):
        """Decorator to register a handler."""
        def decorator(func: Callable):
            self._handlers[event_type].append(func)
            return func
        return decorator
    
    def get_handlers(self, event_type: str) -> list[Callable]:
        """Get all handlers for an event type."""
        handlers = self._handlers.get(event_type, [])
        
        # Also match wildcards (e.g., 'area.*')
        for pattern, pattern_handlers in self._handlers.items():
            if pattern.endswith(".*"):
                prefix = pattern[:-2]
                if event_type.startswith(prefix + "."):
                    handlers.extend(pattern_handlers)
        
        return handlers


event_handlers = EventHandlerRegistry()
```

### 7.2 Konkrete Handler

```python
# events/handlers/notifications.py
from events.handlers.registry import event_handlers
from notifications.services import notification_service


@event_handlers.register("concept.approved")
def notify_concept_approval(event_data: dict):
    """Send notification when concept is approved."""
    notification_service.send(
        tenant_id=event_data["tenant_id"],
        template="concept_approved",
        context={
            "concept_title": event_data["payload"]["concept_title"],
            "approved_by": event_data["payload"]["approved_by"],
        },
        recipients=["safety_manager"],
    )


@event_handlers.register("equipment.inspection_due")
def notify_inspection_due(event_data: dict):
    """Send reminder for upcoming inspection."""
    notification_service.send(
        tenant_id=event_data["tenant_id"],
        template="inspection_reminder",
        context={
            "equipment_name": event_data["payload"]["equipment_name"],
            "due_date": event_data["payload"]["due_date"],
            "days_until_due": event_data["payload"]["days_until_due"],
        },
        channels=["email", "push"],
    )


@event_handlers.register("area.*")
def update_area_search_index(event_data: dict):
    """Update search index when area changes."""
    from search.services import search_service
    
    search_service.reindex(
        index="areas",
        document_id=event_data["payload"]["area_id"],
    )
```

---

## 8. Monitoring

### 8.1 Metrics

```python
# outbox/metrics.py
from prometheus_client import Counter, Histogram, Gauge

# Counters
events_published = Counter(
    "riskhub_events_published_total",
    "Total events published to outbox",
    ["event_type", "tenant_id"],
)

events_processed = Counter(
    "riskhub_events_processed_total",
    "Total events processed",
    ["event_type", "status"],
)

webhooks_delivered = Counter(
    "riskhub_webhooks_delivered_total",
    "Total webhook deliveries",
    ["status"],
)

# Histograms
event_processing_duration = Histogram(
    "riskhub_event_processing_seconds",
    "Event processing duration",
    ["event_type"],
)

webhook_delivery_duration = Histogram(
    "riskhub_webhook_delivery_seconds",
    "Webhook delivery duration",
)

# Gauges
outbox_pending_count = Gauge(
    "riskhub_outbox_pending_count",
    "Number of pending outbox messages",
)

outbox_dead_letter_count = Gauge(
    "riskhub_outbox_dead_letter_count",
    "Number of dead-letter messages",
)
```

---

## 9. Konsequenzen

### Positiv

- ✅ **Zuverlässigkeit**: Keine Lost Events durch Outbox Pattern
- ✅ **Entkopplung**: Module kommunizieren via Events
- ✅ **Skalierbarkeit**: Celery Worker horizontal skalierbar
- ✅ **Integrierbarkeit**: Webhooks für externe Systeme

### Negativ

- ❌ **Eventual Consistency**: Nicht sofort konsistent
- ❌ **Debugging**: Event-Flow schwieriger nachzuvollziehen
- ❌ **Infrastruktur**: Redis + Celery erforderlich

---

## 10. Referenzen

- [Transactional Outbox Pattern](https://microservices.io/patterns/data/transactional-outbox.html)
- [Domain Events](https://martinfowler.com/eaaDev/DomainEvent.html)
- [Celery Best Practices](https://docs.celeryq.dev/en/stable/userguide/tasks.html)
- [Webhook Security](https://webhooks.fyi/security/hmac)

---

**Erstellt:** 2026-02-01  
**Version:** 1.0
