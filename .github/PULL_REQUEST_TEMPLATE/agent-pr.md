# Agent PR Checkliste (ADR-086 + ADR-174)

## Verlinktes Issue

Closes #<!-- Issue-Nummer -->
task_id: <!-- GitHub Issue-Nummer — für Audit-Log -->

## Task-Typ

<!-- feature | bugfix | refactor | test | infra | adr -->

## Zusammenfassung

<!-- Was wurde implementiert? Warum? (≤ 500 Zeichen) -->

## Acceptance Criteria

- [ ] Criterion 1
- [ ] Criterion 2

## Self-Review Gate (Pflicht — /agentic-coding Step 5 · ADR-174)
<!-- CI blockiert Merge wenn ASSUMPTION[unverified] noch im Code -->
- [ ] Tests grün (`python -m pytest`)
- [ ] Ruff clean (`ruff check .`)
- [ ] Acceptance Criteria alle erfüllt
- [ ] ADR-Violations = 0 (`check_violations` ausgeführt)
- [ ] Alle `ASSUMPTION[unverified]` aufgelöst ← CI prüft automatisch
- [ ] Constraint Manifest eingehalten
- [ ] `CHANGELOG.md` unter `[Unreleased]` aktualisiert

## ADR-Impact (Step 3.5 B)

<!-- Welche ADRs wurden berührt? Leer = kein Impact -->
- ADR-XXX: <!-- Beschreibung -->

## Scope-Check (ADR-081)

- [ ] Nur Dateien in `affected_paths` geändert
- [ ] Keine `migrations/` automatisch erstellt
- [ ] Keine `.env*`, `config/settings/prod*` geändert
- [ ] Keine Zertifikate / Keys geändert

## Quality Gates

- [ ] `python -m pytest` → 0 Failures
- [ ] `ruff check src/` → 0 Errors
- [ ] Coverage-Delta ≥ 0%

## Django-Compliance (ADR-022)

- [ ] Views enthalten keine Business-Logik → alles in `services.py`
- [ ] Alle Templates erweitern `base.html`
- [ ] HTMX für dynamische Interaktionen
- [ ] Multi-Tenancy: alle Queries filtern nach `tenant_id`

## Test-Nachweis

```
# Ausgabe von: python -m pytest apps/MODULE/tests/ -v --tb=short
```
