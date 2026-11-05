from django.apps import AppConfig


class ContentTypesConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.content_types"

    def ready(self):
        from . import signals  # noqa: F401

