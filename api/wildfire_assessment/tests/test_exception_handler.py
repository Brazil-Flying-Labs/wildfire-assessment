from unittest.mock import MagicMock, patch

from django.test import TestCase
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from wildfire_assessment.exception_handler import custom_exception_handler


class CustomExceptionHandlerTests(TestCase):
    def _make_context(self):
        request = MagicMock()
        request.method = "POST"
        request.path = "/analysis/"
        request.user = "testuser"
        return {"request": request, "view": None}

    def test_known_drf_exception_passes_through(self):
        exc = ValidationError({"field": ["This field is required."]})
        context = self._make_context()
        response = custom_exception_handler(exc, context)
        self.assertEqual(response.status_code, 400)

    def test_unknown_exception_returns_500(self):
        exc = RuntimeError("something broke")
        context = self._make_context()
        response = custom_exception_handler(exc, context)
        self.assertEqual(response.status_code, 500)
        self.assertEqual(response.data, {"error": "Internal server error."})

    @patch("wildfire_assessment.exception_handler.LOG")
    def test_unknown_exception_logs_with_traceback(self, mock_log):
        exc = RuntimeError("db connection lost")
        context = self._make_context()
        custom_exception_handler(exc, context)
        mock_log.exception.assert_called_once_with(
            "Unhandled %s %s [user=%s]: %s",
            "POST",
            "/analysis/",
            "testuser",
            exc,
        )

    def test_missing_request_in_context(self):
        exc = RuntimeError("boom")
        context = {"request": None, "view": None}
        response = custom_exception_handler(exc, context)
        self.assertEqual(response.status_code, 500)

    def test_known_exception_preserves_response_data(self):
        exc = ValidationError({"name": ["too long"]})
        context = self._make_context()
        response = custom_exception_handler(exc, context)
        self.assertIn("name", response.data)
