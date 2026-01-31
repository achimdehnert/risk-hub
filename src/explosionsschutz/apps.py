# src/explosionsschutz/apps.py
"""
Django App-Konfiguration für Explosionsschutz-Modul
"""

from django.apps import AppConfig


class ExplosionsschutzConfig(AppConfig):
    """
    Konfiguration der Explosionsschutz-App.
    
    Features:
    - Multi-Tenancy via tenant_id
    - Audit-Trail Integration
    - Hybrid-Isolation für Stammdaten
    """
    
    default_auto_field = "django.db.models.BigAutoField"
    name = "explosionsschutz"
    verbose_name = "Explosionsschutz"
    verbose_name_plural = "Explosionsschutz"
    
    def ready(self):
        """
        Wird beim App-Start aufgerufen.
        
        - Registriert Signals
        - Importiert Checks
        """
        try:
            from . import signals  # noqa: F401
        except ImportError:
            pass
