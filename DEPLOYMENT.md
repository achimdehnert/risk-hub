# Risk-Hub (Schutztat) — Deployment Reference

> Quelle: `.github/workflows/ci.yml` (ADR-090)

## Quick Reference

| Parameter | Value |
|-----------|-------|
| **Server** | `88.198.191.108` |
| **Server path** | `/opt/risk-hub` |
| **Domain** | `demo.schutztat.de` |
| **GHCR image** | `ghcr.io/achimdehnert/risk-hub/risk-hub-web:<sha>` |
| **Compose file** | `docker-compose.prod.yml` |
| **Env file** | `.env.prod` |
| **Host port** | `8090` → Gunicorn `:8000` |
| **Container (web)** | `risk_hub_web` |
| **Container (worker)** | `risk_hub_worker` |
| **Container (db)** | `risk_hub_db` |
| **Container (redis)** | `risk_hub_redis` |
| **Database** | Own stack (postgres:16-alpine) |
| **Network** | `risk_hub_network` (isolated) |
| **Health endpoint** | `/livez/` |

---

## CI/CD — Automatischer Ablauf

Push auf `main` → vollautomatisch:

```
push main
 → fast-checks  (ruff lint + format + pip-audit)
 → test         (pytest, coverage ≥ 50%)
 → deploy-build (docker build + push GHCR)
 → deploy-verify:
     1. docker compose pull
     2. DB Backup (pre-deploy)
     3. migrate --noinput  ← expand-only, BEFORE container start
     4. docker compose up -d --force-recreate
     5. healthcheck loop /livez/ (max 150s)
     6. readiness check /healthz/
 → rollback     (nur bei Fehler in deploy-verify)
```

### Migrations — Architekturentscheidung

**Migrationen laufen ausschließlich im CI/CD-Schritt "Run Migrations"**,
*vor* dem Container-Start (`docker compose run --rm`).

**NICHT** im `entrypoint.sh` — das verhindert:
- Unkontrollierte Migrationen bei Container-Restarts
- Race conditions bei mehreren Replicas
- Blockiertes Rollback (migrate läuft im alten Container)

```
ci.yml  →  compose run --rm web python manage.py migrate --noinput
                 ↓
             Container start (entrypoint.sh: nur collectstatic)
```

### Einmalig nach neuem Migration-File (manuell)

Wenn ein Deploy nicht via CI läuft (z.B. Hotfix direkt auf Server):

```bash
ssh root@88.198.191.108 '
  cd /opt/risk-hub &&
  docker compose -f docker-compose.prod.yml run --rm \
    risk-hub-web python manage.py migrate --noinput
'
```

> **Kein `docker exec` auf laufenden Container** — `run --rm` nutzt das neue
> Image und läuft kontrolliert, isoliert, ohne den laufenden Container zu stören.

---

## Services

| Compose service | Image | Purpose |
|-----------------|-------|---------|
| `risk-hub-web` | `ghcr.io/.../risk-hub-web:<sha>` | Gunicorn (Django) |
| `risk-hub-worker` | same image | Outbox publisher |
| `risk-hub-db` | `postgres:16-alpine` | PostgreSQL |
| `risk-hub-redis` | `redis:7-alpine` | Broker + Cache |
| `risk-hub-minio` | `minio/minio:latest` | Object Storage |

---

## Manueller Deploy (Notfall / Hotfix)

```bash
# 1. Build + Push
docker build \
  --label "org.opencontainers.image.revision=$(git rev-parse --short HEAD)" \
  -f docker/app/Dockerfile \
  -t ghcr.io/achimdehnert/risk-hub/risk-hub-web:$(git rev-parse --short HEAD) \
  -t ghcr.io/achimdehnert/risk-hub/risk-hub-web:latest \
  .
docker push ghcr.io/achimdehnert/risk-hub/risk-hub-web:latest

# 2. Deploy auf Server
ssh root@88.198.191.108 '
  cd /opt/risk-hub

  # Backup
  docker exec risk_hub_db pg_dump -U risk_hub risk_hub \
    | gzip > /opt/backups/pre_deploy_$(date +%Y%m%d_%H%M%S).sql.gz

  # Image holen
  docker compose -f docker-compose.prod.yml pull risk-hub-web

  # Migrationen VOR Container-Start
  docker compose -f docker-compose.prod.yml run --rm \
    risk-hub-web python manage.py migrate --noinput

  # Container neu starten
  docker compose -f docker-compose.prod.yml up -d \
    --no-deps --force-recreate risk-hub-web risk-hub-worker

  # Health prüfen
  sleep 10
  curl -sf http://127.0.0.1:8090/livez/ && echo "OK" || echo "FAIL"
'
```

