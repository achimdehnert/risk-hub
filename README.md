# Schutztat (risk-hub) — Enterprise SaaS for Safety Management

> **Version:** 0.1.0 | **Production:** https://schutztat.de | **Demo:** https://demo.schutztat.de
> **Stand:** April 2026

Multi-Tenant SaaS platform for occupational safety, explosion protection, hazardous substances, fire safety, data privacy, and compliance management.

## Module

| Modul | URL-Prefix | Beschreibung |
|-------|-----------|--------------|
| **Explosionsschutz** | `/ex/` | ATEX-Zonen, Konzepte, Betriebsmittel, Zündquellenanalyse |
| **Gefahrstoffe** | `/substances/` | Stoffdatenbank, SDS-Management, CAS-Nummern |
| **SDS-Bibliothek** | `/sds/` | Globale Sicherheitsdatenblätter, periodische Reviews |
| **Kataster** | `/kataster/` | Gefahrstoffkataster mit Produkten, Verwendungen, Import |
| **Risikobewertung** | `/risk/` | Gefährdungsbeurteilungen, Bewertungsmatrix |
| **GBU** | `/gbu/` | Gefährdungsbeurteilungen (erweitertes Modul) |
| **Brandschutz** | `/brandschutz/` | Brandschutzkonzepte, Fluchtpläne |
| **Datenschutz (DSB)** | `/dsb/` | Verarbeitungsverzeichnis, TOMs, DSFA |
| **Dokumente** | `/documents/` | Versioniertes Dokumentenmanagement |
| **Projekte** | `/projects/` | Projektbasierte Workflows |
| **Training** | `/training/` | Unterweisungen, Themen, Teilnahme-Tracking |
| **Audit** | `/audit/` | Vollständiger Audit-Trail aller Änderungen |
| **Dashboard** | `/dashboard/` | Compliance-Übersicht, Statistiken |
| **Benachrichtigungen** | `/notifications/` | Systemweite Alerts und Hinweise |

## Tech Stack

| Komponente | Technologie |
|-----------|------------|
| **Backend** | Django 5.1, Gunicorn |
| **Frontend** | HTMX 1.9 (raw headers, kein `django-htmx`), Bootstrap 5 |
| **API** | Django Ninja (`/api/v1/`) |
| **Database** | PostgreSQL 16 |
| **Queue** | Celery + Redis 7 |
| **LLM** | `iil-aifw` (`aifw.service.sync_completion`) |
| **Multi-Tenancy** | Subdomain-basiert, `ModuleAccessMiddleware` |
| **Auth** | Django built-in + OIDC (mozilla-django-oidc) |
| **Infrastructure** | Docker, Hetzner Cloud, Cloudflare |

## Quick Start (lokal)

```bash
git clone https://github.com/achimdehnert/risk-hub.git
cd risk-hub
cp .env.example .env

docker compose up --build -d
docker compose exec risk-hub-web python manage.py migrate --no-input
docker compose exec risk-hub-web python manage.py seed_demo
docker compose exec -it risk-hub-web python manage.py createsuperuser
```

Zugriff:
- **App:** http://localhost:8090/dashboard/
- **Admin:** http://localhost:8090/admin/
- **API Docs:** http://localhost:8090/api/v1/docs
- **Login:** `/accounts/login/`

## Docker Services (Production)

| Service | Container | Port |
|---------|-----------|------|
| Web (Gunicorn) | `risk-hub-web` | 8090 (→ 8000 intern) |
| Worker (Celery) | `risk-hub-worker` | — |
| Database | `risk-hub-db` | 5432 |
| Redis | `risk-hub-redis` | 6379 |
| MinIO (dev only) | `risk-hub-minio` | 9000/9001 |

## Deployment

```bash
# Via ship.sh (thin wrapper → platform/scripts/ship.sh)
bash scripts/ship.sh

# Config: .ship.conf (SSOT, ADR-120)
# Health: https://schutztat.de/healthz/
# Image: ghcr.io/achimdehnert/risk-hub/risk-hub-web
```

Detailliert: [docs/deployment/DEPLOYMENT.md](docs/deployment/DEPLOYMENT.md)

## Architektur

