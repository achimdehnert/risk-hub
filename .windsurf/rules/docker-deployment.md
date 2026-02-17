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
- HEALTHCHECK: python urllib `/livez/`
- EXPOSE 8000

## Docker Compose
- File: `docker-compose.prod.yml`
- env_file: `.env.prod` (NEVER `${VAR}` interpolation)
- Image: `ghcr.io/achimdehnert/risk-hub:${IMAGE_TAG:-latest}`

## Services
- risk-hub-web: gunicorn on 0.0.0.0:8000
- risk-hub-db: postgres:16-alpine
- risk-hub-redis: redis:7-alpine

## Deploy Flow (ADR-042)
1. `git push origin main`
2. GitHub Actions: docker build + push to GHCR
3. SSH 88.198.191.108: `docker compose pull && up -d --force-recreate`
4. Health check: `/livez/` returns 200

## CRITICAL
- Never commit `.env.prod` to git
- `DJANGO_SETTINGS_MODULE=config.settings`
