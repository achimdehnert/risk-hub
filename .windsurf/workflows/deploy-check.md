---
description: Pre-deployment verification checklist
---

# Deploy Check (risk-hub)

## Steps

1. Verify git status is clean: `git status`
2. Run tests: `cd src && pytest`
3. Check for pending migrations: `python manage.py showmigrations --plan | grep '\[ \]'`
4. Verify Docker builds: `docker build -f docker/app/Dockerfile -t risk-hub-test .`
5. Check container health on server:

```bash
ssh root@88.198.191.108 'docker ps --filter name=risk_hub --format "{{.Names}} {{.Status}}"'
```
