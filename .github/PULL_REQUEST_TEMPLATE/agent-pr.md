# Agent PR Checkliste (ADR-086)

## Verlinktes Issue

Closes #<!-- Issue-Nummer -->

## Task-Typ

<!-- feature | bugfix | refactor | test | infra | adr -->

## Zusammenfassung

<!-- Was wurde implementiert? Warum? (≤ 500 Zeichen) -->

## Acceptance Criteria

- [ ] Criterion 1
- [ ] Criterion 2

## Scope-Check (ADR-081)

- [ ] Nur Dateien in `affected_paths` geändert
- [ ] Keine `migrations/` automatisch erstellt
- [ ] Keine `.env*`, `config/settings/prod*` geändert
- [ ] Keine Zertifikate / Keys geändert

## Quality Gates

- [ ] `pytest` → 0 Failures
- [ ] `ruff check src/` → 0 Errors
- [ ] Coverage-Delta ≥ 0%
- [ ] `mypy src/` → 0 Errors (wenn konfiguriert)

## Django-Compliance (ADR-022)

- [ ] Views enthalten keine Business-Logik → alles in `services.py`
- [ ] Alle Templates erweitern `base.html`
- [ ] HTMX für dynamische Interaktionen
- [ ] Multi-Tenancy: alle Queries filtern nach `tenant_id`
- [ ] `CHANGELOG.md` unter `[Unreleased]` aktualisiert

## Test-Nachweis

```
# Ausgabe von: pytest tests/MODULE/ -v --tb=short
```
