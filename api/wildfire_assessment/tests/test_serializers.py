import tempfile
from decimal import Decimal
from unittest.mock import patch

from django.contrib.auth.models import User
from django.test import TestCase, override_settings
from rest_framework.test import APIRequestFactory
from wildfire_assessment.models import (
    AnalysisRun,
    AnalysisRunProvenance,
    AreaOfInterest,
    Country,
    Notification,
    UserCountry,
    UserProfile,
)
from wildfire_assessment.serializers import (
    MAX_AREA_HA,
    AnalysisRunProvenanceSerializer,
    AnalysisRunSerializer,
    AreaOfInterestCreateSerializer,
    AreaOfInterestSerializer,
    AreaOfInterestUpdateSerializer,
    NotificationSerializer,
    ReportSummaryRequestSerializer,
    UserMeSerializer,
    check_duplicate_area_name,
    compute_area_ha,
    compute_centroid,
    generate_polygon_filename,
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
            {
                "id",
                "name",
                "polygon_path",
                "municipio",
                "site",
                "codigo_ibge",
                "area_ha",
                "country",
                "country_name",
                "country_code",
            },
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
            username="tester",
            email="tester@example.com",
            password="password",
            first_name="Test",
            last_name="User",
        )
        # A UserProfile is auto-created via post_save signal

    def test_contains_expected_fields(self):
        serializer = UserMeSerializer(self.user)
        self.assertEqual(
            set(serializer.data.keys()),
            {
                "email",
                "first_name",
                "last_name",
                "default_language",
                "theme",
                "dashboard_widgets",
                "authorized_countries",
                "terms_accepted_at",
                "terms_last_updated",
            },
        )

    def test_read_only_fields(self):
        meta = UserMeSerializer.Meta
        self.assertIn("email", meta.read_only_fields)
        self.assertIn("authorized_countries", meta.read_only_fields)
        self.assertIn("terms_last_updated", meta.read_only_fields)
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
            "coordinates": [[[0, 0], [0.1, 0], [0.1, 0.1], [0, 0.1], [0, 0]]],
        }
        self.valid_feature = {
            "type": "Feature",
            "geometry": self.valid_polygon,
            "properties": {},
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
                    "coordinates": [[[[0, 0], [0.1, 0], [0.1, 0.1], [0, 0.1], [0, 0]]]],
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
                    "features": [self.valid_feature],
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
                    "coordinates": [[[200, 0], [201, 0], [201, 1], [200, 1], [200, 0]]],
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
                    "coordinates": [[[0, 100], [1, 100], [1, 101], [0, 101], [0, 100]]],
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
                    "coordinates": [[[0, 0], [0.1, 0.1], [0.1, 0], [0, 0.1], [0, 0]]],
                },
            },
            context={"request": request},
        )
        self.assertFalse(serializer.is_valid())
        self.assertIn("geojson", serializer.errors)

    @patch("wildfire_assessment.serializers.upload_polygon")
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
        self.assertIsNotNone(instance.area_ha)
        self.assertGreater(instance.area_ha, 0)
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
                "geojson": {"type": "FeatureCollection", "features": ["not a dict"]},
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
                    "properties": {},
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
                    "properties": {},
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
                    "properties": {},
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
                    "properties": {},
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
                    "properties": {},
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
                "geojson": {"type": "Point", "coordinates": [10, 20]},
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
                    "coordinates": [[0, 0], [1, 1], [2, 2]],
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
                        "coordinates": [[0, 0], [1, 1], [2, 2]],
                    },
                    "properties": {},
                },
            },
            context={"request": request},
        )
        self.assertFalse(serializer.is_valid())
        self.assertIn("geojson", serializer.errors)

    @patch("wildfire_assessment.serializers.upload_polygon")
    def test_duplicate_name_same_country_rejected(self, _mock_upload):
        """Test that duplicate area name in the same country is rejected."""
        AreaOfInterest.objects.create(
            name="Duplicate Area", country=self.country, polygon_path="existing.geojson"
        )
        request = self.factory.post("/")
        request.user = self.user
        serializer = AreaOfInterestCreateSerializer(
            data={
                "name": "Duplicate Area",
                "country": self.country.id,
                "geojson": self.valid_polygon,
            },
            context={"request": request},
        )
        self.assertFalse(serializer.is_valid())
        self.assertIn("name", serializer.errors)

    @patch("wildfire_assessment.serializers.upload_polygon")
    def test_same_name_different_country_allowed(self, _mock_upload):
        """Test that the same area name is allowed in a different country."""
        UserCountry.objects.create(user=self.user, country=self.other_country)
        AreaOfInterest.objects.create(
            name="Shared Name", country=self.country, polygon_path="existing.geojson"
        )
        request = self.factory.post("/")
        request.user = self.user
        serializer = AreaOfInterestCreateSerializer(
            data={
                "name": "Shared Name",
                "country": self.other_country.id,
                "geojson": self.valid_polygon,
            },
            context={"request": request},
        )
        self.assertTrue(serializer.is_valid(), serializer.errors)

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
                "geojson": {"type": "Polygon", "coordinates": [[]]},
            },
            context={"request": request},
        )
        self.assertFalse(serializer.is_valid())
        self.assertIn("geojson", serializer.errors)
        self.assertIn("empty", str(serializer.errors["geojson"]).lower())

    # --- RFC 7946 Relaxed: ring closure ---

    def test_validate_geojson_ring_not_closed(self):
        """Unclosed ring is rejected with translated error."""
        request = self.factory.post("/")
        request.user = self.user
        serializer = AreaOfInterestCreateSerializer(
            data={
                "name": "Test Area",
                "country": self.country.id,
                "geojson": {
                    "type": "Polygon",
                    "coordinates": [[[0, 0], [0.1, 0], [0.1, 0.1], [0, 0.1]]],
                },
            },
            context={"request": request},
        )
        self.assertFalse(serializer.is_valid())
        self.assertIn("geojson", serializer.errors)
        self.assertIn("not closed", str(serializer.errors["geojson"]).lower())

    def test_validate_geojson_multipolygon_ring_not_closed(self):
        """Unclosed ring in MultiPolygon is rejected."""
        request = self.factory.post("/")
        request.user = self.user
        serializer = AreaOfInterestCreateSerializer(
            data={
                "name": "Test Area",
                "country": self.country.id,
                "geojson": {
                    "type": "MultiPolygon",
                    "coordinates": [
                        [[[0, 0], [0.1, 0], [0.1, 0.1], [0, 0.1]]],
                    ],
                },
            },
            context={"request": request},
        )
        self.assertFalse(serializer.is_valid())
        self.assertIn("geojson", serializer.errors)
        self.assertIn("not closed", str(serializer.errors["geojson"]).lower())

    # --- RFC 7946 Relaxed: minimum ring positions ---

    def test_validate_geojson_ring_too_few_positions(self):
        """Ring with fewer than 4 positions is rejected."""
        request = self.factory.post("/")
        request.user = self.user
        serializer = AreaOfInterestCreateSerializer(
            data={
                "name": "Test Area",
                "country": self.country.id,
                "geojson": {
                    "type": "Polygon",
                    "coordinates": [[[0, 0], [0.1, 0], [0, 0]]],
                },
            },
            context={"request": request},
        )
        self.assertFalse(serializer.is_valid())
        self.assertIn("geojson", serializer.errors)
        self.assertIn("at least 4", str(serializer.errors["geojson"]).lower())

    def test_validate_geojson_ring_with_exactly_4_positions_valid(self):
        """Triangle with 4 positions (3 vertices + closure) passes."""
        request = self.factory.post("/")
        request.user = self.user
        serializer = AreaOfInterestCreateSerializer(
            data={
                "name": "Test Area",
                "country": self.country.id,
                "geojson": {
                    "type": "Polygon",
                    "coordinates": [[[0, 0], [0.1, 0], [0.05, 0.1], [0, 0]]],
                },
            },
            context={"request": request},
        )
        self.assertTrue(serializer.is_valid(), serializer.errors)

    # --- RFC 7946 Relaxed: no nested GeometryCollections ---

    def test_validate_geojson_nested_geometry_collection_rejected(self):
        """GeometryCollection within a GeometryCollection is rejected."""
        request = self.factory.post("/")
        request.user = self.user
        serializer = AreaOfInterestCreateSerializer(
            data={
                "name": "Test Area",
                "country": self.country.id,
                "geojson": {
                    "type": "Feature",
                    "geometry": {
                        "type": "GeometryCollection",
                        "geometries": [
                            {
                                "type": "GeometryCollection",
                                "geometries": [],
                            }
                        ],
                    },
                    "properties": {},
                },
            },
            context={"request": request},
        )
        self.assertFalse(serializer.is_valid())
        self.assertIn("geojson", serializer.errors)
        self.assertIn("geometrycollection", str(serializer.errors["geojson"]).lower())

    def test_validate_geojson_geometry_collection_with_polygons_valid(self):
        """GeometryCollection containing Polygons passes."""
        request = self.factory.post("/")
        request.user = self.user
        serializer = AreaOfInterestCreateSerializer(
            data={
                "name": "Test Area",
                "country": self.country.id,
                "geojson": {
                    "type": "Feature",
                    "geometry": {
                        "type": "GeometryCollection",
                        "geometries": [
                            {
                                "type": "Polygon",
                                "coordinates": [
                                    [[0, 0], [0.1, 0], [0.1, 0.1], [0, 0.1], [0, 0]]
                                ],
                            }
                        ],
                    },
                    "properties": {},
                },
            },
            context={"request": request},
        )
        self.assertTrue(serializer.is_valid(), serializer.errors)

    # --- RFC 7946 Relaxed: CRS stripping ---

    def test_validate_geojson_strips_deprecated_crs(self):
        """Polygon with deprecated 'crs' field passes, crs removed."""
        request = self.factory.post("/")
        request.user = self.user
        geojson = {
            "type": "Polygon",
            "coordinates": [[[0, 0], [0.1, 0], [0.1, 0.1], [0, 0.1], [0, 0]]],
            "crs": {
                "type": "name",
                "properties": {"name": "EPSG:4326"},
            },
        }
        serializer = AreaOfInterestCreateSerializer(
            data={
                "name": "Test Area",
                "country": self.country.id,
                "geojson": geojson,
            },
            context={"request": request},
        )
        self.assertTrue(serializer.is_valid(), serializer.errors)
        self.assertNotIn("crs", serializer.validated_data["geojson"])

    def test_validate_geojson_feature_collection_strips_crs(self):
        """FeatureCollection with 'crs' on top-level and features passes, crs removed."""
        request = self.factory.post("/")
        request.user = self.user
        geojson = {
            "type": "FeatureCollection",
            "crs": {"type": "name", "properties": {"name": "EPSG:4326"}},
            "features": [
                {
                    "type": "Feature",
                    "crs": {"type": "name", "properties": {"name": "EPSG:4326"}},
                    "geometry": {
                        "type": "Polygon",
                        "coordinates": [
                            [[0, 0], [0.1, 0], [0.1, 0.1], [0, 0.1], [0, 0]]
                        ],
                    },
                    "properties": {},
                }
            ],
        }
        serializer = AreaOfInterestCreateSerializer(
            data={
                "name": "Test Area",
                "country": self.country.id,
                "geojson": geojson,
            },
            context={"request": request},
        )
        self.assertTrue(serializer.is_valid(), serializer.errors)
        validated = serializer.validated_data["geojson"]
        self.assertNotIn("crs", validated)
        self.assertNotIn("crs", validated["features"][0])

    # --- RFC 7946 Relaxed: winding order ---

    def test_validate_geojson_fixes_clockwise_exterior_ring(self):
        """Clockwise exterior ring is auto-corrected to counterclockwise."""
        request = self.factory.post("/")
        request.user = self.user
        # Clockwise exterior: (0,0) → (0,1) → (1,1) → (1,0) → (0,0)
        cw_ring = [[0, 0], [0, 0.1], [0.1, 0.1], [0.1, 0], [0, 0]]
        serializer = AreaOfInterestCreateSerializer(
            data={
                "name": "Test Area",
                "country": self.country.id,
                "geojson": {"type": "Polygon", "coordinates": [cw_ring]},
            },
            context={"request": request},
        )
        self.assertTrue(serializer.is_valid(), serializer.errors)
        result_ring = serializer.validated_data["geojson"]["coordinates"][0]
        # Verify it's no longer the original CW order
        self.assertNotEqual(
            [list(c) for c in result_ring],
            cw_ring,
        )

    def test_validate_geojson_ccw_exterior_unchanged(self):
        """Already counterclockwise exterior ring is unchanged."""
        request = self.factory.post("/")
        request.user = self.user
        # CCW exterior: (0,0) → (1,0) → (1,1) → (0,1) → (0,0)
        ccw_ring = [[0, 0], [0.1, 0], [0.1, 0.1], [0, 0.1], [0, 0]]
        serializer = AreaOfInterestCreateSerializer(
            data={
                "name": "Test Area",
                "country": self.country.id,
                "geojson": {"type": "Polygon", "coordinates": [ccw_ring]},
            },
            context={"request": request},
        )
        self.assertTrue(serializer.is_valid(), serializer.errors)
        result_ring = serializer.validated_data["geojson"]["coordinates"][0]
        self.assertEqual(
            [list(c) for c in result_ring],
            ccw_ring,
        )

    def test_validate_geojson_fixes_winding_multipolygon(self):
        """Clockwise MultiPolygon exterior is auto-corrected."""
        request = self.factory.post("/")
        request.user = self.user
        cw_ring = [[0, 0], [0, 0.1], [0.1, 0.1], [0.1, 0], [0, 0]]
        serializer = AreaOfInterestCreateSerializer(
            data={
                "name": "Test Area",
                "country": self.country.id,
                "geojson": {
                    "type": "MultiPolygon",
                    "coordinates": [[cw_ring]],
                },
            },
            context={"request": request},
        )
        self.assertTrue(serializer.is_valid(), serializer.errors)
        result_ring = serializer.validated_data["geojson"]["coordinates"][0][0]
        self.assertNotEqual(
            [list(c) for c in result_ring],
            cw_ring,
        )

    def test_validate_geojson_fixes_hole_winding(self):
        """Hole with wrong winding (CCW instead of CW) is corrected."""
        request = self.factory.post("/")
        request.user = self.user
        # CCW exterior (correct)
        exterior = [[0, 0], [0.1, 0], [0.1, 0.1], [0, 0.1], [0, 0]]
        # CCW hole (incorrect — should be CW)
        hole_ccw = [
            [0.02, 0.02],
            [0.08, 0.02],
            [0.08, 0.08],
            [0.02, 0.08],
            [0.02, 0.02],
        ]
        serializer = AreaOfInterestCreateSerializer(
            data={
                "name": "Test Area",
                "country": self.country.id,
                "geojson": {
                    "type": "Polygon",
                    "coordinates": [exterior, hole_ccw],
                },
            },
            context={"request": request},
        )
        self.assertTrue(serializer.is_valid(), serializer.errors)
        result_hole = serializer.validated_data["geojson"]["coordinates"][1]
        # After fix, hole should be CW — different from the input CCW
        self.assertNotEqual(
            [list(c) for c in result_hole],
            hole_ccw,
        )

    def test_validate_geojson_feature_collection_fixes_winding(self):
        """FeatureCollection with CW polygon features gets per-feature fix."""
        request = self.factory.post("/")
        request.user = self.user
        cw_ring = [[0, 0], [0, 0.1], [0.1, 0.1], [0.1, 0], [0, 0]]
        serializer = AreaOfInterestCreateSerializer(
            data={
                "name": "Test Area",
                "country": self.country.id,
                "geojson": {
                    "type": "FeatureCollection",
                    "features": [
                        {
                            "type": "Feature",
                            "geometry": {
                                "type": "Polygon",
                                "coordinates": [cw_ring],
                            },
                            "properties": {},
                        }
                    ],
                },
            },
            context={"request": request},
        )
        self.assertTrue(serializer.is_valid(), serializer.errors)
        result_ring = serializer.validated_data["geojson"]["features"][0]["geometry"][
            "coordinates"
        ][0]
        self.assertNotEqual(
            [list(c) for c in result_ring],
            cw_ring,
        )

    # --- RFC 7946 Relaxed: defensive error handling ---

    def test_validate_geojson_malformed_ring_structure(self):
        """Malformed ring structure produces translated error, never 500."""
        request = self.factory.post("/")
        request.user = self.user
        serializer = AreaOfInterestCreateSerializer(
            data={
                "name": "Test Area",
                "country": self.country.id,
                "geojson": {
                    "type": "Polygon",
                    "coordinates": ["not-a-ring"],
                },
            },
            context={"request": request},
        )
        self.assertFalse(serializer.is_valid())
        self.assertIn("geojson", serializer.errors)

    def test_validate_ring_closure_non_iterable_coords(self):
        """Non-iterable coordinates in ring closure check → translated error."""
        request = self.factory.post("/")
        request.user = self.user
        serializer = AreaOfInterestCreateSerializer(
            data={
                "name": "Test Area",
                "country": self.country.id,
                "geojson": {
                    "type": "Polygon",
                    "coordinates": 42,
                },
            },
            context={"request": request},
        )
        self.assertFalse(serializer.is_valid())
        self.assertIn("geojson", serializer.errors)

    def test_validate_nested_gc_non_iterable_geometries(self):
        """Non-iterable geometries list → translated error, not 500."""
        request = self.factory.post("/")
        request.user = self.user
        serializer = AreaOfInterestCreateSerializer(
            data={
                "name": "Test Area",
                "country": self.country.id,
                "geojson": {
                    "type": "Feature",
                    "geometry": {
                        "type": "GeometryCollection",
                        "geometries": 42,
                    },
                    "properties": {},
                },
            },
            context={"request": request},
        )
        self.assertFalse(serializer.is_valid())
        self.assertIn("geojson", serializer.errors)

    @patch("wildfire_assessment.serializers.orient", side_effect=Exception("boom"))
    def test_fix_winding_order_failure_silently_skipped(self, _mock_orient):
        """If orient() fails, geometry is kept as-is (no 500)."""
        request = self.factory.post("/")
        request.user = self.user
        serializer = AreaOfInterestCreateSerializer(
            data={
                "name": "Test Area",
                "country": self.country.id,
                "geojson": {
                    "type": "Polygon",
                    "coordinates": [[[0, 0], [0.1, 0], [0.1, 0.1], [0, 0.1], [0, 0]]],
                },
            },
            context={"request": request},
        )
        self.assertTrue(serializer.is_valid(), serializer.errors)

    def test_validate_geojson_feature_strips_crs(self):
        """Feature with 'crs' field passes, crs removed."""
        request = self.factory.post("/")
        request.user = self.user
        geojson = {
            "type": "Feature",
            "crs": {"type": "name", "properties": {"name": "EPSG:4326"}},
            "geometry": {
                "type": "Polygon",
                "coordinates": [[[0, 0], [0.1, 0], [0.1, 0.1], [0, 0.1], [0, 0]]],
            },
            "properties": {},
        }
        serializer = AreaOfInterestCreateSerializer(
            data={
                "name": "Test Area",
                "country": self.country.id,
                "geojson": geojson,
            },
            context={"request": request},
        )
        self.assertTrue(serializer.is_valid(), serializer.errors)
        self.assertNotIn("crs", serializer.validated_data["geojson"])

    def test_3d_coordinates_polygon_rejected(self):
        """3D Polygon [lon, lat, z] → rejected with translated error."""
        request = self.factory.post("/")
        request.user = self.user
        geojson = {
            "type": "Polygon",
            "coordinates": [
                [
                    [0, 0, 0.0],
                    [1, 0, 0.0],
                    [1, 1, 0.0],
                    [0, 1, 0.0],
                    [0, 0, 0.0],
                ]
            ],
        }
        serializer = AreaOfInterestCreateSerializer(
            data={
                "name": "Test Area",
                "country": self.country.id,
                "geojson": geojson,
            },
            context={"request": request},
        )
        self.assertFalse(serializer.is_valid())
        self.assertIn("geojson", serializer.errors)
        self.assertIn("3D", serializer.errors["geojson"][0])

    def test_3d_coordinates_multipolygon_rejected(self):
        """3D MultiPolygon → rejected with translated error."""
        request = self.factory.post("/")
        request.user = self.user
        geojson = {
            "type": "MultiPolygon",
            "coordinates": [
                [
                    [
                        [0, 0, 5.0],
                        [1, 0, 5.0],
                        [1, 1, 5.0],
                        [0, 1, 5.0],
                        [0, 0, 5.0],
                    ]
                ],
            ],
        }
        serializer = AreaOfInterestCreateSerializer(
            data={
                "name": "Test Area",
                "country": self.country.id,
                "geojson": geojson,
            },
            context={"request": request},
        )
        self.assertFalse(serializer.is_valid())
        self.assertIn("geojson", serializer.errors)
        self.assertIn("3D", serializer.errors["geojson"][0])

    def test_3d_coordinates_feature_rejected(self):
        """3D Feature geometry → rejected with translated error."""
        request = self.factory.post("/")
        request.user = self.user
        geojson = {
            "type": "Feature",
            "geometry": {
                "type": "Polygon",
                "coordinates": [
                    [
                        [0, 0, 0.0],
                        [1, 0, 0.0],
                        [1, 1, 0.0],
                        [0, 1, 0.0],
                        [0, 0, 0.0],
                    ]
                ],
            },
            "properties": {},
        }
        serializer = AreaOfInterestCreateSerializer(
            data={
                "name": "Test Area",
                "country": self.country.id,
                "geojson": geojson,
            },
            context={"request": request},
        )
        self.assertFalse(serializer.is_valid())
        self.assertIn("geojson", serializer.errors)

    def test_3d_coordinates_feature_collection_rejected(self):
        """3D FeatureCollection → rejected with translated error."""
        request = self.factory.post("/")
        request.user = self.user
        geojson = {
            "type": "FeatureCollection",
            "features": [
                {
                    "type": "Feature",
                    "geometry": {
                        "type": "Polygon",
                        "coordinates": [
                            [
                                [0, 0, 0.0],
                                [1, 0, 0.0],
                                [1, 1, 0.0],
                                [0, 1, 0.0],
                                [0, 0, 0.0],
                            ]
                        ],
                    },
                    "properties": {},
                }
            ],
        }
        serializer = AreaOfInterestCreateSerializer(
            data={
                "name": "Test Area",
                "country": self.country.id,
                "geojson": geojson,
            },
            context={"request": request},
        )
        self.assertFalse(serializer.is_valid())
        self.assertIn("geojson", serializer.errors)

    def test_2d_coordinates_accepted(self):
        """2D coordinates pass validation normally."""
        request = self.factory.post("/")
        request.user = self.user
        geojson = {
            "type": "Polygon",
            "coordinates": [[[0, 0], [0.1, 0], [0.1, 0.1], [0, 0.1], [0, 0]]],
        }
        serializer = AreaOfInterestCreateSerializer(
            data={
                "name": "Test Area",
                "country": self.country.id,
                "geojson": geojson,
            },
            context={"request": request},
        )
        self.assertTrue(serializer.is_valid(), serializer.errors)

    def test_3d_qgis_style_geojson_rejected(self):
        """Real-world QGIS GeoJSON with CRS + 3D coords → rejected."""
        request = self.factory.post("/")
        request.user = self.user
        geojson = {
            "type": "FeatureCollection",
            "name": "test_area",
            "crs": {
                "type": "name",
                "properties": {"name": "urn:ogc:def:crs:OGC:1.3:CRS84"},
            },
            "features": [
                {
                    "type": "Feature",
                    "properties": {"Shape_Leng": 2.127},
                    "geometry": {
                        "type": "MultiPolygon",
                        "coordinates": [
                            [
                                [
                                    [34.857, -18.337, 0.0],
                                    [35.304, -18.268, 0.0],
                                    [35.522, -18.788, 0.0],
                                    [35.034, -18.917, 0.0],
                                    [34.857, -18.337, 0.0],
                                ]
                            ]
                        ],
                    },
                }
            ],
        }
        serializer = AreaOfInterestCreateSerializer(
            data={
                "name": "Test Area",
                "country": self.country.id,
                "geojson": geojson,
            },
            context={"request": request},
        )
        self.assertFalse(serializer.is_valid())
        self.assertIn("geojson", serializer.errors)
        self.assertIn("3D", serializer.errors["geojson"][0])

    def test_3d_coordinates_translated_pt_br(self):
        """3D coordinate error is translated to pt-BR."""
        request = self.factory.post("/")
        request.user = self.user
        UserProfile.objects.update_or_create(
            user=self.user, defaults={"default_language": "pt-BR"}
        )
        geojson = {
            "type": "Polygon",
            "coordinates": [
                [[0, 0, 0.0], [1, 0, 0.0], [1, 1, 0.0], [0, 1, 0.0], [0, 0, 0.0]]
            ],
        }
        serializer = AreaOfInterestCreateSerializer(
            data={
                "name": "Test Area",
                "country": self.country.id,
                "geojson": geojson,
            },
            context={"request": request},
        )
        self.assertFalse(serializer.is_valid())
        self.assertIn("3D", serializer.errors["geojson"][0])

    def test_3d_validation_depth_guard(self):
        """Recursion depth > 10 stops without error (safety guard)."""
        request = self.factory.post("/")
        request.user = self.user
        serializer = AreaOfInterestCreateSerializer(
            data={
                "name": "Test Area",
                "country": self.country.id,
                "geojson": {"type": "Polygon", "coordinates": []},
            },
            context={"request": request},
        )
        # Call the method directly with depth > 10; should return without error
        serializer._validate_coordinates([0, 0, 0.0], "geometry", depth=11)

    # --- Position validation (RFC 7946 §3.1.1) ---

    def test_shapely_parse_failure_still_caught(self):
        """Valid coordinates but wrong nesting depth → shapely parse error."""
        request = self.factory.post("/")
        request.user = self.user
        serializer = AreaOfInterestCreateSerializer(
            data={
                "name": "Test Area",
                "country": self.country.id,
                "geojson": {
                    "type": "Polygon",
                    "coordinates": [0, 0],
                },
            },
            context={"request": request},
        )
        self.assertFalse(serializer.is_valid())
        self.assertIn("geojson", serializer.errors)

    def test_feature_id_null_accepted(self):
        """Feature with 'id': null passes (no id)."""
        request = self.factory.post("/")
        request.user = self.user
        serializer = AreaOfInterestCreateSerializer(
            data={
                "name": "Test Area",
                "country": self.country.id,
                "geojson": {
                    "type": "Feature",
                    "id": None,
                    "geometry": {
                        "type": "Polygon",
                        "coordinates": [
                            [[0, 0], [0.1, 0], [0.1, 0.1], [0, 0.1], [0, 0]]
                        ],
                    },
                    "properties": {},
                },
            },
            context={"request": request},
        )
        self.assertTrue(serializer.is_valid(), serializer.errors)

    def test_position_single_element_rejected(self):
        """Position with only 1 element → error."""
        request = self.factory.post("/")
        request.user = self.user
        serializer = AreaOfInterestCreateSerializer(
            data={
                "name": "Test Area",
                "country": self.country.id,
                "geojson": {
                    "type": "Polygon",
                    "coordinates": [[[10], [20], [30], [10]]],
                },
            },
            context={"request": request},
        )
        self.assertFalse(serializer.is_valid())
        self.assertIn("geojson", serializer.errors)

    def test_position_non_numeric_rejected(self):
        """Position with non-numeric values → error."""
        request = self.factory.post("/")
        request.user = self.user
        serializer = AreaOfInterestCreateSerializer(
            data={
                "name": "Test Area",
                "country": self.country.id,
                "geojson": {
                    "type": "Polygon",
                    "coordinates": [[["a", "b"], ["c", "d"], ["e", "f"], ["a", "b"]]],
                },
            },
            context={"request": request},
        )
        self.assertFalse(serializer.is_valid())
        self.assertIn("geojson", serializer.errors)

    def test_position_mixed_types_rejected(self):
        """Position like [1, "b"] → error."""
        request = self.factory.post("/")
        request.user = self.user
        serializer = AreaOfInterestCreateSerializer(
            data={
                "name": "Test Area",
                "country": self.country.id,
                "geojson": {
                    "type": "Polygon",
                    "coordinates": [[[1, "b"], [2, "c"], [3, "d"], [1, "b"]]],
                },
            },
            context={"request": request},
        )
        self.assertFalse(serializer.is_valid())
        self.assertIn("geojson", serializer.errors)

    def test_position_non_list_non_number_rejected(self):
        """Dict inside coordinates → error."""
        request = self.factory.post("/")
        request.user = self.user
        serializer = AreaOfInterestCreateSerializer(
            data={
                "name": "Test Area",
                "country": self.country.id,
                "geojson": {
                    "type": "Polygon",
                    "coordinates": [[{"x": 1}]],
                },
            },
            context={"request": request},
        )
        self.assertFalse(serializer.is_valid())
        self.assertIn("geojson", serializer.errors)

    # --- FC feature type validation (RFC 7946 §3.3) ---

    def test_fc_feature_missing_type_rejected(self):
        """Feature in FC without 'type' key → error."""
        request = self.factory.post("/")
        request.user = self.user
        serializer = AreaOfInterestCreateSerializer(
            data={
                "name": "Test Area",
                "country": self.country.id,
                "geojson": {
                    "type": "FeatureCollection",
                    "features": [
                        {
                            "geometry": {
                                "type": "Polygon",
                                "coordinates": [
                                    [[0, 0], [0.1, 0], [0.1, 0.1], [0, 0.1], [0, 0]]
                                ],
                            },
                            "properties": {},
                        }
                    ],
                },
            },
            context={"request": request},
        )
        self.assertFalse(serializer.is_valid())
        self.assertIn("geojson", serializer.errors)

    def test_fc_feature_wrong_type_rejected(self):
        """Feature in FC with type 'Polygon' instead of 'Feature' → error."""
        request = self.factory.post("/")
        request.user = self.user
        serializer = AreaOfInterestCreateSerializer(
            data={
                "name": "Test Area",
                "country": self.country.id,
                "geojson": {
                    "type": "FeatureCollection",
                    "features": [
                        {
                            "type": "Polygon",
                            "coordinates": [
                                [[0, 0], [0.1, 0], [0.1, 0.1], [0, 0.1], [0, 0]]
                            ],
                        }
                    ],
                },
            },
            context={"request": request},
        )
        self.assertFalse(serializer.is_valid())
        self.assertIn("geojson", serializer.errors)

    # --- Feature properties validation (RFC 7946 §3.2) ---

    def test_feature_missing_properties_rejected(self):
        """Top-level Feature without 'properties' → error."""
        request = self.factory.post("/")
        request.user = self.user
        serializer = AreaOfInterestCreateSerializer(
            data={
                "name": "Test Area",
                "country": self.country.id,
                "geojson": {
                    "type": "Feature",
                    "geometry": {
                        "type": "Polygon",
                        "coordinates": [
                            [[0, 0], [0.1, 0], [0.1, 0.1], [0, 0.1], [0, 0]]
                        ],
                    },
                },
            },
            context={"request": request},
        )
        self.assertFalse(serializer.is_valid())
        self.assertIn("geojson", serializer.errors)
        self.assertIn("properties", serializer.errors["geojson"][0])

    def test_feature_null_properties_accepted(self):
        """Feature with 'properties': null passes (RFC allows null)."""
        request = self.factory.post("/")
        request.user = self.user
        serializer = AreaOfInterestCreateSerializer(
            data={
                "name": "Test Area",
                "country": self.country.id,
                "geojson": {
                    "type": "Feature",
                    "geometry": {
                        "type": "Polygon",
                        "coordinates": [
                            [[0, 0], [0.1, 0], [0.1, 0.1], [0, 0.1], [0, 0]]
                        ],
                    },
                    "properties": None,
                },
            },
            context={"request": request},
        )
        self.assertTrue(serializer.is_valid(), serializer.errors)

    def test_fc_feature_missing_properties_rejected(self):
        """Feature in FC without 'properties' → error."""
        request = self.factory.post("/")
        request.user = self.user
        serializer = AreaOfInterestCreateSerializer(
            data={
                "name": "Test Area",
                "country": self.country.id,
                "geojson": {
                    "type": "FeatureCollection",
                    "features": [
                        {
                            "type": "Feature",
                            "geometry": {
                                "type": "Polygon",
                                "coordinates": [
                                    [[0, 0], [0.1, 0], [0.1, 0.1], [0, 0.1], [0, 0]]
                                ],
                            },
                        }
                    ],
                },
            },
            context={"request": request},
        )
        self.assertFalse(serializer.is_valid())
        self.assertIn("geojson", serializer.errors)

    def test_fc_feature_null_properties_accepted(self):
        """Feature in FC with 'properties': null passes."""
        request = self.factory.post("/")
        request.user = self.user
        serializer = AreaOfInterestCreateSerializer(
            data={
                "name": "Test Area",
                "country": self.country.id,
                "geojson": {
                    "type": "FeatureCollection",
                    "features": [
                        {
                            "type": "Feature",
                            "geometry": {
                                "type": "Polygon",
                                "coordinates": [
                                    [[0, 0], [0.1, 0], [0.1, 0.1], [0, 0.1], [0, 0]]
                                ],
                            },
                            "properties": None,
                        }
                    ],
                },
            },
            context={"request": request},
        )
        self.assertTrue(serializer.is_valid(), serializer.errors)

    # --- FC feature geometry validation (RFC 7946 §3.2) ---

    def test_fc_feature_missing_geometry_rejected(self):
        """Feature in FC without 'geometry' → error."""
        request = self.factory.post("/")
        request.user = self.user
        serializer = AreaOfInterestCreateSerializer(
            data={
                "name": "Test Area",
                "country": self.country.id,
                "geojson": {
                    "type": "FeatureCollection",
                    "features": [{"type": "Feature", "properties": {}}],
                },
            },
            context={"request": request},
        )
        self.assertFalse(serializer.is_valid())
        self.assertIn("geojson", serializer.errors)

    def test_fc_feature_null_geometry_rejected(self):
        """Feature in FC with 'geometry': null → error."""
        request = self.factory.post("/")
        request.user = self.user
        serializer = AreaOfInterestCreateSerializer(
            data={
                "name": "Test Area",
                "country": self.country.id,
                "geojson": {
                    "type": "FeatureCollection",
                    "features": [
                        {"type": "Feature", "geometry": None, "properties": {}}
                    ],
                },
            },
            context={"request": request},
        )
        self.assertFalse(serializer.is_valid())
        self.assertIn("geojson", serializer.errors)

    # --- Feature id validation (RFC 7946 §3.2) ---

    def test_feature_id_string_accepted(self):
        """Feature with string id passes."""
        request = self.factory.post("/")
        request.user = self.user
        serializer = AreaOfInterestCreateSerializer(
            data={
                "name": "Test Area",
                "country": self.country.id,
                "geojson": {
                    "type": "Feature",
                    "id": "abc-123",
                    "geometry": {
                        "type": "Polygon",
                        "coordinates": [
                            [[0, 0], [0.1, 0], [0.1, 0.1], [0, 0.1], [0, 0]]
                        ],
                    },
                    "properties": {},
                },
            },
            context={"request": request},
        )
        self.assertTrue(serializer.is_valid(), serializer.errors)

    def test_feature_id_number_accepted(self):
        """Feature with numeric id passes."""
        request = self.factory.post("/")
        request.user = self.user
        serializer = AreaOfInterestCreateSerializer(
            data={
                "name": "Test Area",
                "country": self.country.id,
                "geojson": {
                    "type": "Feature",
                    "id": 42,
                    "geometry": {
                        "type": "Polygon",
                        "coordinates": [
                            [[0, 0], [0.1, 0], [0.1, 0.1], [0, 0.1], [0, 0]]
                        ],
                    },
                    "properties": {},
                },
            },
            context={"request": request},
        )
        self.assertTrue(serializer.is_valid(), serializer.errors)

    def test_feature_id_boolean_rejected(self):
        """Feature with boolean id → error."""
        request = self.factory.post("/")
        request.user = self.user
        serializer = AreaOfInterestCreateSerializer(
            data={
                "name": "Test Area",
                "country": self.country.id,
                "geojson": {
                    "type": "Feature",
                    "id": True,
                    "geometry": {
                        "type": "Polygon",
                        "coordinates": [
                            [[0, 0], [0.1, 0], [0.1, 0.1], [0, 0.1], [0, 0]]
                        ],
                    },
                    "properties": {},
                },
            },
            context={"request": request},
        )
        self.assertFalse(serializer.is_valid())
        self.assertIn("geojson", serializer.errors)

    def test_feature_id_array_rejected(self):
        """Feature with array id → error."""
        request = self.factory.post("/")
        request.user = self.user
        serializer = AreaOfInterestCreateSerializer(
            data={
                "name": "Test Area",
                "country": self.country.id,
                "geojson": {
                    "type": "Feature",
                    "id": [],
                    "geometry": {
                        "type": "Polygon",
                        "coordinates": [
                            [[0, 0], [0.1, 0], [0.1, 0.1], [0, 0.1], [0, 0]]
                        ],
                    },
                    "properties": {},
                },
            },
            context={"request": request},
        )
        self.assertFalse(serializer.is_valid())
        self.assertIn("geojson", serializer.errors)

    def test_feature_id_object_rejected(self):
        """Feature with object id → error."""
        request = self.factory.post("/")
        request.user = self.user
        serializer = AreaOfInterestCreateSerializer(
            data={
                "name": "Test Area",
                "country": self.country.id,
                "geojson": {
                    "type": "Feature",
                    "id": {},
                    "geometry": {
                        "type": "Polygon",
                        "coordinates": [
                            [[0, 0], [0.1, 0], [0.1, 0.1], [0, 0.1], [0, 0]]
                        ],
                    },
                    "properties": {},
                },
            },
            context={"request": request},
        )
        self.assertFalse(serializer.is_valid())
        self.assertIn("geojson", serializer.errors)

    def test_fc_feature_id_boolean_rejected(self):
        """Feature in FC with boolean id → error."""
        request = self.factory.post("/")
        request.user = self.user
        serializer = AreaOfInterestCreateSerializer(
            data={
                "name": "Test Area",
                "country": self.country.id,
                "geojson": {
                    "type": "FeatureCollection",
                    "features": [
                        {
                            "type": "Feature",
                            "id": True,
                            "geometry": {
                                "type": "Polygon",
                                "coordinates": [
                                    [[0, 0], [0.1, 0], [0.1, 0.1], [0, 0.1], [0, 0]]
                                ],
                            },
                            "properties": {},
                        }
                    ],
                },
            },
            context={"request": request},
        )
        self.assertFalse(serializer.is_valid())
        self.assertIn("geojson", serializer.errors)

    # --- Bbox validation (RFC 7946 §5) ---

    def test_bbox_valid_accepted(self):
        """Valid bbox with 4 numbers passes."""
        request = self.factory.post("/")
        request.user = self.user
        serializer = AreaOfInterestCreateSerializer(
            data={
                "name": "Test Area",
                "country": self.country.id,
                "geojson": {
                    "type": "Polygon",
                    "bbox": [-0.05, -0.05, 0.05, 0.05],
                    "coordinates": [
                        [
                            [-0.05, -0.05],
                            [0.05, -0.05],
                            [0.05, 0.05],
                            [-0.05, 0.05],
                            [-0.05, -0.05],
                        ]
                    ],
                },
            },
            context={"request": request},
        )
        self.assertTrue(serializer.is_valid(), serializer.errors)

    def test_bbox_not_array_rejected(self):
        """bbox that is not an array → error."""
        request = self.factory.post("/")
        request.user = self.user
        serializer = AreaOfInterestCreateSerializer(
            data={
                "name": "Test Area",
                "country": self.country.id,
                "geojson": {
                    "type": "Polygon",
                    "bbox": "invalid",
                    "coordinates": [[[0, 0], [0.1, 0], [0.1, 0.1], [0, 0.1], [0, 0]]],
                },
            },
            context={"request": request},
        )
        self.assertFalse(serializer.is_valid())
        self.assertIn("geojson", serializer.errors)

    def test_bbox_wrong_length_rejected(self):
        """bbox with 3 elements → error."""
        request = self.factory.post("/")
        request.user = self.user
        serializer = AreaOfInterestCreateSerializer(
            data={
                "name": "Test Area",
                "country": self.country.id,
                "geojson": {
                    "type": "Polygon",
                    "bbox": [1, 2, 3],
                    "coordinates": [[[0, 0], [0.1, 0], [0.1, 0.1], [0, 0.1], [0, 0]]],
                },
            },
            context={"request": request},
        )
        self.assertFalse(serializer.is_valid())
        self.assertIn("geojson", serializer.errors)

    def test_bbox_non_numeric_rejected(self):
        """bbox with non-numeric element → error."""
        request = self.factory.post("/")
        request.user = self.user
        serializer = AreaOfInterestCreateSerializer(
            data={
                "name": "Test Area",
                "country": self.country.id,
                "geojson": {
                    "type": "Polygon",
                    "bbox": [1, 2, "a", 4],
                    "coordinates": [[[0, 0], [0.1, 0], [0.1, 0.1], [0, 0.1], [0, 0]]],
                },
            },
            context={"request": request},
        )
        self.assertFalse(serializer.is_valid())
        self.assertIn("geojson", serializer.errors)

    def test_bbox_boolean_element_rejected(self):
        """bbox with boolean element → error."""
        request = self.factory.post("/")
        request.user = self.user
        serializer = AreaOfInterestCreateSerializer(
            data={
                "name": "Test Area",
                "country": self.country.id,
                "geojson": {
                    "type": "Polygon",
                    "bbox": [1, 2, True, 4],
                    "coordinates": [[[0, 0], [0.1, 0], [0.1, 0.1], [0, 0.1], [0, 0]]],
                },
            },
            context={"request": request},
        )
        self.assertFalse(serializer.is_valid())
        self.assertIn("geojson", serializer.errors)

    def test_bbox_latitude_out_of_range_rejected(self):
        """bbox with south latitude out of range → error."""
        request = self.factory.post("/")
        request.user = self.user
        serializer = AreaOfInterestCreateSerializer(
            data={
                "name": "Test Area",
                "country": self.country.id,
                "geojson": {
                    "type": "Polygon",
                    "bbox": [-180, -100, 180, 90],
                    "coordinates": [[[0, 0], [0.1, 0], [0.1, 0.1], [0, 0.1], [0, 0]]],
                },
            },
            context={"request": request},
        )
        self.assertFalse(serializer.is_valid())
        self.assertIn("geojson", serializer.errors)

    def test_bbox_on_feature_collection_validated(self):
        """bbox on FeatureCollection is validated."""
        request = self.factory.post("/")
        request.user = self.user
        serializer = AreaOfInterestCreateSerializer(
            data={
                "name": "Test Area",
                "country": self.country.id,
                "geojson": {
                    "type": "FeatureCollection",
                    "bbox": [1, 2, 3],
                    "features": [
                        {
                            "type": "Feature",
                            "geometry": {
                                "type": "Polygon",
                                "coordinates": [
                                    [[0, 0], [0.1, 0], [0.1, 0.1], [0, 0.1], [0, 0]]
                                ],
                            },
                            "properties": {},
                        }
                    ],
                },
            },
            context={"request": request},
        )
        self.assertFalse(serializer.is_valid())
        self.assertIn("geojson", serializer.errors)

    def test_bbox_on_geometry_validated(self):
        """bbox on geometry object is validated."""
        request = self.factory.post("/")
        request.user = self.user
        serializer = AreaOfInterestCreateSerializer(
            data={
                "name": "Test Area",
                "country": self.country.id,
                "geojson": {
                    "type": "Feature",
                    "geometry": {
                        "type": "Polygon",
                        "bbox": "not-an-array",
                        "coordinates": [
                            [[0, 0], [0.1, 0], [0.1, 0.1], [0, 0.1], [0, 0]]
                        ],
                    },
                    "properties": {},
                },
            },
            context={"request": request},
        )
        self.assertFalse(serializer.is_valid())
        self.assertIn("geojson", serializer.errors)

    def test_bbox_defensive_exception(self):
        """Non-standard bbox structure triggers translated error."""
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

        # Call _validate_bbox directly with a pathological object
        # that has bbox as a property but __getitem__ throws
        class BadObj(dict):
            def get(self, key, default=None):
                if key == "bbox":
                    raise RuntimeError("boom")
                return super().get(key, default)

        from rest_framework.exceptions import ValidationError

        with self.assertRaises(ValidationError):
            serializer._validate_bbox(BadObj())


