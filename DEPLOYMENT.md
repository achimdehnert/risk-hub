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
| **Health endpoint** | `/livez/` |

## Services

| Compose service | Image | Purpose |
| --- | --- | --- |
| `risk-hub-web` | `ghcr.io/.../risk-hub-web:latest` | Gunicorn (Django) |
| `risk-hub-worker` | same image | Celery worker |
| `risk-hub-db` | `postgres:16-alpine` | PostgreSQL |
| `risk-hub-redis` | `redis:7-alpine` | Broker + Cache |

## CI/CD

Self-contained inline pipeline (`.github/workflows/docker-build.yml`).
No dependency on private `platform` reusable workflows.

```text
push to main → Build Docker image → Push to GHCR → Deploy via SSH → Verify health
```

### Pipeline Steps (Deploy Job)

1. Pull new image on server
2. Recreate containers (`risk-hub-web`, `risk-hub-worker`)
3. Run migrations (`manage.py migrate`)
4. Seed TOM categories (`manage.py seed_tom_categories`)
5. Health check (internal `127.0.0.1:8000/livez/`)
6. External health check (`https://demo.schutztat.de/livez/`)

### Required GitHub Secrets

| Secret | Description |
| --- | --- |
| `DEPLOY_HOST` | Server IP (`88.198.191.108`) |
| `DEPLOY_USER` | SSH user (`root`) |
| `DEPLOY_SSH_KEY` | Private SSH key (OpenSSH format) |

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
  docker exec risk_hub_web python manage.py migrate &&
  docker exec risk_hub_web python manage.py seed_tom_categories &&
  curl -sf http://127.0.0.1:8090/livez/ &&
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

# Seed TOM categories
ssh root@88.198.191.108 'docker exec risk_hub_web python manage.py seed_tom_categories'

# Shell
ssh root@88.198.191.108 'docker exec -it risk_hub_web python manage.py shell'

# Restart
ssh root@88.198.191.108 'cd /opt/risk-hub && docker compose -f docker-compose.prod.yml restart risk-hub-web risk-hub-worker'

# DB Backup
ssh root@88.198.191.108 'docker exec risk_hub_db pg_dump -U risk_hub risk_hub | gzip > /opt/risk-hub/backups/$(date +%Y%m%d).sql.gz'
```

## Seed Data

Initial mandate data must exist per tenant for CSV import to work.

```bash
# Create seed mandates (run on server)
docker exec risk_hub_web python manage.py shell -c "
from dsb.models import Mandate
from datetime import date

tenants = {
    'demo': '61222b22-480b-4f9f-a8b1-ec40572b4729',
    'marold': '6c0d30d7-07f0-40a3-938d-7825d26024e9',
}

for org_name, tid in tenants.items():
    m, created = Mandate.objects.get_or_create(
        tenant_id=tid,
        name=f'{org_name.title()} GmbH',
        defaults={
            'status': 'active',
            'dsb_appointed_date': date(2025, 1, 1),
            'industry': 'other',
        },
    )
    print(f'  Created: {m.name}' if created else f'  Exists: {m.name}')
"

# Seed TOM categories
docker exec risk_hub_web python manage.py seed_tom_categories
```

### Organizations (Production)

| Slug | Tenant ID |
| --- | --- |
| `demo` | `61222b22-480b-4f9f-a8b1-ec40572b4729` |
| `dsb` | `5136057e-ca60-4a28-9ab7-43faf2c58a34` |
| `marold` | `6c0d30d7-07f0-40a3-938d-7825d26024e9` |

## Hardening TODO

- [ ] Add `logging` (json-file with rotation) to all services
- [ ] Add `deploy.resources.limits.memory` to all services
- [ ] Fix `risk_hub_worker` healthcheck (currently unhealthy despite clean logs)
- [x] Implement `/livez/` endpoint
- [x] Bind port to `127.0.0.1:8090:8000`
- [x] CI/CD pipeline with auto-deploy on push to main
