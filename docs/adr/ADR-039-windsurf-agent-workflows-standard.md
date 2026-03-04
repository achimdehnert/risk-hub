# ADR-039: Windsurf Agent Workflows — Cross-Repo Standard

| Metadata | Value |
|----------|-------|
| **Status** | Accepted |
| **Date** | 2026-03-04 |
| **Version** | 2.0 |
| **Author** | Achim Dehnert |
| **Reviewers** | Senior Architect & DevOps Expert (04.03.2026) |
| **Geltungsbereich** | Alle Repos unter `/home/dehnert/github/` |
| **Supersedes** | ADR-039 v1.0 (Initial Draft) |
| **Related** | ADR-086 (risk-hub Agent-Task), ADR-009 (nl2cad Registry) |

> **Review-Ergebnis:** 2 kritische Sicherheitslücken (C-01, C-02) behoben.
> 8 hohe Befunde eingearbeitet. Status von "Proposed" → "Accepted".

---

## 1. Kontext und Problemstellung

Windsurf-Agent-Workflows (`.windsurf/workflows/*.md`) steuern das autonome Verhalten
des Coding-Agents. Bisher existieren sie **ohne gemeinsamen Standard**:

### 1.1 Ist-Stand (2026-03-04)

| Workflow | risk-hub | weltenhub | pptx-hub | travel-beat | cad-hub | nl2cad | bfagent |
|----------|:--------:|:---------:|:--------:|:-----------:|:-------:|:------:|:-------:|
| `/ship` | ✅ | ✅ | ✅ | ✅ | ✅ | — | — |
| `/sync-repos` | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| `/deploy` | ⚠️ alt | — | ⚠️ alt | ⚠️ alt | ⚠️ alt | — | ✅ |
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

### 2.1 Repo-Typen-Klassifikation

**Typ A: Django-Web-App**
risk-hub, weltenhub, pptx-hub, travel-beat, cad-hub, coach-hub, dev-hub, trading-hub, wedding-hub

**Typ B: Python-Library**
nl2cad, aifw, authoringfw, weltenfw, promptfw

**Typ C: Infrastruktur/Platform**
bfagent, mcp-hub, platform, infra-deploy

**Typ D: Static/Documentation** *(neu v2.0)*
illustration-hub, illustration-fw, odoo-hub, 137-hub (docs-only, GitHub Pages)
→ kein Server-Deploy, kein `/ship`

### 2.2 Pflicht-Workflows nach Repo-Typ

**Typ A: Django-Web-App**

| Workflow | Status | Beschreibung |
|----------|--------|--------------|
| `/ship` | **Pflicht** | Production deploy: verify → push → CI → migrate → health check → rollback |
| `/agent-task` | **Pflicht** | Sprint-Task: setup → implement → test → PR |
| `/adr-create` | **Pflicht** | Neuen ADR anlegen mit Template |
| `/pr-review` | **Pflicht** | PR-Review-Checkliste |
| `/run-tests` | **Pflicht** | Lint + Tests + Coverage |
| `/new-django-app` | **Pflicht** | Neues Django-App-Skeleton |
| `/deploy-check` | **Pflicht** | Pre-deploy Checkliste |
| `/sync-repos` | **Pflicht** | mcp_config.json synchronisieren (cross-repo) |
| `/htmx-view` | empfohlen | HTMX-View + Template anlegen |

**Typ B: Python-Library**

| Workflow | Status | Beschreibung |
|----------|--------|--------------|
| `/agent-task` | **Pflicht** | Sprint-Task Workflow |
| `/new-module` | **Pflicht** | Neues Package/Modul anlegen |
| `/new-package` | **Pflicht** | Vollständiges Package-Skeleton |
| `/run-tests` | **Pflicht** | uv run pytest + Coverage |
| `/adr-create` | **Pflicht** | ADR anlegen |
| `/start` | **Pflicht** | Einstiegspunkt für neuen Agent-Context |
| `/sync-repos` | **Pflicht** | mcp_config.json synchronisieren (cross-repo) |

**Typ C: Infrastruktur/Platform**

| Workflow | Status | Beschreibung |
|----------|--------|--------------|
| `/agent-task` | **Pflicht** | Sprint-Task Workflow |
| `/sync-repos` | **Pflicht** | mcp_config.json synchronisieren — Master-Script hier |
| `/deploy-check` | **Pflicht** | Pre-deploy Checkliste |
| `/pr-review` | **Pflicht** | PR-Review-Checkliste |
| `/run-tests` | **Pflicht** | Tests + CI-Verifikation |