class AreaValidationTests(TestCase):
    """Tests for polygon area size validation (max 110,000 ha)."""

    def setUp(self):
        self.country = Country.objects.create(name="Test Country", code="TC")
        self.user = User.objects.create_user(
            username="tester", email="tester@example.com", password="password"
        )
        UserCountry.objects.create(user=self.user, country=self.country)
        self.factory = APIRequestFactory()

    def _make_serializer(self, geojson):
        request = self.factory.post("/")
        request.user = self.user
        return AreaOfInterestCreateSerializer(
            data={"name": "Test Area", "country": self.country.id, "geojson": geojson},
            context={"request": request},
        )

    def test_small_polygon_passes(self):
        """A 0.1° × 0.1° polygon (~12k ha) should pass."""
        geojson = {
            "type": "Polygon",
            "coordinates": [[[0, 0], [0.1, 0], [0.1, 0.1], [0, 0.1], [0, 0]]],
        }
        serializer = self._make_serializer(geojson)
        self.assertTrue(serializer.is_valid(), serializer.errors)

    def test_large_polygon_rejected(self):
        """A 5° × 5° polygon (~3M ha) should be rejected."""
        geojson = {
            "type": "Polygon",
            "coordinates": [[[0, 0], [5, 0], [5, 5], [0, 5], [0, 0]]],
        }
        serializer = self._make_serializer(geojson)
        self.assertFalse(serializer.is_valid())
        self.assertIn("geojson", serializer.errors)
        self.assertIn(f"{MAX_AREA_HA:,}", str(serializer.errors["geojson"]))

    def test_large_feature_rejected(self):
        """A large Feature should be rejected."""
        geojson = {
            "type": "Feature",
            "geometry": {
                "type": "Polygon",
                "coordinates": [[[0, 0], [5, 0], [5, 5], [0, 5], [0, 0]]],
            },
            "properties": {},
        }
        serializer = self._make_serializer(geojson)
        self.assertFalse(serializer.is_valid())
        self.assertIn("geojson", serializer.errors)

    def test_large_feature_collection_rejected(self):
        """A FeatureCollection whose total area exceeds the limit is rejected."""
        geojson = {
            "type": "FeatureCollection",
            "features": [
                {
                    "type": "Feature",
                    "geometry": {
                        "type": "Polygon",
                        "coordinates": [[[0, 0], [3, 0], [3, 3], [0, 3], [0, 0]]],
                    },
                    "properties": {},
                },
                {
                    "type": "Feature",
                    "geometry": {
                        "type": "Polygon",
                        "coordinates": [
                            [[10, 10], [13, 10], [13, 13], [10, 13], [10, 10]]
                        ],
                    },
                    "properties": {},
                },
            ],
        }
        serializer = self._make_serializer(geojson)
        self.assertFalse(serializer.is_valid())
        self.assertIn("geojson", serializer.errors)

    def test_large_multipolygon_rejected(self):
        """A large MultiPolygon should be rejected."""
        geojson = {
            "type": "MultiPolygon",
            "coordinates": [
                [[[0, 0], [5, 0], [5, 5], [0, 5], [0, 0]]],
            ],
        }
        serializer = self._make_serializer(geojson)
        self.assertFalse(serializer.is_valid())
        self.assertIn("geojson", serializer.errors)

    def test_area_error_translated_pt_br(self):
        """Area error message should be translated to pt-BR."""
        profile = self.user.profile
        profile.default_language = "pt-BR"
        profile.save()
        geojson = {
            "type": "Polygon",
            "coordinates": [[[0, 0], [5, 0], [5, 5], [0, 5], [0, 0]]],
        }
        serializer = self._make_serializer(geojson)
        self.assertFalse(serializer.is_valid())
        error_msg = str(serializer.errors["geojson"])
        self.assertIn("excede o tamanho", error_msg)

    def test_area_error_translated_fr(self):
        """Area error message should be translated to French."""
        profile = self.user.profile
        profile.default_language = "fr"
        profile.save()
        geojson = {
            "type": "Polygon",
            "coordinates": [[[0, 0], [5, 0], [5, 5], [0, 5], [0, 0]]],
        }
        serializer = self._make_serializer(geojson)
        self.assertFalse(serializer.is_valid())
        error_msg = str(serializer.errors["geojson"])
        self.assertIn("dépasse la taille", error_msg)

    def test_max_area_ha_constant(self):
        """MAX_AREA_HA should be 110,000."""
        self.assertEqual(MAX_AREA_HA, 110_000)

    @patch("wildfire_assessment.serializers.Geod")
    def test_area_computation_failure_does_not_block(self, mock_geod):
        """If area computation fails, validation should still pass."""
        mock_geod.side_effect = RuntimeError("pyproj error")
        geojson = {
            "type": "Polygon",
            "coordinates": [[[0, 0], [0.1, 0], [0.1, 0.1], [0, 0.1], [0, 0]]],
        }
        serializer = self._make_serializer(geojson)
        self.assertTrue(serializer.is_valid(), serializer.errors)


