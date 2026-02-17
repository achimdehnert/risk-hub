---
trigger: always_on
---

# Project Facts: risk-hub (Schutztat)

## IMPORTANT: App Structure Difference
- Apps have NO "apps." prefix — use bare module names
- Source code lives in `src/` subdirectory
- Settings: SINGLE file `src/config/settings.py` (NOT split base/dev/prod)

## Apps (from src/config/settings.py INSTALLED_APPS)
common, tenancy, identity, permissions, audit, outbox, risk, actions,
documents, reporting, explosionsschutz, substances, notifications,
dashboard, approvals, ai_analysis, dsb

## Auth
- Django built-in auth (NO allauth)
- AUTH_USER_MODEL = "identity.User"
- Login: `/accounts/login/` (django.contrib.auth views)

## HTMX
- django_htmx IS installed and active
- HtmxMiddleware in MIDDLEWARE
- Use `request.htmx` (NOT raw header check)

## URL Namespace Map (from src/config/urls.py)
- "" → home | "dashboard/" → dashboard
- "risk/" → risk | "documents/" → documents | "actions/" → actions
- "ex/" → explosionsschutz (HTML) | "api/ex/" → explosionsschutz (API)
- "substances/" → substances (HTML) | "api/substances/" → substances (API)
- "notifications/" → notifications | "audit/" → audit | "dsb/" → dsb
- "api/v1/" → Django Ninja API

## Multi-Tenancy
- SubdomainTenantMiddleware: `common.middleware.SubdomainTenantMiddleware`
- RequestContextMiddleware: `common.middleware.RequestContextMiddleware`
- Every model MUST have `tenant_id = UUIDField(db_index=True)`

## Docker
- Dockerfile: `docker/app/Dockerfile`
- Container: risk_hub_web
- DB: risk_hub_db (postgres:16) | Redis: risk_hub_redis (redis:7)
- Production: https://demo.schutztat.de
