"""Tests for the register_ucs management command (UC seeding)."""

from unittest.mock import MagicMock, patch

from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase
from wildfire_assessment.models import AreaOfInterest, Country

SMALL_SQUARE = [
    [-47.0, -22.0],
    [-46.9, -22.0],
    [-46.9, -21.9],
    [-47.0, -21.9],
    [-47.0, -22.0],
]

SMALL_SQUARE_2 = [
    [-48.0, -23.0],
    [-47.9, -23.0],
    [-47.9, -22.9],
    [-48.0, -22.9],
    [-48.0, -23.0],
]

# A huge box (2 degrees square) — far above the 110,000 ha platform limit.
HUGE_BOX = [
    [-60.0, -30.0],
    [-58.0, -30.0],
    [-58.0, -28.0],
    [-60.0, -28.0],
    [-60.0, -30.0],
]


def feature(name, geometry, properties=None):
    props = {"Unidade": name}
    props.update(properties or {})
    return {"type": "Feature", "properties": props, "geometry": geometry}


def layer_response(features):
    response = MagicMock()
    response.json.return_value = {
        "type": "FeatureCollection",
        "features": features,
    }
    return response


PI_FEATURES = [
    feature(
        "Parque Estadual Test",
        {"type": "Polygon", "coordinates": [SMALL_SQUARE]},
    ),
    feature(
        "Sem Nome",
        {"type": "Polygon", "coordinates": [SMALL_SQUARE_2]},
        {"Unidade": None},
    ),
    feature("Sem Geometria", None),
]

US_FEATURES = [
    feature(
        "Estação Ecológica Test",
        {
            "type": "MultiPolygon",
            "coordinates": [[SMALL_SQUARE], [SMALL_SQUARE_2]],
        },
    ),
    feature(
        "APA Gigante Test",
        {"type": "Polygon", "coordinates": [HUGE_BOX]},
    ),
]


class RegisterUcsCommandTests(TestCase):
    def _mock_session(self, pi_features=None, us_features=None):
        session = MagicMock()
        responses = [
            layer_response(pi_features if pi_features is not None else PI_FEATURES),
            layer_response(us_features if us_features is not None else US_FEATURES),
        ]
        session.get.side_effect = responses
        return session

    def test_command_registers_units_and_skips_oversized(self):
        session = self._mock_session()
        with (
            patch(
                "wildfire_assessment.management.commands.register_ucs.requests.Session",
                return_value=session,
            ),
            patch(
                "wildfire_assessment.management.commands.register_ucs.upload_polygon"
            ) as mock_upload,
        ):
            call_command("register_ucs")

        brazil = Country.objects.get(code="BR")
        names = set(
            AreaOfInterest.objects.filter(country=brazil).values_list("name", flat=True)
        )
        self.assertEqual(
            names,
            {"Parque Estadual Test", "Estação Ecológica Test"},
        )
        self.assertEqual(mock_upload.call_count, 2)
        area = AreaOfInterest.objects.get(name="Parque Estadual Test")
        self.assertIsNotNone(area.polygon_path)
        self.assertIsNotNone(area.area_ha)
        self.assertIsNotNone(area.centroid_lat)
        self.assertIsNotNone(area.centroid_lng)

    def test_command_skips_existing_names(self):
        brazil, _ = Country.objects.get_or_create(name="Brazil", code="BR")
        AreaOfInterest.objects.create(
            name="Parque Estadual Test",
            country=brazil,
            polygon_path="existing.geojson",
        )
        session = self._mock_session()
        with (
            patch(
                "wildfire_assessment.management.commands.register_ucs.requests.Session",
                return_value=session,
            ),
            patch(
                "wildfire_assessment.management.commands.register_ucs.upload_polygon"
            ) as mock_upload,
        ):
            call_command("register_ucs")

        # Only the new UC is uploaded; the existing one keeps its old path.
        self.assertEqual(mock_upload.call_count, 1)
        existing = AreaOfInterest.objects.get(name="Parque Estadual Test")
        self.assertEqual(existing.polygon_path, "existing.geojson")

    def test_command_download_failure_raises(self):
        session = MagicMock()
        session.get.side_effect = [
            layer_response([]),
            MagicMock(
                raise_for_status=MagicMock(
                    side_effect=__import__("requests").RequestException("boom")
                )
            ),
        ]
        with patch(
            "wildfire_assessment.management.commands.register_ucs.requests.Session",
            return_value=session,
        ):
            with self.assertRaises(CommandError):
                call_command("register_ucs")
