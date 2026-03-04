# Architecture Review: ADR-039
**Windsurf Agent Workflows — Cross-Repo Standard**

> **Reviewer:** Senior Architect & Senior SW-Engineer (GitHub Actions / DevOps Expert)  
> **Datum:** 04.03.2026  
> **Scope:** Vollkritisches Review — Architektur, Sicherheit, GitHub-Best-Practices, Umsetzbarkeit  
> **ADR-Status bei Review:** Proposed — Review ausstehend

---

## 1. Executive Summary

Der ADR adressiert ein reales, schmerzhaftes Problem: **Workflow-Wildwuchs über 22 Repos**.
Die Grundidee (Pflicht-Set, Frontmatter-Standard, `/ship` als Deployment-Primitiv) ist richtig.

Jedoch enthält der ADR **2 kritische Sicherheitslücken**, mehrere fundamentale
GitHub-Actions-Anti-Patterns und eine gefährliche Abhängigkeit auf bfagent als Single Point
of Failure. Der ADR darf in dieser Form **nicht umgesetzt werden**.

| Kategorie | Anzahl |
|---|:---:|
| 🔴 KRITISCH — Sicherheit / Datenverlust-Risiko | **2** |
| 🟠 HOCH — Architektur / GitHub-Best-Practice-Verletzung | **8** |
| 🟡 MITTEL — Robustheit / Umsetzungslücken | **7** |
| 🔵 INFO — Verbesserungen / Empfehlungen | **5** |
| **Gesamt** | **22** |

---

## 2. Kritische Befunde

### 🔴 C-01 — Server-IP hardcoded in Workflow-Frontmatter (commitet in jedes Repo)

**Befund:**  
ADR §2.3 schreibt vor, dass jeder `/ship`-Workflow folgendes Frontmatter enthält:

```yaml
---
server_ip: 88.198.191.108
---
```

Diese IP-Adresse wird damit in **jedem Repo committed** — in `.windsurf/workflows/ship.md`.
Das ist ein Public-Repository-Scenario: jeder mit Repo-Zugriff kennt die Server-IP.
Bei GitHub Public Repos: weltweit abrufbar, indexiert durch Google und Shodan.
Selbst bei Private Repos: jeder Contributor (auch ehemalige) hat diesen Wert gesehen.

**Warum das kritisch ist:**
- Direkte Angriffsfläche: Port-Scans auf bekannte IP werden gezielt auf Schwachstellen geprüft
- In Kombination mit `.env.prod`-Leaks (häufig) → direkter Server-Kompromiss
- IP kann nicht einfach rotiert werden, ohne alle Workflow-Dateien in 22 Repos zu patchen
- Verstößt gegen OWASP A05:2021 (Security Misconfiguration) und allgemeine Secrets-Hygiene

**Empfehlung:**  
Server-Metadaten aus dem Frontmatter entfernen. Deployment-Targets ausschließlich über
GitHub Environments + Secrets verwalten:

```yaml
# .github/workflows/deploy.yml
jobs:
  deploy:
    environment: production   # GitHub Environment mit Protection Rules
    env:
      SERVER_IP: ${{ secrets.PROD_SERVER_IP }}
      DEPLOY_PATH: ${{ secrets.PROD_DEPLOY_PATH }}
```

Das Workflow-Frontmatter darf nur **nicht-sensitive Metadaten** enthalten:

```yaml
---
description: risk-hub auf Production deployen
version: "1.0"
scope: risk-hub
health_port: 8095           # Port ist OK — keine Security-relevanz
cd_workflow: deploy.yml     # Workflow-Dateiname ist OK
---
```

---

### 🔴 C-02 — `/ship` Schritt 1: `// turbo — auto-run` ohne Safety-Gate

**Befund:**  
ADR §2.3 definiert Schritt 1 als:

```
Schritt 1: git status + push    (// turbo — auto-run)
```

`// turbo` bedeutet in Windsurf: **der Agent führt diesen Schritt ohne User-Bestätigung aus**.
Ein automatischer `git push` auf den Production-Branch ist in einem `/ship`-Kontext
ein gravierendes Anti-Pattern:

- **Was passiert bei uncommitted WIP?** Der Agent staged und pusht ggf. halbfertigen Code.
- **Was passiert auf dem falschen Branch?** `git push` auf `feature/xyz` triggert keinen
  Deploy, aber der Agent fährt mit Schritt 2 fort und reportet "Success".
