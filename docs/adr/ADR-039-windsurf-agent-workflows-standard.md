# ADR-039: Windsurf Agent Workflows — Cross-Repo Standard

| Metadata | Value |
|----------|-------|
| **Status** | Proposed — Review ausstehend |
| **Date** | 2026-03-04 |
| **Author** | Achim Dehnert |
| **Reviewers** | — |
| **Geltungsbereich** | Alle Repos unter `/home/dehnert/github/` |
| **Supersedes** | — |
| **Related** | ADR-086 (risk-hub Agent-Task), ADR-009 (nl2cad Registry) |

---

## 1. Kontext und Problemstellung

Windsurf-Agent-Workflows (`.windsurf/workflows/*.md`) steuern das autonome Verhalten
des Coding-Agents. Bisher existieren sie **ohne gemeinsamen Standard**:

### 1.1 Ist-Stand (2026-03-04)

| Workflow | risk-hub | weltenhub | pptx-hub | travel-beat | cad-hub | nl2cad | bfagent |
|----------|:--------:|:---------:|:--------:|:-----------:|:-------:|:------:|:-------:|
| `/ship` | ✅ | ✅ | ✅ | ✅ | ✅ | — | — |
| `/sync-repos` | ✅ | ✅ | ✅ | ✅ | ✅ | — | ✅ |
| `/deploy` | ✅ alt | — | ✅ alt | ✅ alt | ✅ | — | ✅ |
| `/deploy-check` | ✅ | ✅ | — | ✅ | — | — | ✅ |
| `/agent-task` | ✅ | ✅ | — | — | ✅ | ✅ | ✅ |
| `/adr-create` | ✅ | ✅ | ✅ | ✅ | — | — | ✅ |
| `/new-django-app` | ✅ | ✅ | ✅ | ✅ | — | — | — |
| `/htmx-view` | ✅ | ✅ | ✅ | — | — | — | — |
| `/pr-review` | ✅ | ✅ | ✅ | ✅ | — | — | ✅ |
| `/run-tests` | — | — | ✅ | — | — | — | — |
| `/new-module` | — | — | — | — | — | ✅ | — |
| `/new-package` | — | — | — | — | — | ✅ | — |
| `/start` | — | — | — | — | — | ✅ | — |

### 1.2 Festgestellte Probleme

1. **Fehlende Workflows**: `/run-tests` nur in pptx-hub, `/pr-review` fehlt in cad-hub + nl2cad
2. **Veraltete `/deploy`-Workflows**: direktes SSH ohne MCP-Tools, kein strukturierter Health-Check
3. **Kein Frontmatter-Standard**: `version`, `last_reviewed`, `scope` fehlen in den meisten
4. **Keine Selbst-Aktualisierung**: neues Repo → manuell in `mcp_config.json` nachtragen
5. **Kein Pflicht-Set definiert**: unklar welche Workflows jedes Repo haben muss
6. **mcp_config.json unvollständig**: nur 7 von 22 Repos waren im filesystem-MCP eingetragen

---

## 2. Entscheidung

### 2.1 Pflicht-Workflows nach Repo-Typ

**Typ A: Django-Web-App** (risk-hub, weltenhub, pptx-hub, travel-beat, cad-hub, coach-hub, dev-hub, trading-hub, wedding-hub)

| Workflow | Status | Beschreibung |
|----------|--------|--------------|
| `/ship` | **Pflicht** | Production deploy: push → CI → migrate → health check |
| `/agent-task` | **Pflicht** | Sprint-Task: setup → implement → test → PR |
| `/adr-create` | **Pflicht** | Neuen ADR anlegen mit Template |
| `/pr-review` | **Pflicht** | PR-Review-Checkliste |
| `/run-tests` | **Pflicht** | Lint + Tests + Coverage |
| `/new-django-app` | **Pflicht** | Neues Django-App-Skeleton |
| `/deploy-check` | **Pflicht** | Pre-deploy Checkliste |
| `/sync-repos` | **Pflicht** | mcp_config.json synchronisieren |
| `/htmx-view` | empfohlen | HTMX-View + Template anlegen |

