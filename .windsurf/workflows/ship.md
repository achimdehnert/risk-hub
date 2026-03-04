---
description: risk-hub auf Production deployen — Image bauen, migrate, health check
---

## Kontext

- **Repo:** `achimdehnert/risk-hub`
- **Server:** `88.198.191.108`, Pfad: `/opt/risk-hub`
- **Compose:** `docker-compose.prod.yml`
- **Web-Container:** `risk_hub_web` (Port 8090)
- **Deploy-Mechanismus:** GitHub Actions `docker-build.yml` (build) → SSH-Deploy
- **Health-URL:** `http://127.0.0.1:8090/livez/`

---

## Schritt 1 — Änderungen pushen

// turbo
```bash
git -C /home/dehnert/github/risk-hub status
git -C /home/dehnert/github/risk-hub push origin main
```

---

## Schritt 2 — GitHub Actions Deploy triggern

Nutze `mcp5_cicd_manage`:
```
action: dispatch
owner: achimdehnert
repo: risk-hub
workflow_id: docker-build.yml
ref: main
```

Falls kein CI-Trigger: manuell unter https://github.com/achimdehnert/risk-hub/actions

---

## Schritt 3 — Status prüfen

```
mcp5_cicd_manage:
  action: workflow_runs
  owner: achimdehnert
  repo: risk-hub
  workflow_id: docker-build.yml
  per_page: 1
```

---

## Schritt 4 — Health Check

```
mcp5_docker_manage:
  action: container_status
  host: 88.198.191.108
  container_id: risk_hub_web
```

---

## Fehlerbehebung

| Problem | Lösung |
|---------|--------|
| Container crasht | `container_logs container_id=risk_hub_web lines=50 host=88.198.191.108` |
| Migration fehlt | `container_exec container_id=risk_hub_web command="python manage.py migrate --noinput"` |
| Image nicht aktuell | `compose_pull host=88.198.191.108 project_path=/opt/risk-hub` |