**Typ D: Static/Documentation**

| Workflow | Status | Beschreibung |
|----------|--------|--------------|
| `/adr-create` | **Pflicht** | ADR anlegen |
| `/pr-review` | **Pflicht** | PR-Review-Checkliste |
| `/sync-repos` | **Pflicht** | mcp_config.json synchronisieren |

### 2.3 Pflicht-Frontmatter-Schema

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

**Erlaubte `scope`-Werte:**
- `scope: cross-repo` — identischer Inhalt in allen betroffenen Repos, Drift = Fehler
- `scope: <repo-name>` — repo-spezifisch, Abweichungen explizit erlaubt

**Cross-Repo Workflows** (scope: cross-repo, identisch in allen Repos):
- `/sync-repos`
- `/adr-create`
- `/pr-review`

**Sensitive Daten im Frontmatter: VERBOTEN** *(v2.0: C-01-Fix)*

Das Frontmatter eines Windsurf-Workflows wird in Git committed und ist — auch bei
privaten Repos — für alle Contributors dauerhaft sichtbar (Git-History).

```yaml
# ❌ VERBOTEN — sensitive Infrastruktur-Daten
server_ip: 88.198.191.108
project_path: /opt/risk-hub
db_password: ...

# ✅ ERLAUBT — nicht-sensitive Deployment-Metadaten
health_port: 8090
cd_workflow: cd-production.yml
web_container: risk_hub_web
```

Server-IP und Deployment-Pfade gehören ausschließlich in:
1. GitHub Secrets (`PROD_SERVER_IP`, `PROD_DEPLOY_PATH`)
2. Lokale `.env`-Dateien (nicht committed)
3. `mcp_config.json` (lokal, nicht in Git)

### 2.4 `/ship`-Workflow-Standard *(v2.0: C-01/C-02/H-01-Fix)*

**Feste Struktur für alle Typ-A Repos:**

```
Schritt 1: Branch + Status verifizieren    (KEIN // turbo — User-Bestätigung)
Schritt 2: Änderungen pushen               (erst nach User-OK)
Schritt 3: CI/CD-Workflow triggern         (mcp5_cicd_manage:dispatch)
Schritt 4: Deploy-Status verfolgen         (workflow_runs)
Schritt 5: Health Check                    (container_status + HTTP livez/)
Schritt 6: Rollback bei Failure            (previous image tag oder git revert)
[Schritt 7]: Post-Deploy repo-spezifisch   (z.B. Seed, collectstatic)
Fehlerbehebungs-Tabelle                    (konkrete MCP-Tool-Aufrufe)
```

**Schritt 1 — explizit kein `// turbo`:**

```markdown
## Schritt 1 — Branch + Status verifizieren

```bash
git branch --show-current   # muss 'main' sein
git status                  # zeigt uncommitted/untracked
git diff --stat HEAD        # zeigt was gepusht wird
```

**Warte auf User-Bestätigung** bevor Schritt 2.
Bei uncommitted WIP: abbrechen und User informieren.
```

**Schritt 6 — Rollback-Strategie:**

```markdown
## Schritt 6 — Rollback (nur bei Health-Check-Failure)

```bash
# Vorheriges Image-Tag aus Container-History ermitteln
docker ps -a --filter name=<web_container> --format "{{.Image}}"

# Rollback auf previous tag:
docker compose -f docker-compose.prod.yml pull web:<previous-tag>
docker compose -f docker-compose.prod.yml up -d --force-recreate web
```
```

**Erlaubte `/ship`-Frontmatter-Felder:**

```yaml
---
description: <repo> auf Production deployen
version: "1.0"
last_reviewed: YYYY-MM-DD
review_interval_days: 90
scope: <repo-name>
health_port: <port>          # ✅ nicht sensitiv
cd_workflow: <filename>      # ✅ nicht sensitiv
web_container: <name>        # ✅ nicht sensitiv
---
```

### 2.5 `/sync-repos` — zentrales Script *(v2.0: H-04-Fix)*

- **Script-Pfad**: `infra-deploy/scripts/sync_mcp_repos.py` *(verschoben von bfagent)*
- **Fallback**: Script ist auch in `bfagent/scripts/` verfügbar (Symlink oder Kopie)
- **Workflow** in jedem Repo: `.windsurf/workflows/sync-repos.md` (cross-repo, identisch)
- Erkennt automatisch neue Repos unter `/home/dehnert/github/`
- Entfernt Pfade die nicht mehr existieren
- `--dry-run` Modus für sichere Verifikation