- **Kein Branch-Check:** Kein Verify dass `main`/`master` der aktuelle Branch ist.
- **Kein Diff-Check:** Keine Anzeige was tatsächlich gepusht wird, bevor es passiert.
- **Race Condition:** Push + sofortiges CI-Dispatch in Schritt 2 → CI könnte alten
  Stand erwischen wenn der Push noch nicht propagiert ist.

**Empfehlung:**  
Schritt 1 muss ein explizites User-Gate haben und Branch/Status verifizieren:

```markdown
## Schritt 1: Vorbereitung und Push

**NICHT auto-run. User-Bestätigung erforderlich.**

1. Prüfe aktuellen Branch: `git branch --show-current` → muss `main` sein
2. Prüfe Status: `git status` → zeige User was committed/uncommitted ist
3. **Warte auf User-Bestätigung:** "Soll ich folgende Änderungen pushen: [diff summary]?"
4. Erst nach Bestätigung: `git push origin main`
5. Verifiziere Push-Erfolg: Exit-Code 0 + Remote-Response prüfen
```

---

## 3. Hohe Priorität — Architektur & GitHub Best Practices

### 🟠 H-01 — Kein Rollback-Mechanismus in `/ship`

**Befund:**  
Der `/ship`-Workflow dispatcht CI/CD und prüft dann einen Health-Check. Was passiert
bei Failure? Der ADR definiert nur eine "Fehlerbehebungs-Tabelle (konkrete MCP-Tool-Aufrufe)"
— aber keinen automatischen Rollback.

In Production ist ein Deploy ohne definierten Rollback-Path ein Risiko:
- Health-Check schlägt fehl → Service ist down → Agent... macht was?
- Kein `docker rollout undo`, kein "previous image tag", kein Revert-Schritt

**Empfehlung:**  
`/ship`-Struktur um Rollback-Schritt erweitern:

```
Schritt 5 (Fehlerfall): Rollback
  → docker-compose pull <previous-tag>   (oder: git revert + re-push)
  → docker-compose up -d
  → Health-Check wiederholen
  → User benachrichtigen mit Fehlerdetails
```

GitHub Actions: `on: workflow_run` mit `if: failure()` für automatischen Rollback-Trigger.

---

### 🟠 H-02 — MCP-Tool-Nummern sind instabil (`mcp5_cicd_manage`)

**Befund:**  
Der ADR referenziert Tools wie `mcp5_cicd_manage:dispatch` und `mcp6_*`. Die Nummerierung
(`mcp5_`, `mcp6_`) ist durch Windsurf intern bestimmt und **ändert sich mit jeder
`mcp_config.json`-Änderung** (neue Repos → neue Indices). Das bedeutet:

- Nach jedem `/sync-repos`-Aufruf (der neue Repos hinzufügt) **ändern sich alle
  mcp_X_ Indizes** → alle bestehenden Workflows referenzieren falsche Tools
- Ein neues Repo an Position 3 verschiebt alle nachfolgenden Indices
- Cross-Repo Workflows (`scope: cross-repo`) die `mcp5_` hardcoden sind sofort broken

**Empfehlung:**  
MCP-Tool-Referenzen nie mit numerischem Index hardcoden. Stattdessen:

1. Windsurf-Workflows sollen Tool-Namen verwenden (falls Windsurf das unterstützt)
2. Alternativ: Einen "Tool-Discovery"-Schritt an den Anfang jedes Workflows setzen
3. Im ADR explizit dokumentieren: "MCP-Indizes in Workflows sind instabil und
   müssen nach jedem sync-repos verifiziert werden"
4. CI-Test schreiben der prüft ob alle tool-referenzen noch valide sind

---

### 🟠 H-03 — `scope: cross-repo` ohne Enforcement-Mechanismus

**Befund:**  
ADR §2.2 definiert: `scope: cross-repo` = "identischer Inhalt in allen Repos,
keine Abweichung erlaubt". Es gibt aber **keinen Mechanismus der das durchsetzt**:

- Kein Git-Hook der auf Abweichungen prüft
- Kein CI-Workflow der cross-repo Workflows auf Gleichheit prüft
- Kein Script das Drift erkennt
- "Keine Abweichung erlaubt" ist eine Policy ohne Tooling = totes Papier

