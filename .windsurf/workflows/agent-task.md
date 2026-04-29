---
description: Agent Task ausführen — ADR-086-konformer Sprint-Workflow für risk-hub (Schutztat)
source_adr: ADR-086
last_reviewed: 2026-04-29
review_interval_days: 30
version: "1.0"
---

# risk-hub (Schutztat) — Agent Task Workflow (ADR-086)

> **Tipp:** Für Tasks mit `complexity >= moderate` → `/agentic-coding` verwenden.
> Dieser Workflow deckt Phase 0 PCV, Self-Review und AuditStore NICHT ab.

## Schritt 0: Pflicht-Setup

1. Lies `docs/AGENT_HANDOVER.md` — Repo-Kontext
2. Lies das verlinkte GitHub Issue (agent-task Template)
3. Baseline-Check:

```bash
python -m pytest --tb=short -q 2>&1 | tail -5
ruff check src/ 2>&1 | tail -3
```

## Schritt 1: Scope-Lock (ADR-081)

- **Erlaubt**: nur `affected_paths` aus dem Issue
- **Immer verboten**: `migrations/`, `.env*`, `config/settings/prod*`, `*.pem`, `*.key`
- **Keine Deletes** außer explizit erlaubt

## Schritt 2: Feature-Branch

```bash
git checkout -b ai/developer/<task-id>
```

## Schritt 3: Implementieren (Service-Layer-Pattern)

1. **Model** in `models.py` — immer mit `tenant_id = UUIDField(db_index=True)`
2. **Service** in `services.py` — Business-Logik hier, nicht in Views
3. **View** in `views.py` — nur HTTP, delegiert an Service
4. **Template** erweitert `base.html`, nutzt HTMX
5. **Test** in `tests/` — Service + View getrennt testen
6. **`CHANGELOG.md`** unter `[Unreleased]`

## Schritt 4: Quality Gates

```bash
python -m pytest tests/MODULE/ -v --tb=short --cov=src/apps/MODULE
ruff check src/
ruff format src/
```

## Schritt 5: PR erstellen

```bash
git push -u origin ai/developer/<task-id>
```

PR-Body: `.github/PULL_REQUEST_TEMPLATE/agent-pr.md` ausfüllen.

## Kritisch: Multi-Tenancy (ADR-007)

- `Organization.id` != `Organization.tenant_id` — IMMER `org.tenant_id` verwenden
- Middleware setzt `request.tenant_id` — nie manuell ableiten
- Jedes neue Model braucht `tenant_id = UUIDField(db_index=True)`