---

## Operations

```bash
# Logs
ssh root@88.198.191.108 'docker logs risk_hub_web --tail 50'
ssh root@88.198.191.108 'docker logs risk_hub_worker --tail 50'

# Migration-Status prüfen
ssh root@88.198.191.108 \
  'docker compose -f /opt/risk-hub/docker-compose.prod.yml run --rm \
   risk-hub-web python manage.py showmigrations --plan'

# Shell
ssh root@88.198.191.108 \
  'docker exec -it risk_hub_web python manage.py shell'

# Restart (ohne migrate)
ssh root@88.198.191.108 \
  'cd /opt/risk-hub && docker compose -f docker-compose.prod.yml \
   restart risk-hub-web risk-hub-worker'

# DB Backup (manuell)
ssh root@88.198.191.108 \
  'docker exec risk_hub_db pg_dump -U risk_hub risk_hub \
   | gzip > /opt/backups/manual_$(date +%Y%m%d).sql.gz'

# Seed TOM-Kategorien
ssh root@88.198.191.108 \
  'docker exec risk_hub_web python manage.py seed_tom_categories'
```

---

## Rollback

```bash
# Auf spezifischen SHA zurückrollen
PREV_SHA=abc1234
ssh root@88.198.191.108 "
  cd /opt/risk-hub &&
  docker pull ghcr.io/achimdehnert/risk-hub/risk-hub-web:${PREV_SHA} &&
  IMAGE_TAG=${PREV_SHA} docker compose -f docker-compose.prod.yml \
    up -d --no-deps --force-recreate risk-hub-web risk-hub-worker
"
```

> Bei Rollback werden **keine** Migrations zurückgerollt (irreversibel).
> Nur Forward-kompatible Migrations sind erlaubt (expand-only pattern).

---

## GitHub Secrets / Vars

| Name | Typ | Beschreibung |
|------|-----|--------------|
| `DEPLOY_HOST` | Secret | `88.198.191.108` |
| `DEPLOY_USER` | Secret | `root` |
| `DEPLOY_SSH_KEY` | Secret | Private SSH key |
| `DEPLOY_IMAGE` | Var | `ghcr.io/achimdehnert/risk-hub/risk-hub-web` |
| `DEPLOY_DOCKERFILE` | Var | `docker/app/Dockerfile` |
| `DEPLOY_SERVER_PATH` | Var | `/opt/risk-hub` |
| `DEPLOY_WEB_SERVICE` | Var | `risk-hub-web` |
| `DEPLOY_CONTAINER` | Var | `risk_hub_web` |
| `DEPLOY_DB_CONTAINER` | Var | `risk_hub_db` |
| `DEPLOY_APP_NAME` | Var | `risk-hub` |
| `DEPLOY_PORT` | Var | `8090` |

---

## Organisationen (Produktion)

| Slug | Tenant ID |
|------|-----------|
| `demo` | `61222b22-480b-4f9f-a8b1-ec40572b4729` |
| `dsb` | `5136057e-ca60-4a28-9ab7-43faf2c58a34` |
| `marold` | `6c0d30d7-07f0-40a3-938d-7825d26024e9` |

---

## Hardening Status

- [x] Migrations via CI/CD (expand-only gate, nicht im Entrypoint)
- [x] Automatisches Rollback bei Healthcheck-Fehler
- [x] Pre-deploy DB Backup
- [x] `/livez/` + `/healthz/` endpoints
- [x] Port bind auf `127.0.0.1:8090:8000`
- [x] CI/CD pipeline (push to main → auto-deploy)
- [ ] json-file logging mit rotation für alle Services
- [ ] `deploy.resources.limits.memory` für alle Services
- [ ] `risk_hub_worker` healthcheck (aktuell unhealthy trotz sauberer Logs)
