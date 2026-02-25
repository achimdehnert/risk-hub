"""
risk-hub Django Settings
========================

Konfiguration für Enterprise SaaS Risikomanagement Platform.

Umgebungen:
- Development: DEBUG=1, SQLite/Postgres, MinIO
- Staging: DEBUG=0, Postgres mit RLS, Hetzner Object Storage
- Production: DEBUG=0, Postgres mit RLS + Replicas, CDN
"""

import os
from pathlib import Path

import dj_database_url
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Type-safe Settings via Pydantic."""

    # Django Core
    DEBUG: bool = False
    SECRET_KEY: str = "change-me"
    ALLOWED_HOSTS: str = ".localhost,localhost,127.0.0.1"
    LOG_LEVEL: str = "INFO"

    # Database
    DATABASE_URL: str = "postgres://app:app@db:5432/risk_hub"
    DATABASE_RLS_ENABLED: bool = False

    # Redis
    REDIS_URL: str = "redis://redis:6379/0"
    CELERY_BROKER_URL: str = "redis://redis:6379/1"
    CELERY_RESULT_BACKEND: str = "redis://redis:6379/2"

    # Multi-Tenancy
    TENANT_BASE_DOMAIN: str = "localhost"
    TENANT_ALLOW_LOCALHOST: bool = True

    # S3 / Documents
    S3_ENDPOINT: str = ""
    S3_REGION: str = "us-east-1"
    S3_ACCESS_KEY: str = ""
    S3_SECRET_KEY: str = ""
    S3_BUCKET: str = "documents"
    S3_USE_SSL: bool = False
    S3_PUBLIC_BASE_URL: str = ""

    # Security
    CSRF_TRUSTED_ORIGINS: str = ""

    class Config:
        env_prefix = "DJANGO_"
        env_file = ".env"
        extra = "ignore"


# Load settings
env = Settings()

# =============================================================================
# Django Core Settings
# =============================================================================

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = env.SECRET_KEY
DEBUG = env.DEBUG
ALLOWED_HOSTS = [h.strip() for h in env.ALLOWED_HOSTS.split(",") if h.strip()]

ROOT_URLCONF = "config.urls"
WSGI_APPLICATION = "config.wsgi.application"
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# =============================================================================
# Applications
# =============================================================================

INSTALLED_APPS = [
    # Django
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    # Third-party
    "django_htmx",
    "django_extensions",
    "ninja",
    # Core Apps
    "apps.core",
    "apps.tenancy",
    "apps.identity",
    "apps.permissions",
    "apps.audit",
    "apps.outbox",
    # Domain Apps
    "apps.risk",
    "apps.actions",
    "apps.documents",
    "apps.reporting",
]

# =============================================================================
# Middleware
# =============================================================================

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django_htmx.middleware.HtmxMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    # Custom Middleware
    "apps.core.middleware.RequestContextMiddleware",
    "apps.core.middleware.SubdomainTenantMiddleware",
    # Django
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

# =============================================================================
# Database
# =============================================================================

DATABASES = {
    "default": dj_database_url.config(
        default=env.DATABASE_URL,
        conn_max_age=600,
        conn_health_checks=True,
    )
}

# RLS Settings
DATABASE_RLS_ENABLED = env.DATABASE_RLS_ENABLED

# =============================================================================
# Authentication
# =============================================================================

AUTH_USER_MODEL = "identity.User"

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

# =============================================================================
# Templates
# =============================================================================

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                # Custom
                "apps.core.context_processors.tenant_context",
            ],
        },
    },
]

# =============================================================================
# Static & Media
# =============================================================================

STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_DIRS = [BASE_DIR / "static"] if (BASE_DIR / "static").exists() else []

# =============================================================================
# Internationalization
# =============================================================================

LANGUAGE_CODE = "de-de"
TIME_ZONE = "Europe/Berlin"
USE_I18N = True
USE_TZ = True

# =============================================================================
# Multi-Tenancy
# =============================================================================

TENANT_BASE_DOMAIN = env.TENANT_BASE_DOMAIN
TENANT_ALLOW_LOCALHOST = env.TENANT_ALLOW_LOCALHOST

# =============================================================================
# Documents / S3
# =============================================================================

S3_ENDPOINT = env.S3_ENDPOINT
S3_REGION = env.S3_REGION
S3_ACCESS_KEY = env.S3_ACCESS_KEY
S3_SECRET_KEY = env.S3_SECRET_KEY
S3_BUCKET = env.S3_BUCKET
S3_USE_SSL = env.S3_USE_SSL
S3_PUBLIC_BASE_URL = env.S3_PUBLIC_BASE_URL

# =============================================================================
# Celery
# =============================================================================

CELERY_BROKER_URL = env.CELERY_BROKER_URL
CELERY_RESULT_BACKEND = env.CELERY_RESULT_BACKEND
CELERY_TASK_ALWAYS_EAGER = DEBUG  # Sync execution in dev
CELERY_TASK_TRACK_STARTED = True
CELERY_TASK_TIME_LIMIT = 30 * 60  # 30 minutes

# =============================================================================
# Security (Production)
# =============================================================================

if not DEBUG:
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_HSTS_SECONDS = 31536000
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True

CSRF_TRUSTED_ORIGINS = [
    o.strip() for o in env.CSRF_TRUSTED_ORIGINS.split(",") if o.strip()
]

# =============================================================================
# Logging
# =============================================================================

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "verbose": {
            "format": "{levelname} {asctime} {module} {message}",
            "style": "{",
        },
        "json": {
            "()": "apps.core.logging.JsonFormatter",
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "json" if not DEBUG else "verbose",
        },
    },
    "root": {
        "handlers": ["console"],
        "level": env.LOG_LEVEL,
    },
    "loggers": {
        "django": {
            "handlers": ["console"],
            "level": "INFO",
            "propagate": False,
        },
        "apps": {
            "handlers": ["console"],
            "level": "DEBUG" if DEBUG else "INFO",
            "propagate": False,
        },
    },
}
