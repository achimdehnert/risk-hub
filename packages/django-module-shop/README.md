# django-module-shop

Flexible module booking and configuration for multi-tenant Django apps.

## Features

- **Module Catalogue** — define bookable modules via `settings.MODULE_SHOP_CATALOGUE` (no DB model needed)
- **Service Layer** — `activate_module()`, `deactivate_module()`, `apply_module_set()` 
- **HTMX Configurator** — toggle-based UI, saves with one POST
- **JSON API** — `/modules/status/`, `/modules/apply/`, `/modules/toggle/`
- **Stripe-ready** — `stripe_price_id_month/year` fields on each module definition

## Installation

```python
# settings.py
INSTALLED_APPS = [
    ...
    "django_tenancy",
    "django_module_shop",
]

MODULE_SHOP_CATALOGUE = {
    "risk": {
        "name": "Risikobewertung",
        "description": "Gefährdungsbeurteilungen und Maßnahmenverwaltung.",
        "icon": "shield-alert",
        "price_month": 29.0,
        "price_year": 290.0,
        "stripe_price_id_month": "price_xxx",
        "stripe_price_id_year": "price_yyy",
        "category": "safety",
        "dependencies": [],
    },
    "dsb": {
        "name": "Datenschutz",
        "description": "DSGVO-konforme Verwaltung.",
        "icon": "shield",
        "price_month": 19.0,
        "price_year": 190.0,
        "category": "legal",
        "dependencies": [],
    },
}
```

```python
# urls.py
from django.urls import include, path

urlpatterns = [
    path("billing/modules/", include("django_module_shop.urls")),
]
```

## URLs

| URL | View | Beschreibung |
|-----|------|--------------|
| `GET /billing/modules/` | `ModuleConfiguratorView` | Konfigurator-Seite |
| `POST /billing/modules/toggle/` | `ModuleToggleView` | Einzelnes Modul an/aus (HTMX) |
| `POST /billing/modules/apply/` | `ModuleApplyView` | Komplette Konfiguration speichern |
| `GET /billing/modules/status/` | `ModuleStatusView` | JSON: aktive Module |

## Service API

```python
from django_module_shop.services import (
    get_active_modules,    # → set[str]
    activate_module,       # (org, "risk") → ModuleSubscription
    deactivate_module,     # (org, "risk") → bool
    apply_module_set,      # (org, {"risk", "dsb"}) → {"activated": [...], "deactivated": [...]}
)
```

## Templates

Override in your project's `templates/django_module_shop/` directory:

- `configurator.html` — full page
- `partials/module_card.html` — single module card (HTMX swap target)

## Wiederverwendung (nl2cad, risk-hub, ...)

Jedes Projekt definiert seinen eigenen `MODULE_SHOP_CATALOGUE` in `settings.py`.
Die Service-Funktionen und Views sind generisch — kein app-spezifischer Code im Package.
