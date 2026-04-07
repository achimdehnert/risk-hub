# src/substances/apps.py
"""Django App Configuration für Substances Module."""

from django.apps import AppConfig


class SubstancesConfig(AppConfig):
    """App-Konfiguration für Gefahrstoff-Management."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "substances"
    verbose_name = "Gefahrstoffe & SDS"

    def ready(self):
        """Signal-Handler und doc_templates Retrievers registrieren."""
        from doc_template_retrievers import register_all_retrievers

        register_all_retrievers()
