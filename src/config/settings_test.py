"""
Risk Hub - Test Settings (ADR-057)

Uses PostgreSQL (via DATABASE_URL) because django-tenancy requires
PostgreSQL-specific features (SET enable_... statements).
In CI: DATABASE_URL=postgresql://test:test@localhost:5432/risk_hub_ci
Django will create 'test_risk_hub_ci' automatically (test_ prefix).
"""

import os
from urllib.parse import urlparse

from .settings import *  # noqa: F401,F403

DEBUG = False

_db = urlparse(
    os.environ.get(
        "DATABASE_URL",
        "postgresql://test:test@localhost:5432/risk_hub_ci",
    )
)

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": _db.path.lstrip("/"),
        "USER": _db.username,
        "PASSWORD": _db.password,
        "HOST": _db.hostname,
        "PORT": str(_db.port or 5432),
    }
}

PASSWORD_HASHERS = [
    "django.contrib.auth.hashers.MD5PasswordHasher",
]

EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"

MIGRATION_MODULES = {
    "django_tenancy": "config.test_migrations.django_tenancy",
}

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "common.middleware.RequestContextMiddleware",
    "common.middleware.SubdomainTenantMiddleware",
    "django_tenancy.module_access.ModuleAccessMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

CELERY_TASK_ALWAYS_EAGER = True
CELERY_TASK_EAGER_PROPAGATES = True

# Stripe — dummy values for test/CI (no real API calls)
STRIPE_SECRET_KEY = "sk_test_dummy_ci_key"
STRIPE_PUBLISHABLE_KEY = "pk_test_dummy_ci_key"
STRIPE_WEBHOOK_SECRET = "whsec_dummy_ci_secret"
STRIPE_PRICE_STARTER_MONTHLY = "price_test_starter_monthly"
STRIPE_PRICE_STARTER_ANNUAL = "price_test_starter_annual"
STRIPE_PRICE_PROFESSIONAL_MONTHLY = "price_test_professional_monthly"
STRIPE_PRICE_PROFESSIONAL_ANNUAL = "price_test_professional_annual"
STRIPE_PRICE_BUSINESS_MONTHLY = "price_test_business_monthly"
STRIPE_PRICE_BUSINESS_ANNUAL = "price_test_business_annual"

LOGGING = {
    "version": 1,
    "disable_existing_loggers": True,
    "handlers": {"null": {"class": "logging.NullHandler"}},
    "root": {"handlers": ["null"], "level": "CRITICAL"},
}

# Silence security warnings that only apply to production (SSL, HSTS, cookies).
SILENCED_SYSTEM_CHECKS = [
    "security.W004",  # SECURE_HSTS_SECONDS
    "security.W008",  # SECURE_SSL_REDIRECT
    "security.W009",  # SECRET_KEY strength
    "security.W012",  # SESSION_COOKIE_SECURE
    "security.W016",  # CSRF_COOKIE_SECURE
]
