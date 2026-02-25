---
trigger: glob
globs:
  - "**/Dockerfile"
  - "docker-compose*.yml"
  - ".env*"
---

# Docker & Deployment (risk-hub)

## Dockerfile

- Location: `docker/app/Dockerfile`
- Base: `python:3.12-slim`
- Non-root user
- HEALTHCHECK: python urllib `/livez/`
- EXPOSE 8000

## Docker Compose

- File: `docker-compose.prod.yml`
- env_file: `.env.prod` (NEVER `${VAR}` interpolation)
- Image: `ghcr.io/achimdehnert/risk-hub/risk-hub-web:${IMAGE_TAG:-latest}`

## Services

- risk-hub-web: gunicorn on 0.0.0.0:8000
- risk-hub-worker: celery worker
- risk-hub-db: postgres:16-alpine
- risk-hub-redis: redis:7-alpine

## Deploy Flow (ADR-042)

1. `git push origin main`
2. GitHub Actions: docker build + push to GHCR
3. SSH 88.198.191.108: `docker compose pull && up -d --force-recreate`
4. Health check: `/livez/` returns 200

## Deploy Safety (deployment_mcp, Feb 2026)

- **DeployLock**: Atomic `mkdir` lock at `{project_dir}/.deploy.lock/`
  - Prevents concurrent deploys to same app
  - Auto-breaks stale locks after 30 min
  - Returns `{success: false, code: "deploy_locked"}` on conflict
- **Per-Tool Timeouts**: Deploy 900s, Compose 600s, Default 120s
  - Configured in `timeout_config.py`, NOT hardcoded
- **Shell Injection**: All SSH paths use `shlex.quote()`

## CRITICAL

- Never commit `.env.prod` to git
- `DJANGO_SETTINGS_MODULE=config.settings.production`
- Never bypass DeployLock when deploying via MCP tools
