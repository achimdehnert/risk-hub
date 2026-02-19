"""Django settings for Risk-Hub."""

import os
from pathlib import Path

import dj_database_url

from config.secrets import read_secret

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = read_secret("DJANGO_SECRET_KEY", default="dev-only-change-in-production")
DEBUG = read_secret("DJANGO_DEBUG", default="0") == "1"
ALLOWED_HOSTS = read_secret(
    "DJANGO_ALLOWED_HOSTS",
    default=".localhost,localhost,127.0.0.1",
).split(",")

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
    # Platform shared packages
    "platform_context",
    "django_tenancy",
    # Risk-Hub apps
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
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django_htmx.middleware.HtmxMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    # Context + Tenancy
    "common.middleware.RequestContextMiddleware",
    "common.middleware.SubdomainTenantMiddleware",
    "django_tenancy.module_access.ModuleAccessMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "common.context_processors.tenant_context",
            ],
        },
    }
]

WSGI_APPLICATION = "config.wsgi.application"

DATABASES = {
    "default": dj_database_url.config(default=read_secret("DATABASE_URL"))
}

AUTH_USER_MODEL = "identity.User"

STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_STORAGE = (
    "whitenoise.storage.CompressedManifestStaticFilesStorage"
)

MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"
FILE_UPLOAD_MAX_MEMORY_SIZE = 20 * 1024 * 1024  # 20 MB
DATA_UPLOAD_MAX_MEMORY_SIZE = 20 * 1024 * 1024

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# Tenancy
TENANT_BASE_DOMAINS = [
    d.strip()
    for d in os.getenv("TENANT_BASE_DOMAINS", "").split(",")
    if d.strip()
]
TENANT_BASE_DOMAIN = (
    TENANT_BASE_DOMAINS[0]
    if TENANT_BASE_DOMAINS
    else os.getenv("TENANT_BASE_DOMAIN", "localhost")
)
TENANT_ALLOW_LOCALHOST = os.getenv("TENANT_ALLOW_LOCALHOST", "1") == "1"
TENANT_RESERVED_SUBDOMAINS = [
    s.strip().lower()
    for s in os.getenv("TENANT_RESERVED_SUBDOMAINS", "www").split(",")
    if s.strip()
]
TENANT_MODEL = "django_tenancy.Organization"
TENANT_SLUG_FIELD = "slug"
TENANT_ID_FIELD = "tenant_id"

# Module-level access control (ADR-035)
MODULE_URL_MAP = {
    "/risk/": "risk",
    "/dsb/": "dsb",
    "/ex/": "ex",
    "/api/ex/": "ex",
    "/substances/": "ex",
    "/api/substances/": "ex",
}

# CSRF
CSRF_TRUSTED_ORIGINS = [
    o
    for o in read_secret("CSRF_TRUSTED_ORIGINS", default="").split(",")
    if o
]

SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

LOGIN_URL = "/accounts/login/"
LOGIN_REDIRECT_URL = "/dashboard/"
LOGOUT_REDIRECT_URL = "/"

# Documents / S3
S3_ENDPOINT = read_secret("S3_ENDPOINT", default="")
S3_REGION = read_secret("S3_REGION", default="us-east-1")
S3_ACCESS_KEY = read_secret("S3_ACCESS_KEY", default="")
S3_SECRET_KEY = read_secret("S3_SECRET_KEY", default="")
S3_BUCKET = read_secret("S3_BUCKET", default="documents")
S3_USE_SSL = read_secret("S3_USE_SSL", default="0") == "1"
S3_PUBLIC_BASE_URL = read_secret("S3_PUBLIC_BASE_URL", default="")

# LLM Gateway
LLM_GATEWAY_URL = os.getenv("LLM_GATEWAY_URL", "http://localhost:8100")
LLM_GATEWAY_TIMEOUT = float(os.getenv("LLM_GATEWAY_TIMEOUT", "120"))

# Django REST Framework
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework.authentication.SessionAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticated",
    ],
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
    "PAGE_SIZE": 25,
    "DEFAULT_FILTER_BACKENDS": [
        "django_filters.rest_framework.DjangoFilterBackend",
        "rest_framework.filters.SearchFilter",
        "rest_framework.filters.OrderingFilter",
    ],
}

# Celery
CELERY_BROKER_URL = os.getenv("REDIS_URL", "redis://redis:6379/0")
CELERY_RESULT_BACKEND = CELERY_BROKER_URL
CELERY_ACCEPT_CONTENT = ["json"]
CELERY_TASK_SERIALIZER = "json"
CELERY_RESULT_SERIALIZER = "json"

# Email (default: console backend for dev)
EMAIL_BACKEND = os.getenv(
    "EMAIL_BACKEND",
    "django.core.mail.backends.console.EmailBackend",
)
EMAIL_HOST = os.getenv("EMAIL_HOST", "")
EMAIL_PORT = int(os.getenv("EMAIL_PORT", "587"))
EMAIL_HOST_USER = os.getenv("EMAIL_HOST_USER", "")
EMAIL_HOST_PASSWORD = read_secret("EMAIL_HOST_PASSWORD", default="")
EMAIL_USE_TLS = os.getenv("EMAIL_USE_TLS", "1") == "1"
DEFAULT_FROM_EMAIL = os.getenv(
    "DEFAULT_FROM_EMAIL", "noreply@schutztat.de"
)