class DegenerateMultiPolygonPartTests(TestCase):
    """Tests for rejection of MultiPolygons with tiny/degenerate parts.

    Digitization artifacts (e.g. a stray 4-vertex sliver with ~3 m² area)
    dramatically inflate the bounding box and break downstream image
    generation. We reject such uploads so the user can fix the source file.
    """

    # The real Gorongosa sliver from the reproducer case — ~3.5 m²
    GORONGOSA_STRAY = [
        [34.36994289621235, -19.229362147906397],
        [34.369958985759034, -19.229383619014765],
        [34.36994090971726, -19.22939670914272],
        [34.36994289621235, -19.229362147906397],
    ]
    # A normal sized polygon (~12k ha at the equator)
    REAL_POLYGON_RING = [[0, 0], [0.1, 0], [0.1, 0.1], [0, 0.1], [0, 0]]

    def setUp(self):
        self.country = Country.objects.create(name="Test Country", code="TC")
        self.user = User.objects.create_user(
            username="tester", email="tester@example.com", password="password"
        )
        UserCountry.objects.create(user=self.user, country=self.country)
        self.factory = APIRequestFactory()

    def _make_serializer(self, geojson):
        request = self.factory.post("/")
        request.user = self.user
        return AreaOfInterestCreateSerializer(
            data={"name": "Test Area", "country": self.country.id, "geojson": geojson},
            context={"request": request},
        )

    def test_multipolygon_with_stray_sliver_rejected(self):
        """MultiPolygon with a real Gorongosa-like stray sliver must fail."""
        geojson = {
            "type": "MultiPolygon",
            "coordinates": [
                [self.REAL_POLYGON_RING],
                [self.GORONGOSA_STRAY],
            ],
        }
        serializer = self._make_serializer(geojson)
        self.assertFalse(serializer.is_valid())
        self.assertIn("geojson", serializer.errors)
        error_msg = str(serializer.errors["geojson"])
        # Message must be actionable: identify the stray and suggest a fix
        self.assertIn("too small", error_msg.lower())
        self.assertIn("remove", error_msg.lower())

    def test_multipolygon_all_valid_parts_passes(self):
        """MultiPolygon with two real-sized polygons must still pass."""
        geojson = {
            "type": "MultiPolygon",
            "coordinates": [
                [self.REAL_POLYGON_RING],
                [[[1, 1], [1.1, 1], [1.1, 1.1], [1, 1.1], [1, 1]]],
            ],
        }
        serializer = self._make_serializer(geojson)
        self.assertTrue(serializer.is_valid(), serializer.errors)

    def test_single_polygon_unaffected(self):
        """A plain Polygon upload must not be touched by MultiPolygon check."""
        geojson = {
            "type": "Polygon",
            "coordinates": [self.REAL_POLYGON_RING],
        }
        serializer = self._make_serializer(geojson)
        self.assertTrue(serializer.is_valid(), serializer.errors)

    def test_feature_with_degenerate_multipolygon_rejected(self):
        """Feature wrapping a bad MultiPolygon must also be rejected."""
        geojson = {
            "type": "Feature",
            "geometry": {
                "type": "MultiPolygon",
                "coordinates": [
                    [self.REAL_POLYGON_RING],
                    [self.GORONGOSA_STRAY],
                ],
            },
            "properties": {},
        }
        serializer = self._make_serializer(geojson)
        self.assertFalse(serializer.is_valid())
        self.assertIn("geojson", serializer.errors)

    def test_degenerate_error_translated_pt_br(self):
        """Error message must appear in pt-BR when user prefers Portuguese."""
        profile = self.user.profile
        profile.default_language = "pt-BR"
        profile.save()
        geojson = {
            "type": "MultiPolygon",
            "coordinates": [
                [self.REAL_POLYGON_RING],
                [self.GORONGOSA_STRAY],
            ],
        }
        serializer = self._make_serializer(geojson)
        self.assertFalse(serializer.is_valid())
        error_msg = str(serializer.errors["geojson"])
        # Portuguese phrasing — "pequeno demais" / "remova"
        self.assertIn("pequeno demais", error_msg)
        self.assertIn("remova", error_msg.lower())

    def test_degenerate_error_translated_fr(self):
        """Error message must appear in French when user prefers French."""
        profile = self.user.profile
        profile.default_language = "fr"
        profile.save()
        geojson = {
            "type": "MultiPolygon",
            "coordinates": [
                [self.REAL_POLYGON_RING],
                [self.GORONGOSA_STRAY],
            ],
        }
        serializer = self._make_serializer(geojson)
        self.assertFalse(serializer.is_valid())
        error_msg = str(serializer.errors["geojson"])
        self.assertIn("trop petit", error_msg)

    def test_degenerate_error_translated_es(self):
        """Error message must appear in es-ES when user prefers Spanish."""
        profile = self.user.profile
        profile.default_language = "es-ES"
        profile.save()
        geojson = {
            "type": "MultiPolygon",
            "coordinates": [
                [self.REAL_POLYGON_RING],
                [self.GORONGOSA_STRAY],
            ],
        }
        serializer = self._make_serializer(geojson)
        self.assertFalse(serializer.is_valid())
        error_msg = str(serializer.errors["geojson"])
        self.assertIn("demasiado pequeño", error_msg)


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
            "coordinates": [[[0, 0], [0.1, 0], [0.1, 0.1], [0, 0.1], [0, 0]]],
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

    @patch("wildfire_assessment.serializers.delete_polygon")
    @patch("wildfire_assessment.serializers.upload_polygon")
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

    @patch("wildfire_assessment.serializers.get_signed_image_url")
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
        self.assertEqual(
            data["rgb_post_fire_url"], "https://s3.example.com/abc/post.jpg"
        )
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

    def test_serializer_includes_error_fields(self):
        run = AnalysisRun.objects.create(
            user=self.user,
            area_of_interest=self.area,
            pre_fire_date="2024-01-01",
            post_fire_date="2024-01-15",
            scientific_dnbr_error="GEE timeout",
            scientific_rbr_error="Task is no longer running",
        )
        data = AnalysisRunSerializer(run).data
        self.assertEqual(data["scientific_dnbr_error"], "GEE timeout")
        self.assertEqual(data["scientific_rbr_error"], "Task is no longer running")
        self.assertIsNone(data["scientific_rgb_pre_fire_error"])
        self.assertIsNone(data["scientific_rgb_post_fire_error"])
        self.assertIsNone(data["scientific_dndvi_error"])

    def test_report_summary_in_serialized_output(self):
        self.analysis = AnalysisRun.objects.create(
            user=self.user,
            area_of_interest=self.area,
            pre_fire_date="2024-01-01",
            post_fire_date="2024-01-15",
        )
        self.analysis.report_summary = "# Test Report\nSome content"
        self.analysis.report_summary_language = "en"
        self.analysis.save()
        serializer = AnalysisRunSerializer(self.analysis)
        self.assertIn("report_summary", serializer.data)
        self.assertEqual(
            serializer.data["report_summary"], "# Test Report\nSome content"
        )
        self.assertIn("report_summary_language", serializer.data)
        self.assertEqual(serializer.data["report_summary_language"], "en")


