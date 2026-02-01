# ADR-003: Multi-Tenant & RBAC-Architektur (DB-getrieben, normalisiert)

| Metadaten | |
| --------- | --- |
| **Status** | ✅ APPROVED |
| **Version** | 1.0 |
| **Datum** | 2026-02-01 |
| **Autor** | Achim Dehnert (AI-unterstützt) |
| **Reviewer** | Technical Review |
| **Supersedes** | - |

---

## 📋 Executive Summary

Dieses ADR definiert die **referenzielle Grundlage** für Multi-Tenancy und Role-Based Access Control (RBAC) in Risk-Hub. Die Architektur basiert auf:

- **Database-First**: PostgreSQL als Single Source of Truth mit Row Level Security
- **Normalisierung**: 3NF für alle Entitäten, kein JSONB für strukturierte Daten
- **Separation of Concerns**: Klare Schichtentrennung DB → Service → View → Template
- **Naming Conventions**: Einheitliche, vorhersagbare Benennungen

### Kernentscheidungen

| # | Entscheidung | Begründung |
| --- | ------------ | ---------- |
| 1 | UUID als Primary Key | SSO/IAM-fähig, Merge-sicher |
| 2 | `tenant_id` auf allen Domain-Tabellen | RLS-Basis, keine Joins für Isolation |
| 3 | Permissions voll normalisiert | Referential Integrity, Auditierbarkeit |
| 4 | Scope-basierte Permissions | TENANT → SITE → ASSET Hierarchie |
| 5 | PostgreSQL RLS als Enforcement | Defense in Depth, DB ist finaler Gatekeeper |
| 6 | Service Layer für Business Logic | Testbar, wiederverwendbar |

---

## 1. Kontext

Risk-Hub entwickelt sich zu einem **Enterprise Multi-Tenant-System** für Risikomanagement (Explosionsschutz, Gefahrstoffe, Compliance). Die Anforderungen umfassen:

- **Security**: Strikte Tenant-Isolation (kein Cross-Tenant Data Leak)
- **Compliance**: Auditierbarkeit aller Änderungen (ISO 27001, BetrSichV)
- **Skalierbarkeit**: Hunderte Tenants, Tausende User
- **Flexibilität**: Tenant-spezifische Rollen und Permissions

### 1.1 Aktuelle Implementierung (Ist-Zustand)

```
src/
├── tenancy/
│   └── models.py          # Organization, Site
├── permissions/
│   └── models.py          # Permission, Role, Scope, Assignment
├── common/
│   ├── middleware.py      # SubdomainTenantMiddleware
│   └── context.py         # Thread-local tenant context
└── [domain modules]/
    └── models.py          # tenant_id auf allen Entitäten
```

**Stärken:**
- ✅ UUID-basierte IDs
- ✅ Scope-Konzept (TENANT/SITE/ASSET)
- ✅ Subdomain-basierte Tenant-Auflösung
- ✅ Thread-local Context

**Verbesserungspotential:**
- ❌ Keine RLS-Policies aktiv
- ❌ Lifecycle-Constraints fehlen (trial, suspended, deleted)
- ❌ Permission-Overrides nicht implementiert
- ❌ Audit-Trail unvollständig

---

## 2. Architektur-Entscheidungen

### 2.1 Tenant-Modell (Erweitert)

```sql
-- Erweiterte Organization mit Lifecycle
CREATE TABLE tenancy_organization (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL UNIQUE DEFAULT gen_random_uuid(),
    slug VARCHAR(63) NOT NULL UNIQUE,
    name VARCHAR(200) NOT NULL,
    
    -- Lifecycle Management
    status VARCHAR(20) NOT NULL DEFAULT 'trial',
    plan_code VARCHAR(50) NOT NULL DEFAULT 'free',
    trial_ends_at TIMESTAMPTZ,
    suspended_at TIMESTAMPTZ,
    suspended_reason TEXT,
    deleted_at TIMESTAMPTZ,
    
    -- Metadata
    settings JSONB DEFAULT '{}',  -- Nur für tenant-spezifische Config
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    
    -- Invarianten
    CONSTRAINT org_status_chk CHECK (
        status IN ('trial', 'active', 'suspended', 'deleted')
    ),
    CONSTRAINT org_trial_chk CHECK (
        status <> 'trial' OR trial_ends_at IS NOT NULL
    ),
    CONSTRAINT org_suspended_chk CHECK (
        status <> 'suspended' OR suspended_at IS NOT NULL
    ),
    CONSTRAINT org_deleted_chk CHECK (
        status <> 'deleted' OR deleted_at IS NOT NULL
    )
);

CREATE INDEX idx_org_status ON tenancy_organization(status);
CREATE INDEX idx_org_slug ON tenancy_organization(slug);
```

