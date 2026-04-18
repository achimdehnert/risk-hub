# REFLEX Docs Update — Audit Report

**Datum:** 2026-04-18
**Branch:** `main` (HEAD: 4c1d843)
**Scope:** 4 Dateien (3 Rewrites + 1 neu)
**Task-Typ:** Docs-only

## Geänderte Dateien

| Datei | Änderungen | Typ |
|-------|-----------|-----|
| `README.md` | Komplett-Rewrite: 127→172 Zeilen | Rewrite |
| `docs/architecture/ARCHITECTURE.md` | Komplett-Rewrite: 375→242 Zeilen | Rewrite |
| `docs/deployment/DEPLOYMENT.md` | Komplett-Rewrite: 295→225 Zeilen | Rewrite |
| `docs/USER_GUIDE.md` | Neu erstellt: 237 Zeilen | New |

**Gesamt:** 705 Insertions, 626 Deletions

## Was war veraltet?

| Dokument | Problem | Fix |
|----------|---------|-----|
| README.md | Port 8001 (→8090), fehlende Module, `bfagent-core` Imports, `apps/` Prefix | Korrekte 14 Module, Port 8090, HTMX raw headers, iil-Packages |
| ARCHITECTURE.md | `apps/` Verzeichnis (→`src/`), 7 Apps (→26), fehlendes Multi-Tenancy-Flow | Echte Struktur, Layer-Diagramm, Access Control, HTMX-Konvention |
| DEPLOYMENT.md | Terraform/Ansible-basiert, falsche Image-Namen, fehlende ADR-120 | `.ship.conf` SSOT, CI/CD + ship.sh, Cloudflare DNS, Rollback |
| USER_GUIDE.md | Existierte nicht | Komplett neu: alle Module, Rollen, FAQ, API |

## Banned Patterns

| Pattern | Treffer |
|---------|---------|
| `onclick=` | 0 |
| `bg-dark text-light` | 0 |
| `print(` | 0 |
| `except:` | 0 |
| `os.environ` | 0 |

## Verifizierte Fakten in den Docs

| Fakt | Quelle | Korrekt |
|------|--------|---------|
| 14 Module mit URL-Prefixes | `config/urls.py` | ✅ |
| 26 Apps in `src/` | `ls src/` | ✅ |
| HTMX 1.9 raw headers | `requirements.txt` + Code | ✅ |
| Django Ninja `/api/v1/` | `config/api.py` | ✅ |
| Port 8090 | `docker-compose.prod.yml` | ✅ |
| Container: risk-hub-web/worker/db/redis | `docker-compose.prod.yml` | ✅ |
| Image: `ghcr.io/achimdehnert/risk-hub/risk-hub-web` | `.ship.conf` | ✅ |
| Health: `/healthz/` | `reflex.yaml` + `core/healthz.py` | ✅ |
| MODULE_URL_MAP: ex, risk, gbu, dsb | `config/settings.py` | ✅ |
| `Organization.id != Organization.tenant_id` | Known fact | ✅ |

## Bekannte verbleibende Issues (außerhalb Scope)

| Datei | Issue | Priorität |
|-------|-------|-----------|
| `docs/source/` (Sphinx RST) | Veraltet, nicht aktualisiert | Low |
| `docs/stripe-monetarisierung.md` | Nicht geprüft ob aktuell | Low |
| `docs/design/schutzbar-*` | Branding-Dateien, nicht geprüft | Low |

## Fazit

COMPLETE ✅