class AreaOfInterestCreateCentroidTests(TestCase):
    """Tests for centroid computation branches in create serializer."""

    def setUp(self):
        self.country = Country.objects.create(name="Centroid Country", code="CC")
        self.user = User.objects.create_user(
            username="centroid", email="centroid@example.com", password="pw"
        )
        UserCountry.objects.create(user=self.user, country=self.country)
        self.factory = APIRequestFactory()

    @patch("wildfire_assessment.serializers.upload_polygon")
    def test_create_centroid_from_feature_collection(self, _mock_upload):
        request = self.factory.post("/")
        request.user = self.user
        geojson = {
            "type": "FeatureCollection",
            "features": [
                {
                    "type": "Feature",
                    "geometry": {
                        "type": "Polygon",
                        "coordinates": [
                            [[0, 0], [0.1, 0], [0.1, 0.1], [0, 0.1], [0, 0]]
                        ],
                    },
                    "properties": {},
                }
            ],
        }
        serializer = AreaOfInterestCreateSerializer(
            data={
                "name": "FC Centroid",
                "country": self.country.id,
                "geojson": geojson,
            },
            context={"request": request},
        )
        self.assertTrue(serializer.is_valid(), serializer.errors)
        instance = serializer.save()
        self.assertIsNotNone(instance.centroid_lat)
        self.assertIsNotNone(instance.centroid_lng)
        self.assertAlmostEqual(float(instance.centroid_lat), 0.05, places=5)
        self.assertAlmostEqual(float(instance.centroid_lng), 0.05, places=5)
        self.assertIsNotNone(instance.area_ha)
        self.assertGreater(instance.area_ha, 0)

    @patch("wildfire_assessment.serializers.upload_polygon")
    def test_create_centroid_from_raw_polygon(self, _mock_upload):
        request = self.factory.post("/")
        request.user = self.user
        geojson = {
            "type": "Polygon",
            "coordinates": [[[0, 0], [0.1, 0], [0.1, 0.1], [0, 0.1], [0, 0]]],
        }
        serializer = AreaOfInterestCreateSerializer(
            data={
                "name": "Raw Centroid",
                "country": self.country.id,
                "geojson": geojson,
            },
            context={"request": request},
        )
        self.assertTrue(serializer.is_valid(), serializer.errors)
        instance = serializer.save()
        self.assertIsNotNone(instance.centroid_lat)
        self.assertAlmostEqual(float(instance.centroid_lat), 0.05, places=5)

    @patch("wildfire_assessment.serializers.upload_polygon")
    def test_create_centroid_exception_silenced(self, _mock_upload):
        """Test that centroid computation exception doesn't break create."""
        request = self.factory.post("/")
        request.user = self.user
        geojson = {
            "type": "Feature",
            "geometry": {
                "type": "Polygon",
                "coordinates": [[[0, 0], [0.1, 0], [0.1, 0.1], [0, 0.1], [0, 0]]],
            },
            "properties": {},
        }
        serializer = AreaOfInterestCreateSerializer(
            data={
                "name": "Error Centroid",
                "country": self.country.id,
                "geojson": geojson,
            },
            context={"request": request},
        )
        self.assertTrue(serializer.is_valid(), serializer.errors)
        with patch(
            "wildfire_assessment.serializers.shape", side_effect=Exception("bad")
        ):
            instance = serializer.save()
        self.assertEqual(instance.name, "Error Centroid")
        # Centroid should be None since the exception was silenced
        self.assertIsNone(instance.centroid_lat)


