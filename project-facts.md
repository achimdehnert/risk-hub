# Project Facts: risk-hub

> Auto-generiert von `platform/.github/scripts/push_project_facts.py`
> Letzte Aktualisierung: 2026-04-28 — bei Änderungen: `platform/gen-project-facts.yml` triggern

## Meta

- **Type**: `django`
- **GitHub**: `https://github.com/achimdehnert/risk-hub`
- **Branch**: `main` — push: `git push` (SSH-Key konfiguriert)

## Lokale Umgebung (Dev Desktop — adehnert)

- **Pfad**: `~/CascadeProjects/risk-hub` → `$GITHUB_DIR` = `~/CascadeProjects`
- **src_root**: `src/` — `manage.py` liegt dort
- **pythonpath**: `src/`
- **Venv**: `~/CascadeProjects/risk-hub/.venv/bin/python`
- **MCP aktiv**: `mcp0_` = github · `mcp1_` = orchestrator

## Settings

- **Prod-Modul**: `config.settings_production`
- **Test-Modul**: `config.settings_test`
- **Testpfad**: `src/`

## Stack

- **Django**: `5.2`
- **Python**: `3.12`
- **PostgreSQL**: `16`
- **HTMX installiert**: ja (`django-htmx`)
- **HTMX-Detection**: `request.htmx`

- **Celery**: ja (Worker + Beat)

## Apps

- `actions`
- `ai_analysis`
- `approvals`
- `audit`
- `brandschutz`
- `common`
- `dashboard`
- `documents`
- `dsb`
- `explosionsschutz`
- `exschutzdokument`
- `gbu`
- `global_sds`
- `identity`
- `notifications`
- `outbox`
- `permissions`
- `projects`
- `reporting`
- `risk`
- `substances`
- `tenancy`
- `training`

## Infrastruktur

- **Prod-URL**: `schutztat.de`
- **Staging-URL**: `demo.schutztat.de`
- **Port**: `8090`
- **Health-Endpoint**: `/livez/`
- **DB-Name**: `risk_hub`

## System (Hetzner Server)

- devuser hat **KEIN sudo-Passwort** → System-Pakete immer via SSH als root:
  ```bash
  ssh root@localhost "apt-get install -y <package>"
  ```
