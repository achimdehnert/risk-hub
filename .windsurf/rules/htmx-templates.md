---
trigger: glob
globs:
  - "**/templates/**"
---

# HTMX Template Conventions

## HTMX Detection (django_htmx installed)
- Check: `if request.htmx:`
- Access: `request.htmx.target`, `request.htmx.trigger`
- Partial: `return render(request, "<app>/partials/<component>.html", ctx)`
- Full page: `return render(request, "<app>/<model>_<action>.html", ctx)`

## Template Locations
- Full pages: `templates/<app>/<model>_<action>.html` (extend base.html)
- Partials: `templates/<app>/partials/<component>.html` (fragments, no extends)
- Shared includes: `templates/includes/`

## HTMX Attributes
- Target: `hx-target="#section-content"`
- Swap: `hx-swap="innerHTML"` (default), `outerHTML` for replace
- Delete: `hx-delete="..." hx-confirm="Wirklich loeschen?"`
- Empty response for delete: view returns `HttpResponse("")`

## Dual URL Pattern
- HTML views: `/<app>/` (templates with HTMX)
- API views: `/api/<app>/` (JSON responses)
- Example: `/ex/` (HTML) vs `/api/ex/` (API) for explosionsschutz