**Django Model:**

```python
class Organization(models.Model):
    """Tenant organization with lifecycle management."""
    
    STATUS_TRIAL = "trial"
    STATUS_ACTIVE = "active"
    STATUS_SUSPENDED = "suspended"
    STATUS_DELETED = "deleted"
    STATUS_CHOICES = [
        (STATUS_TRIAL, "Trial"),
        (STATUS_ACTIVE, "Active"),
        (STATUS_SUSPENDED, "Suspended"),
        (STATUS_DELETED, "Deleted"),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4)
    tenant_id = models.UUIDField(unique=True, default=uuid.uuid4)
    slug = models.SlugField(max_length=63, unique=True)
    name = models.CharField(max_length=200)
    
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_TRIAL)
    plan_code = models.CharField(max_length=50, default="free")
    trial_ends_at = models.DateTimeField(null=True, blank=True)
    suspended_at = models.DateTimeField(null=True, blank=True)
    suspended_reason = models.TextField(blank=True, default="")
    deleted_at = models.DateTimeField(null=True, blank=True)
    
    settings = models.JSONField(default=dict)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = "tenancy_organization"
        constraints = [
            models.CheckConstraint(
                check=models.Q(status__in=["trial", "active", "suspended", "deleted"]),
                name="org_status_chk"
            ),
        ]
    
    @property
    def is_active(self) -> bool:
        """Check if tenant can perform operations."""
        return self.status in (self.STATUS_TRIAL, self.STATUS_ACTIVE)
```

---

### 2.2 Tenant Membership (normalisiert)

```sql
CREATE TABLE tenancy_membership (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL REFERENCES tenancy_organization(tenant_id),
    user_id UUID NOT NULL,  -- FK zu auth_user oder IAM
    role VARCHAR(20) NOT NULL,
    invited_by_user_id UUID,
    invited_at TIMESTAMPTZ,
    accepted_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    
    CONSTRAINT membership_role_chk CHECK (
        role IN ('owner', 'admin', 'member', 'viewer', 'external')
    ),
    CONSTRAINT membership_unique UNIQUE (tenant_id, user_id)
);

CREATE INDEX idx_membership_tenant ON tenancy_membership(tenant_id);
CREATE INDEX idx_membership_user ON tenancy_membership(user_id);
CREATE INDEX idx_membership_role ON tenancy_membership(role);
```

---

### 2.3 Permission-System (voll normalisiert)

```sql
-- Permission-Katalog (global, nicht tenant-spezifisch)
CREATE TABLE permissions_permission (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    code VARCHAR(100) NOT NULL UNIQUE,
    module VARCHAR(50) NOT NULL,
    resource VARCHAR(50) NOT NULL,
    action VARCHAR(20) NOT NULL,
    description TEXT NOT NULL DEFAULT '',
    is_system BOOLEAN NOT NULL DEFAULT false,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    
    CONSTRAINT perm_code_format CHECK (
        code ~ '^[a-z_]+\.[a-z_]+$'
    ),
    CONSTRAINT perm_action_chk CHECK (
        action IN ('view', 'create', 'edit', 'delete', 'manage', 'export', 'approve')
    )
);

-- Index für schnelle Lookups
CREATE INDEX idx_perm_module ON permissions_permission(module);
CREATE INDEX idx_perm_resource ON permissions_permission(resource);
```

---

### 2.4 Role-Permission-Mapping (normalisiert)