Nach 6 Monaten werden die "cross-repo" Workflows in 22 Repos auseinanderdriften —
genau das Problem das der ADR lösen will.

**Empfehlung:**  
`bfagent/scripts/check_workflow_drift.py` implementieren:

```python
# Prüft ob alle cross-repo Workflows identisch sind
# Ausführen in CI (bfagent) täglich oder bei PR
import hashlib, pathlib

CROSS_REPO_WORKFLOWS = ["sync-repos.md", "adr-create.md", "pr-review.md"]
REPOS_ROOT = pathlib.Path("/home/dehnert/github")

def check_drift():
    for workflow in CROSS_REPO_WORKFLOWS:
        hashes = {}
        for repo in REPOS_ROOT.iterdir():
            wf_path = repo / ".windsurf/workflows" / workflow
            if wf_path.exists():
                hashes[repo.name] = hashlib.md5(wf_path.read_bytes()).hexdigest()
        unique = set(hashes.values())
        if len(unique) > 1:
            print(f"DRIFT DETECTED in {workflow}:")
            for repo, h in hashes.items():
                print(f"  {repo}: {h}")
```

---

### 🟠 H-04 — Single Point of Failure: `bfagent/scripts/sync_mcp_repos.py`

**Befund:**  
Der ADR erkennt das Problem selbst (§4.2): "bfagent muss erreichbar sein". Die Mitigation
("Script ist idempotent und hat --dry-run") adressiert aber das falsche Problem:
das Script kann noch so idempotent sein — wenn bfagent nicht geklont/erreichbar ist,
kann kein anderes Repo synced werden.

Konkrete Failure-Szenarien:
- Developer arbeitet ohne bfagent-Klon (neuer Entwickler, neues Gerät)
- bfagent wird renamed/verschoben/gelöscht
- bfagent-Repo ist temporär private oder gesperrt

**Empfehlung:**  
Das Script gehört in ein **dediziertes Infra-Repo** (der ADR fragt das selbst in §5.3
als offene Frage — die Antwort ist: ja, `infra-deploy` oder ein neues `platform`-Repo).

Alternativ: Das Script in ein **selbstständiges PyPI-Paket** (`iil-devtools`) oder
zumindest als **GitHub Gist** mit stabiler URL hosten. Die richtige Frage ist:
"Wie installiert ein neuer Entwickler auf einem neuen Gerät das sync-Script?"

---

### 🟠 H-05 — Keine GitHub Environments für Production Deployments

**Befund:**  
GitHub Environments sind ein First-Class-Feature für Production-Deployments:
- **Required Reviewers:** Deployment muss von einer Person genehmigt werden
- **Wait Timer:** Deployment startet erst X Minuten nach Trigger
- **Protection Rules:** Nur bestimmte Branches dürfen in `production` deployen
- **Environment Secrets:** Secrets isoliert pro Environment

Der ADR ignoriert dieses Feature komplett. Stattdessen: direkter Dispatch ohne Gate.
Das bedeutet: jeder mit Push-Recht kann sofort auf Production deployen.

**Empfehlung:**  
Für alle Typ-A Django-Apps eine `production` GitHub Environment definieren:

```yaml
# .github/workflows/deploy.yml
jobs:
  deploy:
    environment:
      name: production
      url: https://${{ env.DOMAIN }}
    # → Requires approval before running
    # → Only main branch can deploy
    # → Secrets scoped to this environment
```

ADR muss dieses Pattern als Standard vorschreiben.

---

### 🟠 H-06 — `cd_workflow` Frontmatter-Parameter ist redundant und fehleranfällig

**Befund:**  
Das `/ship`-Frontmatter enthält `cd_workflow: <workflow-dateiname>`. Dieser Wert
wird vom Agent genutzt um `mcp5_cicd_manage:dispatch` aufzurufen. Das Problem:

```yaml
cd_workflow: deploy.yml   # Muss exakt mit dem GitHub Actions filename übereinstimmen
```

Tippfehler im Frontmatter → Agent dispatcht falschen/nicht-existierenden Workflow.
Kein Feedback bis GitHub Actions antwortet. In `// turbo`-Kontext: kein User-Check.

