"""Tests for wildfire_assessment.social_pipeline."""

from unittest.mock import MagicMock

from django.contrib.auth import get_user_model
from django.test import TestCase
from wildfire_assessment.social_pipeline import social_user

UserModel = get_user_model()


class SocialUserPipelineTests(TestCase):
    """Tests for the custom social_user pipeline step."""

    def setUp(self):
        self.backend = MagicMock()
        self.backend.name = "auth0"
        self.storage = self.backend.strategy.storage.user

    # ------------------------------------------------------------------
    # No existing social-auth record
    # ------------------------------------------------------------------

    def test_no_social_record_no_session_user(self):
        """When no social record exists and no session user, returns new-user markers."""
        self.storage.get_social_auth.return_value = None

        result = social_user(self.backend, "auth0|abc123")

        self.storage.get_social_auth.assert_called_once_with("auth0", "auth0|abc123")
        self.assertIsNone(result["social"])
        self.assertIsNone(result["user"])
        self.assertTrue(result["is_new"])
        self.assertTrue(result["new_association"])

    def test_no_social_record_with_session_user(self):
        """When no social record exists but a session user is present, passes user through."""
        self.storage.get_social_auth.return_value = None
        session_user = MagicMock()

        result = social_user(self.backend, "auth0|abc123", user=session_user)

        self.assertIsNone(result["social"])
        self.assertEqual(result["user"], session_user)
        self.assertFalse(result["is_new"])
        self.assertTrue(result["new_association"])

    # ------------------------------------------------------------------
    # Existing social-auth record, same user
    # ------------------------------------------------------------------

    def test_social_record_matches_session_user(self):
        """When the social record matches the session user, returns normally."""
        existing_user = MagicMock()
        social_auth = MagicMock()
        social_auth.user = existing_user
        self.storage.get_social_auth.return_value = social_auth

        result = social_user(self.backend, "auth0|abc123", user=existing_user)

        self.assertEqual(result["social"], social_auth)
        self.assertEqual(result["user"], existing_user)
        self.assertFalse(result["is_new"])
        self.assertFalse(result["new_association"])

    # ------------------------------------------------------------------
    # Existing social-auth record, different user (AuthAlreadyAssociated fix)
    # ------------------------------------------------------------------

    def test_social_record_different_session_user_adopts_associated(self):
        """When social record belongs to user A but session has user B, adopts user A."""
        user_a = MagicMock(spec=["__str__"])
        user_b = MagicMock(spec=["__str__"])
        social_auth = MagicMock()
        social_auth.user = user_a
        self.storage.get_social_auth.return_value = social_auth

        result = social_user(self.backend, "auth0|abc123", user=user_b)

        # Should NOT raise AuthAlreadyAssociated — just adopt user A.
        self.assertEqual(result["user"], user_a)
        self.assertEqual(result["social"], social_auth)
        self.assertFalse(result["is_new"])
        self.assertFalse(result["new_association"])

    # ------------------------------------------------------------------
    # Existing social-auth record, no session user
    # ------------------------------------------------------------------

    def test_social_record_no_session_user(self):
        """When a social record exists but no session user, returns the associated user."""
        existing_user = MagicMock()
        social_auth = MagicMock()
        social_auth.user = existing_user
        self.storage.get_social_auth.return_value = social_auth

        result = social_user(self.backend, "auth0|abc123")

        self.assertEqual(result["user"], existing_user)
        self.assertEqual(result["social"], social_auth)
        self.assertFalse(result["is_new"])
        self.assertFalse(result["new_association"])
