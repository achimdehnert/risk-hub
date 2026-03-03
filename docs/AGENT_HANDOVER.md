# risk-hub (Schutztat) — Agent Handover Document

> **ADR-086-konform** | Zuletzt aktualisiert: 2026-03-03 | Review-Intervall: 30 Tage

## Repo-Zweck

`risk-hub` ist **Schutztat** — eine **Multi-Tenant SaaS-Plattform** für betrieblichen Arbeitsschutz (Django).

---

## Technischer Stack

| Komponente | Details |
|------------|---------|
| Framework | Django 5.x |
| Python | >= 3.11 |
| Frontend | HTMX + Tailwind CSS |
| DB | PostgreSQL 16 (Multi-Schema) |
| Cache/Broker | Redis 7 |
| Container | Docker Compose (`docker-compose.prod.yml`) |
| Registry | GHCR (`ghcr.io/achimdehnert/risk-hub/`) |

---

## Kritische Regeln

- **Multi-Tenancy (KRITISCH)**: `Organization.id` != `Organization.tenant_id` — IMMER `org.tenant_id` verwenden
- **Service-Layer**: `views.py` → `services.py` → `models.py`
- **Jedes Model**: `tenant_id = UUIDField(db_index=True)` Pflicht
- **Middleware**: setzt `request.tenant_id` — nie manuell ableiten
- **HTMX**: kein custom JS-Framework
- **Templates**: alle erweitern `base.html`
- **Migrations**: nie automatisch — immer manuell prüfen

---

## Verbotene Pfade (ADR-081)

```
migrations/          — nie automatisch
.env*                — nie ändern
config/settings/prod* — nie ändern
*.pem, *.key         — nie anfassen
docker-compose.prod.yml — nur explizit
```

---

## Deployment

```bash
docker build -f docker/app/Dockerfile -t ghcr.io/achimdehnert/risk-hub/risk-hub-web:latest .
docker push ghcr.io/achimdehnert/risk-hub/risk-hub-web:latest
# Server: 88.198.191.108
```

Workflow: `/deploy`

---

## Workflows (Windsurf)

| Workflow | Zweck |
|----------|-------|
| `/agent-task` | Task ausführen (ADR-086) |
| `/deploy` | Deployment ausführen |
| `/new-django-app` | Neue Django-App anlegen |
| `/htmx-view` | HTMX-View erstellen |
| `/adr-create` | Neues ADR erstellen |
