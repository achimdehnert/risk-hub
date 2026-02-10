# Risk-Hub (Schutztat) — Deployment Reference

> Auto-generated from [ADR-021](https://github.com/achimdehnert/platform/blob/main/docs/adr/ADR-021-unified-deployment-pattern.md)

## Quick Reference

| Parameter | Value |
| --- | --- |
| **Server** | `88.198.191.108` |
| **Server path** | `/opt/risk-hub` |
| **Domain** | `demo.schutztat.de` |
| **GHCR image** | `ghcr.io/achimdehnert/risk-hub/risk-hub-web:latest` |
| **Compose file** | `docker-compose.prod.yml` |
| **Env file** | `.env.prod` |
| **Host port** | `127.0.0.1:8090` → Gunicorn `:8000` |
| **Container (web)** | `risk_hub_web` |
| **Container (worker)** | `risk_hub_worker` |
| **Container (db)** | `risk_hub_db` |
| **Container (redis)** | `risk_hub_redis` |
| **Database** | Own stack (postgres:16-alpine) |
| **Network** | `risk_hub_network` (isolated) |
| **Health endpoint** | `/healthz/` (TODO: implement) |

## Services

| Compose service | Image | Purpose |
| --- | --- | --- |
| `risk-hub-web` | `ghcr.io/.../risk-hub-web:latest` | Gunicorn (Django) |
| `risk-hub-worker` | same image | Celery worker |
| `risk-hub-db` | `postgres:16-alpine` | PostgreSQL |
| `risk-hub-redis` | `redis:7-alpine` | Broker + Cache |

## CI/CD

Uses platform reusable workflows (`.github/workflows/docker-build.yml`):

```
push to main → CI (lint+test) → Build Docker → Deploy to Hetzner
```

## Deploy Commands

### Via CI (automatic)

Push to `main` triggers full pipeline.

### Manual deploy

```bash
# 1. Build + Push
docker build -f docker/app/Dockerfile -t ghcr.io/achimdehnert/risk-hub/risk-hub-web:latest .
docker push ghcr.io/achimdehnert/risk-hub/risk-hub-web:latest

# 2. Deploy on server
ssh root@88.198.191.108 '
  cd /opt/risk-hub &&
  docker compose -f docker-compose.prod.yml pull risk-hub-web &&
  docker compose -f docker-compose.prod.yml up -d --force-recreate risk-hub-web risk-hub-worker &&
  sleep 5 &&
  curl -sf http://127.0.0.1:8090/healthz/ &&
  docker logs risk_hub_web --tail 10
'
```

### Operations

```bash
# Logs
ssh root@88.198.191.108 'docker logs risk_hub_web --tail 50'
ssh root@88.198.191.108 'docker logs risk_hub_worker --tail 50'

# Migrations
ssh root@88.198.191.108 'docker exec risk_hub_web python manage.py migrate'

# Shell
ssh root@88.198.191.108 'docker exec -it risk_hub_web python manage.py shell'

# Restart
ssh root@88.198.191.108 'cd /opt/risk-hub && docker compose -f docker-compose.prod.yml restart risk-hub-web risk-hub-worker'

# DB Backup
ssh root@88.198.191.108 'docker exec risk_hub_db pg_dump -U risk_hub risk_hub | gzip > /opt/risk-hub/backups/$(date +%Y%m%d).sql.gz'
```

## Hardening TODO

- [ ] Add `logging` (json-file with rotation) to all services
- [ ] Add `deploy.resources.limits.memory` to all services
- [ ] Implement `/livez/` + `/healthz/` endpoints using `platform/deployment/templates/django/healthz.py`
- [ ] Bind port to `127.0.0.1:8090:8000` (currently correct)
