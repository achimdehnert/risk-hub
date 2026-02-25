# risk-hub 🛡️

Enterprise SaaS Platform für EHS/Risikomanagement (Brandschutz, Explosionsschutz, Arbeitsschutz)

## 🏗️ Architektur

```
┌─────────────────────────────────────────────────────────────────────────┐
│                           risk-hub Monorepo                             │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │                        Django Application                        │   │
│  │                                                                  │   │
│  │  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐           │   │
│  │  │ tenancy  │ │ identity │ │permissions│ │  audit   │  CORE    │   │
│  │  └──────────┘ └──────────┘ └──────────┘ └──────────┘           │   │
│  │                                                                  │   │
│  │  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐           │   │
│  │  │   risk   │ │ actions  │ │documents │ │reporting │  DOMAIN   │   │
│  │  └──────────┘ └──────────┘ └──────────┘ └──────────┘           │   │
│  │                                                                  │   │
│  │  ┌──────────┐ ┌──────────┐                                      │   │
│  │  │  outbox  │ │integrations│                         INFRA     │   │
│  │  └──────────┘ └──────────┘                                      │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                                                                         │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐                  │
│  │   Postgres   │  │    Redis     │  │  MinIO/S3    │                  │
│  │   (Primary)  │  │   (Cache)    │  │   (Docs)     │                  │
│  └──────────────┘  └──────────────┘  └──────────────┘                  │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

## 📁 Projektstruktur

```
risk-hub/
├── src/                          # Django Application
│   ├── config/                   # Django Settings & URLs
│   ├── apps/                     # Django Apps (Bounded Contexts)
│   │   ├── core/                 # Shared utilities
│   │   ├── tenancy/              # Multi-Tenancy
│   │   ├── identity/             # Users, Auth
│   │   ├── permissions/          # RBAC + Scopes
│   │   ├── audit/                # Audit Trail
│   │   ├── outbox/               # Event Outbox
│   │   ├── risk/                 # Gefährdungsbeurteilungen
│   │   ├── actions/              # Maßnahmen
│   │   ├── documents/            # Dokumentenverwaltung
│   │   └── reporting/            # PDF/Excel Exports
│   └── templates/                # Shared Templates
├── tests/                        # Test Suite
├── infra/                        # Infrastructure as Code
│   ├── terraform/                # Hetzner Provisioning
│   ├── ansible/                  # Server Configuration
│   └── docker/                   # Container Configs
├── scripts/                      # Dev & Ops Scripts
├── docs/                         # Documentation
└── docker-compose.yml            # Local Development
```

## 🚀 Quick Start

### Prerequisites

- Docker + Docker Compose
- Python 3.12+
- uv (Python package manager)

### Local Development

```bash
# 1. Repository klonen
git clone https://github.com/bfagent/risk-hub.git
cd risk-hub

# 2. Environment vorbereiten
cp .env.example .env

# 3. Services starten
docker compose up -d

# 4. Migrationen ausführen
docker compose exec app python manage.py migrate

# 5. Demo-Tenant erstellen
docker compose exec app python manage.py seed_demo

# 6. /etc/hosts ergänzen
echo "127.0.0.1 demo.localhost" | sudo tee -a /etc/hosts

# 7. Browser öffnen
open http://demo.localhost:8080/risk/assessments/
```

## 🔑 Architekturprinzipien

1. **DB-getrieben**: Constraints, RLS, Migrationen nach Expand/Contract
2. **Service Layer**: Alle Writes über Services, Audit + Outbox verpflichtend
3. **Multi-Tenancy**: Subdomain-basiert mit optionalem RLS
4. **Modular Monolith**: Klare Bounded Contexts, später auskoppelbar

## 📖 Dokumentation

- [Architekturkonzept](docs/architecture/ARCHITECTURE.md)
- [RBAC/Permissions](docs/architecture/PERMISSIONS.md)
- [API Reference](docs/api/README.md)
- [Deployment Guide](docs/deployment/README.md)

## 🔧 Entwicklung

```bash
# Tests ausführen
make test

# Linting
make lint

# Type Checking
make typecheck

# Alle Checks
make ci
```

## 📜 Lizenz

Proprietary - BFAgent GmbH
