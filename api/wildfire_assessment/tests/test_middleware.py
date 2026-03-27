from unittest.mock import MagicMock, patch

from django.http import HttpResponseBadRequest
from django.test import TestCase
from wildfire_assessment.middleware import MalformedURLMiddleware


class MalformedURLMiddlewareTests(TestCase):
    def setUp(self):
        self.get_response = MagicMock()
        self.middleware = MalformedURLMiddleware(self.get_response)

    def test_normal_url_passes_through(self):
        request = MagicMock()
        request.get_full_path.return_value = "/api/v1/areas/"
        self.middleware(request)
        self.get_response.assert_called_once_with(request)

    def test_url_with_query_params_passes_through(self):
        request = MagicMock()
        request.get_full_path.return_value = "/api/v1/areas/?page=1&search=test"
        self.middleware(request)
        self.get_response.assert_called_once_with(request)

    @patch("wildfire_assessment.middleware.urlparse", side_effect=ValueError("bad"))
    def test_malformed_url_returns_400(self, mock_urlparse):
        request = MagicMock()
        request.get_full_path.return_value = "/malformed"
        request.path = "/malformed"
        response = self.middleware(request)
        self.assertIsInstance(response, HttpResponseBadRequest)
        self.get_response.assert_not_called()

    @patch("wildfire_assessment.middleware.urlparse", side_effect=ValueError("bad"))
    @patch("wildfire_assessment.middleware.logger")
    def test_malformed_url_logs_warning(self, mock_logger, mock_urlparse):
        request = MagicMock()
        request.get_full_path.return_value = "/exploit"
        request.path = "/exploit"
        self.middleware(request)
        mock_logger.warning.assert_called_once()

    @patch("wildfire_assessment.middleware.urlparse", side_effect=ValueError("bad"))
    def test_long_path_truncated_in_log(self, mock_urlparse):
        request = MagicMock()
        long_path = "/" + "a" * 300
        request.get_full_path.return_value = long_path
        request.path = long_path
        with patch("wildfire_assessment.middleware.logger") as mock_logger:
            self.middleware(request)
            logged_path = mock_logger.warning.call_args[0][1]
            self.assertLessEqual(len(logged_path), 200)
