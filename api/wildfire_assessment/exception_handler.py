"""Custom DRF exception handler that logs unhandled errors with full tracebacks."""

import logging

from rest_framework.response import Response
from rest_framework.views import exception_handler as drf_exception_handler

LOG = logging.getLogger(__name__)


def custom_exception_handler(exc, context):
    """Handle exceptions raised in DRF views.

    Known DRF exceptions (validation, auth, 404, etc.) are handled normally.
    Unknown exceptions are logged with a full traceback and return a 500.
    """
    response = drf_exception_handler(exc, context)
    if response is not None:
        return response

    request = context.get("request")
    method = getattr(request, "method", "?")
    path = getattr(request, "path", "?")
    user = getattr(request, "user", None)

    LOG.exception(
        "Unhandled %s %s [user=%s]: %s",
        method,
        path,
        user,
        exc,
    )

    return Response(
        {"error": "Internal server error."},
        status=500,
    )
