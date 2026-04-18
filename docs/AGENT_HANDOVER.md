# risk-hub (Schutztat) — Agent Handover Document

> **ADR-086-konform** | Zuletzt aktualisiert: 2026-04-18 | Review-Intervall: 30 Tage

## Repo-Zweck

`risk-hub` ist **Schutztat** — eine **Multi-Tenant SaaS-Plattform** für betrieblichen Arbeitsschutz (Django).
Domäne: Explosionsschutz, Gefährdungsbeurteilung (GBU), Sicherheitsdatenblätter (SDS), Brandschutz, Datenschutz.

Lokaler Pfad: `/home/devuser/github/risk-hub`
GitHub: `achimdehnert/risk-hub` (Branch: `main`)
Production: `https://schutztat.de` (Demo: `https://demo.schutztat.de`)

---

## Technischer Stack

| Komponente | Details |
|------------|---------|
| Framework | Django 5.x (`>=5.0,<6.0`) |
| Python | >= 3.11 |
| Frontend | HTMX (raw headers, **kein** `django-htmx`) + Tailwind CSS |
| DB | PostgreSQL 16-alpine (Multi-Tenant) |
| Cache/Broker | Redis 7-alpine |
| Object Storage | MinIO |
| Worker | Celery + Celery Beat |
| Container | Docker Compose (`docker-compose.prod.yml`) |
| Registry | GHCR (`ghcr.io/achimdehnert/risk-hub/risk-hub-web:latest`) |
| Settings | `config.settings` (single-file + `settings_test.py` / `settings_build.py` Overlays) |
| Auth | `identity.User` (Custom User Model) + mozilla-django-oidc |
| API | Django Ninja (`/api/v1/`) |

---

## App-Struktur (`src/` Prefix)

| App | Beschreibung |
|-----|-------------|
| `config` | Settings, URLs, WSGI, Celery, API-Auth |
| `identity` | Custom User Model, Auth |
| `tenancy` | Multi-Tenant Middleware, Organization Model |
| `permissions` | RBAC, Permission-Checks |
| `core` | Basis-Views, Dashboard-Root |
| `dashboard` | Haupt-Dashboard |
| `common` | BaseProgressService, Shared Utilities |
| `riskfw` | Safety Framework (inlined, ADR-146) |
| **`explosionsschutz`** | ATEX-Zonen, Konzepte, Ex-Dokumente, Doc-Templates |
| **`gbu`** | Gefährdungsbeurteilungen |
| **`brandschutz`** | Brandschutzkonzepte |
| **`global_sds`** | SDS-Upload, PubChem-Enrichment, Compliance-Dashboard |
| **`substances`** | Gefahrstoff-Kataster, CAS-Normalisierung |
| `documents` | Dokumenten-Management |
| `approvals` | Freigabe-Workflows |
| `audit` | Audit-Trail |
| `notifications` | Benachrichtigungen (HTMX) |
| `outbox` | Transactional Outbox Pattern |
| `reporting` | Reports, PDF-Export |
| `ai_analysis` | LLM-gestützte Analysen (via `iil-aifw`) |
| `actions` | Automatisierte Aktionen |
| `projects` | Projekt-basierter Workflow |
| `training` | Unterweisungs-Management |
| `dsb` | Datenschutzbeauftragter-Modul |
| `apps` | App-Registry |
| `tests` | Shared Test-Utilities |

---

## iil-Ecosystem Packages (9 aktiv)

| Package | Zweck |
|---------|-------|
| `iil-platform[shop]` | Shared Platform Utils + Stripe |
| `iil-aifw` | LLM-Calls (`sync_completion`) |
| `iil-promptfw` | Jinja2 Prompt-Templates |
| `iil-authoringfw` | Authoring/Content-Pipelines |
| `iil-concept-templates` | PDF-Extraktion + LLM-Strukturanalyse |
| `iil-doc-templates` | Reusable Django Template System |
| `iil-fieldprefill` | Field-Prefill für Doc-Templates (ADR-107) |
| `iil-learnfw[api,tenancy]` | Kurs/Lern-Management |
| `iil-reflex[web]` | UC Quality Checks + Domain Research (ADR-162) |

