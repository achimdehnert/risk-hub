---
trigger: always_on
---

# Platform Principles (all repos)

## Settings Structure (verified)
- Settings: `config.settings.base` (split: base/development/production/test)
- Root URL conf: `config.urls`
- WSGI: `config.wsgi.application`
- DEFAULT_AUTO_FIELD: `django.db.models.BigAutoField` (NOT UUIDs)
- Templates: `templates/` at project root (NOT per-app)

## Architecture Rules
- Service Layer: views.py → services.py → models.py
- Views handle HTTP only, services contain business logic
- Component Pattern (ADR-041): reusable UI blocks as Components
  - `apps/<app>/components/<name>.py` with `get_context()` as single data source
  - `apps/<app>/templatetags/<app>_components.py` for inclusion tags
  - `templates/<app>/components/_<name>.html` (underscore prefix)
  - 3 access paths: inclusion tag, HTMX fragment, template include
  - Max 3 variants: default, compact, card
- Zero Breaking Changes: deprecate first, remove after 2 releases
- Spec vs. Derived: computed values are @property, never DB columns

## Naming Conventions
- Apps: `apps.<app_name>` (snake_case)
- URLs: `path("<prefix>/", include("apps.<app>.urls", namespace="<app>"))`
- Templates: `templates/<app>/<model>_<action>.html`
- Partials: `templates/<app>/partials/<component>.html`
- Components: `templates/<app>/components/_<name>.html` (underscore!)
- Component Tags: `{% load <app>_components %}` → `{% <name> obj %}`
- Tests: `test_should_<expected_behavior>`

## Infrastructure
- Server: 88.198.191.108
- Registry: `ghcr.io/achimdehnert/<repo>:latest`
- Compose: `docker-compose.prod.yml` at project root
- env_file: `.env.prod` (NEVER `${VAR}` interpolation in compose `environment:` section)
