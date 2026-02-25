---
trigger: glob
globs:
  - "**/urls.py"
  - "config/urls.py"
---

# URL Routing Conventions (risk-hub)

## Root URL Config

- File: `config/urls.py` (`ROOT_URLCONF = "config.urls"`)
- Health checks: `/livez/` (liveness)
- Admin: `/admin/`
- Auth: `/accounts/` (django.contrib.auth)
- API: `/api/v1/` (Django Ninja)

## URL Naming Convention

- HTML views: `/module/` (namespace: `module`)
- API endpoints: `/api/v1/module/` (Django Ninja router)
- List: `<model>_list` | Detail: `<model>_detail`
- Create: `<model>_create` | Edit: `<model>_edit` | Delete: `<model>_delete`