Außerdem: wenn der GitHub Actions Workflow umbenannt wird, müssen alle 22 `/ship`-Dateien
händisch aktualisiert werden (wieder Drift-Problem).

**Empfehlung:**  
Konvention statt Konfiguration: Jedes Repo hat genau ein `deploy.yml` in `.github/workflows/`.
Der Agent sucht es konventionsbasiert, kein Frontmatter-Parameter nötig. Alternativ:
GitHub Actions API liefert alle vorhandenen Workflows → Agent wählt den richtigen.

---

### 🟠 H-07 — Fehlende Definition von "healthy" für Health-Checks

**Befund:**  
Der `/ship`-Standard nennt "Health Check (container_status + HTTP)" als Schritt 4.
Was bedeutet "healthy"?

- HTTP 200 auf `/`? (könnte eine Error-Page mit Status 200 sein)
- HTTP 200 auf `/health/`? (nicht alle Repos haben diesen Endpoint — weltenhub?)
- Spezifisches JSON-Response-Body?
- Container-Status `Up (healthy)`? (nur wenn Dockerfile HEALTHCHECK definiert)
- Response-Zeit < X ms?

Ohne klare Definition prüft der Agent das falsche und reportet "healthy" obwohl
der Service broken ist.

**Empfehlung:**  
Im ADR eine Minimalanforderung für alle Typ-A Repos definieren:

```python
# Jedes Django-Repo MUSS haben:
# GET /health/ → HTTP 200 → {"status": "ok", "service": "<name>", "version": "x.y.z"}

# /ship Schritt 4 prüft exakt:
# 1. HTTP 200 auf GET https://<domain>/health/
# 2. Response-Body enthält "status": "ok"
# 3. Antwortzeit < 5s
# 4. docker ps zeigt Container als "Up" (nicht "Up (unhealthy)")
```

---

### 🟠 H-08 — Kein Secret/Credential-Management-Standard

**Befund:**  
Der ADR beschreibt Deployment-Workflows aber erwähnt an keiner Stelle wie Secrets
verwaltet werden:

- Wie kommen `OPENAI_API_KEY`, `DB_PASSWORD` etc. auf den Server?
- Werden sie per SSH übertragen? (Klartext über Netz)
- Liegen sie in `.env.prod` im Repo? (Sicherheitsrisiko)
- GitHub Secrets → wie gelangen sie zur `docker-compose` auf dem Server?

Das ist der kritischste Lückenpunkt für ein Production-Deployment-Standard-ADR.

**Empfehlung:**  
Eine eigene Sektion "Secret Management" im ADR ergänzen mit:

```yaml
# Standard-Ansatz für alle Repos:
# 1. GitHub Secrets speichern: PROD_ENV_FILE (base64-encoded .env.prod Inhalt)
# 2. GitHub Actions deploy.yml:
- name: Write .env.prod
  run: echo "${{ secrets.PROD_ENV_FILE }}" | base64 -d > /opt/${{ env.APP_NAME }}/.env.prod
# 3. Niemals Secrets in Frontmatter oder Workflow-MD-Dateien
```

---

## 4. Mittlere Priorität — Robustheit & Umsetzungslücken

### 🟡 M-01 — ADR-Cross-Referenz falsch: ADR-086

**Befund:**  
Header: `Related: ADR-086 (risk-hub Agent-Task)`. ADR-086 im Projekt-Kontext beschreibt
aber den `illustration-hub` Django-Service — nicht einen risk-hub Agent-Task.
Nummernkollision oder Verwechslung. Unklar welches ADR gemeint ist.

**Empfehlung:**  
Cross-Referenz korrigieren. ADR-Nummern-Register anlegen (zentrales Dokument das
ADR-Nummer → Titel → Repo mappt) um solche Konflikte zu vermeiden.

---

### 🟡 M-02 — `review_interval_days: 90` ohne Automations-Mechanismus

**Befund:**  
Das Frontmatter-Feld `review_interval_days: 90` ist eine Policy ohne Enforcement.
Der ADR sagt "Agent prüft `last_reviewed` beim `/start`-Workflow" — aber `/start`
existiert nur für Typ-B-Repos. Typ-A und Typ-C Repos haben keinen automatischen
Review-Trigger.

In der Praxis: Das Feld wird nie geprüft, Workflows veralten still.

**Empfehlung:**  
GitHub Actions Scheduled Workflow in bfagent (oder infra-deploy):

