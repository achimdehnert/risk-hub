"""Minimal Django settings for django-module-shop tests."""

SECRET_KEY = "test-secret-key"
INSTALLED_APPS = [
    "django.contrib.contenttypes",
    "django.contrib.auth",
    "django_tenancy",
    "django_module_shop",
]
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": ":memory:",
    }
}
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
AUTH_USER_MODEL = "auth.User"

MODULE_SHOP_CATALOGUE = {
    "risk": {
        "name": "Risikobewertung",
        "description": "Gefährdungsbeurteilungen verwalten.",
        "icon": "shield-alert",
        "price_month": 29.0,
        "price_year": 290.0,
        "category": "safety",
        "dependencies": [],
    },
    "dsb": {
        "name": "Datenschutz",
        "description": "DSGVO-konforme Datenschutzverwaltung.",
        "icon": "shield",
        "price_month": 19.0,
        "price_year": 190.0,
        "category": "legal",
        "dependencies": [],
    },
    "ex": {
        "name": "Explosionsschutz",
        "description": "ATEX-konforme Zoneneinteilung und Betriebsmittelprüfung.",
        "icon": "zap",
        "price_month": 39.0,
        "price_year": 390.0,
        "category": "safety",
        "dependencies": [],
    },
}
