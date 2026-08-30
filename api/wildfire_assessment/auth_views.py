"""Native authentication endpoints (session-based).

Flow: request access (public) -> admin approval -> first-password e-mail
(single-use link) -> set password -> login with e-mail and password.
Password reset reuses the same single-use link mechanism.
"""

import logging

from django.conf import settings
from django.contrib.auth import authenticate, get_user_model, login, logout
from django.contrib.auth.tokens import default_token_generator
from django.core.mail import send_mail
from django.core.validators import validate_email
from django.core.exceptions import ValidationError
from django.middleware.csrf import get_token
from django.utils.encoding import force_bytes, force_str
from django.utils.http import urlsafe_base64_decode, urlsafe_base64_encode
from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.throttling import AnonRateThrottle
from rest_framework.views import APIView

User = get_user_model()

LOG = logging.getLogger(__name__)


class AuthThrottle(AnonRateThrottle):
    """IP-based rate limit shared by all public auth endpoints."""

    scope = "auth"


def _normalize_email(email):
    return email.strip().lower() if email else ""


def _generic_success_response(detail_key="detail"):
    """Public endpoints never reveal whether an e-mail exists."""
    return Response({"detail": detail_key})


def notify_admin_new_request(request, user):
    """E-mail the administrator about a new access request.

    Only sent for newly created users; the e-mail carries a direct link
    to the inactive-users list in the Django Admin.
    """
    admin_email = getattr(settings, "ADMIN_NOTIFICATION_EMAIL", "")
    if not admin_email:
        return
    link = request.build_absolute_uri("/admin/auth/user/?is_active__exact=0")
    send_mail(
        subject="Wildfire Assessment - New access request",
        message=(
            f"A new access request was submitted.\n\n"
            f"Name: {user.first_name} {user.last_name}\n"
            f"E-mail: {user.email}\n\n"
            f"Approve it in the Django Admin:\n{link}"
        ),
        from_email=None,
        recipient_list=[admin_email],
    )


def send_set_password_email(user, first_access):
    """Send the single-use set-password link (first access or reset)."""
    uidb64 = urlsafe_base64_encode(force_bytes(user.pk))
    token = default_token_generator.make_token(user)
    link = f"{settings.UI_BASE_URL}/set-password/{uidb64}/{token}/"

    if first_access:
        subject = "Wildfire Assessment - Account approved"
        intro_en = "Your access was approved."
        intro_pt = "Seu acesso foi aprovado."
    else:
        subject = "Wildfire Assessment - Password reset"
        intro_en = "You requested a password reset."
        intro_pt = "Você solicitou a redefinição de senha."

    body = (
        f"{intro_en} / {intro_pt}\n\n"
        f"Set your password / Defina sua senha:\n{link}\n\n"
        "This link expires in 24 hours and can only be used once. / "
        "Este link expira em 24 horas e só pode ser usado uma vez."
    )
    send_mail(
        subject=subject, message=body, from_email=None, recipient_list=[user.email]
    )


class CsrfTokenView(APIView):
    """Set the CSRF cookie so the UI can read the token for unsafe methods."""

    permission_classes = [permissions.AllowAny]

    def get(self, request):
        return Response({"csrfToken": get_token(request)})


class RequestAccessView(APIView):
    """Public: create an inactive account awaiting admin approval.

    Always returns a generic response — never reveals whether the e-mail
    already exists.
    """

    permission_classes = [permissions.AllowAny]
    throttle_classes = [AuthThrottle]

    def post(self, request):
        email = _normalize_email(request.data.get("email", ""))
        try:
            validate_email(email)
        except ValidationError:
            return Response(
                {"error": "invalid_email"}, status=status.HTTP_400_BAD_REQUEST
            )

        first_name = (request.data.get("first_name") or "").strip()[:150]
        last_name = (request.data.get("last_name") or "").strip()[:150]

        user = User.objects.filter(username=email).first()
        if user is None:
            user = User.objects.create_user(
                username=email,
                email=email,
                first_name=first_name,
                last_name=last_name,
                is_active=False,
            )
            user.set_unusable_password()
            user.save(update_fields=["password"])
            LOG.info("Access requested for %s (user %s)", email, user.pk)
            try:
                notify_admin_new_request(request, user)
            except Exception:  # notification must never break the flow
                LOG.exception(
                    "Failed to notify the administrator about user %s", user.pk
                )

        return _generic_success_response()


class LoginView(APIView):
    """Public: authenticate with e-mail (normalized) and password."""

    permission_classes = [permissions.AllowAny]
    throttle_classes = [AuthThrottle]

    def post(self, request):
        email = _normalize_email(request.data.get("email", ""))
        password = request.data.get("password", "")

        # ModelBackend refuses inactive users, so distinguish "awaiting
        # approval" from wrong credentials without revealing e-mail state.
        user = authenticate(request, username=email, password=password)
        if user is None:
            if User.objects.filter(username=email, is_active=False).exists():
                return Response(
                    {"error": "account_pending"},
                    status=status.HTTP_403_FORBIDDEN,
                )
            return Response(
                {"error": "invalid_credentials"},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        login(request, user)
        return Response(
            {
                "email": user.email,
                "first_name": user.first_name,
                "last_name": user.last_name,
            }
        )


class LogoutView(APIView):
    """Terminate the current session."""

    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        logout(request)
        return Response(status=status.HTTP_204_NO_CONTENT)


class SetPasswordView(APIView):
    """Public: set a password via the single-use link (first access or reset).

    Accepts uidb64/token in the body (the UI receives them from the URL).
    """

    permission_classes = [permissions.AllowAny]
    throttle_classes = [AuthThrottle]

    def post(self, request):
        uidb64 = request.data.get("uidb64", "")
        token = request.data.get("token", "")
        password = request.data.get("password", "")

        try:
            uid = force_str(urlsafe_base64_decode(uidb64))
            user = User.objects.get(pk=uid)
        except (TypeError, ValueError, OverflowError, User.DoesNotExist):
            user = None

        if user is None or not default_token_generator.check_token(user, token):
            return Response(
                {"error": "invalid_link"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        user.set_password(password)
        was_inactive = not user.is_active
        user.is_active = True
        user.save(update_fields=["password", "is_active"])
        LOG.info("Password set for user %s (activated=%s)", user.pk, was_inactive)
        return _generic_success_response()


class PasswordResetRequestView(APIView):
    """Public: request a password reset link. Generic response always."""

    permission_classes = [permissions.AllowAny]
    throttle_classes = [AuthThrottle]

    def post(self, request):
        email = _normalize_email(request.data.get("email", ""))
        user = User.objects.filter(username=email, is_active=True).first()
        if user is not None:
            send_set_password_email(user, first_access=False)
            LOG.info("Password reset requested for %s", email)
        return _generic_success_response()
