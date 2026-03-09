"""Build-safe settings for collectstatic (ADR-083).

Uses SQLite fallback + strips tenant middleware so collectstatic
can run without PostgreSQL or tenant config during Docker build.
"""

import importlib.util

from config.settings import *  # noqa: F401, F403

DEBUG = False
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": ":memory:",
    }
}

MIDDLEWARE = [
    m
    for m in MIDDLEWARE  # noqa: F405
    if "tenancy" not in m.lower() and "tenant" not in m.lower()
]

# Remove optional private packages if not installed (build without PROJECT_PAT)
_OPTIONAL_APPS = ["platform_context", "django_module_shop", "aifw"]
INSTALLED_APPS = [  # noqa: F405
    app
    for app in INSTALLED_APPS  # noqa: F405
    if app not in _OPTIONAL_APPS or importlib.util.find_spec(app.replace("-", "_")) is not None
]
