from unittest.mock import MagicMock, patch

from django.conf import settings
from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from rest_framework import exceptions
from wildfire_assessment.authentication import (
    Auth0JWTAuthentication,
    _decode_jwt,
    _fetch_email_from_auth0,
    _get_auth0_management_token,
    _get_jwks_client,
    _sync_user_from_payload,
)

User = get_user_model()


@override_settings(AUTH0_JWKS_URL="https://auth0.example/jwks.json")
class Auth0AuthenticationTests(TestCase):
    def setUp(self):
        self.auth = Auth0JWTAuthentication()

    @override_settings(AUTH0_JWKS_URL=None)
    def test_get_jwks_client_missing_url(self):
        with self.assertRaises(exceptions.AuthenticationFailed):
            _get_jwks_client()

    @patch("wildfire_assessment.authentication.PyJWKClient")
    def test_get_jwks_client_returns_client(self, mock_jwk_client):
        client = MagicMock()
        mock_jwk_client.return_value = client
        self.assertIs(_get_jwks_client(), client)

    @override_settings(AUTH0_AUDIENCE=None)
    def test_decode_jwt_missing_audience(self):
        with self.assertRaises(exceptions.AuthenticationFailed):
            _decode_jwt("token")

    @override_settings(AUTH0_AUDIENCE="aud", AUTH0_ISSUER="https://issuer/")
    @patch("wildfire_assessment.authentication.jwt.decode")
    @patch("wildfire_assessment.authentication._get_jwks_client")
    def test_decode_jwt_success(self, mock_client, mock_decode):
        mock_key = MagicMock(key="secret")
        mock_client.return_value.get_signing_key_from_jwt.return_value = mock_key
        mock_decode.return_value = {"sub": "user"}
        payload = _decode_jwt("token")
        self.assertEqual(payload["sub"], "user")
        mock_decode.assert_called_once()

    @override_settings(
        AUTH0_DOMAIN="example.auth0.com",
        AUTH0_HTTP_TIMEOUT=1,
    )
    @patch("wildfire_assessment.authentication.requests.get")
    @patch("wildfire_assessment.authentication._get_auth0_management_token")
    def test_fetch_email_from_auth0_success(self, mock_token, mock_get):
        mock_token.return_value = "token"
        mock_response = MagicMock()
        mock_response.json.return_value = {"email": "foo@example.com"}
        mock_get.return_value = mock_response
        self.assertEqual(_fetch_email_from_auth0("auth0|123"), "foo@example.com")

    @patch("wildfire_assessment.authentication._get_auth0_management_token")
    def test_fetch_email_from_auth0_missing_token(self, mock_token):
        mock_token.return_value = None
        self.assertEqual(_fetch_email_from_auth0("auth0|123"), "")

    @override_settings(
        AUTH0_MANAGEMENT_CLIENT_ID="client",
        AUTH0_MANAGEMENT_CLIENT_SECRET="secret",
        AUTH0_MANAGEMENT_AUDIENCE="aud",
        AUTH0_MANAGEMENT_TOKEN_URL="https://auth0/token",
        AUTH0_HTTP_TIMEOUT=1,
    )
    @patch("wildfire_assessment.authentication.requests.post")
    def test_get_auth0_management_token_success(self, mock_post):
        mock_response = MagicMock()
        mock_response.json.return_value = {"access_token": "token"}
        mock_post.return_value = mock_response
        self.assertEqual(_get_auth0_management_token(), "token")

    @override_settings(
        AUTH0_MANAGEMENT_CLIENT_ID=None,
        AUTH0_MANAGEMENT_CLIENT_SECRET=None,
        AUTH0_MANAGEMENT_AUDIENCE=None,
        AUTH0_MANAGEMENT_TOKEN_URL=None,
    )
    def test_get_auth0_management_token_missing_config(self):
        self.assertIsNone(_get_auth0_management_token())

    @patch("wildfire_assessment.authentication._fetch_email_from_auth0")
    def test_sync_user_creates_inactive_user(self, mock_email):
        mock_email.return_value = "new@example.com"
        payload = {"sub": "auth0|1", "given_name": "New", "family_name": "User"}
        with self.assertRaises(exceptions.AuthenticationFailed):
            _sync_user_from_payload(payload)
        self.assertTrue(User.objects.filter(username="new@example.com").exists())

    @patch("wildfire_assessment.authentication._fetch_email_from_auth0")
    def test_sync_user_updates_names(self, mock_email):
        mock_email.return_value = "existing@example.com"
        user = User.objects.create_user(
            username="existing@example.com",
            email="existing@example.com",
            is_active=True,
        )
        payload = {
            "sub": "auth0|2",
            "given_name": "First",
            "family_name": "Last",
        }
        user = _sync_user_from_payload(payload)
        self.assertEqual(user.first_name, "First")
        self.assertEqual(user.last_name, "Last")

    def test_authenticate_missing_header(self):
        request = MagicMock()
        request.META = {}
        self.assertIsNone(self.auth.authenticate(request))

    def test_authenticate_invalid_header(self):
        request = MagicMock()
        request.META = {"HTTP_AUTHORIZATION": b"Basic abc"}
        self.assertIsNone(self.auth.authenticate(request))

    @patch("wildfire_assessment.authentication._decode_jwt")
    @patch("wildfire_assessment.authentication._sync_user_from_payload")
    def test_authenticate_success(self, mock_sync, mock_decode):
        request = MagicMock()
        request.META = {"HTTP_AUTHORIZATION": b"Bearer token"}
        mock_decode.return_value = {"sub": "auth0|123"}
        mock_sync.return_value = User(username="test")
        user, payload = self.auth.authenticate(request)
        self.assertEqual(payload["sub"], "auth0|123")
