---
trigger: glob
globs:
  - "**/models.py"
  - "**/views.py"
  - "**/services.py"
  - "**/forms.py"
---

# Django Conventions (risk-hub)

## Models

- Inherit from `django.db.models.Model` (no custom base classes)
- DEFAULT_AUTO_FIELD is BigAutoField — IDs are integers, not UUIDs
- Foreign keys: `on_delete=models.PROTECT` by default
- Every user-data model MUST have `tenant_id = UUIDField(db_index=True)`

## Views — HTMX Pattern

- Check HTMX: `if request.headers.get("HX-Request"):`
- Return partial: `return render(request, "<app>/partials/<component>.html", ctx)`
- Full page: `return render(request, "<app>/<model>_<action>.html", ctx)`

## Service Layer

- views.py handles HTTP request/response only
- services.py contains business logic
- models.py defines data, not business logic

## API (Django Ninja)

- Framework: Django Ninja (NOT DRF) at `/api/v1/`
- Auth: `ApiKeyAuth` (Bearer token via `identity.ApiKey` model)
- Routers: risk_router (`/risk`), actions_router (`/actions`), documents_router (`/documents`)