```sql
-- Rollen pro Tenant (oder System-Rollen)
CREATE TABLE permissions_role (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID REFERENCES tenancy_organization(tenant_id),  -- NULL = System-Rolle
    name VARCHAR(120) NOT NULL,
    description TEXT NOT NULL DEFAULT '',
    is_system BOOLEAN NOT NULL DEFAULT false,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    
    CONSTRAINT role_tenant_name_unique UNIQUE (tenant_id, name)
);

-- Role → Permission Mapping
CREATE TABLE permissions_role_permission (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    role_id UUID NOT NULL REFERENCES permissions_role(id) ON DELETE CASCADE,
    permission_id UUID NOT NULL REFERENCES permissions_permission(id) ON DELETE CASCADE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    
    CONSTRAINT role_perm_unique UNIQUE (role_id, permission_id)
);

-- Permission-Overrides pro Membership
CREATE TABLE permissions_override (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    membership_id UUID NOT NULL REFERENCES tenancy_membership(id) ON DELETE CASCADE,
    permission_id UUID NOT NULL REFERENCES permissions_permission(id),
    allowed BOOLEAN NOT NULL,  -- true = grant, false = deny
    reason TEXT,
    granted_by_user_id UUID,
    granted_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    expires_at TIMESTAMPTZ,
    
    CONSTRAINT override_unique UNIQUE (membership_id, permission_id)
);
```

---

### 2.5 Scope-basierte Permissions

```sql
-- Scope definiert den Geltungsbereich einer Permission
CREATE TABLE permissions_scope (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL REFERENCES tenancy_organization(tenant_id),
    scope_type VARCHAR(12) NOT NULL,
    site_id UUID,  -- FK zu tenancy_site wenn scope_type = 'SITE'
    asset_id UUID,  -- FK zu asset wenn scope_type = 'ASSET'
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    
    CONSTRAINT scope_type_chk CHECK (
        scope_type IN ('TENANT', 'SITE', 'ASSET')
    ),
    CONSTRAINT scope_site_chk CHECK (
        scope_type <> 'SITE' OR site_id IS NOT NULL
    ),
    CONSTRAINT scope_asset_chk CHECK (
        scope_type <> 'ASSET' OR asset_id IS NOT NULL
    )
);

-- Assignment: User → Role → Scope
CREATE TABLE permissions_assignment (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL REFERENCES tenancy_organization(tenant_id),
    user_id UUID NOT NULL,
    role_id UUID NOT NULL REFERENCES permissions_role(id),
    scope_id UUID NOT NULL REFERENCES permissions_scope(id),
    created_by_user_id UUID,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    valid_from TIMESTAMPTZ,
    valid_to TIMESTAMPTZ,
    
    CONSTRAINT assignment_unique UNIQUE (tenant_id, user_id, role_id, scope_id)
);

CREATE INDEX idx_assignment_user ON permissions_assignment(tenant_id, user_id);
CREATE INDEX idx_assignment_valid ON permissions_assignment(valid_from, valid_to);
```

---

## 3. Permission-Naming-Konvention

### 3.1 Format

```
<module>.<action>
```

oder für Resource-spezifisch:

```
<module>_<resource>.<action>
```

### 3.2 Action-Vokabular (einheitlich)

| Action | Bedeutung | Beispiel |
| ------ | --------- | -------- |
| `view` | Lesen | `assessment.view` |
| `create` | Erstellen | `area.create` |
| `edit` | Bearbeiten | `equipment.edit` |
| `delete` | Löschen | `substance.delete` |
| `manage` | Alle CRUD + Admin | `tenant.manage` |
| `export` | Export/Download | `report.export` |
| `approve` | Freigabe/Genehmigung | `concept.approve` |

### 3.3 Module-Namen (Risk-Hub)

| Module | Prefix | Beispiele |
| ------ | ------ | --------- |
| Tenancy | `tenant` | `tenant.manage`, `tenant.view` |
| Users | `user` | `user.invite`, `user.edit` |
| Sites | `site` | `site.create`, `site.delete` |
| Explosionsschutz | `ex` | `ex_area.create`, `ex_concept.approve` |
| Substances | `substance` | `substance.create`, `substance.edit` |
| Documents | `document` | `document.upload`, `document.delete` |
| Audit | `audit` | `audit.view`, `audit.export` |
| Billing | `billing` | `billing.view`, `billing.manage` |

### 3.4 Standard-Permissions

