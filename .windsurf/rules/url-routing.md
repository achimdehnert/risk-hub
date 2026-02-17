---
trigger: glob
globs:
  - "src/*/urls.py"
  - "src/*/html_urls.py"
  - "src/config/urls.py"
---

# URL Routing Conventions (risk-hub — verified)

## Root URL Config
- File: `src/config/urls.py` (`ROOT_URLCONF = "config.urls"`)
- Health checks: `/livez/` (liveness), `/healthz/` (readiness)
- Admin: `/admin/`
- Auth: `/accounts/login/`, `/accounts/logout/` (django.contrib.auth)

## Dual URL Pattern
Some apps have both HTML and API URLs:
- HTML: `path("ex/", include("explosionsschutz.html_urls"))`
- API: `path("api/ex/", include("explosionsschutz.urls"))`
- Django Ninja: `path("api/v1/", api.urls)`

## App URL Registration
- BARE module names (no apps. prefix): `include("risk.urls")`
- reverse() with names: `reverse("risk:risk_list")`

## URL Naming Convention
- List: `<model>_list` | Detail: `<model>_detail`
- Create: `<model>_create` | Edit: `<model>_edit` | Delete: `<model>_delete`
