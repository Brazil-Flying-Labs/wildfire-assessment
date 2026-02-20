import tempfile
from decimal import Decimal
from unittest.mock import patch

from django.contrib.auth.models import User
from django.test import TestCase, override_settings
from rest_framework.test import APIRequestFactory
from wildfire_assessment.models import (
    AnalysisRun,
    AreaOfInterest,
    Country,
    UserCountry,
    UserProfile,
)
from wildfire_assessment.serializers import (
    AnalysisRunSerializer,
    AreaOfInterestCreateSerializer,
    AreaOfInterestSerializer,
    AreaOfInterestUpdateSerializer,
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
            {"email", "first_name", "last_name", "default_language", "theme", "authorized_countries"},
        )

    def test_read_only_fields(self):
        meta = UserMeSerializer.Meta
        self.assertIn("email", meta.read_only_fields)
        self.assertIn("authorized_countries", meta.read_only_fields)
        # first_name and last_name should be editable
        self.assertNotIn("first_name", meta.read_only_fields)
        self.assertNotIn("last_name", meta.read_only_fields)

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
        # Valid polygon geometry for tests
        self.valid_polygon = {
            "type": "Polygon",
            "coordinates": [[[0, 0], [1, 0], [1, 1], [0, 1], [0, 0]]]
        }
        self.valid_feature = {
            "type": "Feature",
            "geometry": self.valid_polygon,
            "properties": {}
        }

    def test_validate_country_authorized(self):
        request = self.factory.post("/")
        request.user = self.user
        serializer = AreaOfInterestCreateSerializer(
            data={
                "name": "Test Area",
                "country": self.country.id,
                "geojson": self.valid_feature,
            },
            context={"request": request},
        )
        self.assertTrue(serializer.is_valid(), serializer.errors)

    def test_validate_country_unauthorized(self):
        request = self.factory.post("/")
        request.user = self.user
        serializer = AreaOfInterestCreateSerializer(
            data={
                "name": "Test Area",
                "country": self.other_country.id,
                "geojson": self.valid_feature,
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

    def test_validate_geojson_missing_type(self):
        request = self.factory.post("/")
        request.user = self.user
        serializer = AreaOfInterestCreateSerializer(
            data={
                "name": "Test Area",
                "country": self.country.id,
                "geojson": {"coordinates": [[0, 0]]},
            },
            context={"request": request},
        )
        self.assertFalse(serializer.is_valid())
        self.assertIn("geojson", serializer.errors)

    def test_validate_geojson_feature_missing_geometry(self):
        request = self.factory.post("/")
        request.user = self.user
        serializer = AreaOfInterestCreateSerializer(
            data={
                "name": "Test Area",
                "country": self.country.id,
                "geojson": {"type": "Feature", "properties": {}},
            },
            context={"request": request},
        )
        self.assertFalse(serializer.is_valid())
        self.assertIn("geojson", serializer.errors)

    def test_validate_geojson_feature_collection_empty(self):
        request = self.factory.post("/")
        request.user = self.user
        serializer = AreaOfInterestCreateSerializer(
            data={
                "name": "Test Area",
                "country": self.country.id,
                "geojson": {"type": "FeatureCollection", "features": []},
            },
            context={"request": request},
        )
        self.assertFalse(serializer.is_valid())
        self.assertIn("geojson", serializer.errors)

    def test_validate_geojson_valid_feature(self):
        request = self.factory.post("/")
        request.user = self.user
        serializer = AreaOfInterestCreateSerializer(
            data={
                "name": "Test Area",
                "country": self.country.id,
                "geojson": self.valid_feature,
            },
            context={"request": request},
        )
        self.assertTrue(serializer.is_valid(), serializer.errors)

    def test_validate_geojson_valid_polygon(self):
        request = self.factory.post("/")
        request.user = self.user
        serializer = AreaOfInterestCreateSerializer(
            data={
                "name": "Test Area",
                "country": self.country.id,
                "geojson": self.valid_polygon,
            },
            context={"request": request},
        )
        self.assertTrue(serializer.is_valid(), serializer.errors)

    def test_validate_geojson_valid_multipolygon(self):
        request = self.factory.post("/")
        request.user = self.user
        serializer = AreaOfInterestCreateSerializer(
            data={
                "name": "Test Area",
                "country": self.country.id,
                "geojson": {
                    "type": "MultiPolygon",
                    "coordinates": [[[[0, 0], [1, 0], [1, 1], [0, 1], [0, 0]]]]
                },
            },
            context={"request": request},
        )
        self.assertTrue(serializer.is_valid(), serializer.errors)

    def test_validate_geojson_valid_feature_collection(self):
        request = self.factory.post("/")
        request.user = self.user
        serializer = AreaOfInterestCreateSerializer(
            data={
                "name": "Test Area",
                "country": self.country.id,
                "geojson": {
                    "type": "FeatureCollection",
                    "features": [self.valid_feature]
                },
            },
            context={"request": request},
        )
        self.assertTrue(serializer.is_valid(), serializer.errors)

    def test_validate_geojson_invalid_longitude(self):
        request = self.factory.post("/")
        request.user = self.user
        serializer = AreaOfInterestCreateSerializer(
            data={
                "name": "Test Area",
                "country": self.country.id,
                "geojson": {
                    "type": "Polygon",
                    "coordinates": [[[200, 0], [201, 0], [201, 1], [200, 1], [200, 0]]]
                },
            },
            context={"request": request},
        )
        self.assertFalse(serializer.is_valid())
        self.assertIn("geojson", serializer.errors)
        self.assertIn("Longitude", str(serializer.errors["geojson"]))

    def test_validate_geojson_invalid_latitude(self):
        request = self.factory.post("/")
        request.user = self.user
        serializer = AreaOfInterestCreateSerializer(
            data={
                "name": "Test Area",
                "country": self.country.id,
                "geojson": {
                    "type": "Polygon",
                    "coordinates": [[[0, 100], [1, 100], [1, 101], [0, 101], [0, 100]]]
                },
            },
            context={"request": request},
        )
        self.assertFalse(serializer.is_valid())
        self.assertIn("geojson", serializer.errors)
        self.assertIn("Latitude", str(serializer.errors["geojson"]))

    def test_validate_geojson_self_intersecting_polygon(self):
        request = self.factory.post("/")
        request.user = self.user
        # Bowtie/self-intersecting polygon
        serializer = AreaOfInterestCreateSerializer(
            data={
                "name": "Test Area",
                "country": self.country.id,
                "geojson": {
                    "type": "Polygon",
                    "coordinates": [[[0, 0], [1, 1], [1, 0], [0, 1], [0, 0]]]
                },
            },
            context={"request": request},
        )
        self.assertFalse(serializer.is_valid())
        self.assertIn("geojson", serializer.errors)

    @patch("wildfire_assessment.svc.aws.upload_polygon_to_s3")
    def test_create_saves_geojson_file(self, mock_upload):
        request = self.factory.post("/")
        request.user = self.user
        serializer = AreaOfInterestCreateSerializer(
            data={
                "name": "New Area",
                "country": self.country.id,
                "geojson": self.valid_feature,
            },
            context={"request": request},
        )
        self.assertTrue(serializer.is_valid(), serializer.errors)
        instance = serializer.save()

        self.assertEqual(instance.name, "New Area")
        self.assertTrue(instance.polygon_path.startswith("New_Area_"))
        self.assertTrue(instance.polygon_path.endswith(".geojson"))
        mock_upload.assert_called_once()

    def test_validate_country_no_request(self):
        """Test validate_country when no request context is provided."""
        serializer = AreaOfInterestCreateSerializer(
            data={
                "name": "Test Area",
                "country": self.country.id,
                "geojson": self.valid_feature,
            },
            context={},  # No request
        )
        # Should still be valid - validation skipped without request
        self.assertTrue(serializer.is_valid(), serializer.errors)

    def test_validate_geojson_feature_collection_invalid_feature(self):
        """Test FeatureCollection with non-dict feature."""
        request = self.factory.post("/")
        request.user = self.user
        serializer = AreaOfInterestCreateSerializer(
            data={
                "name": "Test Area",
                "country": self.country.id,
                "geojson": {
                    "type": "FeatureCollection",
                    "features": ["not a dict"]
                },
            },
            context={"request": request},
        )
        self.assertFalse(serializer.is_valid())
        self.assertIn("geojson", serializer.errors)

    def test_validate_geojson_geometry_not_dict(self):
        """Test Feature with non-dict geometry."""
        request = self.factory.post("/")
        request.user = self.user
        serializer = AreaOfInterestCreateSerializer(
            data={
                "name": "Test Area",
                "country": self.country.id,
                "geojson": {
                    "type": "Feature",
                    "geometry": "not a dict",
                    "properties": {}
                },
            },
            context={"request": request},
        )
        self.assertFalse(serializer.is_valid())
        self.assertIn("geojson", serializer.errors)

    def test_validate_geojson_geometry_missing_type(self):
        """Test geometry without type field."""
        request = self.factory.post("/")
        request.user = self.user
        serializer = AreaOfInterestCreateSerializer(
            data={
                "name": "Test Area",
                "country": self.country.id,
                "geojson": {
                    "type": "Feature",
                    "geometry": {"coordinates": [[0, 0]]},
                    "properties": {}
                },
            },
            context={"request": request},
        )
        self.assertFalse(serializer.is_valid())
        self.assertIn("geojson", serializer.errors)

    def test_validate_geojson_geometry_missing_coordinates(self):
        """Test geometry without coordinates field."""
        request = self.factory.post("/")
        request.user = self.user
        serializer = AreaOfInterestCreateSerializer(
            data={
                "name": "Test Area",
                "country": self.country.id,
                "geojson": {
                    "type": "Feature",
                    "geometry": {"type": "Polygon"},
                    "properties": {}
                },
            },
            context={"request": request},
        )
        self.assertFalse(serializer.is_valid())
        self.assertIn("geojson", serializer.errors)

    def test_validate_geojson_invalid_geometry_structure(self):
        """Test geometry that shapely can't parse."""
        request = self.factory.post("/")
        request.user = self.user
        serializer = AreaOfInterestCreateSerializer(
            data={
                "name": "Test Area",
                "country": self.country.id,
                "geojson": {
                    "type": "Feature",
                    "geometry": {"type": "Polygon", "coordinates": "invalid"},
                    "properties": {}
                },
            },
            context={"request": request},
        )
        self.assertFalse(serializer.is_valid())
        self.assertIn("geojson", serializer.errors)

    def test_validate_geojson_empty_geometry(self):
        """Test empty geometry."""
        request = self.factory.post("/")
        request.user = self.user
        serializer = AreaOfInterestCreateSerializer(
            data={
                "name": "Test Area",
                "country": self.country.id,
                "geojson": {
                    "type": "Feature",
                    "geometry": {"type": "Polygon", "coordinates": []},
                    "properties": {}
                },
            },
            context={"request": request},
        )
        self.assertFalse(serializer.is_valid())
        self.assertIn("geojson", serializer.errors)

    def test_validate_geojson_rejects_point(self):
        """Test that Point geometry is rejected."""
        request = self.factory.post("/")
        request.user = self.user
        serializer = AreaOfInterestCreateSerializer(
            data={
                "name": "Test Area",
                "country": self.country.id,
                "geojson": {
                    "type": "Point",
                    "coordinates": [10, 20]
                },
            },
            context={"request": request},
        )
        self.assertFalse(serializer.is_valid())
        self.assertIn("geojson", serializer.errors)

    def test_validate_geojson_rejects_linestring(self):
        """Test that LineString geometry is rejected."""
        request = self.factory.post("/")
        request.user = self.user
        serializer = AreaOfInterestCreateSerializer(
            data={
                "name": "Test Area",
                "country": self.country.id,
                "geojson": {
                    "type": "LineString",
                    "coordinates": [[0, 0], [1, 1], [2, 2]]
                },
            },
            context={"request": request},
        )
        self.assertFalse(serializer.is_valid())
        self.assertIn("geojson", serializer.errors)

    def test_validate_geojson_rejects_feature_with_linestring(self):
        """Test that a Feature wrapping a LineString is rejected."""
        request = self.factory.post("/")
        request.user = self.user
        serializer = AreaOfInterestCreateSerializer(
            data={
                "name": "Test Area",
                "country": self.country.id,
                "geojson": {
                    "type": "Feature",
                    "geometry": {
                        "type": "LineString",
                        "coordinates": [[0, 0], [1, 1], [2, 2]]
                    },
                    "properties": {}
                },
            },
            context={"request": request},
        )
        self.assertFalse(serializer.is_valid())
        self.assertIn("geojson", serializer.errors)

    def test_validate_coordinates_depth_limit(self):
        """Test that deeply nested coordinates don't cause infinite recursion."""
        request = self.factory.post("/")
        request.user = self.user
        serializer = AreaOfInterestCreateSerializer(
            data={
                "name": "Test Area",
                "country": self.country.id,
                "geojson": self.valid_polygon,
            },
            context={"request": request},
        )
        # Directly test the _validate_coordinates method at depth limit
        # Should return early without error
        serializer._validate_coordinates([[0, 0]], "test", depth=11)

    def test_validate_coordinates_single_number(self):
        """Test that single numbers in coordinates are handled."""
        request = self.factory.post("/")
        request.user = self.user
        serializer = AreaOfInterestCreateSerializer(
            data={
                "name": "Test Area",
                "country": self.country.id,
                "geojson": self.valid_polygon,
            },
            context={"request": request},
        )
        # Directly test with a single number - should return without error
        serializer._validate_coordinates(42.5, "test")

    def test_validate_geojson_empty_polygon_geometry(self):
        """Test polygon with empty ring creates empty geometry."""
        request = self.factory.post("/")
        request.user = self.user
        # [[]] is truthy so passes the coords check but creates empty geometry
        serializer = AreaOfInterestCreateSerializer(
            data={
                "name": "Test Area",
                "country": self.country.id,
                "geojson": {
                    "type": "Polygon",
                    "coordinates": [[]]
                },
            },
            context={"request": request},
        )
        self.assertFalse(serializer.is_valid())
        self.assertIn("geojson", serializer.errors)
        self.assertIn("empty", str(serializer.errors["geojson"]).lower())


class AreaOfInterestUpdateSerializerTests(TestCase):
    def setUp(self):
        self.country = Country.objects.create(name="Test Country", code="TC")
        self.country2 = Country.objects.create(name="Other Country", code="OC")
        self.user = User.objects.create_user(username="testuser", password="testpass")
        UserCountry.objects.create(user=self.user, country=self.country)
        UserCountry.objects.create(user=self.user, country=self.country2)
        self.factory = APIRequestFactory()
        self.valid_polygon = {
            "type": "Polygon",
            "coordinates": [[[0, 0], [1, 0], [1, 1], [0, 1], [0, 0]]],
        }

    @override_settings(BASE_DIR=tempfile.gettempdir())
    def test_update_name_only(self):
        """Test updating just the name without changing GeoJSON."""
        # Create an area first
        area = AreaOfInterest.objects.create(
            name="Original Name",
            polygon_path="test.geojson",
            country=self.country,
        )

        request = self.factory.patch("/")
        request.user = self.user
        serializer = AreaOfInterestUpdateSerializer(
            area,
            data={"name": "Updated Name"},
            partial=True,
            context={"request": request},
        )
        self.assertTrue(serializer.is_valid(), serializer.errors)
        updated = serializer.save()
        self.assertEqual(updated.name, "Updated Name")
        self.assertEqual(updated.polygon_path, "test.geojson")  # unchanged

    @patch("wildfire_assessment.svc.aws.delete_polygon_from_s3")
    @patch("wildfire_assessment.svc.aws.upload_polygon_to_s3")
    def test_update_with_new_geojson(self, mock_upload, mock_delete):
        """Test updating with a new GeoJSON file."""
        area = AreaOfInterest.objects.create(
            name="Test Area",
            polygon_path="old_file.geojson",
            country=self.country,
        )

        request = self.factory.patch("/")
        request.user = self.user

        serializer = AreaOfInterestUpdateSerializer(
            area,
            data={
                "name": "Test Area",
                "geojson": self.valid_polygon,
            },
            partial=True,
            context={"request": request},
        )
        self.assertTrue(serializer.is_valid(), serializer.errors)
        updated = serializer.save()
        self.assertNotEqual(updated.polygon_path, "old_file.geojson")
        self.assertTrue(updated.polygon_path.endswith(".geojson"))
        mock_delete.assert_called_once_with("old_file.geojson")
        mock_upload.assert_called_once()

    def test_update_country_unauthorized(self):
        """Test that updating to unauthorized country fails."""
        unauthorized_country = Country.objects.create(name="Unauthorized", code="UC")
        area = AreaOfInterest.objects.create(
            name="Test Area",
            polygon_path="test.geojson",
            country=self.country,
        )

        request = self.factory.patch("/")
        request.user = self.user
        serializer = AreaOfInterestUpdateSerializer(
            area,
            data={"country": unauthorized_country.id},
            partial=True,
            context={"request": request},
        )
        self.assertFalse(serializer.is_valid())
        self.assertIn("country", serializer.errors)

    def test_update_country_authorized(self):
        """Test that updating to authorized country succeeds."""
        area = AreaOfInterest.objects.create(
            name="Test Area",
            polygon_path="test.geojson",
            country=self.country,
        )

        request = self.factory.patch("/")
        request.user = self.user
        serializer = AreaOfInterestUpdateSerializer(
            area,
            data={"country": self.country2.id},
            partial=True,
            context={"request": request},
        )
        self.assertTrue(serializer.is_valid(), serializer.errors)


class AnalysisRunSerializerTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="imguser", email="img@example.com", password="pw"
        )
        self.country = Country.objects.create(name="Img Country", code="IC")
        self.area = AreaOfInterest.objects.create(
            name="Img Area", polygon_path="img.geojson", country=self.country
        )

    @patch("wildfire_assessment.svc.aws.get_presigned_image_url")
    def test_serializer_generates_presigned_urls(self, mock_presign):
        mock_presign.side_effect = lambda key, **kw: f"https://s3.example.com/{key}"
        run = AnalysisRun.objects.create(
            user=self.user,
            area_of_interest=self.area,
            pre_fire_date="2024-01-01",
            post_fire_date="2024-01-15",
            rgb_pre_fire_image="abc/pre.jpg",
            rgb_post_fire_image="abc/post.jpg",
            dndvi_image="abc/dndvi.jpg",
            dnbr_image="abc/dnbr.jpg",
            rbr_image="abc/rbr.jpg",
        )
        data = AnalysisRunSerializer(run).data
        self.assertEqual(data["rgb_pre_fire_url"], "https://s3.example.com/abc/pre.jpg")
        self.assertEqual(data["rgb_post_fire_url"], "https://s3.example.com/abc/post.jpg")
        self.assertEqual(data["dndvi_url"], "https://s3.example.com/abc/dndvi.jpg")
        self.assertEqual(data["dnbr_url"], "https://s3.example.com/abc/dnbr.jpg")
        self.assertEqual(data["rbr_url"], "https://s3.example.com/abc/rbr.jpg")

    def test_serializer_returns_none_for_missing_images(self):
        run = AnalysisRun.objects.create(
            user=self.user,
            area_of_interest=self.area,
            pre_fire_date="2024-01-01",
            post_fire_date="2024-01-15",
        )
        data = AnalysisRunSerializer(run).data
        self.assertIsNone(data["rgb_pre_fire_url"])
        self.assertIsNone(data["dndvi_url"])
