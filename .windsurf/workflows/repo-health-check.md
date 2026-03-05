---
description: Quality Gate
---

# Repo Health Check

```bash
for f in Makefile docker-compose.prod.yml .env.example requirements.txt; do
  [ -e "$f" ] && echo OK || echo "MISSING: $f"
done
python3 ~/github/platform/tools/repo_health_check.py --profile django-app --path .
```

- [ ] CI: Tests vor Build+Deploy, `/livez/`, pytest grün
