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
        - Registriert LLM-Scope für Ex-Dokument Prefill
        """
        try:
            from . import signals  # noqa: F401
        except ImportError:
            pass

        try:
            from fieldprefill.prompts import register_system_prompt
            from explosionsschutz.services.ex_doc_prefill import PREFILL_SCOPE

            register_system_prompt(
                scope=PREFILL_SCOPE,
                prompt=(
                    "Du bist ein Experte für Explosionsschutz und erstellst Explosionsschutzdokumente "
                    "gemäß TRBS 2152, ATEX-Richtlinien und der Betriebssicherheitsverordnung. "
                    "Schreibe fachlich präzise, normkonform und in der Sprache des Dokuments (Deutsch). "
                    "Antworte NUR mit dem Feldinhalt ohne Einleitungen, Erklärungen oder Metakommentare."
                ),
            )
        except ImportError:
            pass
