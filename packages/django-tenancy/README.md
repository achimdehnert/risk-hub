# django-tenancy

Shared multi-tenancy infrastructure for the BF Agent platform — per ADR-035.

## Core Components

- **Organization**: Tenant model with lifecycle management (trial → active → suspended → deleted)
- **Membership**: User-to-organization mapping with roles (owner, admin, member, viewer, external)
- **SubdomainTenantMiddleware**: Resolves tenant from subdomain or `X-Tenant-ID` header
- **TenantAwareManager**: Explicit `.for_tenant(uuid)` queryset filtering
- **Context propagation**: Async-safe contextvars + PostgreSQL RLS session variable
- **Health endpoints**: `/livez/` (liveness) + `/healthz/` (readiness with DB + Redis checks)
- **Decorators**: `tenant_context()` context manager, `@with_tenant_from_arg()` for Celery tasks

## Installation

```bash
pip install -e ".[dev]"
```

## Usage

```python
# settings.py
INSTALLED_APPS = [
    ...
    "django_tenancy",
]

MIDDLEWARE = [
    ...
    "django_tenancy.middleware.SubdomainTenantMiddleware",
]

# urls.py
from django_tenancy.healthz import liveness, readiness

urlpatterns = [
    path("livez/", liveness),
    path("healthz/", readiness),
]

# In views / services:
from django_tenancy.managers import TenantAwareManager

class MyModel(models.Model):
    tenant_id = models.UUIDField(db_index=True)
    objects = TenantAwareManager()

# Query with tenant isolation:
MyModel.objects.for_tenant(request.tenant_id)
```

## ADR-137: TenantManager (auto-filter)

```python
from django_tenancy.managers import TenantManager

class MyModel(models.Model):
    tenant_id = models.UUIDField(db_index=True)
    objects = TenantManager()

# In request context → auto-filtered by middleware tenant:
MyModel.objects.all()

# Explicit (Celery, management commands):
MyModel.objects.for_tenant(tenant_uuid)

# Admin / cross-tenant reports:
MyModel.objects.unscoped()
```

## ADR-137: Row-Level Security (Phase 2)

### Setup (once per database)

```bash
# 1. Create separate DB roles
python manage.py setup_rls_roles --dry-run   # preview
python manage.py setup_rls_roles \
    --app-user=risk_hub \
    --app-password=<secret>

# 2. Enable RLS on all tenant tables
python manage.py enable_rls --dry-run        # preview
python manage.py enable_rls                  # execute

# Single table:
python manage.py enable_rls --table=risk_assessment

# Remove RLS:
python manage.py enable_rls --disable
```

### DB Role Separation

| Role | Used by | RLS |
|------|---------|-----|
| `<db>_admin` (table owner) | migrate, createsuperuser | exempt |
| `<db>_app` (non-owner) | gunicorn, celery | **active** |

After `setup_rls_roles`, update `DATABASE_URL` for
gunicorn/celery to use the app-user. Keep the admin-user
for migrations.

## Critical Rule

`Organization.id != Organization.tenant_id` — **always** use `org.tenant_id` for data isolation.