```
risk-hub/
├── src/
│   ├── config/            # Settings, URLs, API, Celery, WSGI
│   ├── common/            # Middleware, Context Processors, S3, Progress
│   ├── core/              # Health Checks (/livez/, /healthz/)
│   ├── tenancy/           # Organization, Site, Tenant-Middleware
│   ├── identity/          # Custom User Model
│   ├── permissions/       # RBAC: Role, Scope, Assignment, ModuleAccess
│   ├── audit/             # AuditEvent, Compliance-Log
│   ├── outbox/            # Event Outbox (Celery)
│   ├── explosionsschutz/  # ATEX-Zonen, Konzepte, Betriebsmittel
│   ├── substances/        # Gefahrstoffe, SDS-Upload
│   ├── global_sds/        # Globale SDS-Bibliothek
│   ├── risk/              # Gefährdungsbeurteilung
│   ├── riskfw/            # Risk-Framework Models + Services
│   ├── gbu/               # GBU-Erweiterung
│   ├── exschutzdokument/  # Explosionsschutzdokument
│   ├── dsb/               # Datenschutzbeauftragter
│   ├── brandschutz/       # Brandschutz
│   ├── documents/         # Dokumente, Versionen, S3
│   ├── actions/           # Maßnahmen, Tasks
│   ├── projects/          # Projektbasierte Workflows
│   ├── training/          # Unterweisungen
│   ├── reporting/         # Export Jobs (PDF/Excel)
│   ├── notifications/     # Benachrichtigungen
│   ├── dashboard/         # Compliance-Dashboard
│   ├── approvals/         # Freigabe-Workflows
│   ├── ai_analysis/       # KI-gestützte Analyse (aifw)
│   ├── tests/             # Test Suite (188 files)
│   └── templates/         # Shared Templates (project root)
├── docker/app/Dockerfile
├── docker-compose.prod.yml
├── .ship.conf             # Deployment SSOT (ADR-120)
├── reflex.yaml            # REFLEX Test-Config (ADR-162)
└── docs/
    ├── AGENT_HANDOVER.md
    ├── architecture/
    ├── deployment/
    ├── use-cases/         # UC-001 bis UC-010
    └── adr/               # ADR-001 bis ADR-042
```

Detailliert: [docs/architecture/ARCHITECTURE.md](docs/architecture/ARCHITECTURE.md)

## Access Control

```
Request → SubdomainTenantMiddleware
        → AuthenticationMiddleware
        → ModuleAccessMiddleware (MODULE_URL_MAP)
        → View (@login_required / @require_module)
```

| URL-Prefix | Modul | Guard |
|------------|-------|-------|
| `/ex/`, `/substances/` | `ex` | ModuleAccess + LoginRequired |
| `/risk/` | `risk` | ModuleAccess + LoginRequired |
| `/gbu/` | `gbu` | ModuleAccess + LoginRequired |
| `/dsb/` | `dsb` | ModuleAccess + LoginRequired |
| `/dashboard/`, `/kataster/`, `/sds/` | — | LoginRequired (kein Modul-Guard) |
| `/livez/`, `/healthz/`, `/api/v1/docs` | — | Public |

Rollen-Hierarchie: `viewer < member < manager < admin`

## iil-Packages

```python
from aifw.service import sync_completion     # LLM-Calls
from platform_context import get_context     # Request-Middleware
from django_tenancy import TenantMixin       # Multi-Tenancy
from django_module_shop import ...           # Modul-Shop/Billing
```

## Dokumentation

| Dokument | Inhalt |
|----------|--------|
| [README.md](README.md) | Übersicht (diese Datei) |
| [AGENT_HANDOVER.md](docs/AGENT_HANDOVER.md) | Agent-Kontext für AI-Sessions |
| [ARCHITECTURE.md](docs/architecture/ARCHITECTURE.md) | Technische Architektur |
| [DEPLOYMENT.md](docs/deployment/DEPLOYMENT.md) | Deployment-Guide |
| [USER_GUIDE.md](docs/USER_GUIDE.md) | Benutzerhandbuch |
| [reflex.yaml](reflex.yaml) | REFLEX Test-Konfiguration |
| [docs/use-cases/](docs/use-cases/) | Use Cases UC-001 bis UC-010 |
| [docs/adr/](docs/adr/) | Architecture Decision Records |

## License

Proprietary - All rights reserved