```python
# permissions/fixtures/default_permissions.py

DEFAULT_PERMISSIONS = [
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
    
    # Explosionsschutz
    {"code": "ex_area.view", "module": "ex", "resource": "area", "action": "view"},
    {"code": "ex_area.create", "module": "ex", "resource": "area", "action": "create"},
    {"code": "ex_area.edit", "module": "ex", "resource": "area", "action": "edit"},
    {"code": "ex_concept.view", "module": "ex", "resource": "concept", "action": "view"},
    {"code": "ex_concept.create", "module": "ex", "resource": "concept", "action": "create"},
    {"code": "ex_concept.approve", "module": "ex", "resource": "concept", "action": "approve"},
    
    # Substances
    {"code": "substance.view", "module": "substance", "resource": "substance", "action": "view"},
    {"code": "substance.create", "module": "substance", "resource": "substance", "action": "create"},
    {"code": "substance.edit", "module": "substance", "resource": "substance", "action": "edit"},
    
    # Documents
    {"code": "document.view", "module": "document", "resource": "document", "action": "view"},
    {"code": "document.upload", "module": "document", "resource": "document", "action": "create"},
    {"code": "document.delete", "module": "document", "resource": "document", "action": "delete"},
    
    # Audit
    {"code": "audit.view", "module": "audit", "resource": "audit", "action": "view"},
    {"code": "audit.export", "module": "audit", "resource": "audit", "action": "export"},
]
```

---

## 4. Row Level Security (RLS)

### 4.1 Prinzip

**Jede tenant-scoped Tabelle** besitzt:

1. `tenant_id UUID NOT NULL`
2. RLS Policy mit `current_setting('app.tenant_id')`

### 4.2 RLS-Template

```sql
-- Aktivieren für Domain-Tabelle
ALTER TABLE explosionsschutz_area ENABLE ROW LEVEL SECURITY;
ALTER TABLE explosionsschutz_area FORCE ROW LEVEL SECURITY;

-- Isolation Policy
CREATE POLICY tenant_isolation ON explosionsschutz_area
    FOR ALL
    USING (tenant_id = current_setting('app.tenant_id', true)::uuid)
    WITH CHECK (tenant_id = current_setting('app.tenant_id', true)::uuid);

-- Superuser-Bypass (optional, für Admin)
CREATE POLICY admin_bypass ON explosionsschutz_area
    FOR ALL
    TO postgres
    USING (true)
    WITH CHECK (true);
```

### 4.3 Session-Kontext (Middleware)

```python
# common/middleware.py

class TenantContextMiddleware(MiddlewareMixin):
    """Set PostgreSQL session variables for RLS."""
    
    def process_request(self, request: HttpRequest) -> None:
        tenant_id = getattr(request, "tenant_id", None)
        user_id = getattr(request, "user", None)
        
        if tenant_id:
            with connection.cursor() as cursor:
                cursor.execute(
                    "SET LOCAL app.tenant_id = %s",
                    [str(tenant_id)]
                )
        
        if user_id and hasattr(user_id, "id"):
            with connection.cursor() as cursor:
                cursor.execute(
                    "SET LOCAL app.user_id = %s",
                    [str(user_id.id)]
                )
```

---

## 5. Separation of Concerns

### 5.1 Schichtenmodell

```
┌─────────────────────────────────────────────────────────────┐
│                     PRESENTATION LAYER                       │
│  Templates (HTML/HTMX) │ JavaScript │ CSS                    │
│  → Darstellung, Progressive Enhancement                      │
│  → KEINE Business-Logik, KEINE Security-Logik               │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                      VIEW LAYER                              │
│  Django Views │ DRF ViewSets │ HTMX Handlers                 │
│  → Request/Response Orchestration                            │
│  → Ruft Services auf, formatiert Output                      │
│  → Darf Permission-Decorator verwenden                       │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                     SERVICE LAYER                            │
│  Business Logic │ Domain Services │ Authorization Service    │
│  → KEINE HTTP-Abhängigkeit                                   │
│  → KEINE Template-Abhängigkeit                               │
│  → Einzige Stelle für Business Rules                         │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                    REPOSITORY LAYER                          │
│  Django ORM │ QuerySets │ Managers                           │
│  → Datenzugriff abstrahiert                                  │
│  → tenant_id Filter                                          │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                     DATABASE LAYER                           │
│  PostgreSQL │ RLS Policies │ Constraints │ Triggers          │
│  → FINALER ENFORCER für Tenant-Isolation                     │
│  → Invarianten in DB-Constraints                             │
│  → Single Source of Truth                                    │
└─────────────────────────────────────────────────────────────┘
```

