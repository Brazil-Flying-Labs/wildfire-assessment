"""Custom python-social-auth pipeline steps for Auth0 integration."""

import logging

LOG = logging.getLogger(__name__)


def social_user(backend, uid, user=None, *args, **kwargs):
    """Look up the social-auth record and return the associated Django user.

    Unlike the default ``social_core.pipeline.social_auth.social_user``, this
    step does **not** raise ``AuthAlreadyAssociated`` when the Auth0 account is
    already linked to a different Django user.  Instead it silently adopts the
    previously associated user, which is the expected behaviour when admins
    pre-create accounts in Django or when the JWT-based API flow auto-creates
    the Django user before the first social-auth login.
    """
    provider = backend.name
    social = backend.strategy.storage.user.get_social_auth(provider, uid)

    if social:
        if user and social.user != user:
            LOG.info(
                "Auth0 UID %s already associated with user %s; "
                "adopting instead of raising AuthAlreadyAssociated "
                "(session user was %s).",
                uid,
                social.user,
                user,
            )
        user = social.user

    return {
        "social": social,
        "user": user,
        "is_new": user is None,
        "new_association": social is None,
    }
