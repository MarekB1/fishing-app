from django.apps import AppConfig


class CatchesConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.catches"

    def ready(self):
        """Zaregistruje HEIF podporu pre Pillow a načíta signal handlery."""
        try:
            from pillow_heif import register_heif_opener
            register_heif_opener()
        except ImportError:
            pass

        from . import signals  # noqa