### 2.6 `/deploy` (alt) — Deprecation *(v2.0: M-05-Fix)*

**Entschieden: `/deploy` wird durch `/ship` ersetzt.**

- **Removal-Datum**: 2026-04-04 (30 Tage ab ADR-Merge)
- Alle `/deploy.md`-Dateien erhalten sofort `deprecated: true` im Frontmatter
- Agent darf `/deploy` nicht mehr als primären Deploy-Weg nutzen
- Automated-Removal-Script: `bfagent/scripts/remove_deprecated_workflows.py`

### 2.7 Branching-Modell *(v2.0: M-06-Fix)*

**Entschieden: Trunk-Based Development für alle Typ-A/B/C Repos.**

- `main` = einziger produktiver Branch
- Feature-Branches für Entwicklung, PR-Merge in `main`
- `/ship` setzt immer voraus: aktueller Branch = `main`
- Branch Protection auf `main`: PRs erforderlich (außer für Owner bei Solo-Dev)

### 2.8 GitHub Reusable Workflows — Langziel *(v2.0: I-02)*

**Entschieden: Reusable Workflows sind das Langziel für GitHub-Actions-Standardisierung.**

```yaml
# Zukünftiger Standard in jedem Typ-A Repo:
jobs:
  deploy:
    uses: achimdehnert/infra-deploy/.github/workflows/deploy-django.yml@main
    with:
      app_name: risk-hub
      health_port: 8090
      web_container: risk_hub_web
    secrets: inherit
```

**Timeline**: Nach Abschluss der Sprint-1/2-Maßnahmen (ca. 2026-05).
Windsurf-Workflows bleiben für Agent-Interaktion, Reusable Workflows für Deploy-Logik.

---

## 3. Tooling — Enforcement

### 3.1 Drift-Detection: `check_workflow_drift.py` *(v2.0: H-03-Fix)*

```
infra-deploy/scripts/check_workflow_drift.py
```

Prüft ob alle `scope: cross-repo` Workflows identisch sind.
Ausführen in CI (bfagent) täglich oder bei PR auf Workflow-Dateien.

Meldet bei Abweichung:
- Welcher Workflow hat gedriftet
- In welchem Repo
- MD5-Hash-Differenz

### 3.2 Frontmatter-Validator: `validate_workflow_frontmatter.py` *(v2.0: M-04-Fix)*

```
infra-deploy/scripts/validate_workflow_frontmatter.py
```

Prüft Pflichtfelder (`description`, `version`, `last_reviewed`, `scope`) und
verbotene Felder (`server_ip`, `project_path`, Passwörter) in allen Workflow-Frontmatters.

Pre-commit Hook + CI-Check.

### 3.3 Review-Check: `check_workflow_reviews.py` *(v2.0: M-02-Fix)*

```
infra-deploy/scripts/check_workflow_reviews.py
```

Scheduled GitHub Actions Job (montags 09:00 UTC): öffnet GitHub Issue wenn
`last_reviewed + review_interval_days < today`.

---

## 4. Implementierung

### 4.1 Sofort erledigt (2026-03-04)

- [x] `mcp_config.json`: alle 22 Repos eingetragen
- [x] `bfagent/scripts/sync_mcp_repos.py`: zentrales Sync-Script
- [x] `GITHUB_TOKEN` in deployment-mcp `env`-Block + start-Script
- [x] `/sync-repos` in: risk-hub, weltenhub, pptx-hub, travel-beat, cad-hub, bfagent, nl2cad
- [x] `/ship` in: risk-hub, weltenhub, pptx-hub, travel-beat, cad-hub

### 4.2 Sprint 1 (bis 2026-03-11) — Kritische Fixes

| Task | Befund | Aufwand |
|------|--------|---------|
| `server_ip`/`project_path` aus allen `/ship`-Frontmattern entfernen | C-01 | 1h |
| `/ship` Schritt 1: Branch-Check + User-Gate (kein `// turbo`) | C-02 | 2h |
| `/ship` Schritt 6: Rollback-Schritt ergänzen | H-01 | 2h |
| `sync_mcp_repos.py` nach `infra-deploy` verschieben | H-04 | 1h |
| `check_workflow_drift.py` implementieren | H-03 | 3h |
| `validate_workflow_frontmatter.py` + pre-commit Hook | M-04 | 2h |
| `/deploy.md` in allen Repos: `deprecated: true` ins Frontmatter | M-05 | 1h |