---

## HTMX-Konvention

- **Kein `django-htmx` Package** — nicht installiert, nicht in INSTALLED_APPS/MIDDLEWARE
- Detection: `request.headers.get("HX-Request")` (raw headers)
- **NIEMALS** `request.htmx` verwenden
- Templates: `hx-get`, `hx-post`, `hx-target`, `hx-swap` direkt in HTML
- Partials: `templates/<app>/partials/_<component>.html`

---

## Kritische Regeln

- **Multi-Tenancy (KRITISCH)**: `Organization.id` != `Organization.tenant_id` — IMMER `org.tenant_id` verwenden
- **Service-Layer**: `views.py` → `services.py` → `models.py`
- **Jedes Model**: `tenant_id = UUIDField(db_index=True)` Pflicht
- **Middleware**: setzt `request.tenant_id` — nie manuell ableiten
- **Primary Keys**: `BigAutoField` (NICHT UUIDs) — ADR-022 Migration abgeschlossen
- **RLS-Policies**: PostgreSQL Row-Level Security aktiv (ADR-161)
- **Templates**: alle erweitern `base.html`
- **Migrations**: nie automatisch — immer manuell prüfen

---

## Production-Container

| Container | Funktion | Status |
|-----------|----------|--------|
| `risk_hub_web` | Gunicorn :8000 (Host-Port 8090) | healthy |
| `risk_hub_worker` | Celery Worker | healthy |
| `risk_hub_celery` | Celery Worker (2nd) | healthy |
| `risk_hub_celery_beat` | Celery Beat Scheduler | healthy |
| `risk_hub_db` | PostgreSQL 16 | healthy |
| `risk_hub_redis` | Redis 7 | healthy |
| `risk_hub_minio` | MinIO Object Storage | healthy |

Health: `https://schutztat.de/healthz/` → 200 (20ms)

---

## Verbotene Pfade (ADR-081)

```
migrations/          — nie automatisch
.env*                — nie ändern
*.pem, *.key         — nie anfassen
docker-compose.prod.yml — nur explizit
```

---

## Dokumentation

- **18 ADRs** in `docs/adr/`
- **11 Use Cases** in `docs/use-cases/` (UC-001 bis UC-010 + UC-011)
- **reflex.yaml** — 33 Test-Routes, 3 Viewports, Domain-Keywords
- **95 Test-Dateien** — pytest

---

## Deployment

```bash
docker build -f docker/app/Dockerfile -t ghcr.io/achimdehnert/risk-hub/risk-hub-web:latest .
docker push ghcr.io/achimdehnert/risk-hub/risk-hub-web:latest
# Server: 88.198.191.108 (hetzner-prod)
```

Workflow: `/deploy` | Nach Deploy: `health_check risk-hub`

---

## Workflows (Windsurf)

| Workflow | Zweck |
|----------|-------|
| `/agent-task` | Task ausführen (ADR-086) |
| `/deploy` | Deployment ausführen |
| `/new-django-app` | Neue Django-App anlegen |
| `/htmx-view` | HTMX-View erstellen |
| `/adr` | Neues ADR erstellen |
| `/run-tests` | Tests + Lint ausführen |

---

## Häufige Fehler / Fallstricke

| Symptom | Ursache | Fix |
|---------|---------|-----|
| `request.htmx` AttributeError | `django-htmx` nicht installiert (by design) | `request.headers.get("HX-Request")` |
| Multi-Tenant Query liefert fremde Daten | `.filter(tenant_id=...)` fehlt | Immer `tenant_id` filtern |
| Migration fails auf Test-DB | `django-tenancy` braucht echtes PostgreSQL | `settings_test.py` nutzt PostgreSQL |
| `Organization.id` vs `Organization.tenant_id` | Unterschiedliche Felder! | Immer `org.tenant_id` für Queries |