```yaml
# .github/workflows/workflow-review-check.yml
on:
  schedule:
    - cron: '0 9 * * 1'  # Montags 09:00 UTC

jobs:
  check-reviews:
    steps:
      - name: Check overdue workflow reviews
        run: python scripts/check_workflow_reviews.py
        # → Öffnet GitHub Issue wenn last_reviewed + interval_days < today
```

---

### 🟡 M-03 — `mcp_config.json` ist eine lokale Datei — nicht in Git

**Befund:**  
`mcp_config.json` liegt auf dem lokalen Rechner des Entwicklers (`~/.codeium/windsurf/`
oder ähnlich). Diese Datei ist:
- Nicht in Git → kein Sharing mit Teammates
- Nicht reproduzierbar auf neuem Gerät
- Der `/sync-repos`-Workflow patcht eine Datei die nur lokal existiert

Das `sync_mcp_repos.py`-Script ist damit ein lokales Tooling-Script, kein echtes
Cross-Repo-Standard-Tool. Ein neuer Entwickler muss den gesamten Setup-Prozess
manuell nachvollziehen.

**Empfehlung:**  
`onboarding.md` oder `setup.sh` in bfagent dokumentiert:
1. Wo `mcp_config.json` liegt (versionsspezifisch!)
2. Wie `sync_mcp_repos.py` bootstrapped wird
3. Was nach einem Windsurf-Update zu tun ist

Langfristig: Template-`mcp_config.json` in bfagent repo committen
(ohne sensitive Pfade, mit Platzhaltern).

---

### 🟡 M-04 — Frontmatter-Validierung fehlt in CI

**Befund:**  
YAML-Frontmatter in Markdown-Dateien (`---`) wird von keinem Standard-Tool validiert.
Fehlende Pflichtfelder (`version`, `scope`) werden nicht erkannt bis ein Agent
den Workflow aufruft und das Feld fehlt.

**Empfehlung:**  
Pre-commit Hook + CI-Check:

```python
# scripts/validate_workflow_frontmatter.py
import yaml, pathlib, sys

REQUIRED_FIELDS = ["description", "version", "last_reviewed", "scope"]
SHIP_REQUIRED   = ["health_port", "cd_workflow"]  # für /ship Workflows

errors = []
for wf in pathlib.Path(".windsurf/workflows").glob("*.md"):
    content = wf.read_text()
    if content.startswith("---"):
        fm_text = content.split("---")[1]
        fm = yaml.safe_load(fm_text)
        for field in REQUIRED_FIELDS:
            if field not in fm:
                errors.append(f"{wf.name}: missing '{field}'")

if errors:
    print("\n".join(errors)); sys.exit(1)
```

```yaml
# .pre-commit-config.yaml
- repo: local
  hooks:
    - id: validate-workflow-frontmatter
      name: Validate Windsurf workflow frontmatter
      entry: python scripts/validate_workflow_frontmatter.py
      language: python
      files: \.windsurf/workflows/.*\.md$
```

---

### 🟡 M-05 — `/deploy` (alt) Deprecation ohne Timeline

**Befund:**  
ADR §4.3: "Alte `/deploy`-Workflows explizit als `deprecated: true` im Frontmatter
markieren (nächster Sprint)". Kein konkretes Datum, kein Owner, kein Removal-Datum.

"Nächster Sprint" bei 22 Repos und Solo-Entwickler = wahrscheinlich nie.
Die alten Workflows verbleiben parallel zu `/ship` und erzeugen Konfusion.

**Empfehlung:**  
Konkretes Deprecation-Datum setzen: 2026-04-04 (30 Tage). GitHub Issue erstellen.
Danach: Automated PR via bfagent Script der alle `/deploy.md` löscht.

---

### 🟡 M-06 — Kein Branching-Modell definiert

**Befund:**  
`/ship` pusht auf Production. Aber welcher Branch ist "Production"?
Der ADR setzt implizit voraus: `main` = Production-Branch. Das ist nicht dokumentiert.

Für Repos mit Feature-Branching oder GitFlow würde `/ship` auf dem Feature-Branch
nichts deployen. Kein Branch-Check im Workflow.

