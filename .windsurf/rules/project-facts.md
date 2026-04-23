---
trigger: always_on
---

# Project Facts: risk-hub

## Meta

- **Type**: `django`
- **GitHub**: `https://github.com/achimdehnert/risk-hub`
- **Branch**: `main` — push: `git push` (SSH-Key konfiguriert)
- **PyPI**: `risk-hub`
- **Venv**: `.venv/` — test: `.venv/bin/python -m pytest`

## Environments

| Env | Compose File | Host Port | Health URL | Public URL |
|-----|-------------|-----------|------------|------------|
| local   | `docker-compose.local.yml`   | `8090` | `http://localhost:8090/livez/` | http://localhost:8090 |
| staging | `docker-compose.staging.yml` | `8090` | `http://localhost:8090/livez/` | https://demo.schutztat.de |
| prod    | `docker-compose.prod.yml`    | `8090` | `http://localhost:8090/livez/` | https://schutztat.de |

## Docker Containers

| Container | Name | Purpose |
|-----------|------|---------|
| web    | `risk_hub_local_web`    | gunicorn:8000 |
| db     | `risk_hub_local_db`     | postgres:16   |
| redis  | `risk_hub_local_redis`  | redis:7       |
| worker | `risk_hub_local_worker` | celery (if present) |

## Database

- **DB name**: `risk_hub`
- **DB container**: `risk_hub_local_db`
- **Migrations**: `docker exec risk_hub_local_web python manage.py migrate`
- **Shell**: `docker exec -it risk_hub_local_web python manage.py shell`

## System (Hetzner Server)

- devuser hat **KEIN sudo-Passwort** → System-Pakete immer via SSH als root:
  ```bash
  ssh root@localhost "apt-get install -y <package>"
  ```

## Secrets / Config

- **Secrets**: `.env` (nicht in Git) — Template: `.env.example`
