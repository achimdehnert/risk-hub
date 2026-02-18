# Risk-Hub (Schutztat) — Project Rules

## Project Overview

Risk-Hub (Schutztat) is a multi-tenant Django SaaS platform for occupational
safety, hazardous substance management, explosion protection, and risk
assessment. Deployed on Hetzner Cloud via Docker Compose.

## Tech Stack

- **Backend**: Django 5.x, Gunicorn, Celery + Redis
- **Frontend**: Tailwind CSS (CDN), HTMX 1.9, Lucide Icons
- **Database**: PostgreSQL 16 (row-level tenant isolation via `tenant_id`)
- **API**: Django Ninja (NOT DRF) at `/api/v1/`
- **Infrastructure**: Docker Compose, Nginx reverse proxy, Hetzner VM
- **Registry**: ghcr.io/achimdehnert/risk-hub/risk-hub-web

## Multi-Tenancy (CRITICAL)

- Every model with user data MUST have `tenant_id = UUIDField(db_index=True)`
- `Organization.id` != `Organization.tenant_id` — ALWAYS use `org.tenant_id`
- Middleware sets `request.tenant_id` from subdomain resolution
- All queries MUST filter by `tenant_id`

## Django Apps (src/)

- `config/` — Settings, root URLs
- `common/` — Shared middleware, tenant utilities
- `tenancy/` — Organization, User models
- `substances/` — Hazardous substance management, SDS, GHS
- `risk/` — Risk assessments, hazard analysis
- `explosionsschutz/` — ATEX explosion protection
- `documents/` — Document management
- `approvals/` — Approval workflows
- `notifications/` — Notification system
- `permissions/` — Authorization layer
- `audit/` — Audit trail

## Code Style

- Python: PEP 8, type hints, double quotes, Google docstrings
- Line length: 100 chars max
- Imports: sorted with isort
- Linting: ruff

## Testing

- Framework: pytest
- Run: `cd src && pytest`
