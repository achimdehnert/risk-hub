"""Minimal Django settings for django-module-shop tests."""

import os

SECRET_KEY = "test-secret-key"
DEBUG = True

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": ":memory:",
    }
}

INSTALLED_APPS = [
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django_tenancy",
    "django_module_shop",
]

MIDDLEWARE = [
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
]

SESSION_ENGINE = "django.contrib.sessions.backends.db"

ROOT_URLCONF = "tests.urls"

_TEST_DIR = os.path.dirname(os.path.abspath(__file__))

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [os.path.join(_TEST_DIR, "templates")],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

MODULE_SHOP_CATALOGUE = {
    "risk": {
        "name": "Risikobewertung",
        "description": "Test-Modul",
        "included_in_plans": ["professional"],
        "standalone_bookable": True,
        "trial_days": 14,
        "icon": "shield",
    },
    "locked": {
        "name": "Locked Module",
        "description": "Not bookable",
        "included_in_plans": ["enterprise"],
        "standalone_bookable": False,
        "trial_days": 0,
        "icon": "lock",
    },
}

PLAN_MODULES = {
    "starter": ["gbu"],
    "professional": ["risk", "dsb", "gbu"],
}

BILLING_HUB_CHECKOUT_URL = "https://billing.test/checkout"
MODULE_SHOP_PRODUCT_NAME = "risk-hub"