### 4.3 Sprint 2 (bis 2026-03-25) — Robustheit

| Task | Befund | Aufwand |
|------|--------|---------|
| `check_workflow_reviews.py` + Scheduled GH Action | M-02 | 2h |
| Fehlende Pflicht-Workflows in: cad-hub, nl2cad, bfagent | §2.2 | 4h |
| Fehlende Pflicht-Workflows in: coach-hub, dev-hub, trading-hub, wedding-hub | §2.2 | 4h |
| `onboarding.md` in bfagent: mcp_config.json Setup dokumentieren | M-03 | 1h |
| CODEOWNERS für cross-repo Workflows | I-03 | 1h |

### 4.4 Sprint 3 / Backlog

| Task | Befund |
|------|--------|
| GitHub Environments für Production Deployments | H-05 |
| GitHub Reusable Workflows in infra-deploy | I-02 |
| `/health/`-Endpoint-Standard für alle Typ-A Repos | H-07 |
| `/deploy`-Removal-Script ausführen (nach 2026-04-04) | M-05 |
| Typ-D-Repos Workflows anlegen | §2.1 |

### 4.5 Gap-Tabelle — Fehlende Pflicht-Workflows

| Repo | Typ | Fehlende Pflicht-Workflows |
|------|-----|---------------------------|
| cad-hub | A | `/adr-create`, `/pr-review`, `/run-tests`, `/new-django-app`, `/deploy-check` |
| nl2cad | B | `/run-tests`, `/pr-review` |
| bfagent | C | `/run-tests` |
| coach-hub | A | alle außer `/sync-repos` |
| dev-hub | A | alle außer `/sync-repos` |
| trading-hub | A | alle außer `/sync-repos` |
| wedding-hub | A | alle außer `/sync-repos` |
| illustration-hub | D | `/adr-create`, `/pr-review`, `/sync-repos` |

---

## 5. Konsequenzen

### 5.1 Positiv
- Agent findet alle 22 Repos via `mcp6_*` Tools — keine "Access denied" Fehler mehr
- `/ship` hat immer gleiche Struktur mit Safety-Gate — kein versehentlicher Push
- Rollback-Schritt definiert — Production-Outages kürzer
- Drift-Detection verhindert auseinanderlaufende cross-repo Workflows
- Frontmatter-Validator verhindert sensitive Daten in Workflow-Dateien

### 5.2 Negativ / Risiken
- Windsurf-Neustart nach `/sync-repos` bleibt manueller Schritt (MCP-API-Limitation)
- MCP-Tool-Nummern (`mcp5_`, `mcp6_`) sind Windsurf-intern — können sich ändern
- Windsurf-Vendor-Lock-in: `// turbo`, MCP-Calls sind nicht IDE-agnostisch

### 5.3 Mitigation
- Sync-Script ist idempotent und hat `--dry-run`
- MCP-Tool-Referenzen in Workflows dokumentiert als "Stand 2026-03" — müssen bei Windsurf-Updates geprüft werden
- Workflow-Inhalt (Was tut `/ship`) ist IDE-agnostisch in Prosa beschrieben; `// turbo` ist nur Syntax-Sugar

---

## 6. Entschiedene Fragen (aus v1.0 §5)

| Frage | Entscheidung |
|-------|-------------|
| Soll `/ship` vollständig `/deploy` ersetzen? | **Ja** — `/deploy` deprecated, Removal 2026-04-04 |
| Welche Repos brauchen kein `/ship`? | **Typ B, C, D** — kein Server-Deploy |
| Soll `sync_mcp_repos.py` nach `infra-deploy`? | **Ja** — primär dort, Fallback in bfagent |
| Review-Trigger automatisieren? | **Ja** — Scheduled GH Action (M-02) |
| `agent-task` cross-repo oder repo-spezifisch? | **Repo-spezifisch** — ADR-086 bleibt in risk-hub, andere Repos passen es an |

---

## 7. Changelog

| Date | Version | Author | Change |
|------|---------|--------|--------|
| 2026-03-04 | 1.0 | Achim Dehnert | Initial draft |
| 2026-03-04 | 2.0 | Achim Dehnert | Review eingearbeitet: C-01 (server_ip entfernt), C-02 (Safety-Gate), H-01 (Rollback), H-03 (Drift-Detection), H-04 (infra-deploy), M-05 (Deprecation-Datum), M-06 (Branching), Typ D, offene Fragen entschieden |
