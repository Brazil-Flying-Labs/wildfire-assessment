"""Custom DRF authentication backend that validates Auth0 JWT access tokens."""

import logging
from functools import lru_cache
from typing import Optional
from urllib.parse import quote

import jwt
import requests
from django.conf import settings
from django.contrib.auth import get_user_model
from jwt import PyJWKClient
from jwt.exceptions import InvalidTokenError
from requests import RequestException
from rest_framework import authentication, exceptions
from rest_framework.authentication import get_authorization_header

UserModel = get_user_model()
LOG = logging.getLogger(__name__)


@lru_cache(maxsize=1)
def _get_jwks_client():
    jwks_url = getattr(settings, "AUTH0_JWKS_URL", None)
    if not jwks_url:
        raise exceptions.AuthenticationFailed("Auth0 JWKS URL is not configured")
    return PyJWKClient(jwks_url)


def _decode_jwt(token: str) -> dict:
    if not getattr(settings, "AUTH0_AUDIENCE", None):
        raise exceptions.AuthenticationFailed("Auth0 audience is not configured")

    signing_key = _get_jwks_client().get_signing_key_from_jwt(token)
    return jwt.decode(
        token,
        signing_key.key,
        algorithms=["RS256"],
        audience=settings.AUTH0_AUDIENCE,
        issuer=getattr(settings, "AUTH0_ISSUER", None),
    )


def _get_email_from_payload(payload: dict) -> str:
    """Return the best email value embedded in the JWT payload."""

    email = payload.get("email")
    if email:
        return email

    custom_claim = getattr(settings, "AUTH0_EMAIL_CLAIM", None)
    if custom_claim:
        claim_value = payload.get(custom_claim)
        if isinstance(claim_value, str):
            return claim_value

    return ""


def _fetch_email_from_auth0(subject: str) -> str:
    """Fetch the user's email from the Auth0 Management API using the subject."""

    token = _get_auth0_management_token()
    if not token:
        return ""

    timeout = getattr(settings, "AUTH0_HTTP_TIMEOUT", 5)
    user_url = f"https://{settings.AUTH0_DOMAIN}/api/v2/users/{quote(subject, safe='')}"

    try:
        response = requests.get(
            user_url,
            headers={"Authorization": f"Bearer {token}"},
            timeout=timeout,
        )
        response.raise_for_status()
    except RequestException as exc:
        LOG.warning("Failed to fetch Auth0 profile for %s: %s", subject, exc)
        return ""

    return response.json().get("email", "")


def _get_auth0_management_token() -> Optional[str]:
    """Return a short-lived Auth0 Management API token."""

    client_id = getattr(settings, "AUTH0_MANAGEMENT_CLIENT_ID", None)
    client_secret = getattr(settings, "AUTH0_MANAGEMENT_CLIENT_SECRET", None)
    audience = getattr(settings, "AUTH0_MANAGEMENT_AUDIENCE", None)
    token_url = getattr(settings, "AUTH0_MANAGEMENT_TOKEN_URL", None)

    if not all([client_id, client_secret, audience, token_url]):
        return None

    timeout = getattr(settings, "AUTH0_HTTP_TIMEOUT", 5)

    payload = {
        "grant_type": "client_credentials",
        "client_id": client_id,
        "client_secret": client_secret,
        "audience": audience,
    }

    try:
        response = requests.post(token_url, json=payload, timeout=timeout)
        response.raise_for_status()
    except RequestException as exc:
        LOG.warning("Failed to retrieve Auth0 management token: %s", exc)
        return None

    return response.json().get("access_token")


def _sync_user_from_payload(payload: dict):
    subject = payload.get("sub")
    if not subject:
        raise exceptions.AuthenticationFailed("Token missing subject (sub) claim")

    first_name = payload.get("given_name", "")
    last_name = payload.get("family_name", "")
    email = _fetch_email_from_auth0(subject)

    user, created = UserModel.objects.get_or_create(
        username=email,
        defaults={
            "email": email,
            "first_name": first_name,
            "last_name": last_name,
            "is_active": False,
        },
    )

    if created:
        user.set_unusable_password()
        user.is_active = False
        user.save(
            update_fields=["password", "is_active", "email", "first_name", "last_name"]
        )
        raise exceptions.AuthenticationFailed(
            "Usuário criado e aguardando aprovação. Contate um administrador."
        )

    updates = []
    if first_name and user.first_name != first_name:
        user.first_name = first_name
        updates.append("first_name")
    if last_name and user.last_name != last_name:
        user.last_name = last_name
        updates.append("last_name")
    if updates:
        user.save(update_fields=updates)

    if not user.is_active:
        raise exceptions.AuthenticationFailed(
            "Usuário ainda não foi autorizado a acessar a API."
        )

    return user


class Auth0JWTAuthentication(authentication.BaseAuthentication):
    """Authenticate requests using Auth0-issued JWT access tokens."""

    keyword = "bearer"

    def authenticate(self, request):
        auth_header = get_authorization_header(request).split()

        if not auth_header:
            return None

        if auth_header[0].lower() != self.keyword.encode():
            return None

        if len(auth_header) == 1:
            raise exceptions.AuthenticationFailed(
                "Invalid Authorization header. No credentials provided."
            )
        if len(auth_header) > 2:
            raise exceptions.AuthenticationFailed(
                "Invalid Authorization header. Credentials string should not contain spaces."
            )

        raw_token = auth_header[1].decode("utf-8")

        try:
            payload = _decode_jwt(raw_token)
        except InvalidTokenError as error:
            raise exceptions.AuthenticationFailed(
                "Invalid or expired access token"
            ) from error

        user = _sync_user_from_payload(payload)
        return user, payload
