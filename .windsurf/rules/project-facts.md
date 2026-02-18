---
trigger: always_on
---

# Project Facts: risk-hub (Schutztat)

## Apps (src/ directory, NOT apps/)

config, common, tenancy, substances, risk, explosionsschutz,
documents, approvals, notifications, permissions, audit

## Auth

- Django built-in auth
- Custom User model in `tenancy`
- Login: `/accounts/login/`

## HTMX

- HTMX 1.9 via CDN (no django_htmx package)
- Check: `request.headers.get("HX-Request")`
- DO NOT use `request.htmx`

## API

- Django Ninja at `/api/v1/` (NOT DRF)
- Auth: Bearer token via `ApiKeyAuth`

## Multi-Tenancy

- Subdomain-based tenant resolution
- All queries MUST filter by `tenant_id`
- `Organization.id` != `Organization.tenant_id`

## Docker

- Dockerfile: `docker/app/Dockerfile`
- Container: risk_hub_web (gunicorn:8000)
- DB: risk_hub_db (postgres:16) | Redis: risk_hub_redis (redis:7)
- Worker: risk_hub_worker (celery)
- Port: 8090 (mapped to host)
- Production: https://schutztat.de (demo.schutztat.de)
