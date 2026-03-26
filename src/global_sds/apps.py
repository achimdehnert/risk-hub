# src/global_sds/apps.py
"""Django App Configuration für Global SDS Library (ADR-012)."""

from django.apps import AppConfig


class GlobalSdsConfig(AppConfig):
    """Globale Gefahrstoff-Stammdaten — tenant-übergreifend."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "global_sds"
    verbose_name = "Globale SDS-Bibliothek"
