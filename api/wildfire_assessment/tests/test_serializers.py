import os
import tempfile
from decimal import Decimal
from unittest.mock import MagicMock, patch

from django.contrib.auth.models import User
from django.test import TestCase, override_settings
from rest_framework.test import APIRequestFactory
from wildfire_assessment.models import AreaOfInterest, Country, UserCountry, UserProfile
from wildfire_assessment.serializers import (
    AreaOfInterestCreateSerializer,
    AreaOfInterestSerializer,
    UserMeSerializer,
)


class AreaOfInterestSerializerTests(TestCase):
    def setUp(self):
        self.country = Country.objects.create(name="Test Country", code="TC")
        self.reserve = AreaOfInterest.objects.create(
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
        serializer = AreaOfInterestSerializer(
            self.reserve, context={"request": request}
        )
        self.assertEqual(
            set(serializer.data.keys()),
            {"id", "name", "polygon_path", "municipio", "site", "codigo_ibge", "area_ha", "country", "country_name", "country_code"},
        )

    def test_field_values(self):
        request = self.factory.get("/")
        serializer = AreaOfInterestSerializer(
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
            {"email", "first_name", "last_name", "default_language", "authorized_countries"},
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


class AreaOfInterestCreateSerializerTests(TestCase):
    def setUp(self):
        self.country = Country.objects.create(name="Test Country", code="TC")
        self.other_country = Country.objects.create(name="Other Country", code="OC")
        self.user = User.objects.create_user(
            username="tester", email="tester@example.com", password="password"
        )
        UserCountry.objects.create(user=self.user, country=self.country)
        self.factory = APIRequestFactory()

    def test_validate_country_authorized(self):
        request = self.factory.post("/")
        request.user = self.user
        serializer = AreaOfInterestCreateSerializer(
            data={
                "name": "Test Area",
                "country": self.country.id,
                "geojson": {"type": "Feature", "geometry": {}, "properties": {}},
            },
            context={"request": request},
        )
        self.assertTrue(serializer.is_valid())

    def test_validate_country_unauthorized(self):
        request = self.factory.post("/")
        request.user = self.user
        serializer = AreaOfInterestCreateSerializer(
            data={
                "name": "Test Area",
                "country": self.other_country.id,
                "geojson": {"type": "Feature", "geometry": {}, "properties": {}},
            },
            context={"request": request},
        )
        self.assertFalse(serializer.is_valid())
        self.assertIn("country", serializer.errors)

    def test_validate_geojson_not_dict(self):
        request = self.factory.post("/")
        request.user = self.user
        serializer = AreaOfInterestCreateSerializer(
            data={
                "name": "Test Area",
                "country": self.country.id,
                "geojson": "not a dict",
            },
            context={"request": request},
        )
        self.assertFalse(serializer.is_valid())
        self.assertIn("geojson", serializer.errors)

    def test_validate_geojson_invalid_type(self):
        request = self.factory.post("/")
        request.user = self.user
        serializer = AreaOfInterestCreateSerializer(
            data={
                "name": "Test Area",
                "country": self.country.id,
                "geojson": {"type": "InvalidType"},
            },
            context={"request": request},
        )
        self.assertFalse(serializer.is_valid())
        self.assertIn("geojson", serializer.errors)

    def test_validate_geojson_valid_types(self):
        request = self.factory.post("/")
        request.user = self.user
        valid_types = ["Feature", "FeatureCollection", "Polygon", "MultiPolygon"]
        for geojson_type in valid_types:
            serializer = AreaOfInterestCreateSerializer(
                data={
                    "name": f"Test Area {geojson_type}",
                    "country": self.country.id,
                    "geojson": {"type": geojson_type},
                },
                context={"request": request},
            )
            self.assertTrue(serializer.is_valid(), f"Failed for type {geojson_type}: {serializer.errors}")

    @patch("os.makedirs")
    @patch("builtins.open", create=True)
    def test_create_saves_geojson_file(self, mock_open, mock_makedirs):
        mock_file = MagicMock()
        mock_open.return_value.__enter__.return_value = mock_file

        request = self.factory.post("/")
        request.user = self.user
        serializer = AreaOfInterestCreateSerializer(
            data={
                "name": "New Area",
                "country": self.country.id,
                "geojson": {"type": "Feature", "geometry": {}, "properties": {}},
            },
            context={"request": request},
        )
        self.assertTrue(serializer.is_valid())
        instance = serializer.save()

        self.assertEqual(instance.name, "New Area")
        self.assertTrue(instance.polygon_path.startswith("New_Area_"))
        self.assertTrue(instance.polygon_path.endswith(".geojson"))
        mock_makedirs.assert_called_once()
        mock_open.assert_called_once()

    def test_validate_country_no_request(self):
        """Test validate_country when no request context is provided."""
        serializer = AreaOfInterestCreateSerializer(
            data={
                "name": "Test Area",
                "country": self.country.id,
                "geojson": {"type": "Feature", "geometry": {}, "properties": {}},
            },
            context={},  # No request
        )
        # Should still be valid - validation skipped without request
        self.assertTrue(serializer.is_valid())
