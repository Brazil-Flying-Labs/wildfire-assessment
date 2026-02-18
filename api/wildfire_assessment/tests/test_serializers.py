from decimal import Decimal

from django.contrib.auth.models import User
from django.test import TestCase
from rest_framework.test import APIRequestFactory
from wildfire_assessment.models import Country, EcologicalReserve, UserProfile
from wildfire_assessment.serializers import (
    EcologicalReserveSerializer,
    UserMeSerializer,
)


class EcologicalReserveSerializerTests(TestCase):
    def setUp(self):
        self.country = Country.objects.create(name="Test Country", code="TC")
        self.reserve = EcologicalReserve.objects.create(
            name="Reserve A",
            polygon_path="polygon.json",
            municipio="Test City",
            site="https://example.com",
            codigo_ibge="1234567",
            area_ha=Decimal("142545.681"),
            country=self.country,
        )
        self.factory = APIRequestFactory()

    def test_contains_expected_fields(self):
        request = self.factory.get("/")
        serializer = EcologicalReserveSerializer(
            self.reserve, context={"request": request}
        )
        self.assertEqual(
            set(serializer.data.keys()),
            {"id", "name", "polygon_path", "municipio", "site", "codigo_ibge", "area_ha"},
        )

    def test_field_values(self):
        request = self.factory.get("/")
        serializer = EcologicalReserveSerializer(
            self.reserve, context={"request": request}
        )
        data = serializer.data
        self.assertEqual(data["id"], self.reserve.id)
        self.assertEqual(data["name"], "Reserve A")
        self.assertEqual(data["polygon_path"], "polygon.json")
        self.assertEqual(data["municipio"], "Test City")
        self.assertEqual(data["site"], "https://example.com")
        self.assertEqual(data["codigo_ibge"], "1234567")
        self.assertEqual(data["area_ha"], "142545.681")


class UserMeSerializerTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="tester", email="tester@example.com", password="password",
            first_name="Test", last_name="User",
        )
        # A UserProfile is auto-created via post_save signal

    def test_contains_expected_fields(self):
        serializer = UserMeSerializer(self.user)
        self.assertEqual(
            set(serializer.data.keys()),
            {"email", "first_name", "last_name", "default_language"},
        )

    def test_read_only_fields(self):
        meta = UserMeSerializer.Meta
        self.assertIn("email", meta.read_only_fields)
        self.assertIn("first_name", meta.read_only_fields)
        self.assertIn("last_name", meta.read_only_fields)

    def test_serializes_profile_language(self):
        profile = self.user.profile
        profile.default_language = "pt-BR"
        profile.save()
        serializer = UserMeSerializer(self.user)
        self.assertEqual(serializer.data["default_language"], "pt-BR")

    def test_update_language(self):
        serializer = UserMeSerializer(self.user)
        serializer.update(self.user, {"profile": {"default_language": "pt-BR"}})
        self.user.profile.refresh_from_db()
        self.assertEqual(self.user.profile.default_language, "pt-BR")

    def test_update_creates_profile_if_missing(self):
        # Delete the auto-created profile to simulate a user without one
        UserProfile.objects.filter(user=self.user).delete()
        self.assertFalse(UserProfile.objects.filter(user=self.user).exists())
        serializer = UserMeSerializer(self.user)
        serializer.update(self.user, {"profile": {"default_language": "fr"}})
        self.assertTrue(UserProfile.objects.filter(user=self.user).exists())
        profile = UserProfile.objects.get(user=self.user)
        self.assertEqual(profile.default_language, "fr")
