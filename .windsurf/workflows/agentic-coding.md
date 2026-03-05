---
description: Agentic Coding Workflow
---

# Agentic Coding

## Governance (bei moderate+): `/governance-check`

## Ausführung
1. Service Layer: views → services → models
2. Tests: `test_should_*`
3. `ruff check . --fix && pytest src/ -q`

## PR
```bash
git checkout -b feat/ISSUE-beschreibung
git commit -m "feat(scope): desc\n\nCloses #ISSUE"
```
