# Risk-Hub — Tech Stack

## Backend

- **Python**: 3.11+
- **Django**: 5.x (with custom multi-tenant middleware)
- **Gunicorn**: WSGI server (2 workers)
- **Celery**: Async task queue (worker + beat)
- **Redis**: Cache + Celery broker

## Frontend

- **Tailwind CSS**: via CDN (`cdn.tailwindcss.com`)
- **HTMX**: 1.9.10 (dynamic content loading)
- **Lucide Icons**: SVG icon library
- **No build step** — all CDN-based

## Database

- **PostgreSQL 16**: Primary database
- **Row-level tenant isolation**: `tenant_id` UUID on every model
- **UUID primary keys**: For all core models

## Infrastructure

- **Hetzner Cloud VM**: `88.198.191.108`
- **Docker Compose**: Production orchestration
- **Nginx**: Reverse proxy + TLS termination
- **GHCR**: Container image registry

## Key Python Packages

- `django` — Web framework
- `psycopg[binary]` — PostgreSQL adapter
- `gunicorn` — WSGI server
- `celery` — Task queue
- `redis` — Cache/broker client
- `pdfplumber` — SDS PDF parsing
- `PyPDF2` — PDF text extraction

## Container Architecture

```text
risk_hub_web      (8090) — Django + Gunicorn
risk_hub_worker   — Celery worker
risk_hub_db       (5432) — PostgreSQL 16
risk_hub_redis    (6379) — Redis 7
```

## Network

- Nginx on host forwards `*.schutztat.de` → `127.0.0.1:8090`
- Docker internal network for container-to-container communication
- SSL via Let's Encrypt (certbot)
