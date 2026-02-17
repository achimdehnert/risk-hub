---
trigger: glob
globs:
  - "src/*/models.py"
  - "src/*/views.py"
  - "src/*/services.py"
  - "src/*/forms.py"
---

# Django Conventions (risk-hub)

## Models
- Inherit from `django.db.models.Model` (no custom base classes)
- DEFAULT_AUTO_FIELD is BigAutoField — IDs are integers, not UUIDs
- Foreign keys: `on_delete=models.PROTECT` by default
- CRITICAL: Every user-data model MUST have `tenant_id = UUIDField(db_index=True)`
- All queries MUST filter by `tenant_id`

## Views — HTMX Pattern (django_htmx installed)
- Check HTMX: `if request.htmx:`
- Return partial: `return render(request, "<app>/partials/<component>.html", ctx)`
- Access headers: `request.htmx.target`, `request.htmx.trigger`

## Service Layer
- views.py handles HTTP request/response only
- services.py contains business logic
- models.py defines data, not business logic

## App Registration
- Apps use BARE names (no "apps." prefix): e.g., "risk", "documents"
- Source in src/ directory