class AreaOfInterestUpdateCentroidTests(TestCase):
    """Tests for centroid computation and edge cases in update serializer."""

    def setUp(self):
        self.country = Country.objects.create(name="Upd Country", code="UP")
        self.user = User.objects.create_user(
            username="upduser", email="upd@example.com", password="pw"
        )
        UserCountry.objects.create(user=self.user, country=self.country)
        self.factory = APIRequestFactory()
        self.valid_polygon = {
            "type": "Polygon",
            "coordinates": [[[0, 0], [0.1, 0], [0.1, 0.1], [0, 0.1], [0, 0]]],
        }

    @patch("wildfire_assessment.serializers.upload_polygon")
    def test_update_with_geojson_no_existing_polygon(self, _mock_upload):
        """Test update when instance has no existing polygon_path."""
        area = AreaOfInterest.objects.create(
            name="No Path Area",
            polygon_path="",
            country=self.country,
        )
        request = self.factory.patch("/")
        request.user = self.user
        serializer = AreaOfInterestUpdateSerializer(
            area,
            data={"geojson": self.valid_polygon},
            partial=True,
            context={"request": request},
        )
        self.assertTrue(serializer.is_valid(), serializer.errors)
        # Should not call delete since polygon_path is empty
        with patch("wildfire_assessment.serializers.delete_polygon") as mock_delete:
            updated = serializer.save()
        mock_delete.assert_not_called()
        self.assertTrue(updated.polygon_path.endswith(".geojson"))
        self.assertIsNotNone(updated.area_ha)
        self.assertGreater(updated.area_ha, 0)

    @patch("wildfire_assessment.serializers.delete_polygon")
    @patch("wildfire_assessment.serializers.upload_polygon")
    def test_update_centroid_from_feature(self, _mock_upload, _mock_delete):
        """Test centroid computation from a Feature GeoJSON on update."""
        area = AreaOfInterest.objects.create(
            name="Feature Update", polygon_path="old.geojson", country=self.country
        )
        request = self.factory.patch("/")
        request.user = self.user
        geojson = {
            "type": "Feature",
            "geometry": {
                "type": "Polygon",
                "coordinates": [[[0, 0], [0.1, 0], [0.1, 0.1], [0, 0.1], [0, 0]]],
            },
            "properties": {},
        }
        serializer = AreaOfInterestUpdateSerializer(
            area,
            data={"geojson": geojson},
            partial=True,
            context={"request": request},
        )
        self.assertTrue(serializer.is_valid(), serializer.errors)
        updated = serializer.save()
        self.assertAlmostEqual(float(updated.centroid_lat), 0.05, places=5)
        self.assertAlmostEqual(float(updated.centroid_lng), 0.05, places=5)
        self.assertIsNotNone(updated.area_ha)
        self.assertGreater(updated.area_ha, 0)

    @patch("wildfire_assessment.serializers.delete_polygon")
    @patch("wildfire_assessment.serializers.upload_polygon")
    def test_update_centroid_from_feature_collection(self, _mock_upload, _mock_delete):
        area = AreaOfInterest.objects.create(
            name="FC Update", polygon_path="old.geojson", country=self.country
        )
        request = self.factory.patch("/")
        request.user = self.user
        geojson = {
            "type": "FeatureCollection",
            "features": [
                {
                    "type": "Feature",
                    "geometry": {
                        "type": "Polygon",
                        "coordinates": [
                            [[0, 0], [0.1, 0], [0.1, 0.1], [0, 0.1], [0, 0]]
                        ],
                    },
                    "properties": {},
                }
            ],
        }
        serializer = AreaOfInterestUpdateSerializer(
            area,
            data={"geojson": geojson},
            partial=True,
            context={"request": request},
        )
        self.assertTrue(serializer.is_valid(), serializer.errors)
        updated = serializer.save()
        self.assertAlmostEqual(float(updated.centroid_lat), 0.05, places=5)

    @patch("wildfire_assessment.serializers.delete_polygon")
    @patch("wildfire_assessment.serializers.upload_polygon")
    def test_update_centroid_from_raw_geometry(self, _mock_upload, _mock_delete):
        area = AreaOfInterest.objects.create(
            name="Raw Update", polygon_path="old.geojson", country=self.country
        )
        request = self.factory.patch("/")
        request.user = self.user
        serializer = AreaOfInterestUpdateSerializer(
            area,
            data={"geojson": self.valid_polygon},
            partial=True,
            context={"request": request},
        )
        self.assertTrue(serializer.is_valid(), serializer.errors)
        updated = serializer.save()
        self.assertAlmostEqual(float(updated.centroid_lat), 0.05, places=5)

    @patch("wildfire_assessment.serializers.delete_polygon")
    @patch("wildfire_assessment.serializers.upload_polygon")
    def test_update_centroid_exception_silenced(self, _mock_upload, _mock_delete):
        area = AreaOfInterest.objects.create(
            name="Error Update", polygon_path="old.geojson", country=self.country
        )
        request = self.factory.patch("/")
        request.user = self.user
        serializer = AreaOfInterestUpdateSerializer(
            area,
            data={"geojson": self.valid_polygon},
            partial=True,
            context={"request": request},
        )
        self.assertTrue(serializer.is_valid(), serializer.errors)
        with patch(
            "wildfire_assessment.serializers.shape", side_effect=Exception("bad")
        ):
            updated = serializer.save()
        self.assertIsNone(updated.centroid_lat)

    def test_update_duplicate_name_rejected(self):
        AreaOfInterest.objects.create(
            name="Taken Name", polygon_path="taken.geojson", country=self.country
        )
        area = AreaOfInterest.objects.create(
            name="My Area", polygon_path="my.geojson", country=self.country
        )
        request = self.factory.patch("/")
        request.user = self.user
        serializer = AreaOfInterestUpdateSerializer(
            area,
            data={"name": "Taken Name"},
            partial=True,
            context={"request": request},
        )
        self.assertFalse(serializer.is_valid())
        self.assertIn("name", serializer.errors)

    def test_update_validate_country_no_request(self):
        """Test validate_country when no request context is provided."""
        area = AreaOfInterest.objects.create(
            name="No Req", polygon_path="noreq.geojson", country=self.country
        )
        serializer = AreaOfInterestUpdateSerializer(
            area,
            data={"name": "Updated No Req"},
            partial=True,
            context={},
        )
        self.assertTrue(serializer.is_valid(), serializer.errors)

    def test_update_fixes_winding_order(self):
        """UpdateSerializer also auto-corrects winding order."""
        area = AreaOfInterest.objects.create(
            name="Wind Area",
            polygon_path="wind.geojson",
            country=self.country,
        )
        request = self.factory.patch("/")
        request.user = self.user
        cw_ring = [[0, 0], [0, 0.1], [0.1, 0.1], [0.1, 0], [0, 0]]
        serializer = AreaOfInterestUpdateSerializer(
            area,
            data={
                "geojson": {"type": "Polygon", "coordinates": [cw_ring]},
            },
            partial=True,
            context={"request": request},
        )
        self.assertTrue(serializer.is_valid(), serializer.errors)
        result_ring = serializer.validated_data["geojson"]["coordinates"][0]
        self.assertNotEqual(
            [list(c) for c in result_ring],
            cw_ring,
        )


class NotificationSerializerTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="notifser", email="notifser@example.com", password="pw"
        )
        self.country = Country.objects.create(name="Ser Country", code="SC")
        self.area = AreaOfInterest.objects.create(
            name="Ser Area", polygon_path="ser.geojson", country=self.country
        )
        self.analysis = AnalysisRun.objects.create(
            user=self.user,
            area_of_interest=self.area,
            pre_fire_date="2024-01-01",
            post_fire_date="2024-01-15",
        )
        self.notification = Notification.objects.create(
            user=self.user,
            analysis_run=self.analysis,
            notification_type="deliverable_ready",
            deliverable_name="DNBR",
            message="DNBR for Ser Area is ready",
        )

    def test_contains_expected_fields(self):
        serializer = NotificationSerializer(self.notification)
        self.assertEqual(
            set(serializer.data.keys()),
            {
                "id",
                "notification_type",
                "deliverable_name",
                "message",
                "is_read",
                "analysis_run_id",
                "area_name",
                "created_at",
            },
        )

    def test_field_values(self):
        serializer = NotificationSerializer(self.notification)
        data = serializer.data
        self.assertEqual(data["notification_type"], "deliverable_ready")
        self.assertEqual(data["deliverable_name"], "DNBR")
        self.assertEqual(data["message"], "DNBR for Ser Area is ready")
        self.assertFalse(data["is_read"])
        self.assertEqual(data["analysis_run_id"], self.analysis.id)
        self.assertEqual(data["area_name"], "Ser Area")

    def test_analysis_run_id_null_when_no_analysis(self):
        notif = Notification.objects.create(
            user=self.user,
            notification_type="deliverable_ready",
            deliverable_name="RBR",
            message="Orphan notification",
        )
        serializer = NotificationSerializer(notif)
        self.assertIsNone(serializer.data["analysis_run_id"])
        self.assertEqual(serializer.data["area_name"], "")


