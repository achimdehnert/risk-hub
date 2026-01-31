# src/explosionsschutz/tests/conftest.py
"""
Pytest Configuration für Explosionsschutz Tests
"""

import os

import django
import pytest


def pytest_configure():
    """Konfiguriert Django für Tests"""
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
    django.setup()


@pytest.fixture(autouse=True)
def enable_db_access_for_all_tests(db):
    """Aktiviert DB-Zugriff für alle Tests"""
    pass