**Empfehlung:**  
Im ADR explizit dokumentieren:
- Alle Typ-A Repos: `main` = einziger Branch, direkte Pushes (trunk-based development)
- Branch Protection Rule: `main` erfordert PR + Review für alle außer dem Owner
- GitHub Branch Protection in allen Repos aktivieren (Script in bfagent)

---

### 🟡 M-07 — Keine Notifications bei `/ship`-Failure

**Befund:**  
Wenn `/ship` fehlschlägt (Health-Check negativ, CI failed), erfährt der Entwickler
davon nur wenn er aktiv den Status prüft. Kein Alert, keine Notification.

Bei einem nächtlichen Auto-Deploy (falls je geplant) oder bei Deployment durch
einen anderen Workflow ist das ein Problem.

**Empfehlung:**  
GitHub Actions failure notification via Slack oder GitHub Issues:

```yaml
- name: Notify on failure
  if: failure()
  uses: 8398a7/action-slack@v3
  with:
    status: failure
    text: "🚨 Deploy failed for ${{ github.repository }}"
  env:
    SLACK_WEBHOOK_URL: ${{ secrets.SLACK_WEBHOOK }}
```

---

## 5. Informative Befunde — Best Practices

### 🔵 I-01 — Windsurf-Vendor-Lock-in: keine IDE-Agnostizität

**Befund:**  
Das gesamte Workflow-System ist auf Windsurf-spezifische Features aufgebaut:
- `// turbo` — Windsurf-spezifisch
- MCP-Tool-Aufrufe — Windsurf-spezifisch
- `.windsurf/workflows/` — Windsurf-Verzeichnisstruktur

Ein Wechsel zu Cursor, Copilot Workspace oder einer anderen Lösung macht
alle 22 Repos × N Workflows obsolet.

**Empfehlung:**  
Die inhaltliche Logik (was tut `/ship`) von der Windsurf-Syntax trennen.
Abstrakte Workflow-Beschreibungen in `docs/workflows/` als portable Markdown,
Windsurf-spezifische Syntax nur in `.windsurf/`.

---

### 🔵 I-02 — GitHub Actions Reusable Workflows nicht genutzt

