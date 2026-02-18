from django.apps import AppConfig


class WildfireAssessmentConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "wildfire_assessment"

    def ready(self):
        import wildfire_assessment.signals  # noqa: F401