class HelperFunctionTests(TestCase):
    """Tests for module-level helper functions extracted during DRY refactoring."""

    def test_generate_polygon_filename_sanitizes_name(self):
        filename = generate_polygon_filename("My Area (Test)")
        self.assertTrue(filename.endswith(".geojson"))
        self.assertNotIn(" ", filename)
        self.assertNotIn("(", filename)

    def test_generate_polygon_filename_unique(self):
        f1 = generate_polygon_filename("Area")
        f2 = generate_polygon_filename("Area")
        self.assertNotEqual(f1, f2)

    def test_compute_centroid_polygon(self):
        geojson = {
            "type": "Polygon",
            "coordinates": [[[0, 0], [0.1, 0], [0.1, 0.1], [0, 0.1], [0, 0]]],
        }
        result = compute_centroid(geojson)
        self.assertIsNotNone(result)
        lat, lng = result
        self.assertAlmostEqual(lat, 0.05, places=5)
        self.assertAlmostEqual(lng, 0.05, places=5)

    def test_compute_centroid_feature(self):
        geojson = {
            "type": "Feature",
            "geometry": {
                "type": "Polygon",
                "coordinates": [[[0, 0], [0.1, 0], [0.1, 0.1], [0, 0.1], [0, 0]]],
            },
            "properties": {},
        }
        result = compute_centroid(geojson)
        self.assertIsNotNone(result)

    def test_compute_centroid_feature_collection(self):
        geojson = {
            "type": "FeatureCollection",
            "features": [
                {
                    "type": "Feature",
                    "geometry": {
                        "type": "Polygon",
                        "coordinates": [
                            [[0, 0], [0.1, 0], [0.1, 0.1], [0, 0.1], [0, 0]]
                        ],
                    },
                    "properties": {},
                }
            ],
        }
        result = compute_centroid(geojson)
        self.assertIsNotNone(result)

    def test_compute_centroid_invalid_returns_none(self):
        result = compute_centroid({"type": "Invalid"})
        self.assertIsNone(result)

    def test_check_duplicate_area_name_found(self):
        country = Country.objects.create(name="Dup Country", code="DC")
        AreaOfInterest.objects.create(
            name="Dup Area", polygon_path="dup.geojson", country=country
        )
        self.assertTrue(check_duplicate_area_name("Dup Area", country))

    def test_check_duplicate_area_name_not_found(self):
        country = Country.objects.create(name="NoDup Country", code="ND")
        self.assertFalse(check_duplicate_area_name("New Area", country))

    def test_check_duplicate_area_name_excludes_instance(self):
        country = Country.objects.create(name="Excl Country", code="EC")
        area = AreaOfInterest.objects.create(
            name="Same Name", polygon_path="same.geojson", country=country
        )
        self.assertFalse(check_duplicate_area_name("Same Name", country, instance=area))

    def test_compute_area_ha_polygon(self):
        """compute_area_ha returns area in hectares for a Polygon."""
        geojson = {
            "type": "Polygon",
            "coordinates": [[[0, 0], [0.1, 0], [0.1, 0.1], [0, 0.1], [0, 0]]],
        }
        result = compute_area_ha(geojson)
        self.assertIsNotNone(result)
        self.assertGreater(result, 0)
        # ~0.1° × 0.1° at equator ≈ 12,300 ha
        self.assertAlmostEqual(result, 12_300, delta=500)

    def test_compute_area_ha_feature(self):
        """compute_area_ha works with Feature type."""
        geojson = {
            "type": "Feature",
            "geometry": {
                "type": "Polygon",
                "coordinates": [[[0, 0], [0.1, 0], [0.1, 0.1], [0, 0.1], [0, 0]]],
            },
            "properties": {},
        }
        result = compute_area_ha(geojson)
        self.assertIsNotNone(result)
        self.assertGreater(result, 0)

    def test_compute_area_ha_feature_collection(self):
        """compute_area_ha sums areas of all features."""
        geojson = {
            "type": "FeatureCollection",
            "features": [
                {
                    "type": "Feature",
                    "geometry": {
                        "type": "Polygon",
                        "coordinates": [
                            [[0, 0], [0.1, 0], [0.1, 0.1], [0, 0.1], [0, 0]]
                        ],
                    },
                    "properties": {},
                },
                {
                    "type": "Feature",
                    "geometry": {
                        "type": "Polygon",
                        "coordinates": [
                            [[1, 1], [1.1, 1], [1.1, 1.1], [1, 1.1], [1, 1]]
                        ],
                    },
                    "properties": {},
                },
            ],
        }
        result = compute_area_ha(geojson)
        self.assertIsNotNone(result)
        # Should be roughly double the single polygon area
        single = compute_area_ha(
            {
                "type": "Polygon",
                "coordinates": [[[0, 0], [0.1, 0], [0.1, 0.1], [0, 0.1], [0, 0]]],
            }
        )
        self.assertAlmostEqual(result, single * 2, delta=500)

    def test_compute_area_ha_invalid_returns_none(self):
        """compute_area_ha returns None on invalid input."""
        result = compute_area_ha({"type": "Invalid"})
        self.assertIsNone(result)

    def test_compute_area_ha_rounds_to_3_decimals(self):
        """compute_area_ha returns value rounded to 3 decimal places."""
        geojson = {
            "type": "Polygon",
            "coordinates": [[[0, 0], [0.1, 0], [0.1, 0.1], [0, 0.1], [0, 0]]],
        }
        result = compute_area_ha(geojson)
        # Check that it has at most 3 decimal places
        self.assertEqual(result, round(result, 3))


