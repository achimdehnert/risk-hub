# risk-hub — Deployment Guide

> **Stand:** April 2026 | **ADR-120 konform**

## Übersicht

| Parameter | Wert |
|-----------|------|
| **Production** | https://schutztat.de |
| **Demo** | https://demo.schutztat.de |
| **Server** | 88.198.191.108 (Hetzner Cloud) |
| **Image** | `ghcr.io/achimdehnert/risk-hub/risk-hub-web` |
| **Health** | https://schutztat.de/healthz/ |
| **Compose Path** | `/opt/risk-hub/docker-compose.prod.yml` |
| **Config SSOT** | `.ship.conf` im Repo-Root |

---

## Deployment ausführen

### Pfad 1: CI/CD (Standard)

Push auf `main` triggert `.github/workflows/deploy.yml`:

```
Push → GitHub Actions → Build Image → Push to GHCR → SSH Deploy → Health Check
```

### Pfad 2: Manuell (ship.sh)

```bash
# Thin wrapper → platform/scripts/ship.sh
bash scripts/ship.sh
```

Beide Pfade lesen `.ship.conf` als Single Source of Truth:

```bash
# .ship.conf
APP_NAME="risk-hub"
IMAGE="ghcr.io/achimdehnert/risk-hub/risk-hub-web"
DOCKERFILE="docker/app/Dockerfile"
WEB_SERVICE="risk-hub-web"
SERVER="root@88.198.191.108"
COMPOSE_PATH="/opt/risk-hub"
COMPOSE_FILE="docker-compose.prod.yml"
HEALTH_URL="https://schutztat.de/healthz/"
MIGRATE_CMD="python manage.py migrate --no-input"
```

---

## Docker Services (Production)

| Service | Container | Port | Beschreibung |
|---------|-----------|------|-------------|
| Web | risk-hub-web | 8090→8000 | Gunicorn + Django |
| Worker | risk-hub-worker | — | Celery Worker |
| Database | risk-hub-db | 5432 | PostgreSQL 16 |
| Redis | risk-hub-redis | 6379 | Queue + Cache |

**Kein MinIO in Production** — nur für lokale Entwicklung.

---

## Server-Setup (einmalig)

```bash
# Auf dem Server
ssh root@88.198.191.108

mkdir -p /opt/risk-hub
cd /opt/risk-hub

# .env.prod erstellen
cat > .env.prod << 'EOF'
DJANGO_SETTINGS_MODULE=config.settings
SECRET_KEY=<generated>
DATABASE_URL=postgres://risk_hub:***@risk-hub-db:5432/risk_hub
REDIS_URL=redis://risk-hub-redis:6379/0
ALLOWED_HOSTS=schutztat.de,demo.schutztat.de
EOF

# docker-compose.prod.yml kopieren (von Repo)
scp docker-compose.prod.yml root@88.198.191.108:/opt/risk-hub/
```

---

## Migrationen

Migrationen werden automatisch beim Deploy ausgeführt:

```bash
# Server-seitig (deploy.sh)
docker compose -f docker-compose.prod.yml exec risk-hub-web \
  python manage.py migrate --no-input
```

Manuell:

```bash
ssh root@88.198.191.108
cd /opt/risk-hub
docker compose -f docker-compose.prod.yml exec risk-hub-web \
  python manage.py migrate --no-input
```

---

## Health Checks

```bash
# Liveness (immer 200 wenn Prozess läuft)
curl https://schutztat.de/livez/

# Readiness (200 wenn DB + Services erreichbar)
curl https://schutztat.de/healthz/

# API Docs
curl https://schutztat.de/api/v1/docs
```

---

## Backup & Restore

### Automatisches Backup

Tägliches Backup via Cron auf dem Server:

```bash
# Backup erstellen
docker compose -f docker-compose.prod.yml exec risk-hub-db \
  pg_dump -U risk_hub risk_hub | gzip > /opt/backups/risk-hub/$(date +%Y%m%d).sql.gz
```

### Restore

```bash
# Container stoppen
docker compose -f docker-compose.prod.yml stop risk-hub-web risk-hub-worker

# Restore
gunzip -c /opt/backups/risk-hub/20260418.sql.gz | \
  docker compose -f docker-compose.prod.yml exec -T risk-hub-db \
  psql -U risk_hub risk_hub

# Container starten
docker compose -f docker-compose.prod.yml up -d risk-hub-web risk-hub-worker
```

---

## SSL / DNS

- **DNS:** Cloudflare (CNAME → Cloudflare Tunnel)
- **SSL:** Cloudflare Full (Strict) — kein Certbot nötig
- **Domain:** `schutztat.de` + `demo.schutztat.de` (Wildcard)

---

## Rollback

```bash
# Auf dem Server: vorheriges Image-Tag setzen
cd /opt/risk-hub
# In docker-compose.prod.yml das IMAGE_TAG ändern
docker compose -f docker-compose.prod.yml pull risk-hub-web
docker compose -f docker-compose.prod.yml up -d risk-hub-web

# Health prüfen
curl -s https://schutztat.de/healthz/
```

---

## Logs

```bash
# Web Logs
ssh root@88.198.191.108 "docker logs --tail 100 -f risk-hub-web"

# Worker Logs
ssh root@88.198.191.108 "docker logs --tail 100 -f risk-hub-worker"

# DB Logs
ssh root@88.198.191.108 "docker logs --tail 50 risk-hub-db"
```

Via MCP:

```
docker_manage(action="container_logs", container_id="risk-hub-web", lines=100)
```

---

## Troubleshooting

| Problem | Diagnose | Lösung |
|---------|---------|--------|
| 502 Bad Gateway | `docker logs risk-hub-web` | Container restart: `docker restart risk-hub-web` |
| DB Connection Error | `docker logs risk-hub-db` | DB Container prüfen, Connection-Limits |
| Migration fehlgeschlagen | `docker exec risk-hub-web python manage.py showmigrations` | Fake/Merge migration |
| Health Check fails | `curl -v https://schutztat.de/healthz/` | Nginx-Config, DNS, Container-Status |
| Module 403 | ModuleSubscription prüfen | `ModuleSubscription.objects.filter(tenant=...)` |
| Tenant nicht gefunden | Subdomain-Auflösung | Organization.slug == Subdomain prüfen |

---

## Monitoring

Health-Dashboard via MCP:

```
system_manage(action="health_dashboard")
```

Einzelcheck:

```
system_manage(action="health_check", app_name="risk-hub")
```
