# Risk-Hub - Enterprise SaaS Risikomanagement

Plattform für Risikomanagement: Brandschutz, Explosionsschutz, Arbeitssicherheit, Audits, Maßnahmen, Dokumente.

## Features

- **Multi-Tenancy**: Subdomain-basierte Mandantentrennung mit Postgres RLS
- **RBAC**: Hierarchisches Berechtigungssystem (Tenant/Site/Asset)
- **Gefährdungsbeurteilung**: Risikobewertung mit KI-Unterstützung
- **Dokumentenmanagement**: S3-kompatibles Storage mit Versionierung
- **Audit Trail**: Vollständige Nachverfolgbarkeit aller Änderungen
- **Export/Reporting**: PDF/Excel Exports als auditierbare Artefakte

## Tech Stack

- **Backend**: Django 5 + HTMX
- **Database**: PostgreSQL 16 mit RLS
- **Storage**: S3-kompatibel (MinIO/Hetzner Object Storage)
- **LLM**: bfagent-llm (Prompt Framework)
- **Infrastructure**: Docker, Hetzner Cloud

## Quick Start

```bash
# Repository klonen
git clone https://github.com/achimdehnert/risk-hub.git
cd risk-hub

# Environment einrichten
cp .env.example .env

# Container starten
docker compose up --build -d

# Migrationen ausführen
docker compose exec app python manage.py migrate

# Demo-Daten laden
docker compose exec app python manage.py seed_demo

# Superuser erstellen
docker compose exec app python manage.py createsuperuser
```

Dann `/etc/hosts` ergänzen:
```
127.0.0.1 demo.localhost
```

Öffnen:
- App: http://demo.localhost:8080/risk/assessments/
- Admin: http://localhost:8080/admin/
- MinIO Console: http://localhost:9001 (minio/minio123)

## RLS aktivieren (Prod/Staging)

```bash
docker compose exec db psql -U app -d app -f /app/scripts/enable_rls.sql
```

## Architektur

```
risk-hub/
├── src/
│   ├── config/           # Django Settings & URLs
│   ├── common/           # Shared: Middleware, Context, S3
│   ├── tenancy/          # Mandanten, Organisationen, Sites
│   ├── identity/         # User, Auth
│   ├── permissions/      # RBAC, Scopes, Assignments
│   ├── risk/             # Gefährdungsbeurteilung
│   ├── actions/          # Maßnahmen, Tasks
│   ├── documents/        # Dokumente, Versionierung
│   ├── reporting/        # Export Jobs, Retention
│   ├── audit/            # Audit Events
│   └── outbox/           # Event Outbox
├── docker/
├── scripts/
└── docker-compose.yml
```

## Shared Packages

Risk-Hub nutzt die gemeinsamen Packages aus dem Platform-Repo:

```python
# bfagent-core: Tenancy, Audit, Outbox
from bfagent_core import emit_audit_event, get_context

# bfagent-llm: LLM Integration
from bfagent_llm import PromptFramework
```

## License

Proprietary - All rights reserved
