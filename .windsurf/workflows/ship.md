---
description: risk-hub auf Production deployen — verify, push, CI, migrate, health check
version: "2.0"
last_reviewed: 2026-03-04
review_interval_days: 90
scope: risk-hub
health_port: 8090
cd_workflow: docker-build.yml
web_container: risk_hub_web
---

## Schritt 1 — Branch + Status verifizieren

**KEIN auto-run. User-Bestätigung vor Push erforderlich.**

```bash
git -C /home/dehnert/github/risk-hub branch --show-current
git -C /home/dehnert/github/risk-hub status
git -C /home/dehnert/github/risk-hub diff --stat HEAD
```

Erwartung: Branch = `main`, keine uncommitted WIP-Änderungen.
**Abbruch wenn:** Branch != main ODER uncommitted Änderungen vorhanden.

---

## Schritt 2 — Änderungen pushen

Erst nach User-Bestätigung aus Schritt 1:

// turbo
```bash
git -C /home/dehnert/github/risk-hub push origin main
```

---

## Schritt 3 — GitHub Actions Deploy triggern

```
mcp5_cicd_manage:
  action: dispatch
  owner: achimdehnert
  repo: risk-hub
  workflow_id: docker-build.yml
  ref: main
```

---

## Schritt 4 — Deploy-Status verfolgen

```
mcp5_cicd_manage:
  action: workflow_runs
  owner: achimdehnert
  repo: risk-hub
  workflow_id: docker-build.yml
  per_page: 1
```

Warte auf `conclusion: success`. Bei `failure` → Schritt 6 (Rollback).

---

## Schritt 5 — Health Check

```
mcp5_docker_manage:
  action: container_status
  host: ${{ secrets.PROD_SERVER_IP }}
  container_id: risk_hub_web
```

```
mcp5_ssh_manage:
  action: http_check
  host: ${{ secrets.PROD_SERVER_IP }}
  url: http://127.0.0.1:8090/livez/
  expect_status: 200
```

Bei HTTP 200 → Deploy erfolgreich. Bei Failure → Schritt 6.

---

## Schritt 6 — Rollback (nur bei Health-Check-Failure)

```bash
# Vorheriges Image ermitteln:
docker ps -a --filter name=risk_hub_web --format "{{.Image}}"

# Rollback:
docker compose -f docker-compose.prod.yml pull web:<previous-tag>
docker compose -f docker-compose.prod.yml up -d --force-recreate web worker
```

Dann Health Check wiederholen. User über Rollback informieren.

---

## Fehlerbehebung

| Problem | Lösung |
|---------|--------|
| Container crasht | `container_logs container_id=risk_hub_web lines=80` |
| Migration fehlt | `container_exec container_id=risk_hub_web command="python manage.py migrate --noinput"` |
| Image nicht aktuell | CI-Log prüfen: `run_logs owner=achimdehnert repo=risk-hub run_id=<id>` |
| Branch falsch | `git checkout main && git pull origin main` |
