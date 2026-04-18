# risk-hub — Technische Architektur

> **Stand:** April 2026 | **Domain:** schutztat.de | **Port:** 8090

## Repository-Struktur

```
risk-hub/
├── src/                              # Django Application (PYTHONPATH root)
│   ├── manage.py
│   ├── config/                       # Django Configuration
│   │   ├── settings.py               # Single-file + overlays (dev/prod/test)
│   │   ├── urls.py                   # URL Routing (all modules)
│   │   ├── api.py                    # Django Ninja API (/api/v1/)
│   │   ├── celery.py                 # Celery Configuration
│   │   └── wsgi.py                   # WSGI Entry Point
│   │
│   ├── common/                       # Shared Utilities
│   │   ├── middleware.py             # Tenant Resolution, Module Access
│   │   ├── context_processors.py    # Template Context
│   │   ├── progress/                # Progress Rail (ADR-017)
│   │   └── s3.py                    # S3 Client Helper
│   │
│   ├── core/                         # Health Checks
│   │   └── healthz.py               # /livez/, /healthz/, /readyz/
│   │
│   ├── tenancy/                      # Multi-Tenancy
│   │   ├── models.py                # Organization, Site, OrgMembership
│   │   ├── middleware.py            # SubdomainTenantMiddleware
│   │   └── management/commands/     # seed_demo, etc.
│   │
│   ├── identity/                     # User Management
│   │   └── models.py                # Custom User (AUTH_USER_MODEL)
│   │
│   ├── permissions/                  # RBAC + Module Access
│   │   ├── models.py                # Role, Permission, Scope, ModuleSubscription
│   │   ├── services.py              # authorize(), has_permission()
│   │   ├── middleware.py            # ModuleAccessMiddleware
│   │   └── decorators.py           # @require_module()
│   │
│   ├── audit/                        # Audit Trail
│   ├── outbox/                       # Event Outbox (Celery)
│   ├── notifications/                # System Notifications
│   ├── dashboard/                    # Compliance Dashboard
│   ├── approvals/                    # Approval Workflows
│   │
│   ├── explosionsschutz/             # ATEX Zones, Concepts, Equipment
│   │   ├── models.py                # Area, Concept, Zone, Equipment
│   │   ├── html_urls.py             # /ex/ Frontend Routes
│   │   ├── urls.py                  # /api/ex/ API Routes
│   │   └── views/                   # HTMX views
│   │
│   ├── substances/                   # Hazardous Substances
│   │   ├── models.py                # Substance, SDS
│   │   ├── html_urls.py             # /substances/ Frontend
│   │   └── urls.py                  # /api/substances/ API
│   │
│   ├── global_sds/                   # Global SDS Library (/sds/)
│   ├── risk/                         # Risk Assessment (/risk/)
│   ├── gbu/                          # Extended GBU (/gbu/)
│   ├── dsb/                          # Data Privacy Officer (/dsb/)
│   ├── brandschutz/                  # Fire Safety (/brandschutz/)
│   ├── documents/                    # Document Management (/documents/)
│   ├── actions/                      # Action Items (/actions/)
│   ├── projects/                     # Project Workflows (/projects/)
│   ├── training/                     # Training Management (/training/)
│   ├── reporting/                    # Export Jobs (PDF/Excel)
│   ├── ai_analysis/                  # LLM Analysis (aifw)
│   ├── media/                        # Media handling
│   ├── riskfw/                       # Risk framework utils
│   │
│   └── templates/                    # Shared Templates (project root)
│       ├── base.html
│       ├── dashboard/
│       ├── explosionsschutz/
│       ├── substances/
│       └── ...
│
├── docker/app/Dockerfile             # Multi-stage build
├── docker-compose.yml                # Local development
├── docker-compose.prod.yml           # Production
├── .ship.conf                        # Deployment SSOT (ADR-120)
├── reflex.yaml                       # REFLEX Test-Config (ADR-162)
├── requirements.txt                  # Python dependencies
│
├── scripts/
│   └── ship.sh                       # Thin wrapper → platform/scripts/ship.sh
│
├── reflex-audit/                     # REFLEX Audit Reports
│   ├── REFLEX-AUDIT-FULL-APP.md
│   ├── REFLEX-AUDIT-RECHTE-ROLLEN.md
│   └── REFLEX-AUDIT-EXPLOSIONSSCHUTZ.md
│
└── docs/
    ├── AGENT_HANDOVER.md             # AI Agent Context
    ├── architecture/ARCHITECTURE.md  # This file
    ├── deployment/DEPLOYMENT.md      # Deployment Guide
    ├── USER_GUIDE.md                 # User Manual
    ├── use-cases/UC-*.md             # Use Cases
    └── adr/ADR-*.md                  # Architecture Decision Records
```

**Wichtig:** Apps liegen direkt in `src/` (kein `apps.` Prefix). `src/` ist im `PYTHONPATH`.

---

## Architektur-Schichten

