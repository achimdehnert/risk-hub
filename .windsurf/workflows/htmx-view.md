---
description: Create an HTMX view with template, partial, and URL registration
---

Inputs: App name, model name, action (list/detail/create/edit/delete).

1. Check that the app exists:
   // turbo
   ls src/{app_name}/views.py
   If not found, STOP and suggest running /new-django-app first.

2. Create or update the view function in `src/{app_name}/views.py`:
   - For list/detail/create/edit: standard view with form handling
   - HTMX detection: `if request.htmx:`
     (risk-hub uses django_htmx)
   - HTMX: `return render(request, "{app_name}/partials/{model}_{action}.html", ctx)`
   - Non-HTMX: `return render(request, "{app_name}/{model}_{action}.html", ctx)`
   - Add `@login_required` decorator
   - CRITICAL: All queries must filter by `request.tenant_id`

3. Create the full-page template:
   `src/templates/{app_name}/{model}_{action}.html`
   Must extend base.html with `{% extends "base.html" %}`
   Include the partial via `{% include "{app_name}/partials/{model}_{action}.html" %}`

4. Create the partial template:
   `src/templates/{app_name}/partials/{model}_{action}.html`
   Standalone HTML fragment (no extends, no base)

5. Register URL in `src/{app_name}/html_urls.py` (for HTML views):
   Add path for the view ONLY IF not already registered.
   Follow naming: `name="{model}_{action}"`

6. Verify:
   // turbo
   cd src && python manage.py check
   If exit code != 0, report the error.

7. Print summary: "Created: view, template, partial, URL for {app_name}.{model}_{action}"
