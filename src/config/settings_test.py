"""
Risk Hub - Test Settings (ADR-057)
"""

from .settings import *  # noqa: F401,F403

DEBUG = False

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": ":memory:",
    }
}

PASSWORD_HASHERS = [
    "django.contrib.auth.hashers.MD5PasswordHasher",
]

EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django_htmx",
    "rest_framework",
    "django_filters",
    "platform_context",
    "django_tenancy",
    "aifw",
    "common",
    "tenancy",
    "identity",
    "permissions",
    "audit",
    "outbox",
    "risk",
    "actions",
    "documents",
    "reporting",
    "explosionsschutz",
    "substances",
    "notifications",
    "dashboard",
    "approvals",
    "ai_analysis",
    "dsb",
    "gbu",
]

MIGRATION_MODULES = {
    "django_tenancy": None,
    "tenancy": None,
    "identity": None,
    "permissions": None,
    "audit": None,
    "outbox": None,
    "risk": None,
    "actions": None,
    "documents": None,
    "reporting": None,
    "explosionsschutz": None,
    "substances": None,
    "notifications": None,
    "dashboard": None,
    "approvals": None,
    "ai_analysis": None,
    "dsb": None,
    "gbu": None,
    "common": None,
    "platform_context": None,
    "aifw": None,
}

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django_htmx.middleware.HtmxMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "common.middleware.RequestContextMiddleware",
    "common.middleware.SubdomainTenantMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

CELERY_TASK_ALWAYS_EAGER = True
CELERY_TASK_EAGER_PROPAGATES = True

LOGGING = {
    "version": 1,
    "disable_existing_loggers": True,
    "handlers": {"null": {"class": "logging.NullHandler"}},
    "root": {"handlers": ["null"], "level": "CRITICAL"},
}

# Silence security warnings that only apply to production (SSL, HSTS, cookies).
# These are configured via env vars in .env.prod, not relevant for CI.
SILENCED_SYSTEM_CHECKS = [
    "security.W004",  # SECURE_HSTS_SECONDS
    "security.W008",  # SECURE_SSL_REDIRECT
    "security.W009",  # SECRET_KEY strength
    "security.W012",  # SESSION_COOKIE_SECURE
    "security.W016",  # CSRF_COOKIE_SECURE
]
