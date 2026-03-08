# tests/conftest.py — ADR-058
import os

import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings_test")
django.setup()
