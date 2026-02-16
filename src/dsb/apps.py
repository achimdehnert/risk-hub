"""Django App Configuration für DSB Module."""

from django.apps import AppConfig


class DsbConfig(AppConfig):
    """App-Konfiguration für Datenschutzbeauftragter-Modul."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "dsb"
    verbose_name = "Datenschutzbeauftragter"
