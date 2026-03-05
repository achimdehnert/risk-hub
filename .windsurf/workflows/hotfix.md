---
description: Schneller Produktions-Fix
---

# Hotfix

> Kein Refactoring. Kleinster möglicher Fix.

// turbo
```bash
git log --oneline -10
git checkout main && git pull
git checkout -b hotfix/$(date +%Y%m%d)-BESCHREIBUNG
```

Fix → Regression Test → `pytest src/ -q` → PR (Squash Merge) → `/deploy`
