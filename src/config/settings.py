"""Django settings for Risk-Hub."""

import os
from pathlib import Path

import dj_database_url

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = os.getenv("DJANGO_SECRET_KEY", "dev-only-change-in-production")
DEBUG = os.getenv("DJANGO_DEBUG", "0") == "1"
ALLOWED_HOSTS = os.getenv(
    "DJANGO_ALLOWED_HOSTS",
    ".localhost,localhost,127.0.0.1",
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
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django_htmx.middleware.HtmxMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    # Context + Tenancy
    "common.middleware.RequestContextMiddleware",
    "common.middleware.SubdomainTenantMiddleware",
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
    "default": dj_database_url.config(default=os.getenv("DATABASE_URL"))
}

AUTH_USER_MODEL = "identity.User"

STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"

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
TENANT_MODEL = "tenancy.Organization"
TENANT_SLUG_FIELD = "slug"
TENANT_ID_FIELD = "tenant_id"

# CSRF
CSRF_TRUSTED_ORIGINS = [
    o
    for o in os.getenv("CSRF_TRUSTED_ORIGINS", "").split(",")
    if o
]

SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

# Documents / S3
S3_ENDPOINT = os.getenv("S3_ENDPOINT", "")
S3_REGION = os.getenv("S3_REGION", "us-east-1")
S3_ACCESS_KEY = os.getenv("S3_ACCESS_KEY", "")
S3_SECRET_KEY = os.getenv("S3_SECRET_KEY", "")
S3_BUCKET = os.getenv("S3_BUCKET", "documents")
S3_USE_SSL = os.getenv("S3_USE_SSL", "0") == "1"
S3_PUBLIC_BASE_URL = os.getenv("S3_PUBLIC_BASE_URL", "")

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
    "PAGE_SIZE": 50,
    "DEFAULT_FILTER_BACKENDS": [
        "django_filters.rest_framework.DjangoFilterBackend",
        "rest_framework.filters.SearchFilter",
        "rest_framework.filters.OrderingFilter",
    ],
}
