from django.apps import AppConfig


class ExplosionsschutzConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.explosionsschutz"
    label = "explosionsschutz"
    verbose_name = "Explosionsschutz"

    def ready(self):
        # Keine post_save Signals – Business Logic läuft im Service Layer (ADR-008)
        pass
