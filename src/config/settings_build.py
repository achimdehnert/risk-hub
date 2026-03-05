"""Build-safe settings for collectstatic (ADR-083).

Uses SQLite fallback + strips tenant middleware so collectstatic
can run without PostgreSQL or tenant config during Docker build.
"""

from config.settings import *  # noqa: F401, F403

DEBUG = False
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": ":memory:",
    }
}

MIDDLEWARE = [
    m for m in MIDDLEWARE  # noqa: F405
    if "tenancy" not in m.lower() and "tenant" not in m.lower()
]
