---
description: Scaffold a new Django app with Platform conventions (risk-hub)
---

Inputs: App name (snake_case), brief description.

NOTE: risk-hub uses BARE module names (no "apps." prefix) in src/ directory.

1. Check if app already exists:
   // turbo
   ls src/{app_name}/ 2>/dev/null
   If directory exists, STOP and report: "App already exists."

2. Create directory structure:
   mkdir -p src/{app_name}/tests
   mkdir -p src/templates/{app_name}/partials
   touch src/{app_name}/__init__.py
   touch src/{app_name}/models.py
   touch src/{app_name}/views.py
   touch src/{app_name}/urls.py
   touch src/{app_name}/html_urls.py
   touch src/{app_name}/forms.py
   touch src/{app_name}/admin.py
   touch src/{app_name}/services.py
   touch src/{app_name}/tests/__init__.py

3. Create apps.py with `default_auto_field = "django.db.models.BigAutoField"`
   and `name = "{app_name}"` (NO "apps." prefix)

4. Create urls.py with `app_name = "{app_name}"` and empty urlpatterns

5. Register in `src/config/settings.py` INSTALLED_APPS:
   Add `"{app_name}"` ONLY IF not already present in the list.

6. Register in `src/config/urls.py`:
   Add `path("{app_name}/", include("{app_name}.urls"))`
   ONLY IF not already present.

7. Create initial migration:
   cd src && python manage.py makemigrations {app_name}

8. Verify:
   // turbo
   cd src && python manage.py check
   If exit code != 0, report the error.