**Typ B: Python-Library** (nl2cad, aifw, authoringfw, weltenfw, promptfw)

| Workflow | Status | Beschreibung |
|----------|--------|--------------|
| `/agent-task` | **Pflicht** | Sprint-Task Workflow |
| `/new-module` | **Pflicht** | Neues Package/Modul anlegen |
| `/new-package` | **Pflicht** | Vollständiges Package-Skeleton |
| `/run-tests` | **Pflicht** | uv run pytest + Coverage |
| `/adr-create` | **Pflicht** | ADR anlegen |
| `/start` | **Pflicht** | Einstiegspunkt für neuen Agent-Context |
| `/sync-repos` | **Pflicht** | mcp_config.json synchronisieren |

**Typ C: Infrastruktur/Platform** (bfagent, mcp-hub, platform, infra-deploy)

| Workflow | Status | Beschreibung |
|----------|--------|--------------|
| `/agent-task` | **Pflicht** | Sprint-Task Workflow |
| `/sync-repos` | **Pflicht** | mcp_config.json synchronisieren (hier liegt das Master-Script) |
| `/deploy-check` | **Pflicht** | Pre-deploy Checkliste |
| `/pr-review` | **Pflicht** | PR-Review-Checkliste |

### 2.2 Pflicht-Frontmatter-Schema

Jeder Workflow **muss** dieses Frontmatter haben:

```yaml
---
description: <max 80 Zeichen, Imperativ-Form, auf Deutsch>
version: "1.0"
last_reviewed: YYYY-MM-DD
review_interval_days: 90
scope: cross-repo | <repo-name>
---
```

- `scope: cross-repo` = identischer Inhalt in allen Repos, keine Abweichung erlaubt
- `scope: <repo-name>` = repo-spezifisch, Abweichungen explizit dokumentieren

**Cross-Repo Workflows** (identisch in allen Repos):
- `/sync-repos` — immer gleich, zentrales Script in `bfagent/scripts/`
- `/adr-create` — gleiche Struktur, ADR-Nummerierung repo-spezifisch
- `/pr-review` — gleiche Checkliste

### 2.3 `/ship`-Workflow-Standard

Jedes Django-Repo hat ein `/ship` mit dieser **fixen Struktur**:

```
Schritt 1: git status + push          (// turbo — auto-run)
Schritt 2: CI/CD triggern             (mcp5_cicd_manage:dispatch)
Schritt 3: Deploy-Status prüfen       (workflow_runs)
Schritt 4: Health Check               (container_status + HTTP)
[Schritt 5]: Post-Deploy-Schritte     (repo-spezifisch, z.B. Seed)
Fehlerbehebungs-Tabelle               (konkrete MCP-Tool-Aufrufe)
```

**Pflicht-Metadaten** im Frontmatter jedes `/ship`:

```yaml
---
description: <repo> auf Production deployen
server_ip: 88.198.191.108
project_path: /opt/<repo-name>
compose_file: docker-compose.prod.yml
web_container: <container-name>
health_port: <port>
cd_workflow: <workflow-dateiname>
---
```

### 2.4 `/sync-repos` — zentrales Script

- **Script-Pfad**: `bfagent/scripts/sync_mcp_repos.py` (single source of truth)
- **Workflow** in jedem Repo: `.windsurf/workflows/sync-repos.md` (cross-repo, identisch)
- Erkennt automatisch neue Repos unter `/home/dehnert/github/`
- Entfernt Pfade die nicht mehr existieren
- `--dry-run` Modus für sichere Verifikation
- **Wann ausführen**: nach jedem `git clone` oder neuem Repo

### 2.5 `/deploy` (alt) → `/ship` (neu)

