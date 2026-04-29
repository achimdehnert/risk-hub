from django.apps import AppConfig


class IntakeConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "intake"
    verbose_name = "Dokument-Intake"

    def ready(self) -> None:
        from . import handlers  # noqa: F401 — registers handlers
