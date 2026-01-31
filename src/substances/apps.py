# src/substances/apps.py
"""Django App Configuration für Substances Module."""

from django.apps import AppConfig


class SubstancesConfig(AppConfig):
    """App-Konfiguration für Gefahrstoff-Management."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "substances"
    verbose_name = "Gefahrstoffe & SDS"

    def ready(self):
        """Signal-Handler registrieren."""
        pass