### 5.2 Authorization Service

```python
# permissions/services/authorization.py

from typing import Protocol
from uuid import UUID

class AuthorizationService(Protocol):
    """Authorization service interface."""
    
    def can(
        self,
        user_id: UUID,
        tenant_id: UUID,
        permission_code: str,
        scope_id: UUID | None = None,
    ) -> bool:
        """Check if user has permission in scope."""
        ...
    
    def get_effective_permissions(
        self,
        user_id: UUID,
        tenant_id: UUID,
    ) -> set[str]:
        """Get all effective permissions for user in tenant."""
        ...


class DatabaseAuthorizationService:
    """Database-driven authorization service."""
    
    def can(
        self,
        user_id: UUID,
        tenant_id: UUID,
        permission_code: str,
        scope_id: UUID | None = None,
    ) -> bool:
        # 1. Get membership
        membership = TenantMembership.objects.filter(
            tenant_id=tenant_id,
            user_id=user_id,
        ).first()
        
        if not membership:
            return False
        
        # 2. Check explicit deny override
        deny_override = PermissionOverride.objects.filter(
            membership_id=membership.id,
            permission__code=permission_code,
            allowed=False,
        ).exists()
        
        if deny_override:
            return False
        
        # 3. Check explicit grant override
        grant_override = PermissionOverride.objects.filter(
            membership_id=membership.id,
            permission__code=permission_code,
            allowed=True,
        ).exists()
        
        if grant_override:
            return True
        
        # 4. Check role-based permission
        return RolePermission.objects.filter(
            role__assignments__user_id=user_id,
            role__assignments__tenant_id=tenant_id,
            permission__code=permission_code,
        ).exists()
```

### 5.3 View-Decorator

```python
# permissions/decorators.py

from functools import wraps
from django.http import HttpResponseForbidden

def require_permission(permission_code: str):
    """Decorator to check permission before view execution."""
    
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            if not hasattr(request, "tenant_id") or not request.tenant_id:
                return HttpResponseForbidden("No tenant context")
            
            auth_service = get_authorization_service()
            
            if not auth_service.can(
                user_id=request.user.id,
                tenant_id=request.tenant_id,
                permission_code=permission_code,
            ):
                return HttpResponseForbidden(f"Missing permission: {permission_code}")
            
            return view_func(request, *args, **kwargs)
        
        return wrapper
    return decorator


# Verwendung in Views
@login_required
@require_permission("ex_area.create")
def area_create(request):
    ...
```

---

## 6. Naming-Konventionen

### 6.1 Datenbank-Tabellen

| Konvention | Beispiel |
| ---------- | -------- |
| `<app>_<entity>` | `tenancy_organization`, `permissions_role` |
| Lowercase, Underscore | `explosionsschutz_area`, `substances_substance` |
| Singular | `tenancy_site` (nicht `sites`) |

### 6.2 Django Models

| Konvention | Beispiel |
| ---------- | -------- |
| PascalCase | `Organization`, `ExArea` |
| Singular | `Permission` (nicht `Permissions`) |
| Suffix für Beziehungen | `TenantMembership`, `RolePermission` |

### 6.3 API-Endpoints

| Konvention | Beispiel |
| ---------- | -------- |
| Plural, kebab-case | `/api/v1/organizations/` |
| Nested Resources | `/api/v1/tenants/{id}/sites/` |
| Actions mit Verb | `/api/v1/concepts/{id}/approve/` |

### 6.4 URL-Namen (Django)

| Konvention | Beispiel |
| ---------- | -------- |
| `<app>:<entity>-<action>` | `explosionsschutz:area-list` |
| `<app>:<entity>-detail` | `substances:substance-detail` |
| Lowercase, hyphen | `permissions:role-create` |

### 6.5 Service-Methoden

| Konvention | Beispiel |
| ---------- | -------- |
| `<action>_<entity>` | `create_area()`, `approve_concept()` |
| `get_<entity>_by_<field>` | `get_user_by_email()` |
| `list_<entities>` | `list_substances()` |
| `can_<action>` | `can_edit_area()` |

### 6.6 Test-Methoden

