---
description: Pre-deployment verification checklist
---

1. Check git status:
   // turbo
   git status --short
   If uncommitted changes exist, STOP and list them.

2. Run test suite:
   // turbo
   cd src && python -m pytest --tb=short -q
   If exit code != 0, STOP and report failures.

3. Run linting:
   // turbo
   ruff check src/
   If exit code != 0, STOP and report lint errors.

4. Check for pending migrations:
   // turbo
   cd src && python manage.py showmigrations --list | grep "\[ \]"
   If unapplied migrations found, STOP and ask for confirmation.

5. Check deploy status:
   // turbo
   bf status
   If bf is not installed, SKIP this step and note it in the report.

6. Print deployment readiness report with pass/fail per step.
