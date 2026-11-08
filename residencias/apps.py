from django.apps import AppConfig


class ResidenciasConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "residencias"
    verbose_name = "Reparto en residencias"

    def ready(self):
        from . import signals  # noqa: F401
