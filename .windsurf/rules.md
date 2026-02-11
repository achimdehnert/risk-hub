# Risk-Hub Project Rules

## Project Overview
Risk-Hub (Schutztat) is a multi-tenant Django SaaS platform for occupational
safety, hazardous substance management, explosion protection, and risk
assessment. Deployed on Hetzner Cloud via Docker Compose.

## Tech Stack
- **Backend**: Django 5.x, Gunicorn, Celery + Redis
- **Frontend**: Tailwind CSS (CDN), HTMX 1.9, Lucide Icons
- **Database**: PostgreSQL 16 (row-level tenant isolation via `tenant_id`)
- **Infrastructure**: Docker Compose, Nginx reverse proxy, Hetzner VM
- **Registry**: ghcr.io/achimdehnert/risk-hub/risk-hub-web

## Architecture Rules

### Multi-Tenancy
- Every model with user data MUST have a `tenant_id = UUIDField(db_index=True)`
- CRITICAL: `Organization.id` != `Organization.tenant_id` — always use
  `org.tenant_id` for data isolation, never `org.id`
- Middleware sets `request.tenant_id` from subdomain resolution
- All queries MUST filter by `tenant_id`

### Django Apps (src/)
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

### Template Rules
- ALL templates MUST extend `base.html` (Tailwind + nav + Lucide)
- Never use standalone HTML with inline `<style>` tags
- Use Tailwind utility classes, not custom CSS
- Status badges: rounded-full with color coding (gray=draft,
  yellow=review, green=approved, red=critical)
- Orange is the brand accent color (bg-orange-500/600)

### Service Layer Pattern
```
views.py → services.py → models.py
```
- Views handle HTTP, call services
- Services contain business logic, use Pydantic commands
- Models are data + simple properties only

### URL Conventions
- HTML views: `/module/` (namespace: `module`)
- API endpoints: `/api/module/` (namespace: `module-api`)

## Deployment

### Server
- Host: `88.198.191.108`
- Project path: `/opt/risk-hub`
- Compose file: `docker-compose.prod.yml`
- Env file: `.env.prod`
- Container names: `risk_hub_web`, `risk_hub_worker`, `risk_hub_db`,
  `risk_hub_redis`

### Deploy Workflow
1. `git push origin main`
2. `docker build -f docker/app/Dockerfile -t ghcr.io/achimdehnert/risk-hub/risk-hub-web:latest .`
3. `docker push ghcr.io/achimdehnert/risk-hub/risk-hub-web:latest`
4. SSH: `docker compose -f docker-compose.prod.yml pull risk-hub-web`
5. SSH: `docker compose -f docker-compose.prod.yml up -d --force-recreate risk-hub-web risk-hub-worker`

### Environment Variables
- `DATABASE_URL` — Full postgres connection string in `.env.prod`
- Do NOT use `${VAR}` interpolation in `docker-compose.prod.yml` environment
  section — rely solely on `env_file: .env.prod`

## Code Style
- Python: PEP 8, type hints, double quotes, Google docstrings
- Line length: 100 chars max
- Imports: sorted with isort
- Linting: ruff
- Templates: 4-space indent, Tailwind classes

## Testing
- Framework: pytest
- Run: `cd src && pytest`
- Management commands tested via Docker exec on server
- Substance import: `python manage.py load_ghs_data && python manage.py import_substances --tenant demo`