**Befund:**  
GitHub bietet [Reusable Workflows](https://docs.github.com/en/actions/sharing-automations/reusing-workflows)
— ein zentrales `.github/workflows/deploy.yml` in einem Repo das alle anderen aufrufen:

```yaml
# In jedem Repo:
jobs:
  deploy:
    uses: achimdehnert/bfagent/.github/workflows/deploy.yml@main
    with:
      app_name: risk-hub
      health_port: 8095
    secrets: inherit
```

Das löst das Drift-Problem für GitHub-Actions-Workflows fundamental:
eine Änderung im Template-Workflow in bfagent propagiert automatisch zu allen Repos.

**Empfehlung:**  
Reusable Workflows als primäre Strategie für GitHub-seitige Standardisierung einsetzen.
Windsurf-Workflows bleiben für Agent-Interaktion, GitHub Actions Reusable Workflows
für die eigentliche Deploy-Logik.

---

### 🔵 I-03 — Keine `CODEOWNERS`-Strategie

**Befund:**  
Cross-Repo Workflows sollen identisch sein. Wer ist Owner dieser Dateien?
Ohne `CODEOWNERS` kann jeder Contributor die Workflows ändern ohne Review.

**Empfehlung:**

```
# .github/CODEOWNERS
.windsurf/workflows/sync-repos.md   @achimdehnert
.windsurf/workflows/adr-create.md   @achimdehnert
.windsurf/workflows/pr-review.md    @achimdehnert
.windsurf/workflows/ship.md         @achimdehnert
```

---

### 🔵 I-04 — `Typ D: Repos ohne Deployment` fehlt in der Klassifikation

**Befund:**  
Der ADR definiert Typ A (Django), Typ B (Python Library), Typ C (Infra).
Was ist mit Repos wie `nl2cad` (GitHub Pages)? Der ADR erwähnt es als Ausnahme
in §5.2 — aber nie systematisch. Es gibt sicher weitere "statische" oder
"documentation-only" Repos.

**Empfehlung:**  
Typ D: Static/Documentation Repos (GitHub Pages, Jekyll, MkDocs) mit eigenem
Pflicht-Set (kein `/ship`, aber `/run-tests`, `/adr-create`).

---

### 🔵 I-05 — Offene Fragen in §5 sind teilweise entscheidungsreif

**Befund:**  
§5 listet 5 offene Fragen. Mindestens 3 davon sind im ADR-Kontext bereits beantwortbar:

| Frage | Antwort |
|---|---|
| Soll `/ship` vollständig `/deploy` ersetzen? | Ja — `/deploy` deprecaten, Datum setzen |
| Welche Repos brauchen kein `/ship`? | Typ B + Typ D (GitHub Pages) |
| Soll sync_mcp_repos.py nach infra-deploy? | Ja (H-04) |

Offene Fragen in einem "Proposed"-ADR die intern entscheidbar sind → nicht
im ADR lassen, entscheiden und dokumentieren.

---

## 6. Positive Bewertung

| | Bewertung |
|---|---|
| ✅ **Problem klar erkannt** | Der Ist-Stand (§1.1) ist präzise dokumentiert. Die Matrix aller Repos × Workflows ist wertvoll und zeigt das Problem deutlich. |
| ✅ **Repo-Typen-Konzept** | Die Klassifikation in Typ A/B/C ist sinnvoll und skaliert gut für neue Repos. |
| ✅ **Frontmatter-Standard** | Die Idee, Workflows mit maschinenlesbaren Metadaten zu versehen, ist gut. Fehlt nur Enforcement. |
| ✅ **`/sync-repos` als Primitiv** | Zentrales Script + Workflow-Aufruf ist der richtige Ansatz für mcp_config.json-Pflege. |
| ✅ **`/ship` als einheitliches Deploy-Primitiv** | Ein konsistentes Deploy-Kommando über alle Repos ist ein echter Gewinn für den Agent-Kontext. |
| ✅ **Selbstkritische offene Fragen** | §5 zeigt Bewusstsein für die verbleibenden Schwächen — das ist gut für ein Proposed-ADR. |
| ✅ **`// turbo` nur wo sinnvoll** | Nicht alle Schritte sind auto-run — der Ansatz ist prinzipiell richtig (Ausnahme: git push, siehe C-02). |

---

## 7. Priorisierte Umsetzungsempfehlung

| Sprint | Maßnahme | Aufwand |
|---|---|:---:|
| **Sofort (vor Merge)** | C-01: Server-IP aus Frontmatter entfernen → GitHub Secrets<br>C-02: git-push Safety-Gate in /ship Schritt 1 | 1 Tag |
| **Sprint 1** | H-01: Rollback-Schritt in /ship<br>H-05: GitHub Environments aktivieren<br>H-08: Secret-Management-Standard dokumentieren<br>M-04: Frontmatter-Validator Script + pre-commit | 2 Tage |
| **Sprint 2** | H-03: Drift-Detection Script (check_workflow_drift.py)<br>H-04: sync_mcp_repos.py → infra-deploy verschieben<br>M-02: Scheduled Review-Check via GitHub Actions<br>I-02: GitHub Reusable Workflows evaluieren | 2 Tage |
| **Sprint 3** | H-07: /health/ Endpoint-Standard für alle Typ-A Repos<br>M-01: ADR-Cross-Referenz-Register<br>M-05: /deploy Deprecation + Removal Script | 1 Tag |
| **Backlog** | I-01: IDE-Agnostizität<br>I-03: CODEOWNERS<br>I-04: Typ D Definition | 1 Tag |

---

## 8. Gesamtbewertung

Der ADR löst ein echtes Problem mit dem richtigen konzeptuellen Ansatz.
Die **Sicherheitslücke C-01** (Server-IP in Workflow-Dateien die in alle Repos commitet werden)
und das **Deployment-Sicherheitsproblem C-02** (auto-run git push) müssen vor dem Merge
zwingend behoben werden.

Die stärkste architektonische Lücke ist die **fehlende Nutzung von GitHub Reusable Workflows**
(I-02/H-03): Das ist das native GitHub-Tool für exakt dieses Problem — zentrale Workflow-Logik
die in N Repos ohne Drift verwendet wird. Ein ADR über Cross-Repo GitHub-Workflow-Standards
sollte Reusable Workflows als Fundament kennen und adressieren.

Nach den Sprint-1-Fixes ist der ADR eine solide Grundlage für die Plattform.

---

*Review: 04.03.2026 · Scope: ADR-039 v1.0 (Initial Draft) · GitHub Actions Expert Review*