Die alten `/deploy`-Workflows (direktes SSH) werden durch `/ship` ersetzt:

| Alt | Neu | Grund |
|-----|-----|-------|
| Direktes SSH | `mcp5_cicd_manage:dispatch` | Kein Token/Key nötig, CI läuft auf self-hosted runner |
| Manuelles `docker pull` | GitHub Actions übernimmt | Reproduzierbar, geloggt |
| Kein Health-Check | 4-Schritt Health-Check | Frühe Fehlerkennung |

Die alten `/deploy`-Dateien bleiben bis zum nächsten Review erhalten (nicht löschen, Scope bleibt).

---

## 3. Implementierung

### 3.1 Sofort (2026-03-04) — bereits erledigt

- [x] `mcp_config.json`: alle 22 Repos eingetragen
- [x] `bfagent/scripts/sync_mcp_repos.py`: zentrales Sync-Script
- [x] `/sync-repos` Workflow in: risk-hub, weltenhub, pptx-hub, travel-beat, cad-hub, bfagent
- [x] `/ship` Workflow in: risk-hub, weltenhub, pptx-hub, travel-beat, cad-hub

### 3.2 Nächster Sprint — Gap-Schließung

Fehlende Pflicht-Workflows nach Repo:

| Repo | Fehlend |
|------|---------|
| cad-hub | `/adr-create`, `/pr-review`, `/run-tests`, `/new-django-app`, `/deploy-check` |
| nl2cad | `/ship` (nicht nötig, GitHub Pages), `/run-tests`, `/pr-review`, `/sync-repos` |
| bfagent | `/ship`, `/run-tests` |
| coach-hub | alle Workflows |
| dev-hub | alle Workflows |
| trading-hub | alle Workflows |
| wedding-hub | alle Workflows |

### 3.3 Review-Zyklus

- `review_interval_days: 90` → alle 90 Tage per Agent-Task prüfen
- Trigger: Agent prüft `last_reviewed` + `review_interval_days` beim `/start`-Workflow

---

## 4. Konsequenzen

### 4.1 Positiv
- Agent findet alle Repos via `mcp6_*` Tools → keine "Access denied" Fehler mehr
- `/ship` hat immer die gleiche Struktur → Agent weiß was zu tun ist
- `/sync-repos` hält `mcp_config.json` automatisch aktuell
- Neue Repos sind sofort zugänglich nach einem Workflow-Aufruf + Reload

### 4.2 Negativ / Risiken
- Windsurf-Neustart nach `sync-repos` bleibt **manueller Schritt** (MCP-API erlaubt keinen Neustart)
- `bfagent/scripts/sync_mcp_repos.py` ist ein Single Point of Dependency — bfagent muss erreichbar sein
- Alte `/deploy`-Workflows erzeugen Duplikate mit `/ship`

### 4.3 Mitigation
- Sync-Script ist idempotent und hat `--dry-run` → sicher ausführbar
- Alte `/deploy`-Workflows explizit als `deprecated: true` im Frontmatter markieren (nächster Sprint)

---

## 5. Offene Fragen (für Review)

1. **Soll `/ship` vollständig `/deploy` ersetzen?** Oder beide parallel halten?
2. **Welche Repos brauchen kein `/ship`?** (nl2cad → GitHub Pages, kein Server-Deploy)
3. **Soll `sync_mcp_repos.py` nach `infra-deploy` verschoben werden** statt `bfagent`?
4. **Review-Trigger automatisieren?** Agent prüft `last_reviewed` beim `/start` — sinnvoll?
5. **Sollen alle Repos denselben `agent-task`-Workflow haben** (cross-repo) oder bleibt er repo-spezifisch (ADR-086)?

---

## 6. Changelog

| Date | Author | Change |
|------|--------|--------|
| 2026-03-04 | Achim Dehnert | Initial draft — nach SHIP-Debugging und mcp_config.json Fix |
