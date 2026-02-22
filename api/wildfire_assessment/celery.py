import os

from celery import Celery
from celery.signals import setup_logging

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "api.settings")

app = Celery("wildfire_assessment")
app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks()


@setup_logging.connect
def preserve_otel_logging(**kwargs):
    """Prevent Celery from resetting logging handlers.

    By default Celery clears all root-logger handlers during worker init,
    which removes the OpenTelemetry LoggingHandler added by
    ``opentelemetry-instrument``.  Connecting to this signal with a no-op
    tells Celery to leave the logging configuration alone.
    """
