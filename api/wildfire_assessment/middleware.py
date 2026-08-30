import logging
from urllib.parse import urlparse

from django.http import HttpResponseBadRequest

logger = logging.getLogger("django.security")


class MalformedURLMiddleware:
    """Reject requests with malformed URLs before they reach the rest of the stack.

    Scanners/bots send garbage URLs (e.g. Struts OGNL injection payloads) that
    cause Python 3.13's stricter urlparse to raise ValueError, which crashes
    middlewares further down the chain and produces noisy 500 errors. This
    middleware catches those early and returns a clean 400.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        try:
            urlparse(request.get_full_path())
        except ValueError:
            logger.warning("Rejected malformed URL: %s", request.path[:200])
            return HttpResponseBadRequest()

        return self.get_response(request)
