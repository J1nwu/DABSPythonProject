from django.apps import AppConfig


class BookingConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "booking"

    def ready(self):
        # Import signal handlers
        from . import signals  # noqa
