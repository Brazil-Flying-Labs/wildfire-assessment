"""Tests for the native session authentication flow."""

from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import override_settings
from django.contrib.auth.tokens import default_token_generator
from django.urls import reverse
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode
from rest_framework import status
from rest_framework.test import APITestCase

from wildfire_assessment.models import UserProfile

User = get_user_model()


class CsrfTokenTests(APITestCase):
    def test_csrf_sets_cookie_and_returns_token(self):
        response = self.client.get(reverse("auth-csrf"))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("csrfToken", response.json())
        self.assertIn("csrftoken", response.cookies)


class RequestAccessTests(APITestCase):
    def test_request_access_creates_inactive_user(self):
        response = self.client.post(
            reverse("auth-request-access"),
            {
                "first_name": "Jane",
                "last_name": "Doe",
                "email": "jane@example.com",
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json(), {"detail": "detail"})

        user = User.objects.get(username="jane@example.com")
        self.assertFalse(user.is_active)
        self.assertFalse(user.has_usable_password())
        self.assertTrue(UserProfile.objects.filter(user=user).exists())

    def test_request_access_uppercase_email_normalized(self):
        self.client.post(
            reverse("auth-request-access"),
            {"email": "Jane@Example.COM"},
            format="json",
        )
        self.assertTrue(User.objects.filter(username="jane@example.com").exists())

    def test_request_access_existing_email_returns_same_generic_response(self):
        User.objects.create_user(
            username="taken@example.com", email="taken@example.com", password="pw"
        )
        response = self.client.post(
            reverse("auth-request-access"),
            {"email": "taken@example.com"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json(), {"detail": "detail"})
        self.assertEqual(User.objects.filter(username="taken@example.com").count(), 1)

    @patch("wildfire_assessment.auth_views.send_mail")
    def test_request_access_notifies_admin_with_admin_link(self, mock_send_mail):
        with override_settings(ADMIN_NOTIFICATION_EMAIL="admin@example.com"):
            response = self.client.post(
                reverse("auth-request-access"),
                {"first_name": "Jane", "last_name": "Doe", "email": "jane@example.com"},
                format="json",
            )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        mock_send_mail.assert_called_once()
        kwargs = mock_send_mail.call_args.kwargs
        self.assertEqual(kwargs["recipient_list"], ["admin@example.com"])
        self.assertIn("jane@example.com", kwargs["message"])
        self.assertIn("/admin/auth/user/?is_active__exact=0", kwargs["message"])

    @patch("wildfire_assessment.auth_views.send_mail")
    def test_request_access_existing_email_does_not_notify_admin(self, mock_send_mail):
        User.objects.create_user(
            username="taken@example.com", email="taken@example.com", password="pw"
        )
        with override_settings(ADMIN_NOTIFICATION_EMAIL="admin@example.com"):
            self.client.post(
                reverse("auth-request-access"),
                {"email": "taken@example.com"},
                format="json",
            )
        mock_send_mail.assert_not_called()

    @patch("wildfire_assessment.auth_views.send_mail")
    def test_request_access_no_admin_email_skips_notification(self, mock_send_mail):
        with override_settings(ADMIN_NOTIFICATION_EMAIL=""):
            response = self.client.post(
                reverse("auth-request-access"),
                {"first_name": "Jane", "last_name": "Doe", "email": "jane@example.com"},
                format="json",
            )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        mock_send_mail.assert_not_called()

    @patch(
        "wildfire_assessment.auth_views.send_mail", side_effect=Exception("smtp down")
    )
    def test_request_access_notification_failure_does_not_break_flow(
        self, mock_send_mail
    ):
        with override_settings(ADMIN_NOTIFICATION_EMAIL="admin@example.com"):
            response = self.client.post(
                reverse("auth-request-access"),
                {"first_name": "Jane", "last_name": "Doe", "email": "jane@example.com"},
                format="json",
            )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json(), {"detail": "detail"})

    def test_request_access_invalid_email_rejected(self):
        response = self.client.post(
            reverse("auth-request-access"), {"email": "not-an-email"}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.json(), {"error": "invalid_email"})


class LoginTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="user@example.com",
            email="user@example.com",
            password="correct-password",
        )

    def test_login_success_starts_session(self):
        response = self.client.post(
            reverse("auth-login"),
            {"email": "User@Example.com", "password": "correct-password"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json()["email"], "user@example.com")
        self.assertIn("_auth_user_id", self.client.session)

    def test_login_wrong_password_rejected(self):
        response = self.client.post(
            reverse("auth-login"),
            {"email": "user@example.com", "password": "wrong"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertEqual(response.json(), {"error": "invalid_credentials"})

    def test_login_inactive_user_rejected(self):
        self.user.is_active = False
        self.user.save(update_fields=["is_active"])
        response = self.client.post(
            reverse("auth-login"),
            {"email": "user@example.com", "password": "correct-password"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(response.json(), {"error": "account_pending"})


class LogoutTests(APITestCase):
    def test_logout_requires_authentication(self):
        response = self.client.post(reverse("auth-logout"))
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_logout_ends_session(self):
        user = User.objects.create_user(username="u@example.com", password="pw")
        self.client.force_authenticate(user=user)
        response = self.client.post(reverse("auth-logout"))
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)


class SetPasswordTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="pending@example.com",
            email="pending@example.com",
            is_active=False,
        )
        self.user.set_unusable_password()
        self.user.save(update_fields=["password"])

    def _payload(self, user, token):
        return {
            "uidb64": urlsafe_base64_encode(force_bytes(user.pk)),
            "token": token,
            "password": "new-password-123",
        }

    def test_set_password_activates_and_sets_password(self):
        token = default_token_generator.make_token(self.user)
        response = self.client.post(
            reverse("auth-set-password"),
            self._payload(self.user, token),
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.user.refresh_from_db()
        self.assertTrue(self.user.is_active)
        self.assertTrue(self.user.check_password("new-password-123"))

    def test_set_password_invalid_token_rejected(self):
        response = self.client.post(
            reverse("auth-set-password"),
            self._payload(self.user, "bad-token"),
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.json(), {"error": "invalid_link"})

    def test_set_password_unknown_uid_rejected(self):
        response = self.client.post(
            reverse("auth-set-password"),
            {
                "uidb64": urlsafe_base64_encode(force_bytes(99999)),
                "token": "any",
                "password": "new-password-123",
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


class PasswordResetRequestTests(APITestCase):
    def test_reset_unknown_email_generic_response_no_email(self):
        with patch("wildfire_assessment.auth_views.send_mail") as mock_mail:
            response = self.client.post(
                reverse("auth-reset-password"),
                {"email": "ghost@example.com"},
                format="json",
            )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        mock_mail.assert_not_called()

    def test_reset_existing_user_sends_email(self):
        user = User.objects.create_user(
            username="real@example.com", email="real@example.com", password="pw"
        )
        with patch("wildfire_assessment.auth_views.send_mail") as mock_mail:
            response = self.client.post(
                reverse("auth-reset-password"),
                {"email": "real@example.com"},
                format="json",
            )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json(), {"detail": "detail"})
        mock_mail.assert_called_once()
        kwargs = mock_mail.call_args.kwargs
        self.assertEqual(kwargs["recipient_list"], [user.email])
        self.assertIn("set-password", kwargs["message"])


class AdminApproveActionTests(APITestCase):
    def test_approve_action_activates_and_emails(self):
        from django.contrib.admin.sites import AdminSite
        from wildfire_assessment.admin import UserAdmin

        user = User.objects.create_user(
            username="waiting@example.com",
            email="waiting@example.com",
            is_active=False,
        )
        user.set_unusable_password()
        user.save(update_fields=["password"])

        site = AdminSite()
        model_admin = UserAdmin(User, site)
        request = self.client.request().wsgi_request
        request.user = User.objects.create_superuser(
            username="admin", email="a@example.com", password="pw"
        )

        with patch("wildfire_assessment.auth_views.send_mail") as mock_mail:
            model_admin.approve_users(request, User.objects.all())

        user.refresh_from_db()
        self.assertTrue(user.is_active)
        mock_mail.assert_called_once()
        kwargs = mock_mail.call_args.kwargs
        self.assertEqual(kwargs["recipient_list"], [user.email])
        self.assertIn("approved", kwargs["subject"])

    def test_approve_action_skips_active_users(self):
        from django.contrib.admin.sites import AdminSite
        from wildfire_assessment.admin import UserAdmin

        active = User.objects.create_user(username="active@example.com", password="pw")
        site = AdminSite()
        model_admin = UserAdmin(User, site)
        request = self.client.request().wsgi_request
        request.user = User.objects.create_superuser(
            username="admin2", email="b@example.com", password="pw"
        )

        with patch("wildfire_assessment.auth_views.send_mail") as mock_mail:
            model_admin.approve_users(request, User.objects.filter(pk=active.pk))

        mock_mail.assert_not_called()