| Konvention | Beispiel |
| ---------- | -------- |
| `test_<action>_<entity>_<scenario>` | `test_create_area_success` |
| `test_should_<expected>_when_<condition>` | `test_should_deny_when_no_permission` |

---

## 7. Migration & Rollout

### 7.1 Phasen

| Phase | Beschreibung | Breaking |
| ----- | ------------ | -------- |
| 1 | Neue Tabellen additiv hinzufügen | Nein |
| 2 | Dual-Write (alt + neu) | Nein |
| 3 | Backfill bestehender Daten | Nein |
| 4 | RLS-Policies aktivieren | Nein |
| 5 | Alte Strukturen deprecaten | Nein |
| 6 | Alte Strukturen entfernen | Ja |

### 7.2 Rollback-Strategie

```sql
-- Notfall-Rollback: RLS deaktivieren
ALTER TABLE explosionsschutz_area DISABLE ROW LEVEL SECURITY;

-- Notfall-Rollback: Session-Variable ignorieren
DROP POLICY tenant_isolation ON explosionsschutz_area;
```

---

## 8. Caching-Strategie

### 8.1 Permission-Cache

```python
# Cache-Key Format
CACHE_KEY = "perms:{tenant_id}:{user_id}:{version}"

# TTL: 60 Sekunden (kurz, da Security-kritisch)
PERMISSION_CACHE_TTL = 60

# Invalidierung bei Änderungen
@receiver(post_save, sender=RolePermission)
def invalidate_permission_cache(sender, instance, **kwargs):
    cache.delete_pattern(f"perms:{instance.role.tenant_id}:*")
```

### 8.2 Fail-Closed

Bei Cache-Fehlern oder Unsicherheit → **immer deny**.

---

## 9. Audit-Trail

### 9.1 Audit-Log-Schema

```sql
CREATE TABLE audit_log (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL,
    user_id UUID,
    action VARCHAR(50) NOT NULL,
    entity_type VARCHAR(100) NOT NULL,
    entity_id UUID NOT NULL,
    old_value JSONB,
    new_value JSONB,
    ip_address INET,
    user_agent TEXT,
    request_id UUID,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    
    CONSTRAINT audit_action_chk CHECK (
        action IN ('create', 'update', 'delete', 'view', 'export', 'approve', 'deny', 'login', 'logout')
    )
);

CREATE INDEX idx_audit_tenant ON audit_log(tenant_id, created_at DESC);
CREATE INDEX idx_audit_entity ON audit_log(entity_type, entity_id);
CREATE INDEX idx_audit_user ON audit_log(user_id, created_at DESC);
```

---

## 10. Konsequenzen

### 10.1 Positiv

- ✅ **Defense in Depth**: DB als finaler Gatekeeper
- ✅ **Compliance-Ready**: Vollständiger Audit-Trail
- ✅ **Skalierbar**: RLS performant bei vielen Tenants
- ✅ **Testbar**: Service Layer ohne HTTP-Abhängigkeit
- ✅ **Wartbar**: Klare Konventionen, vorhersagbar

### 10.2 Negativ

- ❌ Mehr Tabellen (Normalisierung)
- ❌ Höherer Initialaufwand
- ❌ RLS-Debugging komplexer

### 10.3 Risiken

| Risiko | Mitigation |
| ------ | ---------- |
| RLS-Bypass bei DB-Admin | Separate Admin-Rollen, Audit |
| Performance bei vielen Permissions | Caching, Materialized Views |
| Migration bestehender Daten | Schrittweise, Dual-Write |

---

## 11. Referenzen

- [PostgreSQL Row Level Security](https://www.postgresql.org/docs/current/ddl-rowsecurity.html)
- [Django Multi-Tenancy Patterns](https://books.agiliq.com/projects/django-multi-tenant/en/latest/)
- [OWASP Access Control Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Access_Control_Cheat_Sheet.html)
- [ISO 27001 Access Control](https://www.iso.org/standard/27001)

---

## 12. Entscheidung

**✅ APPROVED** – Dieses ADR ist die referenzielle Grundlage für Multi-Tenancy & RBAC in Risk-Hub.

Abweichungen (z.B. JSONB für strukturierte Permissions) sind **nicht erlaubt** ohne neues ADR.

---

**Erstellt:** 2026-02-01
**Letzte Aktualisierung:** 2026-02-01
**Version:** 1.0