class ReportSummaryRequestSerializerTests(TestCase):
    def test_defaults_to_english(self):
        serializer = ReportSummaryRequestSerializer(data={})
        self.assertTrue(serializer.is_valid())
        self.assertEqual(serializer.validated_data["language"], "en")

    def test_accepts_language(self):
        serializer = ReportSummaryRequestSerializer(data={"language": "pt-BR"})
        self.assertTrue(serializer.is_valid())
        self.assertEqual(serializer.validated_data["language"], "pt-BR")


class AnalysisRunProvenanceSerializerTests(TestCase):
    """Tests for provenance serialization in AnalysisRunSerializer."""

    def setUp(self):
        self.user = User.objects.create_user(
            username="provseruser", email="provser@example.com", password="pw"
        )
        self.country = Country.objects.create(name="Prov Ser Country", code="PS")
        self.area = AreaOfInterest.objects.create(
            name="Prov Ser Area",
            polygon_path="provser.geojson",
            country=self.country,
        )
        self.run = AnalysisRun.objects.create(
            user=self.user,
            area_of_interest=self.area,
            pre_fire_date="2024-01-01",
            post_fire_date="2024-01-15",
        )

    def test_includes_provenance_field(self):
        """AnalysisRunSerializer includes provenance records."""
        AnalysisRunProvenance.objects.create(
            analysis_run=self.run,
            phase="pre_fire",
            scene_id="LC08_SER_001",
            date="2024-01-01",
            spacecraft_name="LANDSAT_8",
            cloud_percent=4.5,
        )
        AnalysisRunProvenance.objects.create(
            analysis_run=self.run,
            phase="post_fire",
            scene_id="S2A_SER_001",
            date="2024-01-20",
            spacecraft_name="SENTINEL_2A",
            cloud_percent=1.2,
        )
        data = AnalysisRunSerializer(self.run).data
        self.assertIn("provenance", data)
        self.assertEqual(len(data["provenance"]), 2)

    def test_provenance_record_fields(self):
        """Each provenance record has the expected fields."""
        AnalysisRunProvenance.objects.create(
            analysis_run=self.run,
            phase="pre_fire",
            scene_id="LC08_FIELDS_001",
            date="2024-01-01",
            spacecraft_name="LANDSAT_8",
            cloud_percent=7.3,
        )
        data = AnalysisRunSerializer(self.run).data
        record = data["provenance"][0]
        self.assertIn("id", record)
        self.assertEqual(record["phase"], "pre_fire")
        self.assertEqual(record["scene_id"], "LC08_FIELDS_001")
        self.assertEqual(record["date"], "2024-01-01")
        self.assertEqual(record["spacecraft_name"], "LANDSAT_8")
        self.assertAlmostEqual(float(record["cloud_percent"]), 7.3)

    def test_empty_provenance(self):
        """A run with no provenance records serializes as an empty list."""
        data = AnalysisRunSerializer(self.run).data
        self.assertIn("provenance", data)
        self.assertEqual(data["provenance"], [])

    def test_provenance_standalone_serializer(self):
        """AnalysisRunProvenanceSerializer serializes a single record correctly."""
        record = AnalysisRunProvenance.objects.create(
            analysis_run=self.run,
            phase="post_fire",
            scene_id="STANDALONE_001",
            date="2024-02-01",
            spacecraft_name=None,
            cloud_percent=None,
        )
        data = AnalysisRunProvenanceSerializer(record).data
        expected_fields = {
            "id",
            "phase",
            "scene_id",
            "date",
            "spacecraft_name",
            "cloud_percent",
        }
        self.assertEqual(set(data.keys()), expected_fields)
        self.assertEqual(data["phase"], "post_fire")
        self.assertEqual(data["scene_id"], "STANDALONE_001")
        self.assertIsNone(data["spacecraft_name"])
        self.assertIsNone(data["cloud_percent"])