```
┌─────────────────────────────────────────────────────────────────┐
│                         PLATFORM LAYER                           │
│  tenancy  identity  permissions  audit  outbox  notifications    │
│  common   core      dashboard   approvals                        │
├─────────────────────────────────────────────────────────────────┤
│                         DOMAIN LAYER                             │
│  explosionsschutz  substances  global_sds  risk  gbu  dsb       │
│  brandschutz  documents  actions  projects  training  reporting  │
│  ai_analysis  riskfw  media                                      │
├─────────────────────────────────────────────────────────────────┤
│                         iil-PACKAGES                             │
│  aifw  platform_context  django_tenancy  django_module_shop      │
│  doc_templates  iil_learnfw                                      │
├─────────────────────────────────────────────────────────────────┤
│                         INFRASTRUCTURE                           │
│  Django 5.1  PostgreSQL 16  Redis 7  Celery  Gunicorn  Nginx    │
│  Docker  Hetzner Cloud  Cloudflare                               │
└─────────────────────────────────────────────────────────────────┘
```

---

## Datenfluss

```
Browser (HTMX) ──▶ Cloudflare ──▶ Nginx ──▶ Gunicorn (Django)
                                                   │
          ┌────────────────────────────────────────┤
          ▼                                        ▼
    PostgreSQL 16                           Celery Worker
    (risk_hub DB)                                  │
                                     ┌─────────────┼──────────┐
                                     ▼             ▼          ▼
                                   Redis      MinIO/S3     Email
                                  (Queue)     (Docs)       (SMTP)
```

---

## Multi-Tenancy

```
Request: https://demo.schutztat.de/ex/areas/
         ▼
SubdomainTenantMiddleware:
  1. Extract subdomain "demo" from Host header
  2. Lookup Organization by slug="demo"
  3. Set request.tenant = Organization
  4. Set request.org = Organization
         ▼
ModuleAccessMiddleware:
  1. Match URL /ex/ → module_code="ex"
  2. Check ModuleSubscription(tenant, "ex") → active?
  3. Check ModuleMembership(user, "ex") → role >= viewer?
  4. If no: return 403
         ▼
View: All queries MUST filter by tenant_id
```

**Kritisch:** `Organization.id != Organization.tenant_id`. Immer `tenant_id` für Queries verwenden.

---

## Access Control Architecture

```
ModuleAccessMiddleware (MODULE_URL_MAP)
  │
  ├── /ex/, /api/ex/, /substances/, /api/substances/ → module "ex"
  ├── /risk/ → module "risk"
  ├── /gbu/, /api/gbu/ → module "gbu"
  └── /dsb/ → module "dsb"

Unguarded (nur @login_required):
  /dashboard/, /sds/, /kataster/, /documents/, /brandschutz/,
  /projects/, /notifications/, /audit/, /training/

Public:
  /livez/, /healthz/, /readyz/, /api/v1/docs, /accounts/login/
```

Role hierarchy: `viewer < member < manager < admin`
Org membership: `owner > admin > member > viewer > external`

---

## HTMX-Konvention

- HTMX 1.9 via CDN (kein `django-htmx` Package)
- Detection: `request.headers.get('HX-Request') == 'true'`
- **Verboten:** `request.htmx`, `hx-boost`
- **Pflicht auf Forms:** `hx-indicator`, `hx-disabled-elt`

---

## API (Django Ninja)

- Base: `/api/v1/`
- Auth: Bearer Token via `ApiKeyAuth`
- Docs: `/api/v1/docs` (OpenAPI, public)
- Module-spezifische APIs: `/api/ex/`, `/api/substances/`, `/api/gbu/`

---

## Docker Services (Production)

| Service | Container | Image | Port |
|---------|-----------|-------|------|
| Web | risk-hub-web | `ghcr.io/achimdehnert/risk-hub/risk-hub-web` | 8000→8090 |
| Worker | risk-hub-worker | same image | — |
| DB | risk-hub-db | postgres:16 | 5432 |
| Redis | risk-hub-redis | redis:7 | 6379 |

---

## Key Design Decisions

| Aspekt | Entscheidung | ADR |
|--------|-------------|-----|
| **Framework** | Django 5.1 + HTMX 1.9 | — |
| **Multi-Tenancy** | Subdomain + ModuleAccess | ADR-003 |
| **HTMX Detection** | Raw headers (kein django-htmx) | — |
| **Settings** | Single-file with overlays | — |
| **Apps Layout** | `src/` (kein `apps.` Prefix) | — |
| **API** | Django Ninja (nicht DRF) | ADR-004 |
| **PKs** | BigAutoField (nicht UUIDs) | ADR-022 |
| **Health Endpoint** | `/healthz/` (ADR-022) | ADR-022 |
| **LLM Integration** | `iil-aifw` (nie direkt litellm/openai) | — |
| **Background Jobs** | Celery + Redis | ADR-005 |
| **Documents** | S3-kompatibel (MinIO dev) | — |
| **Deployment** | `.ship.conf` SSOT + CI/CD | ADR-120 |
| **Hosting** | Hetzner Cloud, Cloudflare DNS | — |
